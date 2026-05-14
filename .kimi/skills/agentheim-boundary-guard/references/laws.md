# Project Doctrine

These rules are binding for every agent working in this repository.

## Identity

`agentheim` is a preset-driven, local-first AI automation platform. The core product is a generic orchestration runtime with policy-gated tools, interchangeable model providers, workflow packs, ledgers, memory, and user-facing interfaces.

Coding support is one workflow area. It is not the whole product.

## The 7 Immutable Laws

Violating any law is an architectural breach and blocks merge.

### 1. Core Ignorance

`core/` must not contain concrete provider names, workflow names, agent roles, tool implementations, AICtx implementation details, or product-specific shortcuts. Core knows protocols, registries, events, policies, budgets, ledgers, and generic runtime contracts.

### 2. Workflow Pack Autonomy

Workflow packs in `workflows/` define their own agents, steps, prompts, policies, and verification behavior. They must not import provider implementations directly, mutate core state, or bypass the policy engine.

### 3. Provider Interchangeability

Provider adapters in `providers/` are interchangeable and lazy-loaded. A provider can add capability, but it must not shape the core architecture.

### 4. Progressive Disclosure

The same system must serve beginners through presets, power users through configuration, and developers through stable APIs. Do not force internal complexity into beginner flows, and do not remove power-user or developer control to simplify an implementation.

### 5. Event-Sourced Truth

Run state derives from append-only ledgers and recorded artifacts. Do not mutate ledger history. Do not invent side-channel run state that cannot be replayed, audited, or inspected.

### 6. Local-First Sovereignty

Agentheim is local-first. External services must be explicit, policy-gated, and compatible with privacy settings. Sensitive files, secrets, generated context artifacts, and local runtime state must not be sent to remote systems unless the relevant policy and task explicitly allow it.

### 7. Safety By Default

All side effects go through maintained safety paths: tool protocol, policy engine, approval workflow, path confinement, and redaction. Destructive, networked, credential-bearing, or production-affecting operations require explicit authorization and traceability.

## Current Documentation Authority

- `docs/README.md` is the documentation index.
- `docs/ARCHITECTURE.md` describes current architecture.
- `docs/SAFETY.md` describes current safety behavior.
- `docs/adr/ADR-001-aictx-integration-contract.md` and `agentheim/vendor/MODULE_MAP.md` govern AICtx integration boundaries and module ownership.
- `.github/instructions/*.md` files are binding agent instructions.

If a file referenced by an instruction no longer exists, report and fix the drift rather than following stale guidance.


# Forbidden Behaviors

These behaviors are automatic rejection unless the user explicitly asks for a controlled migration that includes tests, docs, and rollback reasoning.

## Level 4: Constitutional Violations

- Introducing provider-specific logic into `core/`
- Introducing workflow-specific logic into `core/`
- Introducing AICtx-specific implementation logic into `core/`
- Skipping the policy engine for tool calls
- Mutating ledger events after append
- Sending secrets, sensitive files, or strict-private data to remote services without explicit policy approval
- Weakening authentication, authorization, redaction, path confinement, approval, or safety defaults without explicit user intent
- Committing gitignored local reference repositories, including `AICtx/`

## Level 3: Architectural Breaches

- Importing concrete provider, workflow, tool, or interface implementations into `core/`
- Direct tool execution outside the maintained tool protocol
- Adding hidden mutable global state for runtime behavior
- Creating a second provider registry, second policy path, or second ledger system instead of using Agentheim primitives
- Adding public commands, APIs, or workflow behavior without updating docs and tests
- Silently swallowing production errors where callers need actionable failure information

## Level 2: Boundary Concerns

- Changing event schemas without a compatibility or migration plan
- Changing artifact layout without updating docs, tests, and consumers
- Adding workflow packs without registration and smoke coverage
- Adding provider adapters without lazy-loading and capability coverage
- Adding generated files without ignore/update rules
- Touching multiple subsystems without explaining the cross-boundary impact

## Common Anti-Patterns

| Anti-Pattern | Required Approach |
| --- | --- |
| "Put this provider check in core for now." | Route through provider configuration, descriptors, and registry boundaries. |
| "This workflow needs a special core hook." | Extend workflow contracts or workflow pack behavior without hard-coding the workflow in core. |
| "Import the tool directly to save time." | Use the maintained tool protocol and policy path. |
| "Use a global singleton because passing context is noisy." | Prefer explicit dependencies and existing runtime context objects. |
| "Docs can be fixed later." | Fix docs in the same change when behavior, paths, commands, or guarantees change. |
| "Copy AICtx wholesale into Agentheim internals." | Import or adapt through the approved integration boundary and preserve Agentheim ownership. |

## Stop Conditions

Stop and ask for direction if:

- The task requires violating any immutable law.
- The requested change conflicts with `.github/instructions/*.md`.
- The worktree contains user changes that directly conflict with the required edit.
- Verification shows a real defect outside the requested scope that must be fixed before proceeding safely.

