# 05 — REPOSITORY BOUNDARIES
## Ownership Domains, Merge Rules, Forbidden Behaviors, and Subsystem Contracts

**Status:** DERIVED FROM 02_CORE_ARCHITECTURE_PRINCIPLES
**Enforcement:** All repository modifications must respect these boundaries.
**Violation Classification:** BOUNDARY CONCERN (Level 2) — ARCHITECTURAL BREACH (Level 3) for core violations

---

## 1. Subsystem Ownership Domains

### 1.1 Ownership Map

```
Repository Root
|
+-- core/                     → OWNER: Runtime Team
|   +-- workflow_runner.py    →   Primary: Execution Engineer
|   +-- agent_protocol.py     →   Primary: Protocol Engineer
|   +-- model_registry.py     →   Primary: Provider Engineer
|   +-- provider_registry.py  →   Primary: Provider Engineer
|   +-- tool_protocol.py      →   Primary: Tool Engineer
|   +-- policy_engine.py      →   Primary: Security Engineer
|   +-- run_ledger.py         →   Primary: Runtime Engineer
|   +-- artifact_store.py     →   Primary: Runtime Engineer
|   +-- capability_registry() →   Primary: Platform Engineer
|   +-- All other core files  →   Assigned per subsystem
|
+-- providers/                → OWNER: Provider Team
|   +-- base.py               →   Primary: Provider Engineer
|   +-- <name>/               →   Primary: Provider Engineer (per provider)
|   +-- registry_meta.py      →   Primary: Provider Engineer
|
+-- tools/                    → OWNER: Tool Team
|   +-- base.py               →   Primary: Tool Engineer
|   +-- <category>/           →   Primary: Tool Engineer (per category)
|   +-- registry.py           →   Primary: Tool Engineer
|
+-- workflows/                → OWNER: Workflow Team
|   +-- base.py               →   Primary: Workflow Engineer
|   +-- coding/               →   Primary: Workflow Engineer
|   +-- <name>/               →   Primary: Workflow Engineer (per workflow)
|
+-- memory/                   → OWNER: Memory Team
|   +-- base.py               →   Primary: Memory Engineer
|   +-- <backend>/            →   Primary: Memory Engineer (per backend)
|
+-- interfaces/               → OWNER: Interface Team
|   +-- cli/                  →   Primary: CLI Engineer
|   +-- <ui>/                 →   Primary: UI Engineer (per interface)
|
+-- presets/                  → OWNER: Product Team
|   +-- base.py               →   Primary: Product Engineer
|   +-- <name>.py             →   Primary: Product Engineer (per preset)
|
+-- config/                   → OWNER: Platform Team
|   +-- All config files      →   Primary: Platform Engineer
|
+-- tests/                    → OWNER: Quality Team
|   +-- integration/          →   Primary: QA Engineer
|   +-- fixtures/             →   Primary: QA Engineer
|   +-- conftest.py           →   Primary: QA Engineer
|
+-- docs/                     → OWNER: Documentation Team
|   +-- roadmap/              →   Primary: Architecture Lead (FROZEN)
|   +-- architecture/         →   Primary: Technical Writer
|   +-- user_guide/           →   Primary: Technical Writer
|   +-- developer_guide/      →   Primary: Technical Writer
|
+-- scripts/                  → OWNER: Platform Team
|   +-- doctor.py             →   Primary: DevOps Engineer
|   +-- verify_setup.py       →   Primary: DevOps Engineer
```

### 1.2 Primary Owner Responsibilities
- The Primary Owner is the authoritative reviewer for all changes in their domain
- The Primary Owner must approve all PRs touching their files
- The Primary Owner maintains the subsystem's test coverage
- The Primary Owner documents the subsystem's interface contract
- The Primary Owner escalates cross-boundary changes to the Architecture Lead

### 1.3 Ownership Transfers
- Ownership transfer requires Architecture Lead approval
- Transfer includes: code review, documentation update, test handoff
- No ownership transfer during active development phases
- Minimum 2-week overlap period for knowledge transfer

---

## 2. Merge and Integration Rules

### 2.1 Change Classification

| Change Type | Approval Required | Tests Required | Documentation |
|-------------|-------------------|----------------|---------------|
| Core bug fix | Primary Owner | Unit tests | CHANGELOG |
| Core feature | Primary Owner + Architecture Lead | Unit + integration | Architecture docs |
| Provider addition | Provider Team Lead | Unit tests + provider tests | Provider docs |
| Tool addition | Tool Team Lead | Unit tests + tool tests | Tool docs |
| Workflow addition | Workflow Team Lead | Unit + integration + e2e | Workflow docs |
| Interface change | Interface Team Lead | Unit tests | User docs |
| Preset change | Product Team Lead | Integration tests | User guide |
| Config change | Platform Team Lead | Validation tests | Config docs |
| Cross-boundary | Architecture Lead + all affected Primaries | Full test suite | All affected docs |

### 2.2 Forbidden File Modifications (Per Subsystem)

A subsystem owner MAY modify:
- Files within their assigned directory
- Test files for their subsystem
- Documentation for their subsystem
- Configuration defaults for their subsystem

A subsystem owner MAY NOT modify:
- Files in `core/` without Architecture Lead approval
- Files in another subsystem without that subsystem's Primary Owner approval
- The project doctrine or architecture principles
- CI/CD configuration without Platform Team approval

### 2.3 Cross-Boundary Change Protocol
1. Author creates RFC document describing the change and its cross-boundary impact
2. RFC is reviewed by Architecture Lead
3. RFC is circulated to all affected Primary Owners
4. Each Primary Owner approves or raises concerns
5. All concerns are resolved before implementation begins
6. Implementation is done in a feature branch
7. Cross-boundary integration tests must pass before merge
8. Architecture Lead performs final review and merge

---

## 3. Forbidden Implementation Behaviors

### 3.1 Absolute Prohibitions

| Prohibition | Violation Level | Detection |
|-------------|----------------|-----------|
| Provider-specific logic in `core/` | Level 3 (Architectural Breach) | Static analysis + code review |
| Workflow-specific logic in `core/` | Level 3 (Architectural Breach) | Static analysis + code review |
| Direct tool execution bypassing protocol | Level 3 (Architectural Breach) | Runtime validation |
| Mutable global state | Level 3 (Architectural Breach) | Static analysis |
| Import of concrete implementations into core | Level 3 (Architectural Breach) | Import linting |
| Skipping policy engine for tool calls | Level 4 (Constitutional) | Runtime validation |
| Modifying ledger events after append | Level 4 (Constitutional) | Ledger integrity checks |
| Sending sensitive data to remote in strict-private | Level 4 (Constitutional) | Policy enforcement |

### 3.2 Conditional Prohibitions

| Prohibition | Condition | Violation Level |
|-------------|-----------|----------------|
| Adding new providers | Before provider registry is stable | Level 2 |
| Adding workflow packs | Before workflow runtime is stable | Level 2 |
| Adding memory backends | Before memory protocol is stable | Level 2 |
| Adding UI interfaces | Before CLI and core are stable | Level 2 |
| Modifying event schemas | Without migration plan and backward compat | Level 2 |
| Changing phase machine | Without updating all affected subsystems | Level 2 |

---

## 4. Subsystem Isolation Rules

### 4.1 Core Isolation
- Core modules may only import from `core/`, `providers.base`, `tools.base`, `workflows.base`, `memory.base`
- Core modules must not import from any concrete implementation directory
- Core modules must use dependency injection for all external dependencies
- Core module tests must mock all external dependencies

### 4.2 Provider Isolation
- Provider adapters may only import from `providers.base`, `core.types`, `core.schemas`
- Provider adapters must not import from other provider adapters
- Provider adapters must not import from `core/` internals
- Provider adapter tests must mock the network layer

### 4.3 Tool Isolation
- Tool adapters may only import from `tools.base`, `core.types`, `core.schemas`, `core.policy_engine`
- Tool adapters must not import from other tool adapters
- Tool adapters must not import from `core/` internals
- Tool adapters must declare their risk level in their schema

### 4.4 Workflow Isolation
- Workflow packs may import from `workflows.base`, `core.types`, `core.schemas`
- Workflow packs may query the capability registry for tool/provider discovery
- Workflow packs must not import from `core/` internals
- Workflow packs must not import provider implementations directly

### 4.5 Memory Isolation
- Memory backends may only import from `memory.base`, `core.types`, `core.schemas`
- Memory backends must not import from other memory backends
- Memory backends must not import from `core/` internals

---

## 5. Integration Points

### 5.1 Defined Integration Boundaries

```
core.workflow_runner ↔ workflows.base.Workflow
                     → calls: init(), execute_step(), verify(), cleanup()
                     ← receives: StepResult, VerificationResult

core.model_registry ↔ providers.base.ProviderProtocol
                     → calls: complete(), stream(), health_check()
                     ← receives: ModelResponse, ModelChunk, ProviderHealth

core.tool_protocol ↔ tools.base.ToolProtocol
                     → calls: invoke()
                     ← receives: ToolResult

core.policy_engine ↔ tools.base.ToolProtocol.schema.risk_level
                     → reads: RiskLevel declaration
                     ← returns: PolicyDecision

core.run_ledger → (append-only, no consumer reads during run)
                     ← reads: resume replay, artifact generation

core.capability_registry ← providers.* (registration at import)
                          ← tools.* (registration at import)
                          ← workflows.* (registration at import)
                          → queries: core.*, interfaces.*, presets.*

interfaces.cli → core.public_api (defined set of exported functions)
                → presets.* (for preset rendering)
                → workflows.base (for workflow discovery)
```

### 5.2 Integration Test Requirements
Every integration boundary must have:
- Contract tests verifying the interface
- Mock implementations for isolated testing
- At least one end-to-end test per integration path
- Documentation of the interface contract

---

## 6. Branch and Merge Strategy

### 6.1 Branch Types

| Branch | Purpose | Merge Target | Lifetime |
|--------|---------|-------------|----------|
| `main` | Production-ready code | — | Permanent |
| `develop` | Integration branch for next release | `main` | Permanent |
| `feature/<name>` | Single feature development | `develop` | Temporary |
| `bugfix/<name>` | Bug fix | `develop` | Temporary |
| `hotfix/<name>` | Critical production fix | `main` | Temporary |
| `release/<version>` | Release preparation | `main` | Temporary |

### 6.2 Merge Requirements
- All CI checks must pass
- Primary Owner approval for affected subsystems
- Architecture Lead approval for cross-boundary changes
- Test coverage must not decrease
- CHANGELOG must be updated
- Documentation must be updated for user-facing changes

---

*End of 05_REPOSITORY_BOUNDARIES.md*
