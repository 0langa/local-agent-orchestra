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
| [Support Matrix](SUPPORT_MATRIX.md) | Stable, beta, experimental, and internal support states |
| [Tier-1 Contracts](TIER1_CONTRACTS.md) | Baseline user journeys mapped to CLI/API/docs/tests |
| [Contributing](CONTRIBUTING.md) | Setup, coding standards, PR workflow, and governance |
| [Development & Testing](DEV_TESTING.md) | Test commands, smoke tests, devtest runner, CI |
| [Agent Operations](AGENT_OPERATIONS.md) | How agents, instructions, skills, docs, and validation fit together |
| [Changelog](CHANGELOG.md) | Release history and notable changes |

### 🤖 Agent And Governance Rules

The active agent governance surface is in the repository root and `.github/`:

| Document | Purpose |
|----------|---------|
| [Agent Instructions](../AGENTS.md) | GitHub-facing agent entrypoint |
| [Autonomous Engineer Agent](../.github/agents/agentheim-autonomous-engineer.agent.md) | Main project agent definition |
| [Project Doctrine](../.github/instructions/01-doctrine.md) | Binding project laws |
| [Forbidden Behaviors](../.github/instructions/02-forbidden-behaviors.md) | Rejection-level anti-patterns |
| [Traceability](../.github/instructions/03-traceability.md) | Required evidence and reporting |
| [AICtx Integration Rules](../.github/instructions/04-AICtx-integration.md) | Binding rules for AICtx integration work |

---

## 📁 Doc File Map

```
docs/
├── README.md              ← You are here
├── USER_GUIDE.md          # Install, configure, use the CLI and presets
├── ARCHITECTURE.md        # System design, modules, boundaries
├── API_REFERENCE.md       # REST API endpoints and integration
├── SUPPORT_MATRIX.md      # Current support-state promises
├── TIER1_CONTRACTS.md     # Baseline journey contracts
├── CONTRIBUTING.md        # Developer setup and contribution workflow
├── AGENT_OPERATIONS.md    # Agent operating model and validation flow
├── SAFETY.md              # Security model, privacy, threat reporting
├── TROUBLESHOOTING.md     # Common problems and solutions
├── DEV_TESTING.md         # Test commands and runner reference
└── CHANGELOG.md           # Release history
```

---

## 🔗 Quick Links

- [GitHub Repository](https://github.com/0langa/agentheim)
- [Issue Tracker](https://github.com/0langa/agentheim/issues)
- [Security Policy](SAFETY.md#reporting-a-vulnerability)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
