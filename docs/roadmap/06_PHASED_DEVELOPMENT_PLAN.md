# 06 — PHASED DEVELOPMENT PLAN
## Strict Phase Gates, Dependency Ordering, Implementation Prerequisites

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE
**Enforcement:** No agent may implement systems from a phase not yet unlocked.
**Violation Classification:** ARCHITECTURAL BREACH (Level 3)

---

## 1. Phase Overview

The project proceeds through six strictly ordered phases. Each phase unlocks specific subsystems for implementation. Agents may NOT implement subsystems from future phases.

```
PHASE 0: FOUNDATION (Cleanup & Invariants)
    |
    v
PHASE 1: CORE RUNTIME (Generic Engine)
    |
    v
PHASE 2: FIRST WORKFLOW PACK (Coding Workflow)
    |
    v
PHASE 3: TOOL & SAFETY SYSTEM (Mediated Tools + Policy)
    |
    v
PHASE 4: PRESET SYSTEM & CLI (User Surface)
    |
    v
PHASE 5: EXPANSION (Additional Workflows, Providers, Memory)
    |
    v
PHASE 6: ADVANCED SYSTEMS (MCP, UI, Distributed) — RESERVED
```

---

## 2. Phase 0: FOUNDATION

### 2.1 Objective
Clean the existing codebase, enforce architectural invariants, and establish the core directory structure. Nothing new is built in this phase. Existing code is refactored to conform.

### 2.2 Entry Criteria
- Repository exists with basic multi-agent code
- Provider-specific code exists in core
- Coding-specific logic exists in core
- Basic orchestrator/coder/verifier flow works (but not as a workflow pack)

### 2.3 Deliverables

| Deliverable | Owner | Acceptance Criteria |
|-------------|-------|-------------------|
| Directory structure matches 02_CORE_ARCHITECTURE_PRINCIPLES | Architecture Lead | `tree` output matches canonical structure |
| `core/` contains only generic code | Runtime Team | No provider/workflow/tool specifics in `core/` |
| `providers/` contains all provider adapters | Provider Team | All existing providers moved to `providers/<name>/` |
| `workflows/coding/` exists as first workflow pack | Workflow Team | Coding flow is a workflow pack, not core logic |
| `tools/` has base protocol and registry | Tool Team | Tool protocol defined, existing tools migrated |
| Import rules enforced | Architecture Lead | Import linting passes for all modules |
| CI pipeline enforces architecture | Platform Team | CI fails on architectural boundary violations |

### 2.4 Implementation Order

```
1. Fix workflows/base.py create_provider API mismatch
2. Fix cross-platform patch path normalization (Windows backslash)
3. Make ModelRegistry loop over configured models generically
4. Remove legacy Grok path or map to proper capabilities
5. Remove Grok defaults/docs/examples
6. Add lazy provider imports
7. Establish canonical directory structure
8. Migrate existing providers to providers/
9. Extract coding flow to workflows/coding/
10. Define core/ generic interfaces
11. Implement import linting
12. Set up CI architecture enforcement
```

### 2.5 Explicitly NOT in Phase 0
- New providers
- New workflow packs
- New tools
- MCP integration
- Memory system
- Preset system
- TUI/GUI
- Vector DB
- Deep memory
- Plugin marketplace
- Distributed workers

### 2.6 Exit Gate
**GATE 0.1:** All provider-specific logic removed from `core/`
**GATE 0.2:** All workflow-specific logic removed from `core/`
**GATE 0.3:** Directory structure matches canonical specification
**GATE 0.4:** CI enforces architectural boundaries
**GATE 0.5:** Import linting passes on all modules
**GATE 0.6:** ModelRegistry is fully generic

---

## 3. Phase 1: CORE RUNTIME

### 3.1 Objective
Build the generic execution engine that powers all workflow packs. The core runtime is the foundation upon which everything else is built.

### 3.2 Entry Criteria
- Phase 0 exit gates ALL passed
- Clean directory structure
- No provider/workflow/tool specifics in `core/`

### 3.3 Unlocked Subsystems
- `core/workflow_runner.py` — Generic DAG execution
- `core/agent_protocol.py` — Agent message schemas
- `core/model_registry.py` — Capability-based model resolution
- `core/provider_registry.py` — Lazy-loaded provider registry
- `core/tool_protocol.py` — Mediated tool invocation
- `core/policy_engine.py` — Policy enforcement
- `core/run_ledger.py` — Event-sourced ledger
- `core/artifact_store.py` — Artifact management
- `core/capability_registry.py` — Capability discovery
- `core/context_packer.py` — Context compilation
- `core/config_loader.py` — Configuration management
- `core/error_classification.py` — Failure taxonomy
- `core/retry_engine.py` — Bounded retry logic
- `core/step_budget.py` — Budget enforcement
- `core/phase_machine.py` — Runtime state machine
- `core/events.py` — Event type definitions

### 3.4 Deliverables

| Deliverable | Owner | Prerequisites | Exit Criteria |
|-------------|-------|--------------|---------------|
| Workflow runner with DAG execution | Runtime Team | Phase 0 | DAG execution with retries and resumption |
| Agent protocol with message schemas | Runtime Team | Phase 0 | Structured messages, role resolution |
| Model registry with capability resolution | Provider Team | Phase 0 | Role→model resolution via capability matching |
| Provider registry with lazy loading | Provider Team | Phase 0 | Providers loaded only when configured |
| Tool protocol with mediated invocation | Tool Team | Phase 0 | All tool calls go through protocol |
| Policy engine with decision types | Security Team | Phase 0 | allow/deny/ask/boundary/budget decisions |
| Run ledger with append-only events | Runtime Team | Phase 0 | Event log, replay capability, tamper evidence |
| Artifact store with structured output | Runtime Team | Phase 0 | Per-run artifact directory with schema |
| Capability registry | Platform Team | Phase 0 | Registration and discovery of all extensions |
| Context packer | Runtime Team | Phase 0 | Repository snapshot preparation |
| Config loader with validation | Platform Team | Phase 0 | YAML config loading with schema validation |
| Error classification | Runtime Team | Phase 0 | Failure taxonomy with retry strategies |
| Retry engine | Runtime Team | Phase 0 | Bounded retry with backoff |
| Step budget enforcement | Runtime Team | Phase 0 | Budget checking before every agent/tool call |
| Phase machine | Runtime Team | Phase 0 | All 14 phases with deterministic transitions |
| Event system | Runtime Team | Phase 0 | All event types with validation |

### 3.5 Implementation Order

```
1. Event system (events.py, schemas)
2. Phase machine (phase_machine.py)
3. Config loader (config_loader.py)
4. Error classification (error_classification.py)
5. Retry engine (retry_engine.py)
6. Step budget (step_budget.py)
7. Agent protocol (agent_protocol.py)
8. Tool protocol (tool_protocol.py)
9. Policy engine (policy_engine.py)
10. Provider registry (provider_registry.py)
11. Model registry (model_registry.py)
12. Capability registry (capability_registry.py)
13. Run ledger (run_ledger.py)
14. Artifact store (artifact_store.py)
15. Context packer (context_packer.py)
16. Workflow runner (workflow_runner.py)
```

### 3.6 Explicitly NOT in Phase 1
- Any workflow pack implementation
- Any concrete tool implementation (beyond protocol)
- Any concrete provider implementation (beyond base)
- Any memory system
- CLI interface
- Preset system
- MCP integration
- TUI/GUI

### 3.7 Exit Gate
**GATE 1.1:** All core subsystems have unit tests with >80% coverage
**GATE 1.2:** Integration tests pass for all core subsystem interactions
**GATE 1.3:** Phase machine executes full lifecycle without errors
**GATE 1.4:** Ledger replay produces identical state
**GATE 1.5:** Policy engine correctly evaluates all decision types
**GATE 1.6:** Provider registry lazy-loads without eager imports
**GATE 1.7:** Model registry resolves capabilities correctly
**GATE 1.8:** Budget enforcement halts runs cleanly on exhaustion

---

## 4. Phase 2: FIRST WORKFLOW PACK

### 4.1 Objective
Implement the coding workflow as the first workflow pack. Validate that the core runtime is genuinely generic by building a complete workflow on top of it.

### 4.2 Entry Criteria
- ALL Phase 1 exit gates passed
- Core runtime is complete and tested
- Workflow base class is defined

### 4.3 Unlocked Subsystems
- `workflows/coding/` — Coding workflow pack
- `workflows/base.py` — Base workflow class (refined)
- Concrete integration between core and workflow pack

### 4.4 Deliverables

| Deliverable | Owner | Prerequisites | Exit Criteria |
|-------------|-------|--------------|---------------|
| Coding workflow definition | Workflow Team | Phase 1 | Full workflow with agents, steps, policies |
| Orchestrator agent | Workflow Team | Phase 1 | Planning agent with structured output |
| Executor agent | Workflow Team | Phase 1 | Code generation agent |
| Verifier agent | Workflow Team | Phase 1 | Verification agent with test execution |
| Patching logic | Workflow Team | Phase 1 | File modification with diff generation |
| Test execution | Workflow Team | Phase 1 | Run tests, capture results |
| Report generation | Workflow Team | Phase 1 | Final report artifact |
| Workflow-level policies | Workflow Team | Phase 1 | Coding-specific policy rules |
| Verification logic | Workflow Team | Phase 1 | Pass/fail criteria for code changes |

### 4.5 Implementation Order

```
1. Refine workflows/base.py with real integration points
2. Define coding workflow DAG
3. Implement orchestrator agent
4. Implement executor agent
5. Implement verifier agent
6. Implement patching logic
7. Integrate test execution
8. Implement report generation
9. Define workflow-specific policies
10. End-to-end coding workflow test
```

### 4.6 Explicitly NOT in Phase 2
- Other workflow packs (documents, research, etc.)
- Preset system
- CLI (basic test harness only)
- New providers
- New tools (beyond what coding needs)
- Memory system
- MCP

### 4.7 Exit Gate
**GATE 2.1:** Coding workflow executes end-to-end without core modifications
**GATE 2.2:** Workflow uses only public core APIs
**GATE 2.3:** All workflow artifacts generated correctly
**GATE 2.4:** Policy engine enforces workflow-specific policies
**GATE 2.5:** Verifier correctly evaluates code changes
**GATE 2.6:** Run is fully replayable from ledger
**GATE 2.7:** Core has zero code changes due to workflow integration

---

## 5. Phase 3: TOOL & SAFETY SYSTEM

### 5.1 Objective
Implement the complete tool system with mediated invocation, safety policies, and approval workflows.

### 5.2 Entry Criteria
- ALL Phase 2 exit gates passed
- Coding workflow works end-to-end
- Tool protocol is defined (from Phase 1)

### 5.3 Unlocked Subsystems
- `tools/filesystem/` — File operations with path bounding
- `tools/shell/` — Command execution with allowlist/denylist
- `tools/git/` — Git operations
- `tools/http/` — Outbound HTTP with network policy
- `tools/memory/` — Structured memory read/write
- Safety policies for all tools
- Approval workflow implementation

### 5.4 Deliverables

| Deliverable | Owner | Prerequisites | Exit Criteria |
|-------------|-------|--------------|---------------|
| Filesystem tool | Tool Team | Phase 2 | Read, write, list, stat with path boundaries |
| Shell tool | Tool Team | Phase 2 | Execute with allowlist/denylist |
| Git tool | Tool Team | Phase 2 | Clone, diff, commit, status |
| HTTP tool | Tool Team | Phase 2 | Request with network policy enforcement |
| Memory tool | Tool Team | Phase 2 | Read/write structured memory |
| Tool registry | Tool Team | Phase 2 | Registration and discovery |
| Approval workflow | Security Team | Phase 2 | Ask/approve/deny UI flow |
| Risk classification | Security Team | Phase 2 | None/Low/Medium/High/Critical levels |
| Path confinement | Security Team | Phase 2 | Filesystem scoped to declared boundaries |
| Network confinement | Security Team | Phase 2 | No network by default, policy-gated |
| Secret redaction | Security Team | Phase 2 | Secrets removed from all logs/artifacts |

### 5.5 Implementation Order

```
1. Tool registry implementation
2. Filesystem tool with path bounding
3. Shell tool with command classification
4. Git tool integration
5. HTTP tool with network policy
6. Memory tool (basic, no vector)
7. Risk classification system
8. Approval workflow (CLI-based)
9. Secret redaction in context packer
10. Integration tests for all tools
```

### 5.6 Explicitly NOT in Phase 3
- MCP integration
- Browser tool
- Local DB tool
- Vector-based memory
- Advanced monitoring (eBPF/ETW)

### 5.7 Exit Gate
**GATE 3.1:** All tools pass through policy engine
**GATE 3.2:** Path confinement prevents directory escape
**GATE 3.3:** Shell command classification works correctly
**GATE 3.4:** Approval workflow functions for all risk levels
**GATE 3.5:** Secret redaction removes sensitive data from artifacts
**GATE 3.6:** Network policy blocks unauthorized outbound requests
**GATE 3.7:** Tool registry discovers and registers all tools

---

## 6. Phase 4: PRESET SYSTEM & CLI

### 4.1 Objective
Build the user-facing surface: presets that hide complexity and a CLI that serves all three user layers.

### 4.2 Entry Criteria
- ALL Phase 3 exit gates passed
- Tool system complete
- Safety system functional

### 4.3 Unlocked Subsystems
- `presets/` — All preset definitions
- `interfaces/cli/` — Full CLI implementation
- `config/` — Default configurations
- `scripts/doctor.py` — Diagnostics

### 4.4 Deliverables

| Deliverable | Owner | Prerequisites | Exit Criteria |
|-------------|-------|--------------|---------------|
| Preset base class | Product Team | Phase 3 | Schema, validation, defaults |
| Codebase Assistant preset | Product Team | Phase 3 | Inspect → plan → patch → test → report |
| Local Document Chat preset | Product Team | Phase 3 | Index → answer → cite |
| Research Report preset | Product Team | Phase 3 | Gather → summarize → compare → report |
| File Organizer preset | Product Team | Phase 3 | Analyze → propose → preview → apply |
| CLI with preset picker | Interface Team | Phase 3 | Guided preset selection |
| CLI with power-user flags | Interface Team | Phase 3 | Model, privacy, approval overrides |
| Doctor command | Platform Team | Phase 3 | System diagnostics and verification |
| Default configuration | Platform Team | Phase 3 | Sensible defaults for all settings |
| Beginner-friendly output | Interface Team | Phase 3 | Plain language, progress indicators |

### 4.5 Implementation Order

```
1. Preset base class and schema
2. Default configuration files
3. CLI main entry point
4. Preset picker (guided selection)
5. Power-user settings interface
6. Codebase Assistant preset
7. Local Document Chat preset
8. Research Report preset
9. File Organizer preset
10. Doctor script
11. Integration tests for presets
12. User documentation for presets
```

### 4.6 Explicitly NOT in Phase 4
- TUI interface (terminal UI)
- Web UI
- Desktop UI
- API server
- Additional workflow packs beyond coding

### 4.7 Exit Gate
**GATE 4.1:** Beginner can launch a preset with 3 inputs or fewer
**GATE 4.2:** Power-user can override all relevant settings via CLI
**GATE 4.3:** Doctor script diagnoses common issues
**GATE 4.4:** All presets produce complete artifact sets
**GATE 4.5:** Preset selection requires no technical knowledge
**GATE 4.6:** Configuration is portable (export/import)

---

## 7. Phase 5: EXPANSION

### 7.1 Objective
Expand the platform with additional workflow packs, providers, memory backends, and the guided TUI.

### 7.2 Entry Criteria
- ALL Phase 4 exit gates passed
- Preset system functional
- CLI complete

### 7.3 Unlocked Subsystems
- `workflows/documents/` — Document workflow pack
- `workflows/research/` — Research workflow pack
- `workflows/file_organization/` — File organization workflow pack
- `workflows/docs_maintenance/` — Docs maintenance workflow pack
- `workflows/github_maintenance/` — GitHub maintenance workflow pack
- `workflows/command_assistant/` — Command assistant workflow pack
- `interfaces/guided_tui/` — Terminal UI
- Additional providers (as needed)
- Additional memory backends (jsonl, sqlite)
- Vector retrieval (Chroma/Qdrant)

### 7.4 Deliverables

| Deliverable | Owner | Prerequisites | Exit Criteria |
|-------------|-------|--------------|---------------|
| Documents workflow | Workflow Team | Phase 4 | Index, retrieve, answer, cite |
| Research workflow | Workflow Team | Phase 4 | Gather, summarize, compare, report |
| File organization workflow | Workflow Team | Phase 4 | Analyze, propose, preview, apply |
| Docs maintenance workflow | Workflow Team | Phase 4 | Detect stale, update, align |
| GitHub maintenance workflow | Workflow Team | Phase 4 | Summarize issues, draft PRs |
| Command assistant workflow | Workflow Team | Phase 4 | Parse intent, generate safe commands |
| Guided TUI | Interface Team | Phase 4 | Terminal-native preset picker |
| Additional memory backends | Memory Team | Phase 4 | jsonl, sqlite backends |
| Vector retrieval (optional) | Memory Team | Phase 4 | Chroma or Qdrant integration |

### 7.5 Explicitly NOT in Phase 5
- MCP integration
- Browser tool
- Local DB tool
- Web UI
- Desktop UI
- API server
- Distributed workers

### 7.6 Exit Gate
**GATE 5.1:** At least 3 workflow packs functional beyond coding
**GATE 5.2:** Guided TUI provides beginner-friendly experience
**GATE 5.3:** Memory system functional with at least 2 backends
**GATE 5.4:** All workflow packs produce complete artifacts
**GATE 5.5:** Platform is usable by non-technical users

---

## 8. Phase 6: ADVANCED SYSTEMS (RESERVED)

### 8.1 Status
Phase 6 is RESERVED ARCHITECTURE ONLY. These systems are defined for architectural alignment but are NOT unlocked for implementation.

### 8.2 Reserved Subsystems
- MCP integration (`tools/mcp/`)
- Browser tool (`tools/browser/`)
- Local DB tool (`tools/local_db/`)
- Web UI (`interfaces/web_ui/`)
- Desktop UI (`interfaces/desktop_ui/`)
- API server (`interfaces/api_server/`)
- Distributed workers
- Plugin marketplace
- eBPF/ETW monitoring
- Self-improving agents
- Cross-modal capabilities
- Federated agent networks

### 8.3 Unlock Criteria
Phase 6 unlocks ONLY when:
- ALL Phase 5 exit gates passed
- Core runtime has been stable for 3 months
- At least 5 workflow packs are production-quality
- Architecture Lead approves Phase 6 commencement
- Explicit roadmap update published

---

*End of 06_PHASED_DEVELOPMENT_PLAN.md*
