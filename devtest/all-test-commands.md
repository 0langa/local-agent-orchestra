# Test Command Reference

## Quick Start

```powershell
pip install -e .
pytest -q
```

## Full Suite

```powershell
pytest -q tests/
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
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode broad
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -K registry
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -K "not slow"
```

## AI Connectivity Test

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1 -AllowMismatchPurpose
```

## CLI Smoke Tests

```powershell
agentheim --help
agentheim doctor
agentheim presets
agentheim inspect --repo .
agentheim start codebase-assistant --help
agentheim guided --help
```

## Workflow Smoke Tests

```powershell
python -c "import sys; sys.path.insert(0, '.'); import workflows.research; print('research workflow registered:', [e.id for e in __import__('core.capability_registry', fromlist=['list_workflows']).list_workflows()])"
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

## Architecture Check

```powershell
python scripts/roadmap-check.py --phase 6 --ci
```
