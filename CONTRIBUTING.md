# Contributing to local-agent-orchestra

## Before You Start

### 1. Read the Roadmap
This project is governed by a strict architecture roadmap in `docs/roadmap/`. Every contributor must understand:

- **00_PROJECT_DOCTRINE.md** — The 7 Immutable Laws (supreme authority)
- **06_PHASED_DEVELOPMENT_PLAN.md** — Which phase we're in and what's unlocked
- **02_CORE_ARCHITECTURE_PRINCIPLES.md** — Directory structure and boundary rules
- **05_REPOSITORY_BOUNDARIES.md** — Subsystem ownership

### 2. Context Preamble (Required)

When starting work with an AI agent, paste this preamble:

```markdown
## OPERATING CONTEXT
**Project:** local-agent-orchestra
**Current Phase:** [see 01-phase-lock.md]
**My Subsystem:** [your assigned directory]
**Task:** [description]

### Laws Check
- [ ] No provider-specific logic in core/
- [ ] No workflow-specific logic in core/
- [ ] All tool calls through policy engine
- [ ] Event-sourced, no mutable state
- [ ] Local-first, privacy-respecting
- [ ] Safety by default
- [ ] Progressive disclosure preserved
```

### 3. Run Architecture Checks

```bash
# Before committing
python scripts/roadmap-check.py --phase [CURRENT_PHASE]

# In CI (blocks merge on failure)
python scripts/roadmap-check.py --ci --phase [CURRENT_PHASE]
```

## Development Workflow

### Phase-Locked Development
We use strict phase gates. Check `docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md` for the current phase.

**Rules:**
- Only implement subsystems unlocked for the current phase
- Do NOT implement Phase 6 (RESERVED) systems
- Do NOT modify locked subsystems without Architecture Lead approval

### Subsystem Ownership
Every directory has a primary owner. See `docs/roadmap/05_REPOSITORY_BOUNDARIES.md`.

**Rules:**
- You may modify files within your assigned subsystem
- You may NOT modify files in another subsystem without owner approval
- You may NOT modify `docs/roadmap/` without Architecture Lead approval

### Cross-Boundary Changes
If your change touches multiple subsystems:

1. Create an RFC in `docs/rfc/` describing the change and cross-boundary impact
2. Get Architecture Lead review
3. Get approval from ALL affected subsystem owners
4. Implement in a feature branch
5. All integration tests must pass
6. Architecture Lead performs final merge

## Code Standards

### Architecture Invariants
- Core runtime is provider-agnostic, workflow-agnostic, tool-agnostic
- All tool calls go through `tools.base.ToolProtocol`
- All provider access goes through `providers.base.ProviderProtocol`
- All workflow execution goes through `workflows.base.Workflow`
- All runs produce full artifact sets in `runs/<run-id>/`
- All events are append-only in the ledger

### Testing
- Unit tests: >80% coverage for all new code
- Integration tests for all cross-subsystem interactions
- Run `pytest` before submitting PR
- Run `python scripts/roadmap-check.py` before submitting PR

### Documentation
- Docstrings for all public methods
- Update relevant docs in `docs/` for user-facing changes
- Add CHANGELOG entry for all changes

### Commit Messages
```
[subsystem] Brief description

- What changed
- Why it changed
- Which phase gate it advances (if any)

Refs: #issue-number
```

## Pull Request Checklist

- [ ] Roadmap check passes: `python scripts/roadmap-check.py --ci`
- [ ] Tests pass: `pytest`
- [ ] No architectural law violations
- [ ] Only unlocked subsystems modified
- [ ] Docs updated for user-facing changes
- [ ] CHANGELOG entry added
- [ ] Subsystem owner approval (if applicable)
- [ ] Architecture Lead approval (for cross-boundary changes)

## Getting Help

- Architecture questions: Open an issue with `[ARCH]` prefix
- Phase advancement: Contact Architecture Lead
- Subsystem ownership: See `docs/roadmap/05_REPOSITORY_BOUNDARIES.md`
- Security concerns: Open an issue with `[SECURITY]` prefix

## Enforcement

Violations are classified by level:

| Level | Name | Action |
|-------|------|--------|
| 1 | Style | Auto-corrected |
| 2 | Boundary | Requires review before merge |
| 3 | Architecture | Blocks merge, triggers review |
| 4 | Constitutional | Immediate revert, swarm notification |

The CI pipeline enforces these automatically via `scripts/roadmap-check.py --ci`.
