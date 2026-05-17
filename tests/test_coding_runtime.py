from __future__ import annotations

from pathlib import Path
from unittest.mock import DEFAULT, MagicMock, patch

import pytest

from config.config import ModelRole
from core.public_api import ExecutionError, PatchApplicationError, RuntimeState
from core.repo.command_detect import DetectedCommand
from core.repo.scanner import GitSnapshot, RepoDocument, RepoFile, RepoScanResult
from core.schemas_runtime import (
    FileChange,
    ImplementationPlan,
    PatchPlan,
    TaskGraph,
    TaskNode,
    TaskType,
    VerificationReport,
    WorkOrder,
)
from workflows.coding.runtime import PlanningError, plan_task, run_task


def _make_repo_scan_result() -> RepoScanResult:
    return RepoScanResult(
        repo_name="test-repo",
        files=[RepoFile(path="a.py", size=10)],
        languages=["python"],
        commands=[
            DetectedCommand(
                name="pytest", command=["python", "-m", "pytest"], risk_level="safe", reason="run tests"
            )
        ],
        docs=[RepoDocument(path="README.md", excerpt="docs")],
        instruction_files=[],
        manifests=[],
        ci_files=[],
        git=GitSnapshot(is_git_repo=True),
        warnings=[],
    )


def _make_work_order(task_id: str = "task-1", task_type: str = "inspect") -> WorkOrder:
    return WorkOrder(
        id=f"wo-{task_id}",
        title=f"Task {task_id}",
        objective="do something",
        relevant_files=["a.py"],
        expected_commands=[["python", "-m", "pytest"]],
    )


def _make_plan(num_tasks: int = 1, task_type: str = "inspect") -> ImplementationPlan:
    tasks: list[TaskNode] = []
    for i in range(num_tasks):
        tid = f"task-{i + 1}"
        wo = _make_work_order(tid, task_type)
        tasks.append(
            TaskNode(
                id=tid,
                type=TaskType(task_type),
                title=f"Task {tid}",
                work_order=wo,
            )
        )
    return ImplementationPlan(
        summary="test plan",
        detected_repo_type="python",
        task_graph=TaskGraph(ordered_tasks=tasks),
    )


class TestPlanTask:
    @patch("workflows.coding.runtime.create_orchestrator_agent")
    @patch("workflows.coding.runtime.ModelRegistry")
    @patch("workflows.coding.runtime.RunLedger.create")
    @patch("workflows.coding.runtime.load_team_config")
    @patch("workflows.coding.runtime._resolve_context_pack")
    @patch("workflows.coding.runtime.inspect_repository")
    def test_plan_task_raises_planning_error_on_invalid_output(
        self,
        mock_inspect_repo,
        mock_resolve_context,
        mock_load_team,
        mock_ledger_create,
        mock_model_registry,
        mock_create_orchestrator,
    ):
        mock_inspect_repo.return_value = _make_repo_scan_result()
        mock_resolve_context.return_value = ("ctx", False)
        mock_load_team.return_value = MagicMock(by_role=lambda: {ModelRole.PLANNER: MagicMock(role="planner")})
        mock_ledger = MagicMock()
        mock_ledger.run_dir = Path("/tmp/fake-run")
        mock_ledger_create.return_value = mock_ledger
        mock_model_registry.from_team_config.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error = "bad plan"
        mock_result.parsed_output = None
        mock_result.raw_output = "raw"
        mock_agent = MagicMock()
        mock_agent.run_structured.return_value = mock_result
        mock_create_orchestrator.return_value = mock_agent

        with pytest.raises(PlanningError, match="bad plan"):
            plan_task("do thing", "/tmp/fake-repo", write_ledger=True)

    @patch("workflows.coding.runtime.create_orchestrator_agent")
    @patch("workflows.coding.runtime.ModelRegistry")
    @patch("workflows.coding.runtime.RunLedger.create")
    @patch("workflows.coding.runtime.load_team_config")
    @patch("workflows.coding.runtime._resolve_context_pack")
    @patch("workflows.coding.runtime.inspect_repository")
    def test_plan_task_raises_planning_error_on_none_parsed_output(
        self,
        mock_inspect_repo,
        mock_resolve_context,
        mock_load_team,
        mock_ledger_create,
        mock_model_registry,
        mock_create_orchestrator,
    ):
        mock_inspect_repo.return_value = _make_repo_scan_result()
        mock_resolve_context.return_value = ("ctx", False)
        mock_load_team.return_value = MagicMock(by_role=lambda: {ModelRole.PLANNER: MagicMock(role="planner")})
        mock_ledger = MagicMock()
        mock_ledger.run_dir = Path("/tmp/fake-run")
        mock_ledger_create.return_value = mock_ledger
        mock_model_registry.from_team_config.return_value = MagicMock()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.parsed_output = None
        mock_result.error = None
        mock_result.raw_output = "raw"
        mock_agent = MagicMock()
        mock_agent.run_structured.return_value = mock_result
        mock_create_orchestrator.return_value = mock_agent

        with pytest.raises(PlanningError, match="Planning failed"):
            plan_task("do thing", "/tmp/fake-repo", write_ledger=False)

    @patch("workflows.coding.runtime.create_orchestrator_agent")
    @patch("workflows.coding.runtime.ModelRegistry")
    @patch("workflows.coding.runtime.RunLedger.create")
    @patch("workflows.coding.runtime.load_team_config")
    @patch("workflows.coding.runtime._resolve_context_pack")
    @patch("workflows.coding.runtime.inspect_repository")
    def test_plan_task_success_returns_plan(
        self,
        mock_inspect_repo,
        mock_resolve_context,
        mock_load_team,
        mock_ledger_create,
        mock_model_registry,
        mock_create_orchestrator,
    ):
        mock_inspect_repo.return_value = _make_repo_scan_result()
        mock_resolve_context.return_value = ("ctx", False)
        mock_load_team.return_value = MagicMock(by_role=lambda: {ModelRole.PLANNER: MagicMock(role="planner")})
        mock_ledger = MagicMock()
        mock_ledger.run_dir = Path("/tmp/fake-run")
        mock_ledger_create.return_value = mock_ledger
        mock_model_registry.from_team_config.return_value = MagicMock()

        plan = _make_plan(1, "inspect")
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.parsed_output = plan.model_dump()
        mock_result.error = None
        mock_result.raw_output = "raw"
        mock_agent = MagicMock()
        mock_agent.run_structured.return_value = mock_result
        mock_create_orchestrator.return_value = mock_agent

        scan, context_pack, returned_plan, ledger_dir = plan_task(
            "do thing", "/tmp/fake-repo", write_ledger=False
        )
        assert returned_plan.summary == plan.summary
        assert len(returned_plan.task_graph.ordered_tasks) == 1


@pytest.fixture
def run_task_mocks(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    with patch.multiple(
        "workflows.coding.runtime",
        inspect_repository=DEFAULT,
        _resolve_context_pack=DEFAULT,
        load_team_config=DEFAULT,
        RunLedger=DEFAULT,
        ModelRegistry=DEFAULT,
        create_orchestrator_agent=DEFAULT,
        create_coder_agent=DEFAULT,
        create_verifier_agent=DEFAULT,
        tool_invoke=DEFAULT,
        PatchApplier=DEFAULT,
        RuntimeStateMachine=DEFAULT,
        policy_evaluate=DEFAULT,
        GitHubCliAdapter=DEFAULT,
        MCPClientAdapter=DEFAULT,
        WebResearchAdapter=DEFAULT,
    ) as mocks:
        mocks["inspect_repository"].return_value = _make_repo_scan_result()
        mocks["_resolve_context_pack"].return_value = ("ctx", False)
        mocks["load_team_config"].return_value = MagicMock(by_role=lambda: {})

        mock_ledger = MagicMock()
        mock_ledger.run_dir = repo_path / ".ai-team" / "runs" / "test-run"
        mocks["RunLedger"].create.return_value = mock_ledger

        mocks["ModelRegistry"].from_team_config.return_value = MagicMock()

        mock_sm = MagicMock()
        mock_sm.current = RuntimeState.BLOCKED
        mocks["RuntimeStateMachine"].return_value = mock_sm

        def _tool_side_effect(tool_name, **kwargs):
            if tool_name == "git":
                return ""
            if tool_name == "shell.execute":
                return MagicMock(stdout="", stderr="", returncode=0)
            return ""

        mocks["tool_invoke"].side_effect = _tool_side_effect

        mock_applier = MagicMock()
        mock_apply_result = MagicMock()
        mock_apply_result.applied = True
        mock_apply_result.file_changes = [MagicMock(path="a.py")]
        mock_apply_result.diff_text = "diff"
        mock_applier.apply_changes.return_value = mock_apply_result
        mock_applier.rollback = MagicMock()
        mocks["PatchApplier"].return_value = mock_applier

        mocks["policy_evaluate"].return_value = {"decision": "allow"}

        mocks["GitHubCliAdapter"].return_value = MagicMock(available=False)
        mocks["MCPClientAdapter"].return_value = MagicMock(available=False)
        mocks["WebResearchAdapter"].return_value = MagicMock(available=False)

        yield {
            "repo_path": repo_path,
            "mocks": mocks,
            "ledger": mock_ledger,
            "sm": mock_sm,
            "applier": mock_applier,
        }


class TestRunTask:
    def test_run_task_writes_resume_metadata_and_uses_large_plan_budget(self, run_task_mocks):
        repo_path = run_task_mocks["repo_path"]
        mocks = run_task_mocks["mocks"]
        ledger = run_task_mocks["ledger"]

        plan = _make_plan(1, "inspect")
        mocks["create_orchestrator_agent"].return_value.run_structured.return_value = MagicMock(
            success=True, parsed_output=plan.model_dump(), raw_output="raw", error=None
        )

        run_task("do thing", repo_path)

        run_json_call = next(
            call for call in ledger.write_json.call_args_list if call.args[0] == "run.json"
        )
        run_payload = run_json_call.args[1]
        assert run_payload["workflow_id"] == "coding"
        assert run_payload["preset_id"] == "codebase-assistant"
        mocks["create_orchestrator_agent"].return_value.run_structured.assert_called_once()
        assert mocks["create_orchestrator_agent"].return_value.run_structured.call_args.kwargs["max_output_tokens"] == 6000

    def test_run_task_blocks_when_more_than_20_tasks(self, run_task_mocks):
        repo_path = run_task_mocks["repo_path"]
        mocks = run_task_mocks["mocks"]
        sm = run_task_mocks["sm"]

        plan = _make_plan(21, "inspect")
        mocks["create_orchestrator_agent"].return_value.run_structured.return_value = MagicMock(
            success=True, parsed_output=plan.model_dump(), raw_output="raw", error=None
        )
        mocks["create_coder_agent"].return_value.run_work_order.return_value = MagicMock(
            success=True, parsed_output=None, raw_output="raw", error=None
        )
        mocks["create_verifier_agent"].return_value.run_verification.return_value = MagicMock(
            success=True,
            parsed_output=VerificationReport(work_order_id="wo", status="pass").model_dump(),
            raw_output="raw",
            error=None,
        )

        with pytest.raises(ExecutionError, match="Maximum total task limit reached"):
            run_task("do thing", repo_path)

        blocked = [
            call
            for call in sm.transition.call_args_list
            if call.args and call.args[0] == RuntimeState.BLOCKED
        ]
        assert blocked
        assert blocked[-1].args[1]["reason"] == "max_total_tasks_exceeded"

    def test_run_task_fix_loop_blocks_when_total_tasks_exceeds_20(self, run_task_mocks):
        repo_path = run_task_mocks["repo_path"]
        mocks = run_task_mocks["mocks"]
        sm = run_task_mocks["sm"]

        plan = _make_plan(19, "edit")
        mocks["create_orchestrator_agent"].return_value.run_structured.return_value = MagicMock(
            success=True, parsed_output=plan.model_dump(), raw_output="raw", error=None
        )

        patch_plan = PatchPlan(file_changes=[FileChange(path="a.py", patch="diff")])
        mocks["create_coder_agent"].return_value.run_work_order.return_value = MagicMock(
            success=True, parsed_output=patch_plan.model_dump(), raw_output="raw", error=None
        )

        verifier_call_count = 0

        def _verifier_side_effect(*args, **kwargs):
            nonlocal verifier_call_count
            verifier_call_count += 1
            if verifier_call_count <= 18:
                report = VerificationReport(work_order_id="wo", status="pass")
            elif verifier_call_count == 19:
                report = VerificationReport(
                    work_order_id="wo", status="failed", failed_checks=["fail-0"]
                )
            elif verifier_call_count == 20:
                report = VerificationReport(
                    work_order_id="wo", status="failed", failed_checks=["fail-1"]
                )
            else:
                report = VerificationReport(
                    work_order_id="wo", status="failed", failed_checks=["fail-2"]
                )
            return MagicMock(
                success=True,
                parsed_output=report.model_dump(),
                raw_output="raw",
                error=None,
            )

        mocks["create_verifier_agent"].return_value.run_verification.side_effect = _verifier_side_effect

        with pytest.raises(ExecutionError, match="Maximum total task limit reached"):
            run_task("do thing", repo_path, mode="auto", max_fix_attempts=3)

        blocked = [
            call
            for call in sm.transition.call_args_list
            if call.args and call.args[0] == RuntimeState.BLOCKED
        ]
        assert blocked
        assert blocked[-1].args[1]["reason"] == "max_total_tasks_exceeded"

    def test_run_task_fix_loop_blocks_after_max_fix_attempts(self, run_task_mocks):
        repo_path = run_task_mocks["repo_path"]
        mocks = run_task_mocks["mocks"]
        sm = run_task_mocks["sm"]

        plan = _make_plan(1, "edit")
        mocks["create_orchestrator_agent"].return_value.run_structured.return_value = MagicMock(
            success=True, parsed_output=plan.model_dump(), raw_output="raw", error=None
        )

        patch_plan = PatchPlan(file_changes=[FileChange(path="a.py", patch="diff")])
        mocks["create_coder_agent"].return_value.run_work_order.return_value = MagicMock(
            success=True, parsed_output=patch_plan.model_dump(), raw_output="raw", error=None
        )

        verifier_reports = [
            VerificationReport(
                work_order_id="wo-1", status="failed", failed_checks=["fail-1"]
            ),
            VerificationReport(
                work_order_id="wo-1-fix-1", status="failed", failed_checks=["fail-2"]
            ),
            VerificationReport(
                work_order_id="wo-1-fix-2", status="failed", failed_checks=["fail-3"]
            ),
            VerificationReport(
                work_order_id="wo-1-fix-3", status="failed", failed_checks=["fail-4"]
            ),
        ]

        def _verifier_side_effect(*args, **kwargs):
            report = verifier_reports.pop(0)
            return MagicMock(
                success=True,
                parsed_output=report.model_dump(),
                raw_output="raw",
                error=None,
            )

        mocks["create_verifier_agent"].return_value.run_verification.side_effect = _verifier_side_effect

        report, run_dir = run_task("do thing", repo_path, mode="auto", max_fix_attempts=2)
        assert report.status == "blocked"

        blocked = [
            call
            for call in sm.transition.call_args_list
            if call.args and call.args[0] == RuntimeState.BLOCKED
        ]
        assert blocked
        reasons = {
            call.args[1].get("reason")
            for call in blocked
            if len(call.args) > 1 and isinstance(call.args[1], dict)
        }
        assert "max_fix_attempts_reached" in reasons


class TestCodingRuntimeRollback:
    def test_run_task_rollback_called_on_patch_apply_failure(self, run_task_mocks):
        repo_path = run_task_mocks["repo_path"]
        mocks = run_task_mocks["mocks"]
        applier = run_task_mocks["applier"]

        plan = _make_plan(1, "edit")
        mocks["create_orchestrator_agent"].return_value.run_structured.return_value = MagicMock(
            success=True, parsed_output=plan.model_dump(), raw_output="raw", error=None
        )

        patch_plan = PatchPlan(file_changes=[FileChange(path="a.py", patch="diff")])
        mocks["create_coder_agent"].return_value.run_work_order.return_value = MagicMock(
            success=True, parsed_output=patch_plan.model_dump(), raw_output="raw", error=None
        )

        mock_apply_result = MagicMock()
        mock_apply_result.applied = False
        mock_apply_result.file_changes = []
        mock_apply_result.diff_text = ""
        mock_apply_result.errors = ["apply failed"]
        applier.apply_changes.return_value = mock_apply_result

        mocks["create_verifier_agent"].return_value.run_verification.return_value = MagicMock(
            success=True,
            parsed_output=VerificationReport(work_order_id="wo", status="pass").model_dump(),
            raw_output="raw",
            error=None,
        )

        with pytest.raises(PatchApplicationError, match="apply failed"):
            run_task("do thing", repo_path)

        assert applier.rollback.called

    def test_run_task_fix_loop_rollback_called(self, run_task_mocks):
        repo_path = run_task_mocks["repo_path"]
        mocks = run_task_mocks["mocks"]
        sm = run_task_mocks["sm"]
        applier = run_task_mocks["applier"]

        plan = _make_plan(1, "edit")
        mocks["create_orchestrator_agent"].return_value.run_structured.return_value = MagicMock(
            success=True, parsed_output=plan.model_dump(), raw_output="raw", error=None
        )

        patch_plan = PatchPlan(file_changes=[FileChange(path="a.py", patch="diff")])

        call_count = 0

        def _coder_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return MagicMock(
                success=True,
                parsed_output=patch_plan.model_dump(),
                raw_output="raw",
                error=None,
            )

        mocks["create_coder_agent"].return_value.run_work_order.side_effect = _coder_side_effect

        verifier_reports = [
            VerificationReport(work_order_id="wo-1", status="failed", failed_checks=["fail-1"]),
        ]

        def _verifier_side_effect(*args, **kwargs):
            report = verifier_reports.pop(0)
            return MagicMock(
                success=True,
                parsed_output=report.model_dump(),
                raw_output="raw",
                error=None,
            )

        mocks["create_verifier_agent"].return_value.run_verification.side_effect = _verifier_side_effect

        apply_call_count = 0

        def _apply_side_effect(*args, **kwargs):
            nonlocal apply_call_count
            apply_call_count += 1
            if apply_call_count == 1:
                return MagicMock(applied=True, file_changes=[MagicMock(path="a.py")], diff_text="diff")
            return MagicMock(applied=False, file_changes=[], diff_text="", errors=["fix loop apply failed"])

        applier.apply_changes.side_effect = _apply_side_effect

        report, run_dir = run_task("do thing", repo_path, mode="auto", max_fix_attempts=1)
        assert report.status == "blocked"

        blocked = [
            call
            for call in sm.transition.call_args_list
            if call.args and call.args[0] == RuntimeState.BLOCKED
        ]
        assert blocked
        reasons = {
            call.args[1].get("reason")
            for call in blocked
            if len(call.args) > 1 and isinstance(call.args[1], dict)
        }
        assert "fix_loop_patch_failed" in reasons
        assert applier.rollback.called


class TestCodingRuntimeRepeatedFailure:
    def test_run_task_repeated_failure_guard_blocks(self, run_task_mocks):
        repo_path = run_task_mocks["repo_path"]
        mocks = run_task_mocks["mocks"]
        sm = run_task_mocks["sm"]

        plan = _make_plan(1, "edit")
        mocks["create_orchestrator_agent"].return_value.run_structured.return_value = MagicMock(
            success=True, parsed_output=plan.model_dump(), raw_output="raw", error=None
        )

        patch_plan = PatchPlan(file_changes=[FileChange(path="a.py", patch="diff")])
        mocks["create_coder_agent"].return_value.run_work_order.return_value = MagicMock(
            success=True, parsed_output=patch_plan.model_dump(), raw_output="raw", error=None
        )

        verifier_reports = [
            VerificationReport(work_order_id="wo-1", status="failed", failed_checks=["same-error"]),
            VerificationReport(work_order_id="wo-1-fix-1", status="failed", failed_checks=["same-error"]),
        ]

        def _verifier_side_effect(*args, **kwargs):
            report = verifier_reports.pop(0)
            return MagicMock(
                success=True,
                parsed_output=report.model_dump(),
                raw_output="raw",
                error=None,
            )

        mocks["create_verifier_agent"].return_value.run_verification.side_effect = _verifier_side_effect

        report, run_dir = run_task("do thing", repo_path, mode="auto", max_fix_attempts=3)
        assert report.status == "blocked"

        blocked = [
            call
            for call in sm.transition.call_args_list
            if call.args and call.args[0] == RuntimeState.BLOCKED
        ]
        assert blocked
        reasons = {
            call.args[1].get("reason")
            for call in blocked
            if len(call.args) > 1 and isinstance(call.args[1], dict)
        }
        assert "same_failure_repeated_twice" in reasons


class TestBasicVerify:
    def test_no_tests_skips_expected_commands(self, tmp_path: Path) -> None:
        from workflows.coding.runtime import _basic_verify
        from core.schemas_runtime import WorkOrder
        from core.ledger import RunLedger

        ledger = RunLedger.create(tmp_path, "test")
        wo = WorkOrder(
            id="wo-1",
            title="Task",
            objective="do thing",
            relevant_files=["a.py"],
            expected_commands=[["python", "-m", "pytest"]],
        )
        with patch("workflows.coding.runtime.tool_invoke", return_value=""):
            records, commands = _basic_verify(wo, tmp_path, ledger, 120, no_tests=True)

        assert commands == []
        basic_test_record = next((r for r in records if r.name == "basic-tests"), None)
        assert basic_test_record is not None
        assert basic_test_record.status == "skipped"
        assert "--no-tests passed" in basic_test_record.details
