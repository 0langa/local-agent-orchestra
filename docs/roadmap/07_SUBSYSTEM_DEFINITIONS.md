# 07 — SUBSYSTEM DEFINITIONS
## Detailed Specifications for Core, Workflow Packs, Providers, Tools, Memory, and Interfaces

**Status:** DERIVED FROM 02_CORE_ARCHITECTURE_PRINCIPLES
**Enforcement:** All implementations must conform to these definitions.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. Core Runtime Subsystem

### 1.1 Purpose
The generic execution engine. All other subsystems depend on core. Core depends on nothing concrete.

### 1.2 Components

#### workflow_runner.py
- **Responsibility:** Execute workflow DAGs with retries, resumption, and parallel safety
- **Inputs:** Workflow instance, configuration, context pack
- **Outputs:** Run artifacts, ledger, final report
- **Dependencies:** phase_machine, agent_protocol, model_registry, tool_protocol, policy_engine, run_ledger, artifact_store, step_budget
- **Owner:** Runtime Team

#### agent_protocol.py
- **Responsibility:** Structured agent message schema, role resolution, message validation
- **Inputs:** Agent role, messages, tool definitions
- **Outputs:** Validated agent messages, role bindings
- **Dependencies:** model_registry, capability_registry
- **Owner:** Runtime Team

#### model_registry.py
- **Responsibility:** Capability-based model resolution from role requirements
- **Inputs:** Role requirement (e.g., "planner", capability="reasoning")
- **Outputs:** Resolved model binding (provider + model_id)
- **Dependencies:** provider_registry, capability_registry
- **Owner:** Provider Team

#### provider_registry.py
- **Responsibility:** Lazy-loaded provider adapter registry
- **Inputs:** Provider configuration
- **Outputs:** Provider adapter instances
- **Dependencies:** providers.registry_meta
- **Owner:** Provider Team

#### tool_protocol.py
- **Responsibility:** Mediated tool invocation interface
- **Inputs:** Tool call request, parameters, context
- **Outputs:** Tool result, policy decision
- **Dependencies:** policy_engine
- **Owner:** Tool Team

#### policy_engine.py
- **Responsibility:** Allow/deny/ask/boundary enforcement
- **Inputs:** Tool call, risk level, current configuration
- **Outputs:** Policy decision (allow/deny/ask + reason)
- **Dependencies:** config_loader
- **Owner:** Security Team

#### run_ledger.py
- **Responsibility:** Append-only run event log
- **Inputs:** Events from all subsystems
- **Outputs:** Ordered event stream, replay capability
- **Dependencies:** None (foundational)
- **Owner:** Runtime Team

#### artifact_store.py
- **Responsibility:** Structured per-run artifact management
- **Inputs:** Artifact data from workflow execution
- **Outputs:** Organized run directory with all artifacts
- **Dependencies:** run_ledger
- **Owner:** Runtime Team

#### capability_registry.py
- **Responsibility:** Discoverable provider/tool/workflow capability declarations
- **Inputs:** Registration calls from extensions
- **Outputs:** Capability queries and resolution
- **Dependencies:** None (foundational)
- **Owner:** Platform Team

#### Supporting Components
- **context_packer.py:** Repository snapshot preparation
- **config_loader.py:** Configuration validation and loading
- **error_classification.py:** Failure taxonomy and retry logic
- **retry_engine.py:** Bounded retry with backoff
- **step_budget.py:** Token/time/iteration budget enforcement
- **phase_machine.py:** Runtime state machine transitions
- **events.py:** Event type definitions
- **schemas.py:** Shared Pydantic/dataclass schemas
- **types.py:** Type definitions and protocols

### 1.3 Extension Points
Core provides extension through:
- Protocol interfaces (base classes)
- Registration functions (capability_registry)
- Configuration hooks (config_loader)
- Event subscribers (run_ledger)

---

## 2. Workflow Pack Subsystem

### 2.1 Purpose
Use-case-specific workflow definitions. Each workflow pack is a self-contained unit that defines agents, steps, policies, and artifacts for a specific automation domain.

### 2.2 Workflow Pack Structure

```
workflows/<name>/
    __init__.py              # Workflow registration
    workflow.py              # Workflow class extending workflows.base.Workflow
    agents.py                # Agent role definitions and prompt templates
    schemas.py               # Workflow-specific Pydantic schemas
    policies.py              # Workflow-specific policy rules
    verification.py          # Verification logic for this workflow
    prompts/                 # Prompt templates
        planner.md
        executor.md
        verifier.md
    tests/
        test_workflow.py
        test_agents.py
        test_verification.py
```

### 2.3 Workflow Pack Requirements
Every workflow pack MUST:
1. Extend `workflows.base.Workflow`
2. Declare `workflow_id`, `required_agents`, `required_tools`, `dag`
3. Implement `execute_step()`
4. Define verification logic
5. Declare output artifact types
6. Include test fixtures
7. Register with capability_registry on import

### 2.4 Workflow Pack Forbidden Behaviors
- Import provider implementations directly
- Mutate core runtime state
- Bypass policy engine
- Execute tools outside mediated protocol
- Hardcode model names (use capability-based resolution)
- Assume specific directory structures outside declared scope

### 2.5 Workflow Pack: Coding (Reference Implementation)

```python
class CodingWorkflow(Workflow):
    workflow_id = "coding"

    required_agents = [
        AgentRole(id="planner", capabilities=["reasoning"]),
        AgentRole(id="executor", capabilities=["code_generation", "tool_use"]),
        AgentRole(id="verifier", capabilities=["critique", "structured_output"]),
    ]

    required_tools = [
        "filesystem.read", "filesystem.write",
        "shell.execute", "git.status", "git.diff"
    ]

    dag = ExecutionDAG(
        steps=[
            Step(id="scan", agent="planner", type="context_scan"),
            Step(id="plan", agent="planner", type="plan_generation",
                 depends_on=["scan"]),
            Step(id="execute", agent="executor", type="code_execution",
                 depends_on=["plan"]),
            Step(id="verify", agent="verifier", type="verification",
                 depends_on=["execute"]),
            Step(id="fix", agent="executor", type="fix_application",
                 depends_on=["verify"], condition="verification_failed",
                 max_iterations=5),
            Step(id="report", agent="planner", type="report_generation",
                 depends_on=["verify"]),
        ]
    )
```

---

## 3. Provider Subsystem

### 3.1 Purpose
Provider-agnostic model access. Each provider is an interchangeable adapter.

### 3.2 Provider Structure

```
providers/<name>/
    __init__.py              # Provider registration and lazy loading
    adapter.py               # ProviderAdapter implementation
    config.py                # Provider-specific configuration schema
    models.py                # Model capability declarations
    tests/
        test_adapter.py
        test_config.py
```

### 3.3 Provider Requirements
Every provider MUST:
1. Implement `providers.base.ProviderProtocol`
2. Declare all supported models with capabilities
3. Implement `complete()` and optionally `stream()`
4. Implement `health_check()`
5. Declare required environment variables
6. Declare Python dependencies
7. Register with provider_registry on import
8. Be lazy-loaded (not imported at startup)

### 3.4 Lazy Loading Mechanism

```python
# providers/registry_meta.py
PROVIDER_METADATA = {
    "openai-compatible": {
        "module": "providers.openai_compatible",
        "class": "OpenAICompatibleProvider",
        "dependencies": ["openai"],
        "env_vars": ["OPENAI_API_KEY"],
    },
    # ...
}

# core/provider_registry.py
class ProviderRegistry:
    def get_provider(self, provider_id: str) -> ProviderProtocol:
        if provider_id not in self._loaded:
            meta = PROVIDER_METADATA[provider_id]
            module = importlib.import_module(meta["module"])
            cls = getattr(module, meta["class"])
            self._loaded[provider_id] = cls(self._config.get(provider_id, {}))
        return self._loaded[provider_id]
```

### 3.5 Provider Configuration Schema

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
models:
  - model_id: gpt-4o
    context_window: 128000
    supports_function_calling: true
    supports_structured_output: true
    cost_per_1k_input: 0.005
    cost_per_1k_output: 0.015
    specialties: ["reasoning", "coding", "long-context"]
```

---

## 4. Tool Subsystem

### 4.1 Purpose
Mediated tool invocation with policy gating. All side effects go through named, policy-checked tools.

### 4.2 Tool Categories

| Category | Tools | Risk Level |
|----------|-------|------------|
| filesystem | read, write, list, stat | Low (read) / Medium (write) |
| shell | execute | High |
| git | clone, diff, commit, status | Medium |
| http | request | High |
| mcp | tool_call | Depends on MCP tool |
| memory | read, write | Low |
| browser | navigate, extract | High |
| local_db | query | Medium |

### 4.3 Tool Structure

```python
class FilesystemReadTool(ToolProtocol):
    tool_id = "filesystem.read"
    schema = ToolSchema(
        description="Read a file from the filesystem",
        parameters={
            "path": {"type": "string", "description": "File path"},
            "max_size": {"type": "integer", "default": 100000},
        },
        risk_level=RiskLevel.NONE,
    )

    async def invoke(self, params: Dict[str, Any], 
                     context: ToolContext) -> ToolResult:
        # Path validation and confinement
        safe_path = self._validate_path(params["path"], context.allowed_paths)
        content = await self._read_file(safe_path, params.get("max_size"))
        return ToolResult(success=True, data={"content": content})
```

### 4.4 Tool Requirements
Every tool MUST:
1. Implement `tools.base.ToolProtocol`
2. Declare `tool_id`, `schema`, `risk_level`
3. Implement `invoke(params, context) -> ToolResult`
4. Validate all parameters before execution
5. Respect path/network/budget boundaries from context
6. Return structured results
7. Handle errors gracefully
8. Register with tool registry on import

---

## 5. Memory Subsystem

### 5.1 Purpose
Cross-run memory and context persistence. Three-tier memory model.

### 5.2 Memory Tiers

**Tier 1: Working Memory (Ephemeral)**
- Duration: Single run
- Contents: Active context pack, current plan, pending tasks, intermediate results
- Storage: In-memory during run, written to ledger

**Tier 2: Run Memory (Repository-Scoped)**
- Duration: Cross-run for a specific repository
- Contents: Previous plans, patterns, frequently modified files, test outcomes
- Storage: `.agent-arena/memory/` within the repo

**Tier 3: Global Memory (Cross-Repository)**
- Duration: Cross-project
- Contents: User preferences, coding style, model performance profiles
- Storage: `~/.agent-arena/global-memory/`

### 5.3 Memory Types

| Type | Description | Implementation |
|------|-------------|---------------|
| Structured Memory | Key-value project facts | JSON/JSONL files |
| Project Facts | Persistent cross-run knowledge | SQLite backend |
| Run History | Searchable run event archive | Ledger files |
| Vector Retrieval | Semantic search (DEFERRED) | Chroma/Qdrant |
| Context Bundles | Pre-compiled context packages | Generated per-run |

### 5.4 Memory Backend Protocol

```python
class MemoryBackend(Protocol):
    @property
    def backend_id(self) -> str: ...

    async def read(self, key: str, scope: MemoryScope) -> Optional[MemoryEntry]: ...
    async def write(self, key: str, value: Any, scope: MemoryScope) -> None: ...
    async def search(self, query: str, scope: MemoryScope, 
                     limit: int = 10) -> List[MemoryEntry]: ...
    async def delete(self, key: str, scope: MemoryScope) -> None: ...
    async def list_keys(self, scope: MemoryScope, 
                        prefix: str = "") -> List[str]: ...
```

---

## 6. Interface Subsystem

### 6.1 Purpose
User-facing interaction layers. All interfaces are thin wrappers over the core runtime.

### 6.2 CLI Interface (Primary)

**Entry point:** `agent-arena [command] [options]`

**Beginner commands:**
```
agent-arena run                    # Launch preset picker
agent-arena run --preset coding    # Run coding preset
agent-arena run --preset organize  # Run file organizer
```

**Power-user commands:**
```
agent-arena run --preset coding   --model-planner claude-sonnet   --model-executor local-qwen   --privacy local-preferred   --approval risk-based   --folder ./my-project
```

**Developer commands:**
```
agent-arena doctor                 # System diagnostics
agent-arena verify-setup         # Verify installation
agent-arena list-providers       # Show available providers
agent-arena list-models          # Show available models
agent-arena list-workflows       # Show available workflows
agent-arena config get/set       # Configuration management
```

### 6.3 Interface Requirements
- All interfaces call only `core.public_api`
- No interface may bypass the core runtime
- Interfaces handle user input validation
- Interfaces format core output for human consumption
- Interfaces are responsible for approval prompt rendering

---

*End of 07_SUBSYSTEM_DEFINITIONS.md*
