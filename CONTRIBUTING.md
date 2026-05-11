# Contributing to Agentheim

Thanks for your interest in contributing! This guide covers everything you need to get started.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/0langa/agentheim.git
cd agentheim

# 2. Install dependencies
pip install -e .

# 3. Run the test suite
$env:PYTHONPATH="."; pytest tests\ -q        # Windows
PYTHONPATH="." pytest tests/ -q             # Linux/Mac

# 4. Run the architecture check
python scripts/roadmap-check.py --phase 6
```

## Development Setup

### Requirements
- Python 3.12+
- Git
- (Optional) Playwright for browser tool tests: `playwright install chromium`

### Install in editable mode
```bash
pip install -e .
```

### Running tests
```bash
# Full suite
$env:PYTHONPATH="."; pytest tests\ -v

# Specific module
$env:PYTHONPATH="."; pytest tests\test_api_server.py -v

# With coverage
$env:PYTHONPATH="."; pytest tests\ --cov=core --cov=tools --cov=workflows
```

### Running the CLI locally
```bash
python -m ai_team doctor
python -m ai_team ping-models
python -m ai_team inspect --repo .
```

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
docs/roadmap/   # Architecture roadmap
```

**Key rule:** `core/` knows no provider, model, workflow, or tool names. Everything concrete lives in its own subsystem.

## How to Contribute

### 1. Pick an issue
- Check [open issues](https://github.com/0langa/agentheim/issues) for `good first issue` or `help wanted`
- Or propose a new feature via an issue first

### 2. Create a branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make your changes
- Follow existing code style (type hints, docstrings for public methods)
- Add tests for new code
- Keep changes focused — one concern per PR

### 4. Run checks before submitting
```bash
# Tests must pass
$env:PYTHONPATH="."; pytest tests\ -q

# Architecture check must pass
python scripts/roadmap-check.py --phase 6 --ci
```

### 5. Submit a PR
- Fill out the PR template
- Link related issues
- Keep the description focused on *what* and *why*

## Code Standards

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
