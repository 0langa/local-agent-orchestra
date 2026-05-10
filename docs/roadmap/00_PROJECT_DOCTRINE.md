# 00 — PROJECT DOCTRINE
## The Binding Engineering Constitution for `local-agent-orchestra`

**Status:** IMMUTABLE FOUNDATION
**Version:** 1.0
**Authority:** OVERRIDES ALL OTHER DOCUMENTS ON CONFLICT
**Violation Classification:** ARCHITECTURAL BREACH — triggers mandatory review and potential rollback

---

## 1. Identity Statement

`local-agent-orchestra` is a **preset-driven, local-first AI automation platform** with a serious generic orchestration runtime underneath. The system must simultaneously satisfy three user layers — beginner, power-user, and developer — without compromising any layer's integrity.

**The north star:**
- Simple on the surface.
- Serious underneath.
- Extensible when needed.
- Safe by default.
- Local-first by default.

**The identity test:** If a non-technical user can launch useful AI workflows without understanding what an agent is, while a developer can add new providers and workflow packs without touching the core, the system is architecturally correct.

---

## 2. Core Thesis (Immutable)

1. **The project must NOT become a developer-only multi-agent framework.** Accessibility is core infrastructure, not bolt-on polish.

2. **The core runtime must remain generic.** No provider, model, agent role, workflow type, or tool category is ever hardcoded into core.

3. **The coding workflow is the first workflow pack, not the product identity.** The orchestrator/coder/verifier flow becomes `workflows/coding/`. It validates the runtime; it does not define it.

4. **Provider agnosticism is architectural law.** Grok, OpenAI, Azure, OCI, AWS, Ollama, LM Studio, and all future providers are interchangeable adapters. No provider shapes the architecture.

5. **Safety is the default state, not a configurable option.** All side effects are mediated. Destructive operations require approval. Policies are defined in code, not by models.

6. **Every run is fully auditable.** The system does not ask users to trust it. It gives them the tools to verify.

---

## 3. Architectural Laws (Absolute Constraints)

### Law 1: Core Runtime Ignorance
The core runtime knows nothing about:
- Any specific provider (Grok, OpenAI, Ollama, etc.)
- Any specific workflow type (coding, documents, research, etc.)
- Any specific agent role beyond the generic agent protocol
- Any specific tool implementation beyond the tool protocol interface
- Any specific model name or capability beyond the capability registry

**Enforcement:** Any code change that introduces provider-specific, workflow-specific, or tool-specific logic into `core/` is an architectural breach.

### Law 2: Workflow Pack Autonomy
Workflow packs define:
- Agent roles, prompts, and schemas
- Step sequences and DAG structure
- Model role requirements (resolved at runtime via registry)
- Tool requirements and permission requests
- Workflow-specific policies
- Verification logic
- Output artifact specifications
- Preset UI metadata

Workflow packs MUST NOT:
- Import provider implementations directly
- Mutate core runtime state
- Bypass the policy engine
- Execute tools outside the mediated tool protocol

### Law 3: Provider Adapter Interchangeability
Provider adapters:
- Are lazy-loaded configuration objects, not first-class framework citizens
- Declare capabilities; the runtime resolves roles to configured models
- Must be replaceable without any core code changes
- Must not leak provider-specific assumptions into agent prompts or workflow logic

### Law 4: Progressive Disclosure
The same underlying system serves three layers:
- **Beginner:** Guided presets, jargon-free, safe defaults, mandatory approval gates
- **Power-user:** Inspectable, configurable, precise overrides
- **Developer:** Extensible, modular, schema-driven, testable

Complexity is hidden until explicitly requested. The product never dumbs down the underlying engine.

### Law 5: Event-Sourced Truth
All run state is derived from an append-only event log. There is no mutable run state that cannot be reconstructed from the ledger. This is not an implementation detail; it is a foundational design choice enabling reproducibility, fault recovery, and auditability.

### Law 6: Local-First Sovereignty
The default mode requires zero external services beyond model APIs. All orchestration, planning, verification, and artifact generation happens on the host machine. Privacy modes (remote-allowed, local-preferred, local-only, strict-private) are enforced at the policy engine level, not merely advisory.

### Law 7: Deterministic Replayability
Given the same configuration and inputs, a run must produce the same sequence of state transitions. Non-determinism is confined to model inference outputs and explicitly marked external state changes.

---

## 4. Anti-Patterns (Forbidden System Trajectories)

These are **architectural anti-patterns** that violate the project identity. Any implementation exhibiting these patterns must be rejected:

| Anti-Pattern | Violation | Correct Path |
|-------------|-----------|-------------|
| LLM + tools + chat UI with no deeper runtime | No orchestration identity | Build the generic runtime first |
| Hardcoded agent pile | Core knows about specific roles | Roles live in workflow packs |
| Provider-specific demo | Violates Law 1 | Provider-agnostic from day one |
| Prompt-template collection | No execution runtime | Templates are workflow pack internals |
| Unsafe local shell executor | Violates Law 5 (safety) | All shell execution is policy-mediated |
| Developer-only framework | Violates Law 4 | Beginner surface is core, not polish |
| Grok/OpenAI/Ollama wrapper | Violates Law 3 | All providers are adapters |
| Cloud-first architecture | Violates Law 6 | Local-first is default |
| Black-box runs | Violates Law 5 | Every run produces full artifacts |
| Speculative abstraction | Premature generalization | Build concrete, extract generic |

---

## 5. Swarm Execution Doctrine

This roadmap is designed for execution by up to 300 concurrent autonomous agents. The following rules govern swarm behavior:

### Swarm Rule 1: Subsystem Ownership
Every agent operates within a defined subsystem boundary. An agent may not modify files outside its assigned subsystem without explicit cross-boundary approval.

### Swarm Rule 2: Phase-Locked Implementation
Agents may only implement systems unlocked by the current development phase. Future-phase subsystems are marked RESERVED and are forbidden from implementation.

### Swarm Rule 3: Dependency-Ordered Execution
No agent may begin implementing a subsystem until all its declared dependencies have passed their integration gates.

### Swarm Rule 4: No Cross-Module Edits Without Gates
Agents may not modify multiple subsystems in a single change. Cross-subsystem integration must pass through defined integration gates.

### Swarm Rule 5: Architecture Invariant Preservation
No agent change may violate the seven Architectural Laws. Violations are automatically flagged for mandatory review.

---

## 6. Authority Hierarchy

```
00_PROJECT_DOCTRINE.md (this document)
    |
    +-- 02_CORE_ARCHITECTURE_PRINCIPLES.md (structural constraints)
    |       |
    |       +-- 06_PHASED_DEVELOPMENT_PLAN.md (execution ordering)
    |               |
    |               +-- 07_SUBSYSTEM_DEFINITIONS.md (ownership boundaries)
    |                       |
    |                       +-- All subsystem specifications
    |
    +-- 04_SWARM_GOVERNANCE.md (agent coordination rules)
    |
    +-- 20_NON_GOALS_AND_ANTI_PATTERNS.md (forbidden behaviors)
```

On conflict, the higher document overrides the lower. No subsystem specification may contradict the Project Doctrine.

---

## 7. Enforcement

Violation of any Architectural Law or Swarm Execution Rule is classified as:

- **Level 1:** Style or naming deviation — auto-corrected
- **Level 2:** Boundary concern — requires review before merge
- **Level 3:** Architectural breach — blocks merge, triggers rollback review
- **Level 4:** Constitutional violation — immediate revert, swarm-wide notification

**This document is binding engineering law. It is not optional guidance.**

---

## 8. Immutable Declarations

The following declarations are frozen until an explicit constitutional amendment process is completed:

1. The project identity is: preset-driven, local-first AI automation platform.
2. The core runtime is provider-agnostic, workflow-agnostic, and tool-agnostic.
3. The coding workflow is ONE workflow pack among many future packs.
4. Safety is the default state.
5. All runs are fully auditable via event-sourced ledgers.
6. Local-first is the default operational mode.
7. Provider adapters are interchangeable and lazy-loaded.
8. Progressive disclosure governs the user experience.
9. The AICtx relationship is: Local Agent Orchestration consumes AICtx as a context intelligence layer.
10. MCP integration is optional and deferred until core contracts are stable.

---

*End of 00_PROJECT_DOCTRINE.md*
*This document is the supreme authority for all swarm execution.*
