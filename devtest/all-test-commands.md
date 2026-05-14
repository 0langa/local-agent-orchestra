# Test Command Reference

## Quick Start

```powershell
pip install -e .
pytest -q                # ~30s — fast subset (excludes stress/e2e/lint)
pytest -q -n auto        # ~15s — parallel fast subset (requires pytest-xdist)
```

## Full Suite

```powershell
pytest -q --override-ini="addopts="          # ~2min — all tests including slow
pytest -q --override-ini="addopts=" -n auto  # ~1min — parallel full suite
```

## Slow Tests Only

```powershell
pytest -q -m slow       # stress tests, integration tests, lint checks
pytest -q -m e2e        # real browser / network end-to-end tests
```

## Targeted Subsets

```powershell
pytest -q tests/core/test_model_registry.py tests/smoke/test_cli.py tests/smoke/test_presets.py
pytest -q tests/core/test_model_registry.py tests/core/test_schemas.py tests/core/test_ledger.py tests/smoke/test_cli.py tests/smoke/test_presets.py tests/test_mcp.py tests/test_local_db_tool.py
```

## DevTest Runner

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode narrow
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode phase7 -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode broad -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -K registry
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -K "not slow" -NoPrompt
```

`phase7` is a legacy roadmap-era validation mode. Prefer `directive` plus `targeted` or `broad` for current directive-system work.

## AI Connectivity Test

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1 -AllowMismatchPurpose
```

## CLI Smoke Tests

```powershell
python -m interfaces.cli.cli --help
python -m interfaces.cli.cli doctor --skip-connectivity
python -m interfaces.cli.cli presets
python -m interfaces.cli.cli inspect --repo .
python -m interfaces.cli.cli start codebase-assistant --help
python -m interfaces.cli.cli guided --help
```

Use the repo-local module entry for CLI smoke checks. In environments with another `agentheim.exe` already installed, the global console script can resolve to a different checkout.

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
    root/'Agent-Team'/'README.md',
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

## Directive Governance Checks

```powershell
python scripts/check-agent-instructions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
```

Use these after editing root docs, `docs/`, `.github/agents/`, `.github/instructions/`, GitHub templates, skills, or devtest command guidance.

## Agent Instruction Smoke Tests

```powershell
python -c "from pathlib import Path; files=sorted(Path('.github/instructions').glob('*.md')); assert files and all(f.read_text(encoding='utf-8').strip() for f in files); print('instruction files ok:', [f.name for f in files])"
python -c "from pathlib import Path; p=Path('.github/agents/agentheim-autonomous-engineer.agent.md'); text=p.read_text(encoding='utf-8'); required=['00-instruction-priority.md','01-doctrine.md','02-forbidden-behaviors.md','03-traceability.md','04-AICtx-integration.md','05-documentation-integrity.md','06-tooling-and-verification.md']; missing=[item for item in required if item not in text]; assert not missing, missing; print('agent references ok')"
```

## Workflow Smoke Tests

```powershell
python -c "from workflows.registry import register_builtin_workflows; from core.capability_registry import list_workflows; register_builtin_workflows(); print('registered workflows:', [e.id for e in list_workflows()])"
python -c "from workflows.documents import DocumentsWorkflow; print('documents workflow import ok')"
python -c "from workflows.documents.runtime import plan_task, run_task; print('documents runtime import ok')"
python -c "from workflows.file_organization import FileOrganizationWorkflow; print('file_organization workflow import ok')"
python -c "from workflows.file_organization.runtime import plan_task, run_task; print('file_organization runtime import ok')"
```

## Preset Smoke Tests

```powershell
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

## Memory Smoke Tests

```powershell
python -c "from pathlib import Path; from memory.brain import Brain; b = Brain(Path('.')); b.perceive('test','action','ok'); print('brain ok')"
python -c "from pathlib import Path; from memory.episodic import EpisodicMemory; e = EpisodicMemory(Path('.ai-team/memory/episodes')); e.record('ctx','act'); print('episodic ok')"
python -c "from pathlib import Path; from memory.semantic import SemanticMemory; s = SemanticMemory(Path('.ai-team/memory/semantic')); s.learn('x','X'); print('semantic ok')"
python -c "from memory.embeddings import get_engine; v = get_engine().encode('hello'); print('embedding dim:', len(v))"
python -c "from pathlib import Path; from memory.bus import MemoryBus; b = MemoryBus(Path('.')); b.write('jsonl','k',{'v':1}); print('bus ok')"
python -c "from memory.tiers.working import WorkingMemory; wm = WorkingMemory(); wm.set('k','v'); print('working memory ok:', wm.get('k'))"
python -c "from memory.tiers.global_ import GlobalMemory; gm = GlobalMemory(base_path=Path('.ai-team/memory/global-test')); gm.set_preference('theme','dark'); print('global memory ok:', gm.get_preference('theme'))"
python -c "from memory import WorkingMemory, GlobalMemory; print('memory tier exports ok')"
```

## Module Test Suites

```powershell
pytest tests/core -v
pytest tests/memory -v
pytest tests/smoke -v
pytest tests/test_mcp.py -v
pytest tests/test_mcp_pool.py -v
pytest tests/test_browser_tool.py -v
pytest tests/test_local_db_tool.py -v
pytest tests/test_web_ui.py -v
pytest tests/test_api_server.py -v
pytest tests/test_distributed.py -v
pytest tests/test_distributed_transport.py -v
pytest tests/test_marketplace.py -v
pytest tests/test_monitoring.py -v
pytest tests/test_self_improving.py -v
pytest tests/test_multimodal.py -v
pytest tests/test_federation.py -v
pytest tests/test_federation_transport.py -v
pytest tests/test_run_executor.py -v
pytest tests/test_tool_protocol.py -v
pytest tests/test_desktop_ui.py -v
```

## Legacy Architecture Check

```powershell
python scripts/roadmap-check.py --phase 7 --ci
```

`roadmap-check.py` and `phase7` mode are legacy validation paths. Prefer directive governance checks for current agent/instruction work.

## Slice 1: Event Foundation

```powershell
pytest -q tests/test_events.py -v
pytest -q tests/test_ledger_hash.py -v
pytest -q tests/test_ledger_index.py -v
pytest -q tests/test_ledger_checkpoints.py -v
```

## Slice 2: Runtime Engine

```powershell
pytest -q tests/test_error_classification.py -v
pytest -q tests/test_retry_engine.py -v
pytest -q tests/test_step_budget.py -v
pytest -q tests/test_workflow_runner.py -v
pytest -q tests/test_workflow_runner_parallel.py -v
```

## Slice 3: Artifacts & Protocols

```powershell
pytest -q tests/test_artifact_store.py -v
pytest -q tests/test_context_packer.py -v
pytest -q tests/test_agent_protocol.py -v
pytest -q tests/test_public_api.py -v
```

## Slice 4: Boundaries & Loading

```powershell
pytest -q tests/test_provider_lazy_loading.py -v
pytest -q tests/test_interface_isolation.py -v
pytest -q tests/test_workflow_isolation.py -v
pytest -q tests/test_import_linting.py -v
```

## Slice 5: Safety & Privacy

```powershell
pytest -q tests/test_policy_engine.py -v
pytest -q tests/test_privacy_enforcer.py -v
pytest -q tests/test_approval_workflow.py -v
pytest -q tests/test_policy_audit.py -v
```

## Phase 7: Production Hardening Tests (Future Slices)

```powershell
# Runtime Engine
pytest -q tests/test_error_classification.py -v
pytest -q tests/test_retry_engine.py -v
pytest -q tests/test_step_budget.py -v
pytest -q tests/test_workflow_runner.py -v
pytest -q tests/test_workflow_runner_parallel.py -v

# Artifacts & Protocols
pytest -q tests/test_artifact_store.py -v
pytest -q tests/test_context_packer.py -v
pytest -q tests/test_agent_protocol.py -v
pytest -q tests/test_public_api.py -v

# Boundaries & Loading
pytest -q tests/test_provider_lazy_loading.py -v
pytest -q tests/test_interface_isolation.py -v
pytest -q tests/test_workflow_isolation.py -v
pytest -q tests/test_import_linting.py -v

# Safety & Privacy
pytest -q tests/test_policy_engine.py -v
pytest -q tests/test_privacy_enforcer.py -v
pytest -q tests/test_approval_workflow.py -v
pytest -q tests/test_policy_audit.py -v

# Advanced Routing & Resume
pytest -q tests/test_cascading_router.py -v
pytest -q tests/test_resume.py -v
pytest -q tests/test_replay_engine.py -v
```

## Project Skills Validation

```powershell
python C:\Users\juliu\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\skills\agentheim-devtest-runner
python C:\Users\juliu\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\skills\agentheim-roadmap-guard
python C:\Users\juliu\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\skills\agentheim-release-hygiene
```
