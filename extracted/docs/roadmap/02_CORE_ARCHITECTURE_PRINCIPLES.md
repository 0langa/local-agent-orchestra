# 02 — CORE ARCHITECTURE PRINCIPLES
## Directory Structure, Runtime Invariants, and Subsystem Separation

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE
**Enforcement:** All code placement must conform to this structure.
**Violation Classification:** ARCHITECTURAL BREACH (Level 3)

---

## 1. Canonical Directory Structure

```
local-agent-orchestra/
|
+-- core/                          # GENERIC RUNTIME — no provider/workflow/tool specifics
|   +-- __init__.py
|   +-- workflow_runner.py         # DAG execution, retries, resumption
|   +-- agent_protocol.py          # Structured agent message schema, role resolution
|   +-- model_registry.py          # Capability-based model resolution
|   +-- provider_registry.py       # Lazy-loaded provider adapter registry
|   +-- tool_protocol.py           # Mediated tool invocation interface
|   +-- policy_engine.py           # Allow/deny/ask/boundary enforcement
|   +-- run_ledger.py              # Append-only run event log
|   +-- artifact_store.py          # Structured per-run artifact management
|   +-- capability_registry.py     # Discoverable provider/tool capability declarations
|   +-- context_packer.py          # Repository snapshot preparation for agents
|   +-- config_loader.py           # Configuration validation and loading
|   +-- error_classification.py    # Failure taxonomy and retry logic
|   +-- retry_engine.py            # Bounded retry with backoff strategies
|   +-- step_budget.py             # Token, time, and iteration budget enforcement
|   +-- phase_machine.py           # Runtime state machine transitions
|   +-- events.py                  # Event type definitions and validation
|   +-- schemas.py                 # Shared Pydantic/dataclass schemas
|   +-- types.py                   # Type definitions and protocols
|   +-- constants.py               # System-wide constants
|   +-- exceptions.py              # Core exception hierarchy
|   +-- logging_config.py          # Structured logging setup
|
+-- providers/                     # PROVIDER ADAPTERS — interchangeable, lazy-loaded
|   +-- __init__.py
|   +-- base.py                    # Abstract provider protocol
|   +-- openai_compatible/         # OpenAI-compatible REST adapter
|   |   +-- __init__.py
|   |   +-- adapter.py
|   |   +-- config.py
|   |   +-- models.py
|   |   +-- tests/
|   +-- azure/                     # Azure AI Foundry adapter
|   +-- oci/                       # Oracle Cloud Infrastructure adapter
|   +-- aws/                       # AWS Bedrock adapter
|   +-- anthropic/                 # Anthropic adapter
|   +-- google/                    # Google AI adapter
|   +-- ollama/                    # Ollama local model adapter
|   +-- lm_studio/                 # LM Studio adapter
|   +-- llama_cpp/                 # llama.cpp adapter
|   +-- vllm/                      # vLLM adapter
|   +-- openrouter/                # OpenRouter adapter
|   +-- mistral/                   # Mistral adapter
|   +-- groq/                      # Groq adapter
|   +-- registry_meta.py           # Provider metadata and import paths
|   +-- tests/
|
+-- tools/                          # TOOL ADAPTERS — mediated, policy-gated
|   +-- __init__.py
|   +-- base.py                     # Abstract tool protocol
|   +-- filesystem/                 # read, write, list, stat — path-bounded
|   +-- shell/                      # command execution with allowlist/denylist
|   +-- git/                        # clone, diff, commit, status
|   +-- http/                       # outbound HTTP with network policy enforcement
|   +-- mcp/                        # MCP server tool call bridge
|   +-- memory/                     # structured memory read/write
|   +-- browser/                    # optional web automation
|   +-- local_db/                   # optional local database access
|   +-- registry.py                 # Tool registration and discovery
|   +-- tests/
|
+-- workflows/                      # WORKFLOW PACKS — use-case-specific
|   +-- __init__.py
|   +-- base.py                     # Abstract workflow base class
|   +-- coding/                     # planner/executor/verifier/patcher/reporter
|   |   +-- __init__.py
|   |   +-- workflow.py
|   |   +-- agents.py
|   |   +-- prompts.py
|   |   +-- schemas.py
|   |   +-- policies.py
|   |   +-- verification.py
|   |   +-- tests/
|   +-- documents/                  # indexer/retriever/answerer/citer
|   +-- research/                   # gatherer/summarizer/comparator/reporter
|   +-- file_organization/          # analyzer/proposer/previewer/applier
|   +-- docs_maintenance/           # staleness_detector/updater/aligner
|   +-- github_maintenance/         # issue_summarizer/pr_reviewer/label_suggester
|   +-- command_assistant/          # intent_parser/command_generator/approver
|   +-- custom_workflow_builder/    # guided wizard to repeatable workflow
|   +-- tests/
|
+-- memory/                         # MEMORY SUBSYSTEM
|   +-- __init__.py
|   +-- base.py                     # Abstract memory protocol
|   +-- structured_memory.py        # Key-value project facts
|   +-- project_facts.py            # Persistent cross-run project knowledge
|   +-- run_history.py              # Searchable run event archive
|   +-- vector_retrieval.py         # Embedding-based semantic search (DEFERRED)
|   +-- context_bundles.py          # Pre-compiled context packages
|   +-- backends/                   # Pluggable memory backends
|   |   +-- jsonl/                  # Simple JSONL backend
|   |   +-- sqlite/                 # SQLite backend
|   |   +-- chroma/                 # Chroma vector backend (DEFERRED)
|   |   +-- qdrant/                 # Qdrant vector backend (DEFERRED)
|   +-- tests/
|
+-- interfaces/                     # USER INTERFACES
|   +-- cli/                        # Primary interface; always available
|   |   +-- __init__.py
|   |   +-- main.py                 # Entry point
|   |   +-- commands/               # CLI command modules
|   |   +-- presets.py              # Preset rendering and selection
|   |   +-- settings.py             # Configuration management
|   |   +-- formatting.py           # Terminal output formatting
|   |   +-- tests/
|   +-- guided_tui/                 # Terminal UI (DEFERRED)
|   +-- web_ui/                     # Web interface (RESERVED)
|   +-- desktop_ui/                 # Desktop interface (RESERVED)
|   +-- api_server/                 # API server (RESERVED)
|
+-- presets/                        # PRESET DEFINITIONS
|   +-- __init__.py
|   +-- base.py                     # Preset schema and base class
|   +-- codebase_assistant.py
|   +-- local_document_chat.py
|   +-- research_report.py
|   +-- file_organizer.py
|   +-- docs_maintainer.py
|   +-- github_maintainer.py
|   +-- command_assistant.py
|   +-- personal_workflow_builder.py
|   +-- tests/
|
+-- config/                         # DEFAULT CONFIGURATIONS
|   +-- default.yaml                # Default system configuration
|   +-- providers.yaml              # Provider template configurations
|   +-- policies.yaml               # Default policy rules
|   +-- presets.yaml                # Preset default values
|
+-- tests/                          # INTEGRATION TESTS
|   +-- integration/
|   +-- fixtures/
|   +-- conftest.py
|
+-- docs/                           # DOCUMENTATION
|   +-- roadmap/                    # THIS ROADMAP (immutable during phase)
|   +-- architecture/
|   +-- user_guide/
|   +-- developer_guide/
|   +-- api_reference/
|
+-- scripts/                        # UTILITY SCRIPTS
|   +-- doctor.py                   # System diagnostics
|   +-- verify_setup.py             # Installation verification
|
+-- pyproject.toml                  # Project metadata and dependencies
+-- README.md
+-- LICENSE
+-- CHANGELOG.md
```

---

## 2. The Core Invariant (Absolute)

> **No provider, model, agent role, workflow type, or tool category is hardcoded into the core runtime.**

The core runtime (`core/`) knows only:
- **Workflows** — as abstract DAGs with step sequences
- **Agents** — as entities that implement the agent protocol
- **Tools** — as mediated invocations through the tool protocol
- **Policies** — as allow/deny/ask/boundary decisions
- **Runs** — as event-sourced executions with artifact production
- **Models** — as capability-resolved logical bindings
- **Providers** — as lazy-loaded adapter instances

The core runtime does NOT know:
- That "Grok" exists
- That "coding" is a workflow type
- That "planner" is a common agent role
- That "filesystem" is a tool category
- That any specific model name exists

**Enforcement:** Any import from `providers/`, `workflows/`, or `tools/` into `core/` (except through protocol interfaces) is an architectural breach.

---

## 3. Subsystem Boundary Rules

### 3.1 Core → Provider Boundary
- Core imports: `providers.base.ProviderProtocol` only
- Core calls: Provider methods through the protocol interface
- Core stores: Provider configuration in the provider registry
- Core does NOT: Import provider implementations, reference provider names in logic

### 3.2 Core → Workflow Boundary
- Core imports: `workflows.base.Workflow` only
- Core calls: Workflow lifecycle methods (init, execute_step, verify, cleanup)
- Core stores: Workflow metadata in the capability registry
- Core does NOT: Reference workflow type names in logic, import workflow internals

### 3.3 Core → Tool Boundary
- Core imports: `tools.base.ToolProtocol` only
- Core calls: Tool.invoke() through the mediated protocol
- Core stores: Tool capability declarations in the capability registry
- Core does NOT: Import tool implementations, execute tools directly

### 3.4 Core → Memory Boundary
- Core imports: `memory.base.MemoryProtocol` only
- Core calls: Memory read/write through the protocol
- Core stores: Memory configuration in the config loader
- Core does NOT: Import memory backends directly

### 3.5 Interface → Core Boundary
- Interfaces import: Public APIs from `core/` only
- Interfaces call: Core workflow runner, config loader, artifact store
- Interfaces do NOT: Import core internals, modify core state directly, access ledgers directly

---

## 4. Extension Point Contracts

### 4.1 Provider Extension Contract
```python
class ProviderProtocol(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def capabilities(self) -> List[ModelCapability]: ...

    async def complete(self, messages: List[AgentMessage], 
                       model: str, **kwargs) -> ModelResponse: ...

    async def stream(self, messages: List[AgentMessage],
                     model: str, **kwargs) -> AsyncIterator[ModelChunk]: ...

    def health_check(self) -> ProviderHealth: ...
```

### 4.2 Tool Extension Contract
```python
class ToolProtocol(Protocol):
    @property
    def tool_id(self) -> str: ...

    @property
    def schema(self) -> ToolSchema: ...

    @property
    def risk_level(self) -> RiskLevel: ...

    async def invoke(self, params: Dict[str, Any], 
                     context: ToolContext) -> ToolResult: ...
```

### 4.3 Workflow Extension Contract
```python
class Workflow(ABC):
    @property
    @abstractmethod
    def workflow_id(self) -> str: ...

    @property
    @abstractmethod
    def required_agents(self) -> List[AgentRole]: ...

    @property
    @abstractmethod
    def required_tools(self) -> List[str]: ...

    @property
    @abstractmethod
    def dag(self) -> ExecutionDAG: ...

    @abstractmethod
    async def execute_step(self, step: Step, 
                          context: StepContext) -> StepResult: ...
```

### 4.4 Memory Extension Contract
```python
class MemoryProtocol(Protocol):
    @property
    def backend_id(self) -> str: ...

    async def read(self, key: str, scope: MemoryScope) -> Optional[MemoryEntry]: ...

    async def write(self, key: str, value: Any, 
                    scope: MemoryScope) -> None: ...

    async def search(self, query: str, scope: MemoryScope,
                     limit: int = 10) -> List[MemoryEntry]: ...
```

---

## 5. Import Rules (Enforced)

### 5.1 Allowed Imports
```
core/ → providers.base, tools.base, workflows.base, memory.base
core/ → core.* (internal)
providers/ → providers.base, core.types, core.schemas, core.exceptions
tools/ → tools.base, core.types, core.schemas, core.exceptions, core.policy_engine
workflows/ → workflows.base, core.types, core.schemas, core.exceptions
workflows/ → tools.registry (for capability discovery only)
memory/ → memory.base, core.types, core.schemas, core.exceptions
interfaces/ → core.public_api (only), presets.*, workflows.base
presets/ → core.public_api, workflows.*.workflow
```

### 5.2 Forbidden Imports
```
core/ → providers.*.adapter (concrete implementations)
core/ → tools.*.* (concrete implementations)
core/ → workflows.*.* (concrete implementations)
core/ → memory.backends.* (concrete implementations)
providers/ → core.workflow_runner, core.agent_protocol
tools/ → core.workflow_runner
workflows/ → core.provider_registry, core.model_registry
interfaces/ → core.* (internals — only public_api)
```

---

## 6. File Placement Enforcement

Any file added to the repository MUST be placed according to these rules:

| If the file implements... | It belongs in... |
|---------------------------|-----------------|
| Generic workflow execution | `core/` |
| Provider API integration | `providers/<name>/` |
| Tool functionality | `tools/<category>/` |
| Use-case workflow | `workflows/<name>/` |
| Memory storage/retrieval | `memory/` |
| User-facing command | `interfaces/cli/` |
| Preset definition | `presets/` |
| Default configuration | `config/` |
| Integration test | `tests/integration/` |
| Diagnostic script | `scripts/` |

Files placed in incorrect locations are architectural breaches.

---

*End of 02_CORE_ARCHITECTURE_PRINCIPLES.md*
