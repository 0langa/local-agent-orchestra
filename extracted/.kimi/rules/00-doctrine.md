# PROJECT DOCTRINE — BINDING LAW

## Identity
local-agent-orchestra is a preset-driven, local-first AI automation platform. The core is a generic orchestration runtime. Coding is ONE workflow pack among many — not the product identity.

## The 7 Immutable Laws

These laws are ABSOLUTE. Violating any law is an architectural breach that blocks merge.

### Law 1: Core Ignorance
The `core/` directory MUST NOT contain provider names (Grok, OpenAI, Ollama), workflow types (coding, research), agent roles (planner, executor), or tool implementations. Core knows only protocols and registries.

### Law 2: Workflow Pack Autonomy
Workflow packs in `workflows/` define their own agents, steps, policies, and verification. They MUST NOT import provider implementations directly, mutate core state, or bypass the policy engine.

### Law 3: Provider Interchangeability
Provider adapters in `providers/` are lazy-loaded configuration objects. All providers are interchangeable. No provider shapes the architecture.

### Law 4: Progressive Disclosure
The same system serves beginners (preset picker), power-users (configurable settings), and developers (extensible APIs). Complexity is hidden until requested. Never dumb down; never force complexity.

### Law 5: Event-Sourced Truth
All run state derives from an append-only event log. No mutable run state exists outside the ledger. This enables replayability, auditability, and fault recovery.

### Law 6: Local-First Sovereignty
Default operation requires zero external services beyond model APIs. Privacy modes (remote-allowed, local-preferred, local-only, strict-private) are enforced at the policy engine, not advisory.

### Law 7: Safety by Default
All destructive operations require explicit approval. Policies are defined in code, not by models. Side effects are mediated through the tool protocol.

## Authority Hierarchy
```
00_PROJECT_DOCTRINE.md > 02_CORE_ARCHITECTURE_PRINCIPLES.md > 06_PHASED_DEVELOPMENT_PLAN.md > 07_SUBSYSTEM_DEFINITIONS.md > all other specs
```
Higher documents override lower on conflict.

## Swarm Rules for This Session
1. I operate within ONE subsystem boundary per task
2. I do NOT implement future-phase systems
3. I do NOT modify files outside my assigned subsystem
4. I do NOT introduce provider-specific logic into core
5. I preserve ALL architectural invariants
