# Project Doctrine

These rules are binding for every agent working in this repository.

## Identity

`agentheim` is a preset-driven, local-first AI automation platform. The core product is a generic orchestration runtime with policy-gated tools, interchangeable model providers, workflow packs, ledgers, memory, and user-facing interfaces.

Coding support is one workflow area. It is not the whole product.

## The 7 Immutable Laws

Violating any law is an architectural breach and blocks merge.

### 1. Core Ignorance

`core/` must not contain concrete provider names, workflow names, agent roles, tool implementations, AICtx implementation details, or product-specific shortcuts. Core knows protocols, registries, events, policies, budgets, ledgers, and generic runtime contracts.

> Exception: `core/model_registry.py` contains `DEFAULT_PROVIDER_MAP` as a bootstrapping default. The `ModelRegistry` class itself remains fully generic and accepts any `provider_map`.

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
- `docs/adr/ADR-001-aictx-integration-contract.md` and `agentheim/vendor/MODULE_MAP.md` describe the AICtx integration contract and current module ownership.
- `BASELINE-ROADMAP.md` is the active roadmap for baseline hardening.
- `.github/instructions/*.md` files are binding agent instructions.

If a file referenced by an instruction no longer exists, report and fix the drift rather than following stale guidance.
