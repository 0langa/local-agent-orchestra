# Agentheim

[![Tests](https://img.shields.io/badge/tests-1133%20collected-blue)](https://github.com/0langa/agentheim/actions)
[![Architecture](https://img.shields.io/badge/architecture-local_first-blue)](docs/ARCHITECTURE.md)
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
| [Agent Operations](docs/AGENT_OPERATIONS.md) | Agent instructions, skills, validation, and future MCP guidance |
| [Changelog](docs/CHANGELOG.md) | Release history |

---

## 🚀 Quick start

### Install

```powershell
pip install -e .
```

### Configure

Configure providers via the CLI (secrets stored in OS keychain):

```powershell
agentheim provider add openai --template openai_v1 --model gpt-4o-mini --role planner
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

Current local collection: **1133 total tests collected**. The default `pytest -q` lane selects 1098 tests and deselects 35 slow/e2e/lint tests via configured markers.

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
├── docs/               # Unified documentation
└── .github/            # Agent, instruction, workflow, and issue templates
```

---

## 📄 Documentation

- [Docs Index](docs/README.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Safety & Security](docs/SAFETY.md)
- [Agent Instructions](AGENTS.md)

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, architecture rules, and governed development workflow.

---

## 📜 License

MIT — see [LICENSE](LICENSE).
