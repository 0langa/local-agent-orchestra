# ADR-001: AICtx Integration Contract

**Status:** Approved  
**Date:** 2026-05-12  
**Author:** Agentheim Autonomous Engineer  

---

## Context

AICtx is a v1-complete, local-first CLI tool for deterministic repository-context generation. It has ~95 tests, 7 repo fixtures, a fully defined `context.lock.json` schema, OCI remote execution infrastructure, and a standalone CLI. Agentheim needs AICtx's deterministic context capabilities as a first-class subsystem.

## Decision

### Canonical Runtime Ownership

Agentheim owns the top-level runtime model:

| Concern | Owner |
|---------|-------|
| CLI, API, Web UI, TUI, Desktop UI surfaces | Agentheim |
| Workflow and preset registration | Agentheim |
| Provider/model selection and policy governance | Agentheim |
| Ledgers, run artifacts, resume, replay | Agentheim |
| Safety, privacy, approval, redaction, path confinement | Agentheim |
| Repository inventory | AICtx (via `ContextOps`) |
| Context planning and shard selection | AICtx (via `ContextOps`) |
| Deterministic context generation | AICtx (via `ContextOps`) |
| `context.lock.json` schema and verification | AICtx (via `ContextOps`) |
| Stale-context detection | AICtx (via `ContextOps`) |
| Public-doc impact mapping | AICtx (via `ContextOps`) |
| Snapshot/export for optional remote execution | AICtx (via `ContextOps`) |

### Transient Artifact Location

`.ai-team/` is the canonical Agentheim runtime store. AICtx transient state migrates under `.ai-team/` during M6. Legacy `.aictx/` reads are supported during migration only.

### Source Namespace

AICtx source lives under `agentheim/vendor/aictx/` after a **filtered-history subtree merge**. This preserves git history while keeping the subsystem visibly bounded. No direct imports from `agentheim.vendor.aictx` are allowed in `core/`.

### Lockfile Schema Versioning

Adopt AICtx `context.lock.json` v1.0 schema directly. Agentheim writes and reads the same schema at the same path (`docs/AIprojectcontext/context.lock.json`). No envelope wrapper. Schema evolution uses lockfile's own `schema_version` field.

### Provider Interface Strategy

Pre-M7: AICtx keeps its own `llm/base.py` provider abstraction. `ContextOps` hides AICtx provider internals. An adapter layer converts between AICtx and Agentheim provider interfaces when M7 unifies them.

M7 scope: route AICtx provider calls through Agentheim `providers/base.py`. The adapter dies.

### Test Migration

AICtx tests and fixtures import into `tests/vendor/aictx/`. Run as-is through M1-M2. Adapt to Agentheim conventions (use `core.public_api` imports, Agentheim path conventions) by M3.

### CLI Namespace

`agentheim ctx <subcommand>` is the canonical surface. Example mapping:

| AICtx command | Agentheim command |
|---------------|-------------------|
| `aictx scan` | `agentheim ctx scan` |
| `aictx run` | `agentheim ctx run` |
| `aictx verify` | `agentheim ctx verify` |
| `aictx public-docs update` | `agentheim ctx public-docs update` |
| `aictx snapshot create` | `agentheim ctx snapshot create` |
| `aictx oci doctor` | `agentheim ctx oci doctor` |

The standalone `aictx` CLI remains as a thin compatibility wrapper during M1-M9, calling `agentheim ctx` internally. Deprecated after M9.

### Verification Composition

AICtx `verify` (hash-based lockfile verification) and Agentheim `PolicyEngine` (runtime safety verification) are orthogonal:

- AICtx verify runs at **context-use time**: before a workflow consumes context artifacts
- PolicyEngine runs at **tool-invocation time**: when a tool call is made
- Both emit events to the same Agentheim ledger
- Neither replaces the other

### Compatibility Guarantees

Until a later milestone explicitly changes them, preserve compatibility for:

- `AGENTS.md` (generated, unmanaged sections preserved)
- `docs/AIprojectcontext/**` (all context shard files)
- `docs/AIprojectcontext/context.lock.json` (v1.0 schema)
- `.aictxignore` (ignore patterns for scanner)
- AICtx verification result codes and meanings
- Patch-first write behavior (generated context writes to patch files, not directly to working tree)

### Deprecation Policy

| Item | Deprecation | Removal |
|------|-------------|---------|
| Standalone `aictx` CLI | M3 (thin wrapper) | M9 |
| `.aictx/runs/` transient state | M6 | M9 |
| AICtx `llm/base.py` provider | M7 | M9 |
| Legacy `cli.py` commands (non-`ctx`-namespaced) | M3 | M9 |

## Consequences

- Core ignorance is preserved: AICtx code lives in `agentheim/vendor/aictx/`, not `core/`.
- No parallel provider system: M7 unifies.
- No parallel runtime store: M6 unifies.
- User surface is clear: `agentheim ctx` is the one command namespace.
- Deterministic verification survives as code-level logic, not prompt-driven behavior.
- Existing AICtx users see their committed outputs remain valid.

## Risks

- Subtree merge size may be large (~40 source files). Mitigate by excluding AICtx tests/Oci docs from initial merge.
- Provider interface adapter in M7 may be complex if both interfaces diverge further. Mitigate by keeping adapter thin.
- Legacy `.aictx/runs/` readers may be needed longer than M9 if users have existing runs. Mitigate with migration docs.