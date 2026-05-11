# Agentheim Documentation

> **A local-first, preset-driven AI automation platform.**
> *Simple on the surface. Serious underneath. Extensible when needed. Safe by default. Local-first by default.*

---

## 📖 Documentation Index

### 🧑‍💻 For Users

| Document | What you'll find |
|----------|-----------------|
| [User Guide](USER_GUIDE.md) | Installation, configuration, CLI commands, presets, and daily usage |
| [Troubleshooting](TROUBLESHOOTING.md) | Common issues, diagnostics, and recovery steps |
| [Safety & Security](SAFETY.md) | Privacy modes, approval gates, threat model, and reporting |

### 🏗️ For Developers

| Document | What you'll find |
|----------|-----------------|
| [Architecture](ARCHITECTURE.md) | System design, module overview, runtime phases, boundary rules |
| [API Reference](API_REFERENCE.md) | REST API endpoints, SDK usage, WebSocket streaming |
| [Contributing](CONTRIBUTING.md) | Setup, coding standards, PR workflow, and governance |
| [Development & Testing](DEV_TESTING.md) | Test commands, smoke tests, devtest runner, CI |
| [Changelog](CHANGELOG.md) | Release history and notable changes |
| [AICtx Integration Plan](AICTX_INTEGRATION_PLAN.md) | Milestone plan for fully absorbing AICtx into Agentheim |

### 📐 Architecture Roadmap (Design Docs)

The [roadmap/](roadmap/) directory contains the architectural specification that governs development:

| # | Document | Purpose |
|---|----------|---------|
| 00 | [Project Doctrine](roadmap/00_PROJECT_DOCTRINE.md) | **Immutable** — 7 Laws, identity statement, anti-patterns |
| 01 | [System Vision](roadmap/01_SYSTEM_VISION.md) | Three-layer user model, progressive disclosure |
| 02 | [Core Architecture Principles](roadmap/02_CORE_ARCHITECTURE_PRINCIPLES.md) | Directory structure, runtime invariants, subsystem separation |
| 03 | [Execution Model](roadmap/03_EXECUTION_MODEL.md) | Workflow DAG, retry, budgets, event sourcing |
| 04 | [Swarm Governance](roadmap/04_SWARM_GOVERNANCE.md) | Agent coordination, handoff, escalation |
| 05 | [Repository Boundaries](roadmap/05_REPOSITORY_BOUNDARIES.md) | Ownership domains, merge rules, forbidden behaviors |
| 06 | [Phased Development Plan](roadmap/06_PHASED_DEVELOPMENT_PLAN.md) | **Active** — current phase, exit gates, as-built notes |
| 07–20 | [Subsystem Definitions & Future](roadmap/) | Provider architecture, memory, tools, safety, future plans |
| — | [Agent Pocket Card](roadmap/AGENT_POCKET_CARD.md) | One-page cheat sheet for AI agents working on this codebase |

---

## 📁 Doc File Map

```
docs/
├── README.md              ← You are here
├── USER_GUIDE.md          # Install, configure, use the CLI and presets
├── ARCHITECTURE.md        # System design, modules, boundaries
├── API_REFERENCE.md       # REST API endpoints and integration
├── CONTRIBUTING.md        # Developer setup and contribution workflow
├── SAFETY.md              # Security model, privacy, threat reporting
├── TROUBLESHOOTING.md     # Common problems and solutions
├── DEV_TESTING.md         # Test commands and runner reference
├── AICTX_INTEGRATION_PLAN.md # Milestone plan for AICtx integration
├── CHANGELOG.md           # Release history
└── roadmap/               # Architectural specification (design docs)
    ├── 00_PROJECT_DOCTRINE.md
    ├── ...
    └── AGENT_POCKET_CARD.md
```

---

## 🔗 Quick Links

- [GitHub Repository](https://github.com/0langa/agentheim)
- [Issue Tracker](https://github.com/0langa/agentheim/issues)
- [Security Policy](SAFETY.md#reporting-a-vulnerability)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
