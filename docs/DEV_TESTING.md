# Development & Testing

> Complete reference for running tests, smoke checks, and the devtest runner.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Full Suite](#full-suite)
- [Targeted Subsets](#targeted-subsets)
- [DevTest Runner](#devtest-runner)
- [Baseline Smoke Gate](#baseline-smoke-gate)
- [AI Connectivity Test](#ai-connectivity-test)
- [CLI Smoke Tests](#cli-smoke-tests)
- [Docs Smoke Tests](#docs-smoke-tests)
- [Directive Governance Checks](#directive-governance-checks)
- [Agent Instruction Smoke Tests](#agent-instruction-smoke-tests)
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

Current collection status: **1256 total tests collected**. The default `pytest -q` lane selects 1220 tests and deselects 36 slow/e2e/lint tests via configured markers.

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

# Directive — docs, GitHub instructions, and governance checks
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt

# Baseline — roadmap-entry smoke gate
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt

# Legacy Phase 7 — roadmap-era production hardening gates
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode phase7 -NoPrompt

# Broad — functional + memory suites
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode broad -NoPrompt

# Full — complete validation
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -NoPrompt

# Filtered by keyword
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -K registry
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -K "not slow" -NoPrompt
```

`phase7` is a legacy roadmap-era validation mode. Prefer `directive` plus `targeted` or `broad` for current directive-system work.

---

## Baseline Smoke Gate

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt
```

Use this before roadmap implementation batches. It checks instruction drift, repo-local CLI help, doctor without connectivity, provider template loading, preset registry loading, canonical tool registry loading, and pytest collection. It does not run live AI or execute the full test suite.

---

## AI Connectivity Test

Tests provider connectivity with configured models:

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1 -AllowMismatchPurpose
```

---

## Live Validation Runner

Run bounded live checks against configured providers and record structured evidence:

```powershell
python scripts/live_validate.py --list
python scripts/live_validate.py --repo-root . --test-repo ../agentheim-testing-enviroment
python scripts/live_validate.py --only doctor,ping-models --profile azure-real
```

Output includes `evidence.jsonl`, `summary.json`, `summary.md`, and per-test stdout/stderr logs in `.localtest/runs/<timestamp>-live-validation/`.

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
files = [
    root/'README.md',
    root/'CONTRIBUTING.md',
    root/'SECURITY.md',
    root/'AGENTS.md',
]
files += sorted((root/'docs').glob('*.md'))
files += sorted((root/'.github').glob('*.md'))
files += sorted((root/'.github'/'agents').glob('*.md'))
files += sorted((root/'.github'/'instructions').glob('*.md'))
files += sorted((root/'.github'/'ISSUE_TEMPLATE').glob('*.md'))
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

Checks local Markdown links across root GitHub-facing docs, `docs/`, and GitHub Markdown files.

---

## Directive Governance Checks

```powershell
python scripts/check-agent-instructions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
```

Use these after editing root docs, `docs/`, `.github/agents/`, `.github/instructions/`, GitHub templates, skills, or devtest command guidance.

---

## Agent Instruction Smoke Tests

```powershell
python -c "from pathlib import Path; files=sorted(Path('.github/instructions').glob('*.md')); assert files and all(f.read_text(encoding='utf-8').strip() for f in files); print('instruction files ok:', [f.name for f in files])"
python -c "from pathlib import Path; p=Path('.github/agents/agentheim-autonomous-engineer.agent.md'); text=p.read_text(encoding='utf-8'); required=['00-instruction-priority.md','01-doctrine.md','02-forbidden-behaviors.md','03-traceability.md','04-AICtx-integration.md','05-documentation-integrity.md','06-tooling-and-verification.md','07-chat-output.md']; missing=[item for item in required if item not in text]; assert not missing, missing; print('agent references ok')"
```

Confirms binding `.github/instructions/*.md` files are present, non-empty, and referenced by the main autonomous engineer agent.

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
├── api_server/        # API server route tests
├── cli/               # CLI command tests
├── core/              # Core runtime tests (events, ledger, runner, policy, etc.)
├── memory/            # Memory system tests (brain, episodic, semantic, backends)
├── smoke/             # Smoke tests (CLI, presets, workflow execution, basic integration)
├── test_agent_protocol.py        # Agent message protocol tests
├── test_approval_workflow.py     # Approval gate tests
├── test_artifact_store.py        # Artifact store tests
├── test_browser_e2e.py           # Browser end-to-end tests
├── test_browser_tool.py          # Browser automation tool tests
├── test_cascading_router.py      # Cascading model router tests
├── test_context_ops_impl.py      # ContextOps implementation tests
├── test_context_ops_paths.py     # ContextOps path tests
├── test_context_packer.py        # Context packer tests
├── test_desktop_ui.py            # Desktop UI tests
├── test_distributed.py           # Distributed worker tests
├── test_distributed_transport.py # Distributed transport tests
├── test_error_classification.py  # Error classification tests
├── test_events.py                # Event system tests
├── test_federation.py            # Federation protocol tests
├── test_federation_transport.py  # Federation transport tests
├── test_import_linting.py        # Import boundary enforcement
├── test_interface_isolation.py   # Interface boundary tests
├── test_ledger_checkpoints.py    # Ledger checkpoint tests
├── test_ledger_hash.py           # Ledger hash chain tests
├── test_ledger_index.py          # Ledger index tests
├── test_legacy_aictx_reader.py   # Legacy AICtx reader tests
├── test_local_db_tool.py         # Local DB tool tests
├── test_marketplace.py           # Plugin marketplace tests
├── test_mcp.py                   # MCP integration tests
├── test_mcp_pool.py              # MCP connection pool tests
├── test_monitoring.py            # Monitoring tests
├── test_multimodal.py            # Multimodal processor tests
├── test_oci_commands.py          # OCI CLI command tests
├── test_policy_audit.py          # Policy audit tests
├── test_policy_engine.py         # Policy engine tests
├── test_privacy_enforcer.py      # Privacy mode tests
├── test_provider_adapter.py      # Provider adapter tests
├── test_provider_lazy_loading.py # Provider lazy loading tests
├── test_provider_profiles.py     # Provider profile tests
├── test_public_api.py            # Public API facade tests
├── test_replay_engine.py         # Run replay tests
├── test_resume.py                # Resume orchestrator tests
├── test_retry_engine.py          # Retry engine tests
├── test_run_executor.py          # Run executor tests
├── test_self_improving.py        # Self-improving agent tests
├── test_step_budget.py           # Step budget tests
├── test_tool_protocol.py         # Tool protocol tests
├── test_web_ui.py                # Web UI tests
├── test_workflow_isolation.py    # Workflow boundary tests
├── test_workflow_runner.py       # Workflow runner tests
└── test_workflow_runner_parallel.py # Parallel execution tests
```

---

## See Also

- [Contributing](CONTRIBUTING.md) — PR workflow and code standards
- [User Guide](USER_GUIDE.md) — installing and configuring Agentheim
