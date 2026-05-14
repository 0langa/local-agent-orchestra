---
name: agentheim-docs-sync
description: >
  Keep Agentheim documentation in sync with code changes. Identifies which docs
  need updates when behavior, paths, commands, or guarantees change. Use when
  modifying code in core/, workflows/, providers/, tools/, interfaces/, presets/,
  config/, or memory/. Auto-triggers when public interfaces, CLI commands, API
  endpoints, or event schemas are modified.
---

# Agentheim Docs Sync

Ensure docs stay accurate when code changes. Run this before finishing any task.

## When to Run

- After code change is complete, before declaring task done
- When user says "update docs", "docs sync", "what docs need changing"
- When behavior, paths, commands, or guarantees change
- When adding new public commands, APIs, workflows, or tools

## Workflow

### 1. Identify Changed Code Areas

Map modified files to code areas:

| File Pattern | Code Area |
|-------------|-----------|
| `core/*.py` | Core Runtime |
| `core/workflow_runner.py` | Workflow Runner |
| `core/ledger.py` | Ledger |
| `core/policy_engine.py` | Policy Engine |
| `core/tool_protocol.py` | Tool Protocol |
| `core/model_registry.py` | Model Registry |
| `providers/*.py` | Providers |
| `tools/**/*.py` | Tools |
| `tools/browser/*.py` | Browser Tool |
| `workflows/**/*.py` | Workflows |
| `workflows/coding/*.py` | Coding Workflow |
| `interfaces/cli/*.py` | CLI |
| `interfaces/api_server/*.py` | API Server |
| `memory/*.py` | Memory Subsystem |
| `presets/*.py` | Presets |
| `config/*.py` | Config |
| `.github/instructions/*.md` | Agent Instructions |
| `agentheim/vendor/aictx/**/*.py` | AICtx Integration |

### 2. Map to Required Doc Updates

Read `references/doc-map.md` for full mapping. Key rules:

**Always update `docs/CHANGELOG.md`**
- Append before any commit
- Use `## YYYY-MM-DD` date header
- Group by category (`### Feature`, `### Bug Fix`, `### Docs`, etc.)

**Core/ changes → `docs/ARCHITECTURE.md`**
- Update component tables, runtime phases, boundary rules
- Also check `docs/API_REFERENCE.md` if public interfaces affected

**Provider/ changes → `docs/ARCHITECTURE.md` + `docs/API_REFERENCE.md`**
- Add to Provider Layer section
- Document in API reference if public

**Tool/ changes → `docs/API_REFERENCE.md` + `docs/USER_GUIDE.md`**
- Document tool schema, parameters, examples
- Add user-facing examples to USER_GUIDE

**Workflow/ changes → `docs/ARCHITECTURE.md` + `docs/USER_GUIDE.md` + `docs/DEV_TESTING.md`**
- Add to Workflows section in ARCHITECTURE
- Add preset/user guide content
- Add smoke test coverage notes

**CLI changes → `docs/USER_GUIDE.md` + `docs/API_REFERENCE.md`**
- Update CLI commands table
- Add copy-paste examples

**API changes → `docs/API_REFERENCE.md` + `docs/USER_GUIDE.md`**
- Document endpoints, request/response schemas
- Add usage examples

**Event schema changes → `docs/ARCHITECTURE.md`**
- Document compatibility plan

**Test count changes → `docs/DEV_TESTING.md` + `README.md`**
- Update test status badges/counts

**`.github/instructions/` changes → `AGENTS.md`**
- Update binding instructions list

**AICtx changes → `docs/AICTX_INTEGRATION_PLAN.md` + `agentheim/vendor/MODULE_MAP.md`**
- Update milestone status
- Update module mapping

### 3. Check for Stale References

After identifying docs to update, grep for old references:
- Old file paths
- Old command names
- Old test counts
- Old API endpoints
- Old model roles or enum values

### 4. Report Required Updates

List each doc file and what needs changing. Format:

```
- docs/CHANGELOG.md — append M1 completion entry
- docs/ARCHITECTURE.md — update ModelRegistry table row
- docs/API_REFERENCE.md — add new /memory/{backend}/{key} endpoint
```

Do not silently skip doc updates. If user says "skip docs", note it explicitly.
