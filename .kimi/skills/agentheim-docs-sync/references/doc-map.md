# Architecture

> System design, module layout, runtime phases, and boundary rules for Agentheim.

---

## Table of Contents

- [System Overview](#system-overview)
- [Directory Layout](#directory-layout)
- [Core Runtime](#core-runtime)
- [Subsystems](#subsystems)
- [Runtime Phases](#runtime-phases)
- [Architectural Laws](#architectural-laws)
- [Boundary Rules](#boundary-rules)
- [Ownership Model](#ownership-model)

---

## System Overview

Agentheim is a **preset-driven, local-first AI automation platform** with a generic orchestration runtime at its core. The system is organized around three user layers — beginner, power-user, and developer — all served by the same extensible engine.

```
                    +------------------+
                    |   Beginner Layer  |
                    |  (Preset-driven)  |
                    +--------+---------+
                             | exposes
                    +--------v---------+
                    |  Power-User Layer |
                    | (Configurable)    |
                    +--------+---------+
                             | exposes
                    +--------v---------+
                    |   Developer Layer |
                    |  (Extensible)     |
                    +------------------+
                             |
                    +--------v---------+
                    |   Core Runtime    |
                    | (Generic Engine)  |
                    +------------------+
```

### Design Principles

- **Core ignorance** — `core/` knows no provider, model, workflow, or tool names
- **Local-first** — zero external services required; privacy modes enforced in code
- **Safety by default** — destructive ops require approval; policies are code, not prompts
- **Fully auditable** — every run produces an append-only event ledger
- **Provider-agnostic** — swap providers without code changes

---

## Directory Layout

```
agentheim/
│
├── core/                      # Generic runtime engine
│   ├── workflow_runner.py     # DAG execution, retries, resumption
│   ├── agent_protocol.py      # Agent message schemas
│   ├── model_registry.py      # Capability-based model resolution
│   ├── tool_protocol.py       # Mediated tool invocation interface
│   ├── policy_engine.py       # Allow/deny/ask enforcement
│   ├── ledger.py              # Append-only event log with hash chain
│   ├── artifact_store.py      # Per-run artifact management
│   ├── capability_registry.py # Provider/tool capability declarations
│   ├── context_packer.py      # Repository snapshot for agents
│   ├── events.py              # Structured event schema
│   ├── error_classification.py # Failure taxonomy
│   ├── retry_engine.py        # Bounded retry with backoff
│   ├── step_budget.py         # Token/time/iteration budgets
│   ├── cascading_router.py    # Model failover chains
│   ├── privacy_enforcer.py    # Privacy mode enforcement
│   ├── approval_workflow.py   # Approval gate management
│   ├── public_api.py          # Stable public interface
│   ├── resume.py              # Run replay and resumption
│   ├── run_executor.py        # Top-level run execution
│   ├── logging.py             # Logging setup
│   ├── errors.py              # Exception hierarchy
│   ├── schemas.py / schemas_runtime.py
│   └── state_machine.py       # Runtime phase machine
│
├── providers/                 # Lazy-loaded provider adapters
│   ├── base.py                # Abstract provider protocol
│   ├── openai_v1.py           # OpenAI-compatible adapter
│   ├── azure_foundry.py       # Azure AI Foundry adapter
│   ├── aws_bedrock.py         # AWS Bedrock adapter
│   └── oci_genai.py           # OCI GenAI adapter
│
├── tools/                     # Mediated, policy-gated tool implementations
│   ├── browser/               # Web automation (Playwright)
│   ├── mcp/                   # MCP server bridge
│   └── ...                    # Additional tool categories
│
├── workflows/                 # Workflow packs (use-case-specific)
│   ├── base.py                # Abstract workflow base
│   ├── coding/                # Planner/executor/verifier
│   ├── research/              # Gatherer/summarizer/reporter
│   ├── documents/             # Indexer/retriever/answerer
│   ├── file_organization/     # Analyzer/proposer/applier
│   ├── docs_maintenance/      # Detector/updater/aligner
│   ├── github_maintenance/    # Summarizer/drafter
│   └── command_assistant/     # Parser/generator
│
├── memory/                    # Three-tier memory system
│   ├── brain.py               # Unified orchestrator
│   ├── episodic.py            # Timeline-based memory
│   ├── semantic.py            # Concept graph memory
│   ├── embeddings.py          # Vector embedding engine
│   ├── bus.py                 # Cross-process memory bus
│   ├── registry.py            # Memory backend registry
│   └── tiers/                 # Working, global memory
│
├── interfaces/                # User-facing interfaces
│   ├── cli/                   # Command-line interface
│   ├── api_server/            # FastAPI REST server
│   ├── web_ui/                # Web dashboard
│   ├── desktop_ui/            # PyQt6/tkinter desktop app
│   └── guided_tui/            # Interactive terminal UI
│
├── presets/                   # Beginner-friendly preset definitions
│   ├── base.py
│   ├── codebase_assistant.py
│   ├── research_report.py
│   ├── local_document_chat.py
│   ├── file_organizer.py
│   ├── docs_maintainer.py
│   ├── github_maintainer.py
│   └── command_assistant.py
│
├── federation/                # Distributed agent coordination
├── marketplace/               # Plugin marketplace
├── multimodal/                # Vision model support
├── monitoring/                # Metrics and health reporting
├── config/                    # Configuration loading
├── tests/                     # Full test suite
├── docs/                      # Documentation (you are here)
├── scripts/                   # Tooling (directive checks, validation helpers, legacy checks)
└── skills/                    # Copilot agent skill definitions
```

---

## Core Runtime

The core runtime (`core/`) is the heart of the system. It is intentionally **generic** — it knows nothing about specific providers, workflows, tools, or models.

### Key Components

| Component | File | Responsibility |
|-----------|------|---------------|
| **WorkflowRunner** | `workflow_runner.py` | Executes DAGs in topological order, parallel groups, retry logic |
| **RunLedger** | `ledger.py` | Append-only event log with SHA-256 hash chain verification |
| **PolicyEngine** | `policy_engine.py` | Evaluates allow/deny/ask decisions for every tool call |
| **ToolRegistry** | `tool_protocol.py` | Mediates all tool invocations through the policy engine |
| **ModelRegistry** | `model_registry.py` | Resolves capability-based model bindings |
| **CapabilityRegistry** | `capability_registry.py` | Discovers and registers workflows, presets, and memory backends |
| **Event** | `events.py` | Structured event schema (20+ types) with UUID, sequence, hash |
| **ArtifactStore** | `artifact_store.py` | Produces and validates 15+ run artifacts |
| **ContextPacker** | `context_packer.py` | Prepares repository context for agent consumption |
| **RetryEngine** | `retry_engine.py` | Bounded retry with exponential backoff per error category |
| **StepBudgetEnforcer** | `step_budget.py` | Enforces token, time, and iteration budgets |
| **CascadingRouter** | `cascading_router.py` | Model failover with health tracking |
| **PrivacyEnforcer** | `privacy_enforcer.py` | Enforces privacy modes at the policy level |
| **ApprovalWorkflow** | `approval_workflow.py` | Manages approval gates with ledger events |

### Runtime Phases

Every run proceeds through these phases:

```
INIT → LOAD_CONFIG → PREPARE_WORKSPACE → SCAN_REPOSITORY →
BUILD_CONTEXT_PACK → PLAN → EXECUTE_TASK → BASIC_VERIFY →
VERIFY_TASK → FIX_LOOP → FINAL_VERIFY → FINAL_REPORT →
RESUME_AVAILABLE → DONE
```

Phases are managed by the state machine in `core/state_machine.py`.

---

## Subsystems

### Provider Layer (`providers/`)

Provider adapters are lazy-loaded and interchangeable. They implement the abstract `ModelProvider` protocol and are never imported eagerly — the registry loads them via `importlib` only when a configured model needs one.

**Current providers:**
- `openai_v1` — OpenAI and all OpenAI-compatible APIs (Grok, Ollama, LM Studio, etc.)
- `azure_foundry` — Azure AI Foundry / Azure OpenAI
- `aws_bedrock` — AWS Bedrock
- `oci_genai` — Oracle Cloud Infrastructure GenAI

### Tool Layer (`tools/`)

All tools are mediated through `ToolRegistry.invoke()`, which routes through the `PolicyEngine` for allow/deny/ask decisions. Tools declare their risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and the policy engine enforces approval thresholds.

**Notable tools:**
- **Browser tool** — Web automation via Playwright with session reuse
- **MCP bridge** — Connects to MCP servers at runtime
- **Filesystem, Shell, Git** — Standard developer tools (path-bounded)

### Workflow Layer (`workflows/`)

Workflow packs define agent roles, step DAGs, prompts, policies, and verification logic. They are self-contained and import from `core.public_api` only.

### Memory Layer (`memory/`)

Three-tier memory with multiple backends:
- **Working memory** — ephemeral, run-scoped
- **Episodic memory** — timeline-based, bounded growth, importance scoring
- **Semantic memory** — concept graph with deduplication

Backends: JSONL, SQLite, Vector (embeddings).

### Interface Layer (`interfaces/`)

Multiple interfaces all backed by the same core runtime:
- **CLI** (`interfaces/cli/`) — Primary user surface via `agentheim` command
- **API Server** (`interfaces/api_server/`) — FastAPI REST + WebSocket
- **Web UI** (`interfaces/web_ui/`) — Browser dashboard
- **Desktop UI** (`interfaces/desktop_ui/`) — PyQt6/tkinter wrapper
- **Guided TUI** (`interfaces/guided_tui/`) — Interactive prompt-based wizard

---

## Architectural Laws

The project is governed by **7 Immutable Laws** defined in the [Project Doctrine](../../../../.github/instructions/01-doctrine.md):

| # | Law | One-Line Rule |
|---|-----|---------------|
| 1 | **Core Ignorance** | `core/` knows NO provider, workflow, tool, or model names |
| 2 | **Pack Autonomy** | Workflow packs don't import providers or mutate core state |
| 3 | **Provider Swap** | All providers are lazy-loaded, interchangeable adapters |
| 4 | **Disclosure** | Beginner gets presets. Power-user gets config. Dev gets APIs. |
| 5 | **Event Truth** | All state from append-only ledger. No mutable run state. |
| 6 | **Local-First** | Zero external services by default. Privacy modes enforced. |
| 7 | **Safety Default** | All destructive ops require approval. Policies are code. |

---

## Boundary Rules

### Import Rules

| Module | May Import From | May NOT Import From |
|--------|----------------|-------------------|
| `core/` | `core.*`, `providers.base`, `tools.base`, `workflows.base`, `memory.base` | Any concrete implementation |
| `workflows/` | `core.public_api`, `workflows.base` | `core.*` internals, provider implementations |
| `providers/` | `providers.base`, `core.types` | Other provider adapters |
| `tools/` | `core.public_api`, `tools.base` | Other tool implementations |
| `interfaces/` | `core.public_api` ONLY | Any `core.*` internal module |

### Forbidden Patterns

- Provider-specific logic in `core/`
- Workflow-specific logic in `core/`
- Direct tool execution bypassing `tool_protocol`
- Mutable global state
- Importing concrete implementations into `core/`
- Skipping policy engine for tool calls
- Modifying ledger events after append

---

## Ownership Model

Every directory has an implied subsystem owner. Cross-boundary changes must explain the impact and preserve the rules in `.github/instructions/`.

| Directory | Owner |
|-----------|-------|
| `core/` | Runtime Team |
| `providers/` | Provider Team |
| `tools/` | Tool Team |
| `workflows/` | Workflow Team |
| `memory/` | Memory Team |
| `interfaces/` | Interface Team |
| `presets/` | Product Team |
| `config/` | Platform Team |
| `tests/` | Quality Team |
| `docs/` | Documentation Team |
| `.github/instructions/` | Project governance |
| `.github/agents/` | Agent definitions |

---

## See Also

- [Project Doctrine](../../../../.github/instructions/01-doctrine.md) — binding project laws
- [Forbidden Behaviors](../../../../.github/instructions/02-forbidden-behaviors.md) — hard rejection rules
- [Traceability](../../../../.github/instructions/03-traceability.md) — evidence and verification expectations
- [AICtx Integration Rules](../../../../.github/instructions/04-AICtx-integration.md) — integration-specific rules
- [AICtx Integration Contract](../../../../docs/adr/ADR-001-aictx-integration-contract.md) — integration contract
- [AICtx Module Map](../../../../agentheim/vendor/MODULE_MAP.md) — module ownership and adaptation state
