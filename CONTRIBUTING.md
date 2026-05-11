# Contributing to Agentheim

> **Full contribution guide is at [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).**

This file provides quick-start instructions. For the complete guide — including phase-locked development, cross-boundary changes, subsystem ownership, and architecture checks — see the documentation directory.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/0langa/agentheim.git
cd agentheim

# 2. Install dependencies
pip install -e .

# 3. Run the test suite
pytest tests\ -q        # Windows
PYTHONPATH="." pytest tests/ -q             # Linux/Mac

# 4. Run the architecture check
python scripts/roadmap-check.py --phase 7
```

## Documentation

All project documentation is in the [`docs/`](docs/README.md) directory:

| Document | Description |
|----------|-------------|
| [Contributing Guide](docs/CONTRIBUTING.md) | Full development setup, standards, and governance |
| [Architecture](docs/ARCHITECTURE.md) | System design, module overview, boundary rules |
| [Development & Testing](docs/DEV_TESTING.md) | Complete test command reference |
| [Roadmap](docs/roadmap/) | Architecture specification (design docs) |

## Key Rules

- `core/` knows no provider, model, workflow, or tool names
- All tool calls go through the policy engine
- All runs produce append-only event ledgers
- Safety is the default state
- Run `python scripts/roadmap-check.py --phase 7 --ci` before submitting

- **Type hints** required for all public methods
- **Docstrings** for all public APIs
- **Tests** for all new functionality
- **No hardcoded secrets** — use env vars or config files
- **No provider/workflow/tool names in `core/`** — use protocols and registries

## Testing Guidelines

| Test Type | Location | Coverage Target |
|-----------|----------|----------------|
| Unit tests | `tests/core/`, `tests/memory/` | >80% for new code |
| Tool tests | `tests/test_*_tool.py` | All operations covered |
| Integration | `tests/test_api_server.py`, `tests/test_web_ui.py` | Critical paths |
| Smoke tests | `tests/smoke/` | End-to-end workflow execution |

## Getting Help

- **General questions:** Open a [discussion](https://github.com/0langa/agentheim/discussions) (if enabled) or an issue with `[QUESTION]` prefix
- **Bug reports:** Use the bug report template
- **Security issues:** See [SECURITY.md](SECURITY.md) — do NOT open public issues

## Architecture Resources

If you want to understand the system deeply:

- [`docs/roadmap/00_PROJECT_DOCTRINE.md`](docs/roadmap/00_PROJECT_DOCTRINE.md) — Core principles and laws
- [`docs/roadmap/02_CORE_ARCHITECTURE_PRINCIPLES.md`](docs/roadmap/02_CORE_ARCHITECTURE_PRINCIPLES.md) — Structure and boundaries
- [`docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md`](docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md) — Current phase and unlocked subsystems

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
