---
name: agentheim-aictx-guide
description: >
  Guide AICtx integration work in Agentheim. Knows the milestone plan (M0-M9),
  ContextOps boundary, vendor module map, and migration steps. Use when working
  on agentheim/context_ops.py, agentheim/context_ops_impl.py, or docs/AICTX_INTEGRATION_PLAN.md.
  Auto-triggers when ContextOps or integration docs are modified.
---

# Agentheim AICtx Guide

Navigate the AICtx integration without duplicating work or breaching boundaries.

## Current Status

- **M0 Architecture Freeze**: COMPLETE
- **M1 Source Import And Boundary**: COMPLETE
- **M2 Local Context Domain Integration**: COMPLETE
- **M2.5 ABC Expansion + Editable Install**: COMPLETE
- **M3-M9**: PENDING

Read `docs/AICTX_INTEGRATION_PLAN.md` for full milestone details.

## Key Boundaries

### Agentheim owns
- Workflows and presets
- CLI, API server, web UI, guided TUI, desktop UI
- Provider/model abstraction
- Policy engine and approval flow
- Run ledgers, artifacts, and resume/replay

### AICtx owns (behind ContextOps)
- Repository inventory
- Context planning and shard selection
- Deterministic context generation
- Lockfile creation and verification
- Stale-context detection
- Public-doc impact mapping
- Snapshot/export for optional remote context jobs

### Stop: Do Not
- Import AICtx directly into core/ → Law 1 violation
- Copy AICtx provider stack into Agentheim providers/ → duplicate work
- Bypass ContextOps ABC → boundary breach
- Commit copied AICtx source into Agentheim → Level 4 violation

## ContextOps Interface

File: `agentheim/context_ops.py`

ABC methods:
- `init()` — initialize repo for context processing
- `clean()` — remove generated run artifacts
- `scan()` — repository inventory
- `plan()` — context planning
- `generate()` — deterministic context generation
- `write()` — write context outputs
- `run_pipeline()` — end-to-end local Phase-1 pipeline
- `verify()` — lockfile verification
- `status()` — stale-context check
- `public_docs_impact()` — doc impact mapping
- `public_docs_update()` — generate patches for impacted public docs

Agentheim code calls through ContextOps. AICtx implements behind it via the editable install.

## Provider Interface Delta

AICtx `llm/base.py` vs Agentheim `providers/base.py`:
- AICtx `ChatRequest`: system_prompt + messages + json_schema
- Agentheim `ModelRequest`: system_prompt + user_prompt + temperature
- Decision: thin adapter in M7. Until then, AICtx keeps its own provider stack behind ContextOps.

## Milestone Quick Reference

| Milestone | Status | Key Deliverable |
|-----------|--------|-----------------|
| M0 | ✅ | ADR-001 approved |
| M1 | ✅ | Source imported, ContextOps defined |
| M2 | ✅ | ContextOps implementation (7 methods) |
| M2.5 | ✅ | ABC expanded with init, clean, run_pipeline, public_docs_update; editable install |
| M3 | ⏳ | Workflow And Preset Exposure |
| M4 | ⏳ | CLI integration (`agentheim ctx`) |
| M5 | ⏳ | Workflow integration |
| M6 | ⏳ | Transient state migration to .ai-team/ |
| M7 | ⏳ | Provider adapter layer |
| M8 | ⏳ | Public docs convergence |
| M9 | ⏳ | Standalone CLI deprecation |

## Module Map

File: `agentheim/vendor/MODULE_MAP.md`

Documents preserved / adapted / replaced modules. Check before touching vendor code.

## Test Locations

- ContextOps tests: `tests/test_context_ops_impl.py` (18 passed)
- Vendor tests: `agentheim/vendor/aictx/tests/` (101 passed)
- Target location by M3: `tests/vendor/aictx/`
