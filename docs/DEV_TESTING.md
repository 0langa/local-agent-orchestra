# Development & Testing

> Complete reference for running tests, smoke checks, and the devtest runner.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Full Suite](#full-suite)
- [Targeted Subsets](#targeted-subsets)
- [DevTest Runner](#devtest-runner)
- [AI Connectivity Test](#ai-connectivity-test)
- [CLI Smoke Tests](#cli-smoke-tests)
- [Docs Smoke Tests](#docs-smoke-tests)
- [Workflow Smoke Tests](#workflow-smoke-tests)
- [Preset Smoke Tests](#preset-smoke-tests)
- [Memory Smoke Tests](#memory-smoke-tests)
- [Module Test Suites](#module-test-suites)
- [Test Organization](#test-organization)

---

## Quick Start

```bash
pip install -e .
pytest -q
```

---

## Full Suite

```bash
pytest -q tests/
```

Current status: **692 passed, 3 skipped** (skipped tests are optional GUI-environment checks when desktop dependencies are unavailable).

---

## Targeted Subsets

```bash
pytest -q tests/core/test_model_registry.py tests/smoke/test_cli.py tests/smoke/test_presets.py
pytest -q tests/core/test_model_registry.py tests/core/test_schemas.py tests/core/test_ledger.py tests/smoke/test_cli.py tests/smoke/test_presets.py tests/test_mcp.py tests/test_local_db_tool.py
```

---

## DevTest Runner

The devtest runner provides organized test modes for different validation scenarios:

```powershell
# Narrow — focused subset
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode narrow

# Targeted — specific test areas
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted

# Phase 7 — production hardening gates
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode phase7 -NoPrompt

# Broad — functional + memory suites
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode broad -NoPrompt

# Full — complete validation
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -NoPrompt

# Filtered by keyword
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -K registry
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -K "not slow" -NoPrompt
```

---

## AI Connectivity Test

Tests provider connectivity with configured models:

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1 -AllowMismatchPurpose
```

---

## CLI Smoke Tests

```bash
python -m interfaces.cli.cli --help
python -m interfaces.cli.cli doctor --skip-connectivity
python -m interfaces.cli.cli presets
python -m interfaces.cli.cli inspect --repo .
python -m interfaces.cli.cli start codebase-assistant --help
python -m interfaces.cli.cli guided --help
```

Use the repo-local module entry for CLI smoke checks. In environments with another `agentheim.exe` already installed, the global console script can resolve to a different checkout.

---

## Docs Smoke Tests

```powershell
@'
import re
from pathlib import Path
root = Path('.').resolve()
files = [root/'README.md', root/'CONTRIBUTING.md', root/'AGENTS.md'] + sorted((root/'docs').glob('*.md')) + [root/'Agent-Team'/'README.md']
link_re = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
problems = []
for f in files:
    if not f.exists():
        continue
    text = f.read_text(encoding='utf-8')
    for target in link_re.findall(text):
        target = target.strip()
        if not target or target.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        target = target.split('#', 1)[0]
        p = (f.parent / target).resolve()
        if not p.exists():
            problems.append((str(f.relative_to(root)), target))
if problems:
    for src, target in problems:
        print(f'BROKEN {src} -> {target}')
    raise SystemExit(1)
print('markdown links ok')
'@ | python -
```

Checks local Markdown links across the root docs, `docs/`, and `Agent-Team/README.md`.

---

## Workflow Smoke Tests

```bash
python -c "from workflows.registry import register_builtin_workflows; from core.capability_registry import list_workflows; register_builtin_workflows(); print('registered workflows:', [e.id for e in list_workflows()])"
python -c "from workflows.documents import DocumentsWorkflow; print('documents workflow import ok')"
python -c "from workflows.documents.runtime import plan_task, run_task; print('documents runtime import ok')"
python -c "from workflows.file_organization import FileOrganizationWorkflow; print('file_organization workflow import ok')"
python -c "from workflows.file_organization.runtime import plan_task, run_task; print('file_organization runtime import ok')"
```

---

## Preset Smoke Tests

```bash
python -c "from presets import PRESET_REGISTRY; print('presets registered:', [p.preset_id for p in PRESET_REGISTRY.list()])"
python -c "from presets.codebase_assistant import CodebaseAssistantPreset; print('codebase preset ok')"
python -c "from presets.local_document_chat import LocalDocumentChatPreset; print('documents preset ok')"
python -c "from presets.research_report import ResearchReportPreset; print('research preset ok')"
python -c "from presets.file_organizer import FileOrganizerPreset; print('file org preset ok')"
python -c "from presets.docs_maintainer import DocsMaintainerPreset; print('docs maintainer preset ok')"
python -c "from presets.github_maintainer import GitHubMaintainerPreset; print('github preset ok')"
python -c "from presets.command_assistant import CommandAssistantPreset; print('command preset ok')"
python -c "from interfaces.guided_tui.app import run_guided_tui; print('guided TUI import ok')"
```

---

## Memory Smoke Tests

```bash
python -c "from pathlib import Path; from memory.brain import Brain; b = Brain(Path('.')); b.perceive('test','action','ok'); print('brain ok')"
python -c "from pathlib import Path; from memory.episodic import EpisodicMemory; e = EpisodicMemory(Path('.ai-team/memory/episodes')); e.record('ctx','act'); print('episodic ok')"
python -c "from pathlib import Path; from memory.semantic import SemanticMemory; s = SemanticMemory(Path('.ai-team/memory/semantic')); s.learn('x','X'); print('semantic ok')"
python -c "from memory.embeddings import get_engine; v = get_engine().encode('hello'); print('embedding dim:', len(v))"
python -c "from pathlib import Path; from memory.bus import MemoryBus; b = MemoryBus(Path('.')); b.write('jsonl','k',{'v':1}); print('bus ok')"
python -c "from memory.tiers.working import WorkingMemory; wm = WorkingMemory(); wm.set('k','v'); print('working memory ok:', wm.get('k'))"
python -c "from memory.tiers.global_ import GlobalMemory; gm = GlobalMemory(base_path=Path('.ai-team/memory/global-test')); gm.set_preference('theme','dark'); print('global memory ok:', gm.get_preference('theme'))"
python -c "from memory import WorkingMemory, GlobalMemory; print('memory tier exports ok')"
```

---

## Module Test Suites

```bash
pytest tests/core -v
pytest tests/memory -v
pytest tests/smoke -v
pytest tests/test_mcp.py -v
pytest tests/test_mcp_pool.py -v
pytest tests/test_browser_tool.py -v
```

---

## Test Organization

Tests are organized by subsystem under `tests/`:

```
tests/
├── core/              # Core runtime tests (events, ledger, runner, policy, etc.)
├── memory/            # Memory system tests (brain, episodic, semantic, backends)
├── smoke/             # Smoke tests (CLI, presets, basic integration)
├── integration/       # Cross-subsystem integration tests
├── test_mcp.py        # MCP integration tests
├── test_mcp_pool.py   # MCP connection pool tests
├── test_browser_tool.py # Browser automation tool tests
├── test_api_server.py # API server tests
├── test_web_ui.py     # Web UI tests
├── test_workflow_runner.py       # Workflow runner tests
├── test_workflow_runner_parallel.py # Parallel execution tests
├── test_workflow_isolation.py    # Workflow boundary tests
├── test_import_linting.py        # Import boundary enforcement
├── test_privacy_enforcer.py      # Privacy mode tests
├── test_approval_workflow.py     # Approval gate tests
├── test_policy_engine.py         # Policy engine tests
├── test_provider_lazy_loading.py # Provider lazy loading tests
├── test_interface_isolation.py   # Interface boundary tests
└── ...                           # Additional test modules
```

---

## See Also

- [Contributing](CONTRIBUTING.md) — PR workflow and code standards
- [User Guide](USER_GUIDE.md) — installing and configuring Agentheim
