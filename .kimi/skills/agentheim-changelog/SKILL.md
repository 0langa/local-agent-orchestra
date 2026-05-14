---
name: agentheim-changelog
description: >
  Write proper changelog entries for Agentheim. Ensures docs/CHANGELOG.md follows
  project conventions. Use before any commit, when user says "write changelog",
  "update changelog", or "what changed". Auto-triggers when preparing to commit
  or when docs/CHANGELOG.md is modified.
---

# Agentheim Changelog

Append to `docs/CHANGELOG.md` before every commit.

## Format

```markdown
## YYYY-MM-DD

### Category Name
- Change description with file references
- Another change

### Another Category
- Change description
```

## Categories

Common category names:
- `### Public Docs Sync` — README, USER_GUIDE, API_REFERENCE updates
- `### AICtx Integration` — milestone progress, vendor changes
- `### Bug Fixes` — fixed behaviors
- `### Features` — new capabilities
- `### Refactor` — internal restructuring with no behavior change
- `### Tests` — test additions, fixes, infra
- `### Repository Cleanup` — git, tracking, structure
- `### MCP Configuration` — MCP server changes
- `### Architecture` — boundary, design changes

## Rules

1. **Date header**: `## YYYY-MM-DD` — use today's date
2. **Group by category**: put related changes under same `###` header
3. **File references**: mention changed files in parens or backticks
4. **Test counts**: update when they change (e.g., "→ 695 passed, 3 skipped")
5. **Append only**: never rewrite history, add to top
6. **One line per change**: keep entries scannable
7. **Link to issues/PRs**: include `(#123)` when relevant

## Example Entry

```markdown
## 2026-05-13

### Public Docs Sync
- Updated test counts across README.md and docs/DEV_TESTING.md → 695 passed, 3 skipped
- Fixed mismatched email link in CODE_OF_CONDUCT.md

### AICtx Integration — M1 Complete
- Imported AICtx source via filtered-history subtree merge into agentheim/vendor/aictx/
- Defined ContextOps ABC in agentheim/context_ops.py
- Vendor unit tests: 101 passed
```

## What Not to Include

- Internal implementation details invisible to users
- Changes that are fully covered by another entry
- WIP or planned work (only completed changes)
- Formatting-only changes unless they fix rendering bugs

## Verification

After writing, run:
```bash
python scripts/check-agent-instructions.py
```
Or validate markdown renders correctly.
