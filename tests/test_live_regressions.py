from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from core.events import EventType
from core.ledger import RunLedger
from core.policy_engine import PolicyEngine
from core.tool_protocol import ToolRegistry
from interfaces.cli.cli import app
from presets.context_maintainer import ContextMaintainerPreset
from presets.research_report import ResearchReportPreset
from tools.registry import ToolRegistry as DefaultToolRegistry, create_core_tool_registry
from workflows.research.agents.gatherer import GathererAgent, GatherResult
from tests.smoke.test_workflows import _make_model_registry
from workflows.documents.agents.indexer import IndexerOutput, IndexerAgent
from workflows.documents.agents.retriever import RetrieverAgent, RetrieverOutput
from workflows.documents.workflows.documents import DocumentsWorkflow
from workflows.documents.workflows.documents import _fallback_answer, _fallback_retrieval
from workflows.command_assistant.agents.parser import ParsedIntent, ParserAgent
from workflows.file_organization.agents.analyzer import AnalyzerAgent, AnalyzerResult
from workflows.file_organization.agents.applier import ApplierAgent, ApplierResult
from workflows.file_organization.agents.proposer import ProposerAgent, ProposerResult
from workflows.file_organization.workflows.file_organization import FileOrganizationWorkflow
from workflows.coding.adapters import tool_invoke


runner = CliRunner()


def test_provider_test_uses_resolved_default_profile(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "providers.json").write_text(
        json.dumps(
            {
                "version": 1,
                "default_profile": "azure-real",
                "profiles": {
                    "azure-real": {
                        "name": "azure-real",
                        "providers": {
                            "azure-real": {
                                "id": "azure-real",
                                "kind": "openai_compatible",
                                "endpoint": "https://example.test/v1",
                                "auth_mode": "none",
                                "timeout_seconds": 60,
                                "headers": {},
                                "metadata": {},
                            }
                        },
                        "models": {
                            "planner": {
                                "id": "planner",
                                "role": "planner",
                                "provider": "azure-real",
                                "model": "gpt-test",
                                "capabilities": ["text", "json"],
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    class _Resp:
        content = "pong"

    monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr("providers.openai_v1.OpenAIV1Provider.invoke", lambda self, request: _Resp())

    result = runner.invoke(app, ["provider", "test", "--role", "planner"])
    assert result.exit_code == 0
    assert '"profile": "azure-real"' in result.output


def test_mcp_list_missing_config_exits_zero(tmp_path: Path) -> None:
    result = runner.invoke(app, ["mcp-list", "--config", str(tmp_path / "missing.json")])
    assert result.exit_code == 0
    assert "No MCP servers configured." in result.output


def test_research_preset_passes_repo(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_run_task(*, topic: str, repo_path: str) -> tuple[str, str]:
        seen["topic"] = topic
        seen["repo_path"] = repo_path
        return ("ok", "run-dir")

    monkeypatch.setattr("workflows.research.runtime.run_task", fake_run_task)
    preset = ResearchReportPreset()
    preset.run({"topic": "hello", "repo": "C:/tmp/repo"})
    assert seen == {"topic": "hello", "repo_path": "C:/tmp/repo"}


def test_context_maintainer_preset_accepts_repo_alias(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_create(repo_root: Path, workflow_id: str):  # noqa: ARG001
        class _Ledger:
            run_dir = Path(repo_root) / ".ai-team" / "runs" / "rid"

        return _Ledger()

    def fake_create_run(run_dir: Path, workflow_id: str, preset_id: str, config: dict[str, object]):  # noqa: ARG001
        return type("_Store", (), {"run_dir": run_dir})()

    def fake_run_context_maintainer(*, repo_root: Path, scope: str, write_mode: str, ledger, artifact_store):
        seen["repo_root"] = repo_root
        seen["scope"] = scope
        seen["write_mode"] = write_mode
        return ("ok", ledger, artifact_store)

    monkeypatch.setattr("core.ledger.RunLedger.create", fake_create)
    monkeypatch.setattr("core.artifact_store.ArtifactStore.create_run", fake_create_run)
    monkeypatch.setattr("workflows.context_maintainer.runtime.run_context_maintainer", fake_run_context_maintainer)

    preset = ContextMaintainerPreset()
    preset.run({"repo": "C:/tmp/repo"})
    assert seen["repo_root"] == Path("C:/tmp/repo").resolve()
    assert seen["scope"] == "full"
    assert seen["write_mode"] == "patch"


def test_file_organization_analyzer_normalizes_mapping_output() -> None:
    agent = object.__new__(AnalyzerAgent)
    agent.output_schema = AnalyzerResult
    parsed = agent._parse(
        json.dumps(
            {
                "draft.md": {"category": "document", "confidence": 0.9},
                "temp1.txt": {"category": "document", "confidence": 0.7},
            }
        )
    )
    assert [item.path for item in parsed.files] == ["draft.md", "temp1.txt"]
    assert parsed.summary == "Classified 2 files."


def test_file_organization_prompts_include_user_goal() -> None:
    proposer = object.__new__(ProposerAgent)
    analysis = AnalyzerResult.model_validate(
        {
            "files": [{"path": "temp1.txt", "category": "text", "confidence": 0.9}],
            "summary": "one file",
        }
    )
    propose_prompt = proposer.build_propose_prompt(analysis, "Move temp1.txt into text/")
    assert "Move temp1.txt into text/" in propose_prompt

    proposal = ProposerResult.model_validate(
        {
            "actions": [{"source": "temp1.txt", "target": "text/temp1.txt", "reason": "group text files"}],
            "new_structure_summary": "text folder",
            "preview": "",
            "warnings": [],
        }
    )
    preview_prompt = proposer.build_preview_prompt(proposal, "Move temp1.txt into text/")
    assert "Move temp1.txt into text/" in preview_prompt

    applier = object.__new__(ApplierAgent)
    apply_prompt = applier.build_apply_prompt(proposal, Path("C:/tmp/repo"), "Move temp1.txt into text/")
    assert "Move temp1.txt into text/" in apply_prompt


def test_file_organization_agents_normalize_common_aliases() -> None:
    proposer = object.__new__(ProposerAgent)
    proposer.output_schema = ProposerResult
    parsed_proposal = proposer._parse(
        json.dumps(
            {
                "moves": [
                    {"source": "temp1.txt", "destination": "text/temp1.txt", "reason": "group text files"}
                ],
                "summary": "organized by extension",
            }
        )
    )
    assert parsed_proposal.actions[0].target == "text/temp1.txt"
    assert parsed_proposal.new_structure_summary == "organized by extension"

    applier = object.__new__(ApplierAgent)
    applier.output_schema = ApplierResult
    parsed_apply = applier._parse(
        json.dumps(
            {
                "moves": [
                    {"source": "temp1.txt", "destination": "text/temp1.txt", "status": "success"},
                    {"source": "temp2.log", "destination": "logs/temp2.log", "status": "failure", "error": "blocked"},
                ]
            }
        )
    )
    assert parsed_apply.moves[0].target == "text/temp1.txt"
    assert parsed_apply.moves[0].success is True
    assert parsed_apply.moves[1].success is False


def test_command_assistant_parser_accepts_boolean_parameters() -> None:
    agent = object.__new__(ParserAgent)
    agent.output_schema = ParsedIntent
    parsed = agent._parse(
        json.dumps(
            {
                "action": "list",
                "target": "files",
                "parameters": {
                    "file_type": "Python",
                    "directory": "src",
                    "recursive": True,
                },
            }
        )
    )
    assert parsed.parameters["recursive"] is True


def test_documents_agents_normalize_common_aliases() -> None:
    indexer = object.__new__(IndexerAgent)
    indexer.output_schema = IndexerOutput
    parsed_index = indexer._parse(json.dumps({"index": [{"file": "README.md", "description": "Repo doc", "tags": ["repo"]}]}))
    assert parsed_index.documents[0].path == "README.md"

    retriever = object.__new__(RetrieverAgent)
    retriever.output_schema = RetrieverOutput
    parsed_retrieval = retriever._parse(json.dumps({"results": [{"file": "README.md", "text": "hello", "score": 2}]}))
    assert parsed_retrieval.chunks[0].path == "README.md"
    assert parsed_retrieval.chunks[0].excerpt == "hello"

    gatherer = object.__new__(GathererAgent)
    gatherer.output_schema = GatherResult
    parsed_gather = gatherer._parse(
        json.dumps(
            {
                "search_queries": ["repo summary"],
                "sources": [
                    {
                        "title": "Example",
                        "url": "https://example.com",
                        "description": "summary text",
                        "relevance": "High",
                    }
                ],
                "summary": "overall summary",
            }
        )
    )
    assert parsed_gather.sources[0].snippet == "summary text"
    assert parsed_gather.raw_findings == "overall summary"


def test_documents_fallback_retrieval_finds_matching_readme() -> None:
    chunks = _fallback_retrieval(
        "what does this repo do",
        {
            "README.md": "# Test Project\nA realistic test environment for Agentheim validation.",
            "notes.txt": "misc scratch",
        },
    )
    assert chunks
    assert chunks[0]["path"] == "README.md"


def test_documents_fallback_answer_adds_citation() -> None:
    answer = _fallback_answer(
        "What does this repo do?",
        [{"path": "README.md", "excerpt": "A realistic test environment for Agentheim validation."}],
    )
    assert answer["citations"][0]["path"] == "README.md"


def test_documents_workflow_uses_real_repo_root() -> None:
    registry = _make_model_registry()
    tools = ToolRegistry()
    policy = PolicyEngine()
    ledger = RunLedger.create(Path("."), "docs-real-root-test")
    with patch.object(type(registry), "create_provider", return_value=MagicMock()):
        workflow = DocumentsWorkflow(registry, tools, policy, ledger)
    assert all(not workflow.dag.steps[step_id].workspace_isolation for step_id in ("index", "retrieve", "answer"))


def test_file_organization_workflow_uses_real_repo_root() -> None:
    registry = _make_model_registry()
    tools = ToolRegistry()
    policy = PolicyEngine()
    ledger = RunLedger.create(Path("."), "file-org-real-root-test")
    with patch.object(type(registry), "create_provider", return_value=MagicMock()):
        workflow = FileOrganizationWorkflow(registry, tools, policy, ledger)
    assert all(not workflow.dag.steps[step_id].workspace_isolation for step_id in ("analyze", "propose", "preview", "apply"))


def test_default_and_core_tool_registries_share_http_and_memory(tmp_path: Path) -> None:
    default_registry = DefaultToolRegistry(tmp_path)
    default_tool_ids = {tool.tool_id for tool in default_registry.tool_objects()}
    assert "http.request" in default_tool_ids
    assert "memory" in default_tool_ids

    core_registry = create_core_tool_registry(tmp_path, include_mcp=False)
    core_tool_ids = set(core_registry.list_tools())
    assert "http.request" in core_tool_ids
    assert "memory" in core_tool_ids


def test_command_assistant_run_writes_run_initiated_event(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    fake_parse = MagicMock(success=True, parsed_output={"action": "list", "target": "files", "parameters": {}}, raw_output="{}")
    fake_generate = MagicMock(success=True, parsed_output={"command": ["Get-ChildItem"], "explanation": "ok", "safe": True}, error=None)
    monkeypatch.setattr("workflows.command_assistant.runtime.plan_task", lambda user_input: ({}, None))
    monkeypatch.setattr("workflows.command_assistant.runtime.create_parser_agent", lambda registry: type("_P", (), {"run_parse": lambda self, text: fake_parse})())
    monkeypatch.setattr("workflows.command_assistant.runtime.create_generator_agent", lambda registry: type("_G", (), {"run_generate": lambda self, text: fake_generate})())

    from workflows.command_assistant.runtime import run_task

    report, run_dir = run_task("List files")
    assert report.status == "done"
    assert run_dir is not None
    events = RunLedger(repo_root=tmp_path, run_dir=run_dir).read_ledger()
    started = next(event for event in events if event.event_type == EventType.RUN_INITIATED)
    assert started.payload["workflow_id"] == "command_assistant"
    assert started.payload["metadata"]["user_input"] == "List files"


def test_context_maintainer_runtime_writes_final_report_and_run_initiated(monkeypatch, tmp_path: Path) -> None:
    ledger = RunLedger.create(tmp_path, "context-maintainer-regression")

    class _WriteReport:
        generated_files = ["docs/AIprojectcontext/ai-index.md"]
        lockfile_path = "docs/AIprojectcontext/context.lock.json"
        run_report = type("_RunReport", (), {"files_scanned": 3, "files_selected": 2})()
        timing = type(
            "_Timing",
            (),
            {"scan_duration_ms": 1.0, "plan_duration_ms": 2.0, "generation_duration_ms": 3.0, "total_duration_ms": 6.0},
        )()
        entropy = type("_Entropy", (), {"estimated_redundancy_ratio": 0.1, "warning": None})()

    monkeypatch.setattr("workflows.context_maintainer.runtime.AictxContextOps.run_pipeline", lambda *args, **kwargs: _WriteReport())
    (tmp_path / "docs" / "AIprojectcontext").mkdir(parents=True)
    (tmp_path / "docs" / "AIprojectcontext" / "context.lock.json").write_text("{}", encoding="utf-8")

    from workflows.context_maintainer.runtime import run_context_maintainer

    report = run_context_maintainer(tmp_path, ledger=ledger)
    assert report.run_id == ledger.run_dir.name
    assert (ledger.run_dir / "final_report.json").exists()
    events = ledger.read_ledger()
    started = next(event for event in events if event.event_type == EventType.RUN_INITIATED)
    assert started.payload["workflow_id"] == "context_maintainer"


def test_coding_tool_invoke_allows_safe_shell_verification(tmp_path: Path) -> None:
    result = tool_invoke(
        "shell.execute",
        repo_root=tmp_path,
        command=["python", "--version"],
        timeout_seconds=30,
    )
    assert "Python" in (result.stdout or result.stderr)


def test_coding_run_skips_inspect_tasks(monkeypatch, tmp_path: Path) -> None:
    from core.repo.scanner import GitSnapshot, RepoScanResult, RepoFile
    from workflows.coding.runtime import run_task

    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "main.py").write_text("def divide(a, b):\n    return a / b\n", encoding="utf-8")

    scan = RepoScanResult(
        repo_name=repo.name,
        files=[RepoFile(path="src/main.py", size=35)],
        languages=["python"],
        commands=[],
        docs=[],
        instruction_files=[],
        manifests=[],
        ci_files=[],
        git=GitSnapshot(is_git_repo=True, dirty=False),
        warnings=[],
    )

    plan_payload = {
        "summary": "Fix divide-by-zero",
        "assumptions": [],
        "non_goals": [],
        "detected_repo_type": "python",
        "risks": [],
        "task_graph": {
            "ordered_tasks": [
                {
                    "id": "task-1",
                    "type": "inspect",
                    "title": "Inspect source",
                    "dependencies": [],
                    "acceptance_criteria": [{"description": "Locate bug", "measurable": True}],
                    "max_edit_scope": "src/main.py",
                    "expected_verifier_commands": [],
                    "work_order": {
                        "id": "wo-1",
                        "title": "Inspect source",
                        "objective": "Locate bug",
                        "relevant_files": ["src/main.py"],
                        "required_context_excerpts": [],
                        "constraints": [],
                        "forbidden_changes": ["No code edits"],
                        "acceptance_criteria": [{"description": "Locate bug", "measurable": True}],
                        "expected_commands": [],
                        "max_edit_scope": "src/main.py",
                    },
                },
                {
                    "id": "task-2",
                    "type": "edit",
                    "title": "Fix source",
                    "dependencies": ["task-1"],
                    "acceptance_criteria": [{"description": "Guard zero divisor", "measurable": True}],
                    "max_edit_scope": "src/main.py",
                    "expected_verifier_commands": [],
                    "work_order": {
                        "id": "wo-2",
                        "title": "Fix source",
                        "objective": "Guard zero divisor",
                        "relevant_files": ["src/main.py"],
                        "required_context_excerpts": [],
                        "constraints": [],
                        "forbidden_changes": [],
                        "acceptance_criteria": [{"description": "Guard zero divisor", "measurable": True}],
                        "expected_commands": [],
                        "max_edit_scope": "src/main.py",
                    },
                },
            ],
            "dependencies": [{"from": "task-1", "to": "task-2"}],
        },
        "verification_strategy": [],
        "estimated_commands": [],
        "files_likely_to_change": ["src/main.py"],
        "stop_conditions": ["done"],
    }

    class _StructuredResult:
        def __init__(self, parsed_output: dict, raw_output: str | None = None) -> None:
            self.success = True
            self.parsed_output = parsed_output
            self.raw_output = raw_output or json.dumps(parsed_output)
            self.error = None

    class _Orchestrator:
        def run_structured(self, prompt: str, max_output_tokens: int = 2500):  # noqa: ARG002
            return _StructuredResult(plan_payload)

    class _Coder:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def run_work_order(self, work_order, repo_root):  # noqa: ARG002
            self.calls.append(work_order.id)
            return _StructuredResult(
                {
                    "summary": "apply fix",
                    "fileChanges": [
                        {
                            "filePath": "src/main.py",
                            "patch": "def divide(a, b):\n    if b == 0:\n        return 0\n    return a / b\n",
                        }
                    ],
                }
            )

    class _Verifier:
        def run_verification(self, *args, **kwargs):  # noqa: ARG002
            return _StructuredResult(
                {
                    "workOrderId": "wo-2",
                    "status": "passed",
                    "commandsRun": [],
                    "passedChecks": ["guard added"],
                    "failedChecks": [],
                    "diffFindings": [],
                    "missingTests": [],
                    "regressions": [],
                    "securityConcerns": [],
                    "performanceConcerns": [],
                    "fixRequests": [],
                    "finalSummary": "ok",
                }
            )

    coder = _Coder()
    monkeypatch.setattr("workflows.coding.runtime.load_team_config", lambda: object())
    monkeypatch.setattr("workflows.coding.runtime.inspect_repository", lambda repo_path: scan)
    monkeypatch.setattr("workflows.coding.runtime._resolve_context_pack", lambda repo_root, scan, ledger=None: ("ctx", False))
    monkeypatch.setattr("workflows.coding.runtime.ModelRegistry.from_team_config", lambda *args, **kwargs: object())
    monkeypatch.setattr("workflows.coding.runtime.create_orchestrator_agent", lambda registry: _Orchestrator())
    monkeypatch.setattr("workflows.coding.runtime.create_coder_agent", lambda registry: coder)
    monkeypatch.setattr("workflows.coding.runtime.create_verifier_agent", lambda registry: _Verifier())

    def fake_tool_invoke(tool_name: str, *, repo_root: Path | None = None, **kwargs):
        if tool_name == "git":
            operation = kwargs.get("operation")
            if operation == "status":
                return ""
            if operation == "diff_patch":
                return ""
        raise AssertionError(f"Unexpected tool invocation: {tool_name} {kwargs}")

    monkeypatch.setattr("workflows.coding.runtime.tool_invoke", fake_tool_invoke)

    report, run_dir = run_task("Fix divide by zero", repo, mode="apply", allow_dirty=True)
    assert report.status == "done"
    assert coder.calls == ["wo-2"]
    assert (run_dir / "inspect_task-1.md").exists()
    patch_attempts = (run_dir / "patch_attempts.jsonl").read_text(encoding="utf-8")
    assert '"task_id": "task-1"' not in patch_attempts
    assert '"task_id": "task-2"' in patch_attempts


def test_coding_file_change_accepts_path_aliases() -> None:
    from core.schemas_runtime import FileChange, PatchPlan

    for alias in ("path", "filePath", "FilePath", "file_path", "file", "filename"):
        change = FileChange.model_validate({alias: "src/main.py", "patch": "x = 1\n"})
        assert change.path == "src/main.py"
        assert change.patch == "x = 1\n"

    # PascalCase patch + ChangeType aliases
    change2 = FileChange.model_validate({"FilePath": "a.py", "Patch": "y = 2\n", "ChangeType": "edit"})
    assert change2.path == "a.py"
    assert change2.patch == "y = 2\n"
    assert change2.change_type == "edit"

    plan = PatchPlan.model_validate(
        {
            "file_changes": [
                {"file_path": "tests/test_main.py", "patch": "def test(): pass\n"}
            ]
        }
    )
    assert plan.file_changes[0].path == "tests/test_main.py"

    # PascalCase FileChanges wrapper
    plan2 = PatchPlan.model_validate(
        {
            "FileChanges": [
                {"FilePath": "src/main.py", "Patch": "fixed\n"}
            ]
        }
    )
    assert len(plan2.file_changes) == 1
    assert plan2.file_changes[0].path == "src/main.py"

    # patchPlan / patches aliases
    plan3 = PatchPlan.model_validate(
        {"patchPlan": [{"file": "a.py", "patch": "x\n"}]}
    )
    assert len(plan3.file_changes) == 1
    assert plan3.file_changes[0].path == "a.py"

    plan4 = PatchPlan.model_validate(
        {"patches": [{"file": "b.py", "patch": "y\n"}]}
    )
    assert len(plan4.file_changes) == 1
    assert plan4.file_changes[0].path == "b.py"
