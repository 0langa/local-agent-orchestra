# Contributing to Agentheim

> Development setup, coding standards, PR workflow, and governance for contributors.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Before You Start](#before-you-start)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [How to Contribute](#how-to-contribute)
- [Code Standards](#code-standards)
- [Commit Messages](#commit-messages)
- [Phase-Locked Development](#phase-locked-development)
- [Cross-Boundary Changes](#cross-boundary-changes)

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/0langa/agentheim.git
cd agentheim

# 2. Install dependencies
pip install -e .

# 3. Run the test suite
pytest tests\ -q                  # Windows
PYTHONPATH="." pytest tests/ -q   # Linux/Mac

# 4. Run the architecture check
python scripts/roadmap-check.py --phase 7
```

---

## Before You Start

### Read the Roadmap

This project is governed by a strict architecture roadmap in `docs/roadmap/`. Every contributor must understand:

- **[00_PROJECT_DOCTRINE.md](roadmap/00_PROJECT_DOCTRINE.md)** — The 7 Immutable Laws (supreme authority)
- **[06_PHASED_DEVELOPMENT_PLAN.md](roadmap/06_PHASED_DEVELOPMENT_PLAN.md)** — Which phase we're in and what's unlocked
- **[02_CORE_ARCHITECTURE_PRINCIPLES.md](roadmap/02_CORE_ARCHITECTURE_PRINCIPLES.md)** — Directory structure and boundary rules
- **[05_REPOSITORY_BOUNDARIES.md](roadmap/05_REPOSITORY_BOUNDARIES.md)** — Subsystem ownership

### Context Preamble for AI Agents

When starting work with an AI agent, paste this preamble:

```markdown
## OPERATING CONTEXT
**Project:** agentheim
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

### Run Architecture Checks

```bash
# Before committing
python scripts/roadmap-check.py --phase 7

# In CI (blocks merge on failure)
python scripts/roadmap-check.py --ci --phase 7
```

---

## Development Setup

### Requirements

- **Python 3.12+**
- **Git**
- **(Optional) Playwright** for browser tool tests: `playwright install chromium`

### Install in Editable Mode

```bash
pip install -e .
```

### Running Tests

```bash
# Full suite
pytest tests\ -v

# Specific module
pytest tests\test_api_server.py -v

# With coverage
pytest tests\ --cov=core --cov=tools --cov=workflows

# DevTest runner modes
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode narrow
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -NoPrompt
```

See [Development & Testing](DEV_TESTING.md) for the complete test reference.

### Running the CLI Locally

```bash
python -m interfaces.cli.cli doctor
python -m interfaces.cli.cli ping-models
python -m interfaces.cli.cli inspect --repo .
```

---

## Project Structure

```
core/           # Generic runtime engine — provider/workflow/tool agnostic
providers/      # Lazy-loaded provider adapters
workflows/      # Workflow packs (coding, research, documents, ...)
tools/          # Mediated tools with policy gating
memory/         # Three-tier memory system
interfaces/     # CLI, TUI, Web UI, API server, Desktop UI
presets/        # Beginner-friendly preset definitions
tests/          # Full test suite
docs/           # Documentation (roadmap, user guide, API, architecture)
scripts/        # Tooling (roadmap checker, etc.)
```

**Key rule:** `core/` knows no provider, model, workflow, or tool names. Everything concrete lives in its own subsystem.

---

## How to Contribute

### 1. Pick an Issue

- Check [open issues](https://github.com/0langa/agentheim/issues) for `good first issue` or `help wanted`
- Or propose a new feature via an issue first

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Make Your Changes

- Follow existing code style (type hints, docstrings for public methods)
- Add tests for new code
- Keep changes focused — one concern per PR
- Respect [subsystem boundaries](roadmap/05_REPOSITORY_BOUNDARIES.md)

### 4. Run Checks Before Submitting

```bash
# Tests must pass
pytest tests\ -q

# Architecture check must pass
python scripts/roadmap-check.py --phase 7 --ci
```

### 5. Submit a PR

- Fill out the [PR template](../.github/PULL_REQUEST_TEMPLATE.md)
- Link related issues
- Keep the description focused on *what* and *why*

---

## Code Standards

### Architecture Invariants

- Core runtime is provider-agnostic, workflow-agnostic, tool-agnostic
- All tool calls go through `core.tool_protocol`
- All provider access goes through `providers.base`
- All workflow execution goes through `workflows.base.Workflow`
- All runs produce full artifact sets in `.ai-team/runs/<run-id>/`
- All events are append-only in the ledger

### Import Rules

| Module | May Import From | May NOT Import From |
|--------|----------------|-------------------|
| `core/` | `core.*`, `providers.base`, `tools.base`, `workflows.base`, `memory.base` | Any concrete implementation |
| `workflows/` | `core.public_api`, `workflows.base` | `core.*` internals, provider implementations |
| `providers/` | `providers.base`, `core.types` | Other provider adapters |
| `tools/` | `core.public_api`, `tools.base` | Other tool implementations |
| `interfaces/` | `core.public_api` ONLY | Any `core.*` internal module |

### Testing

- Unit tests: >80% coverage for all new code
- Integration tests for all cross-subsystem interactions
- Run `pytest` before submitting PR
- Run `python scripts/roadmap-check.py` before submitting PR

### Documentation

- Docstrings for all public methods
- Update relevant docs in `docs/` for user-facing changes
- Add CHANGELOG entry for all changes

---

## Commit Messages

```
[subsystem] Brief description

- What changed
- Why it changed
- Which phase gate it advances (if any)
```

---

## Phase-Locked Development

We use strict phase gates. Check [`docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md`](roadmap/06_PHASED_DEVELOPMENT_PLAN.md) for the current phase.

**Rules:**
- Only implement subsystems unlocked for the current phase
- Do NOT implement future-phase systems
- Do NOT modify locked subsystems without Architecture Lead approval

### Phase Advancement Protocol

When ALL exit gates for a phase pass:

1. Architecture Lead updates `docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md` — mark gates passed
2. Update `.kimi/rules/01-phase-lock.md` — new phase, new unlocked/locked lists
3. Update CI workflow — change `--phase N` to `--phase N+1`
4. Announce to team — which subsystems are now unlocked
5. Update `AGENT_POCKET_CARD.md` — new phase status

Do NOT advance a phase until ALL gates pass. Partial advancement is forbidden.

---

## Cross-Boundary Changes

If your change touches multiple subsystems:

1. Create an RFC in `docs/rfc/` describing the change and cross-boundary impact
2. Get Architecture Lead review
3. Get approval from ALL affected subsystem owners
4. Implement in a feature branch
5. All integration tests must pass
6. Architecture Lead performs final merge

---

## See Also

- [Architecture](ARCHITECTURE.md) — system design and module overview
- [Development & Testing](DEV_TESTING.md) — complete test reference
- [Roadmap: Project Doctrine](roadmap/00_PROJECT_DOCTRINE.md) — immutable laws
- [Roadmap: Repository Boundaries](roadmap/05_REPOSITORY_BOUNDARIES.md) — ownership and merge rules
