# Agentheim

[![Tests](https://img.shields.io/badge/tests-692%20passing-brightgreen)](https://github.com/0langa/agentheim/actions)
[![Phase](https://img.shields.io/badge/phase-7%20production_hardening-blue)](docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-unified-blue)](docs/README.md)

**A local-first, preset-driven AI automation platform.**

> *Simple on the surface. Serious underneath. Extensible when needed. Safe by default. Local-first by default.*

Agentheim lets you run multi-agent workflows entirely on your own machine. Your data never leaves your box unless you explicitly allow it. Pick a preset, answer three questions, and watch a team of specialized AI agents code, research, organize, or maintain your projects.

---

## ✨ What it does

| Preset | What happens |
|--------|-------------|
| **Codebase Assistant** | Inspects → plans → patches → tests → reports on your code |
| **Research Report** | Gathers sources → summarizes → compares → writes a report |
| **Local Document Chat** | Indexes your documents → answers questions with citations |
| **File Organizer** | Analyzes → proposes → previews → applies file organization |
| **Docs Maintainer** | Detects stale documentation → updates or aligns it |
| **GitHub Maintainer** | Summarizes issues → drafts PR descriptions |
| **Command Assistant** | Parses natural language → generates safe shell commands |

All workflows run through the same core engine: a **generic, provider-agnostic orchestration runtime** with event-sourced ledgers, policy-gated tools, and capability-based model resolution.

---

## 📚 Documentation

Full documentation is available in the [`docs/`](docs/README.md) directory:

| Document | Description |
|----------|-------------|
| [User Guide](docs/USER_GUIDE.md) | Install, configure, run presets |
| [Architecture](docs/ARCHITECTURE.md) | System design, modules, boundaries |
| [API Reference](docs/API_REFERENCE.md) | REST API, WebSocket, SDK usage |
| [Contributing](docs/CONTRIBUTING.md) | Setup, standards, PR workflow |
| [Safety & Security](docs/SAFETY.md) | Privacy modes, approval gates, vulnerabilities |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [Development & Testing](docs/DEV_TESTING.md) | Test commands and runner reference |
| [Changelog](docs/CHANGELOG.md) | Release history |
| [AICtx Integration Plan](docs/AICTX_INTEGRATION_PLAN.md) | Planned full integration path for AICtx |
| [Roadmap](docs/roadmap/) | Architecture specification (design docs) |

---

## 🚀 Quick start

### Install

```powershell
pip install -e .
```

### Configure

Copy `.env.example` to `.env` and fill in your provider details:

```powershell
cp Agent-Team/.env.example .env
```

### Run a preset

```powershell
# Interactive preset picker
agentheim guided

# Or run a specific preset directly
agentheim start codebase-assistant --input repo=./my-project --input task="Review code"
```

### Check system health

```powershell
agentheim doctor
agentheim ping-models
agentheim list-runs --repo .
agentheim resume --repo . --run-id <run-id>
```

---

## 🏗️ Architecture

Agentheim serves three user layers from the same runtime:

```
Beginner (Presets)        →  Pick intent, system handles the rest
    ↓
Power-User (CLI/Config)   →  Override models, privacy modes, approval rules
    ↓
Developer (Extensible)    →  Add workflow packs, providers, tools — no core changes
    ↓
Core Runtime (Generic)    →  DAG execution, policy engine, ledger, model registry
```

**Key design principles:**
- **Core ignorance** — `core/` knows no provider, model, or workflow names
- **Local-first** — zero external services required; privacy modes enforced in code
- **Safety by default** — destructive ops require approval; policies are code, not prompts
- **Fully auditable** — every run produces an append-only event ledger
- **Provider-agnostic** — swap Grok, OpenAI, Azure, Ollama, LM Studio without code changes

---

## 🧪 Test suite

```powershell
pytest tests\ -v
```

**692 tests passing, 3 skipped in this validated environment.** The skipped tests are optional GUI-environment checks when desktop dependencies are unavailable.

---

## 📂 Repository layout

```
agentheim/
├── core/               # Generic runtime engine (provider/workflow/tool agnostic)
├── providers/          # Lazy-loaded provider adapters (OpenAI, Azure, Ollama, ...)
├── workflows/          # Workflow packs (coding, research, documents, ...)
├── tools/              # Mediated tools with policy gating (filesystem, shell, git, browser, MCP)
├── memory/             # Three-tier memory system (working, episodic, semantic, global)
├── interfaces/         # CLI, TUI, Web UI, API server, Desktop UI
├── presets/            # Beginner-friendly preset definitions
├── config/             # Configuration schemas and loader
├── tests/              # Full test suite
└── docs/roadmap/       # Architecture roadmap and subsystem definitions
```

---

## 📄 Documentation

- [Docs Index](docs/README.md)
- [AICtx Integration Plan](docs/AICTX_INTEGRATION_PLAN.md)
- [Architecture Principles](docs/roadmap/02_CORE_ARCHITECTURE_PRINCIPLES.md)
- [Safety Model](docs/roadmap/18_SAFETY_AND_PERMISSION_MODEL.md)
- [Phased Development Plan](docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md)

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, architecture rules, and the phase-locked development workflow.

---

## 📜 License

MIT — see [LICENSE](LICENSE).
