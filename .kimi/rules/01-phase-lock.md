# PHASE LOCK — CURRENT EXECUTION BOUNDARY

## Current Phase: 0 (FOUNDATION)
## Status: ACTIVE
## Unlocked: 2025-01-15

---

## What Phase 0 Does
Clean existing codebase. Establish canonical directory structure. Enforce architectural invariants. NOTHING new is built.

## Unlocked Subsystems (I may work on these)
- `core/` — refactoring to remove provider/workflow specifics
- `providers/<name>/` — migrating existing providers
- `workflows/coding/` — extracting coding flow from core
- `tools/base.py` — defining tool protocol
- `providers/base.py` — defining provider protocol
- Directory structure alignment
- Import linting setup
- CI pipeline for architecture enforcement

## Explicitly LOCKED (I must NOT touch these)
- `workflows/documents/` — Phase 5
- `workflows/research/` — Phase 5
- `workflows/file_organization/` — Phase 5
- `workflows/docs_maintenance/` — Phase 5
- `workflows/github_maintenance/` — Phase 5
- `workflows/command_assistant/` — Phase 5
- `memory/vector_retrieval.py` — Phase 5
- `interfaces/guided_tui/` — Phase 5
- `interfaces/web_ui/` — Phase 6 (RESERVED)
- `interfaces/desktop_ui/` — Phase 6 (RESERVED)
- `interfaces/api_server/` — Phase 6 (RESERVED)
- `tools/mcp/` — Phase 6 (RESERVED)
- `tools/browser/` — Phase 6 (RESERVED)
- `tools/local_db/` — Phase 6 (RESERVED)
- Plugin marketplace — Phase 6 (RESERVED)
- Distributed workers — Phase 6 (RESERVED)

## Phase 0 Exit Gates (ALL must pass to advance)
- [ ] GATE 0.1: No provider-specific logic in `core/`
- [ ] GATE 0.2: No workflow-specific logic in `core/`
- [ ] GATE 0.3: Directory structure matches canonical spec
- [ ] GATE 0.4: CI enforces architectural boundaries
- [ ] GATE 0.5: Import linting passes on all modules
- [ ] GATE 0.6: ModelRegistry is fully generic

## My Boundaries
Before modifying ANY file, I must confirm:
1. The file is in an unlocked subsystem
2. The change preserves all 7 Laws
3. The change does not implement future-phase functionality
4. Tests exist or will be created for the change
