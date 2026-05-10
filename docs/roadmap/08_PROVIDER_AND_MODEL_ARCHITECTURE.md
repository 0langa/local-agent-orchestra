# 08 — PROVIDER AND MODEL ARCHITECTURE
## Lazy Loading, Capability-Based Routing, and Provider Registry

**Status:** DERIVED FROM 02_CORE_ARCHITECTURE_PRINCIPLES
**Enforcement:** All provider implementations must conform.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. Provider as Configuration Object

### 1.1 Principle
Providers are lazy-loaded configuration objects, not first-class framework citizens. The core runtime does not know which providers exist until runtime configuration is loaded.

### 1.2 Provider Configuration Schema

```yaml
id: my-openai-compatible
type: openai-compatible
base_url: https://api.example.com/v1
api_key_env: MY_API_KEY
timeout: 30
headers:
  X-Custom-Header: value
options:
  max_retries: 3
  max_connections: 10
models:
  - model_id: gpt-4o
    context_window: 128000
    supports_function_calling: true
    supports_structured_output: true
    cost_per_1k_input: 0.005
    cost_per_1k_output: 0.015
    latency_profile:
      ttfb_ms: 500
      tokens_per_second: 50
    specialties: ["reasoning", "coding", "long-context"]
    fallback_chain: ["gpt-4o-mini", "claude-sonnet"]
```

### 1.3 Provider Metadata Registry

The `providers/registry_meta.py` file contains metadata for all known providers. This metadata is used for lazy loading and dependency management.

```python
PROVIDER_METADATA: Dict[str, ProviderMeta] = {
    "openai-compatible": ProviderMeta(
        module="providers.openai_compatible",
        class_name="OpenAICompatibleProvider",
        pip_dependencies=["openai>=1.0"],
        optional_dependencies=["tiktoken"],
        env_vars=["OPENAI_API_KEY"],
        default_base_url="https://api.openai.com/v1",
    ),
    "ollama": ProviderMeta(
        module="providers.ollama",
        class_name="OllamaProvider",
        pip_dependencies=["aiohttp"],
        optional_dependencies=[],
        env_vars=["OLLAMA_HOST"],
        default_base_url="http://localhost:11434",
    ),
    # ... additional providers
}
```

---

## 2. Lazy Provider Loading

### 2.1 Principle
Provider classes must not be imported at startup. The provider registry stores import paths; a provider class is loaded only when that provider is configured and invoked.

### 2.2 Lazy Loading Implementation

```python
class ProviderRegistry:
    def __init__(self, config: ProviderConfig):
        self._config = config
        self._loaded: Dict[str, ProviderProtocol] = {}
        self._import_paths: Dict[str, str] = {}

        # Only store import paths, no actual imports
        for provider_id, meta in PROVIDER_METADATA.items():
            self._import_paths[provider_id] = f"{meta.module}:{meta.class_name}"

    def get_provider(self, provider_id: str) -> ProviderProtocol:
        if provider_id not in self._loaded:
            if provider_id not in self._import_paths:
                raise UnknownProviderError(f"Unknown provider: {provider_id}")

            module_path, class_name = self._import_paths[provider_id].split(":")
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)

            provider_config = self._config.get(provider_id, {})
            self._loaded[provider_id] = cls(provider_config)

        return self._loaded[provider_id]

    def list_available(self) -> List[str]:
        # Return providers that can be loaded (deps satisfied)
        available = []
        for pid, meta in PROVIDER_METADATA.items():
            if self._deps_satisfied(meta.pip_dependencies):
                available.append(pid)
        return available

    def list_configured(self) -> List[str]:
        # Return providers with valid configuration
        return list(self._config.keys())
```

### 2.3 Benefits of Lazy Loading
- Users with only Ollama do not require AWS/OCI/Anthropic dependencies
- Provider availability is checked at runtime from config, not from import-time presence
- Future providers are addable without increasing baseline startup cost
- Startup time is minimized

---

## 3. Model as Logical Role Binding

### 3.1 Principle
Models are bound to logical roles or capability requirements, not hardcoded names. A workflow asks for capabilities; the registry resolves them to configured models.

### 3.2 Logical Roles

| Role | Required Capabilities | Typical Model Class |
|------|----------------------|-------------------|
| planner | reasoning, instruction-following | Reasoning-heavy |
| executor | code-generation, tool-use | Code-optimized |
| verifier | critique, structured-output | Fast/cheap |
| summarizer | compression, extraction | Fast/cheap |
| classifier | labeling, routing | Fast/cheap |
| embedder | embedding | Specialized |
| critic | evaluation | Reasoning-heavy |
| vision | image-understanding | Vision-capable |
| local-fast | low-latency, offline | Local model |
| remote-strong | high-accuracy | Frontier model |

### 3.3 Capability Resolution Flow

```
1. Workflow declares: role=planner, capabilities=[reasoning, long-context]
   |
   v
2. ModelRegistry queries: Which configured models match these capabilities?
   |
   v
3. ProviderRegistry checks: Which providers are available and configured?
   |
   v
4. Resolution: provider=openai-compatible, model=gpt-4o
   |
   v
5. Execution: AgentProtocol formats prompt for resolved model
   |
   v
6. ProviderAdapter sends request, receives response
   |
   v
7. Response validated and returned to workflow
```

### 3.4 Model Resolution Algorithm

```python
class ModelRegistry:
    def resolve(self, role: str, required_capabilities: List[str],
                preferences: Optional[ModelPreferences] = None) -> ModelBinding:
        candidates = []

        for provider_id, provider in self._registry.list_available_providers():
            for model in provider.list_models():
                if self._matches_capabilities(model, required_capabilities):
                    score = self._score_model(model, role, preferences)
                    candidates.append((score, provider_id, model))

        if not candidates:
            raise NoMatchingModelError(
                f"No model matches role={role}, capabilities={required_capabilities}"
            )

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, provider_id, model = candidates[0]

        return ModelBinding(
            provider_id=provider_id,
            model_id=model.model_id,
            role=role,
        )

    def _score_model(self, model: ModelCapability, role: str,
                     preferences: Optional[ModelPreferences]) -> float:
        score = 0.0

        # Specialty match
        if role in model.specialties:
            score += 10.0

        # Cost preference
        if preferences and preferences.cost_preference == "low":
            score -= model.estimated_cost_per_1k * 100

        # Latency preference
        if preferences and preferences.latency_preference == "low":
            score += 5.0 / (model.latency_profile.ttfb_ms / 100)

        # Local preference
        if preferences and preferences.local_only and not model.is_local:
            score -= 1000.0  # Heavy penalty

        return score
```

---

## 4. Routing Strategies

### 4.1 Cascading Router (Default)
Attempt the cheapest capable model first. Escalate on failure.

```
Request → Filter by capability → Sort by cost → Try cheapest
  |                                        |
  v                                        v
Success ← Retry with next cheapest ← Failure
```

### 4.2 Capability-Based Router
Classify task complexity before routing.

| Task Class | Model Selection | Rationale |
|------------|----------------|-----------|
| Simple refactor | Local model or mini | Low complexity |
| New feature | Code-optimized | Generation required |
| Complex architecture | Reasoning model | Planning required |
| Verification | Fast/cheap | Simple evaluation |
| Research | Long-context | Large input required |

### 4.3 Fallback Chains
Each model declares a fallback chain. If primary fails, automatically failover.

```yaml
models:
  - model_id: gpt-4o
    fallback_chain: ["gpt-4o-mini", "claude-sonnet", "local-qwen-32b"]
```

### 4.4 Local Model Fallback
Maintain a cold standby local model for zero-dependency operation during outages.

| Local Platform | Recommended Model | Use Case |
|----------------|------------------|----------|
| Ollama | qwen3-coder:32b | General coding |
| Ollama | llama3.1:70b | General purpose |
| LM Studio | Any GGUF | GUI-friendly |
| vLLM | Qwen3-32B-AWQ | High-throughput |

---

## 5. Provider Health Monitoring

### 5.1 Health Checks
Each provider implements health_check() returning:

```python
class ProviderHealth:
    status: Literal["healthy", "degraded", "unavailable"]
    latency_ms: float
    rate_limit_remaining: Optional[int]
    last_error: Optional[str]
    models_available: List[str]
```

### 5.2 Health Check Schedule
- Check before first use in a run
- Re-check after any provider error
- Re-check when switching models
- Cache health status for 60 seconds

### 5.3 Auto-Failover
1. Provider returns error → Mark degraded
2. Retry with same provider (bounded)
3. Still failing → Switch to fallback in chain
4. Log provider failure in ledger
5. Report provider issue in final artifacts

---

## 6. Provider Implementation Checklist

A valid provider adapter must implement:

- [ ] ProviderProtocol interface
- [ ] complete() method with message formatting
- [ ] stream() method for streaming responses
- [ ] health_check() method
- [ ] Configuration schema validation
- [ ] Environment variable handling
- [ ] Error classification (transient vs. permanent)
- [ ] Token counting (input/output)
- [ ] Rate limit handling
- [ ] Timeout handling
- [ ] Structured output support (if applicable)
- [ ] Function calling support (if applicable)
- [ ] Registration with capability_registry
- [ ] Unit tests with mocked HTTP layer
- [ ] Integration tests with real provider (optional, skipped in CI)

---

*End of 08_PROVIDER_AND_MODEL_ARCHITECTURE.md*
