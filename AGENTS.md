# Custom Agents for Agentheim

This file documents Copilot custom agents and skills available for working on the Agentheim codebase.

## Skills (Copilot Agent Skills)

Skills are located in the `skills/` directory and provide domain-specific knowledge for AI agents working on this project.

| Skill | Description | Location |
|-------|-------------|----------|
| **agentheim-devtest-runner** | Run devtest workflows, interpret results, and validate test gates | `skills/agentheim-devtest-runner/` |
| **agentheim-release-hygiene** | Release checklist, version bumping, CHANGELOG review, and packaging | `skills/agentheim-release-hygiene/` |
| **agentheim-roadmap-guard** | Phase gate enforcement, architecture violation detection | `skills/agentheim-roadmap-guard/` |

## Instructions (Copilot Instructions)

Project-level instruction files for AI agents are in `~/.vscode/agents/` (user-wide) and this repository's documentation.

### Key Reference Documents

- [docs/README.md](docs/README.md) — Documentation index
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — Contribution guide with agent preamble
- [docs/roadmap/AGENT_POCKET_CARD.md](docs/roadmap/AGENT_POCKET_CARD.md) — One-page cheat sheet for autonomous agents
- [docs/roadmap/00_PROJECT_DOCTRINE.md](docs/roadmap/00_PROJECT_DOCTRINE.md) — The 7 Immutable Laws (supreme authority)
- [docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md](docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md) — Current phase and unlocked subsystems

### Agent Preamble

When starting work with an AI agent, provide this preamble:

```markdown
## OPERATING CONTEXT
**Project:** agentheim
**Current Phase:** 7 (Production Hardening)
**My Subsystem:** [your assigned directory]
**Task:** [description]
```

## Architecture Check

Before submitting changes, always run:

```bash
python scripts/roadmap-check.py --phase 7 --ci
```