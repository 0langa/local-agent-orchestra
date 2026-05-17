"""Tests for core/resume.py — resume from interruption."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.events import EventType
from core.ledger import RunLedger
from core.policy_engine import PolicyEngine
from core.resume import ResumeError, ResumeOrchestrator, list_runs, load_run
from core.run_summary import build_run_summary
from core.tool_protocol import ToolRegistry
from core.workflow_runner import WorkflowRunner
from workflows.base import ExecutionDAG, Step, StepResult, Workflow

import json

from typer.testing import CliRunner

from core.model_registry import ModelRegistry
from interfaces.cli.cli import app


class FakeWorkflow(Workflow):
    workflow_id = "test-resume"
    required_agents = []
    required_tools = []

    def __init__(self, ledger: RunLedger | None = None, **kwargs) -> None:
        from core.model_registry import ModelRegistry

        super().__init__(
            model_registry=kwargs.get("model_registry", ModelRegistry({}, {})),
            tool_registry=kwargs.get("tool_registry", ToolRegistry()),
            policy_engine=kwargs.get("policy_engine", PolicyEngine()),
            ledger=ledger or RunLedger.create(Path("."), "dummy"),
        )
        self.dag = ExecutionDAG(
            steps=[
                Step(id="s1", agent="a", type="t"),
                Step(id="s2", agent="a", type="t"),
                Step(id="s3", agent="a", type="t"),
            ]
        )
        self.call_log: list[str] = []

    def execute_step(self, step: Step, context) -> StepResult:
        self.call_log.append(step.id)
        return StepResult(step_id=step.id, success=True, output=f"done-{step.id}")


class TestListRuns:
    def test_empty_when_no_runs(self, tmp_path: Path) -> None:
        assert list_runs(tmp_path) == []

    def test_lists_run_dirs(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / ".ai-team" / "runs"
        runs_dir.mkdir(parents=True)
        (runs_dir / "run-a").mkdir()
        (runs_dir / "run-b").mkdir()
        assert list_runs(tmp_path) == ["run-a", "run-b"]


class TestLoadRun:
    def test_missing_run_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ResumeError):
            load_run(tmp_path, "nonexistent")


class TestCanonicalRunSummary:
    def test_build_summary_from_final_report_and_ledger(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "summary")
        (ledger.run_dir / "run.json").write_text(
            json.dumps(
                {
                    "run_id": ledger.run_dir.name,
                    "workflow_id": "coding",
                    "preset_id": "codebase-assistant",
                    "created_at": "2026-05-14T10:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        ledger.emit_event(
            EventType.RUN_INITIATED,
            payload={"workflow_id": "coding", "repo_root": "${REPO_ROOT}"},
        )
        ledger.emit_event(
            EventType.MODEL_SELECTED,
            payload={"role": "planner", "model_id": "gemini-2.5-pro", "capability": "plan", "fallback_count": 0},
        )
        ledger.emit_event(
            EventType.TOOL_CALLED,
            tool_id="shell.execute",
            payload={"command": ["pytest"]},
        )
        ledger.emit_event(
            EventType.POLICY_EVALUATED,
            tool_id="shell.execute",
            payload={"decision": "allow"},
        )
        ledger.emit_event(
            EventType.APPROVAL_REQUESTED,
            tool_id="fs.write",
            payload={"request_id": "req-1"},
        )
        ledger.emit_event(
            EventType.APPROVAL_GRANTED,
            tool_id="fs.write",
            payload={"request_id": "req-1"},
        )
        ledger.emit_event(
            EventType.STATE_TRANSITION,
            step_id="verify",
            payload={"from": "running", "to": "completed", "output_preview": "ok"},
        )
        ledger.write_json(
            "final_report.json",
            {
                "run_id": ledger.run_dir.name,
                "task_summary": "Fix flaky test",
                "status": "done",
                "tests": [{"name": "pytest", "status": "pass", "details": "1 passed", "command": ["pytest", "-q"]}],
                "next_command_suggestions": ["python -m interfaces.cli.cli report --repo . --run-id x"],
            },
        )
        (ledger.run_dir / "final_report.md").write_text("# Report", encoding="utf-8")

        summary = build_run_summary(tmp_path, ledger.run_dir.name)

        assert summary.run_id == ledger.run_dir.name
        assert summary.workflow_id == "coding"
        assert summary.preset_id == "codebase-assistant"
        assert summary.status == "completed"
        assert summary.summary == "Fix flaky test"
        assert summary.repo_root == "${REPO_ROOT}"
        assert summary.provider_models_by_role["planner"].model_id == "gemini-2.5-pro"
        assert summary.tool_counts.total_calls == 1
        assert summary.tool_counts.by_tool["shell.execute"] == 1
        assert summary.policy_decisions.by_decision["allow"] == 1
        assert summary.approvals.requested == 1
        assert summary.approvals.granted == 1
        assert summary.approvals.pending == 0
        assert summary.verification.status == "passed"
        assert "final_report.json" in summary.artifacts


class TestResumeOrchestrator:
    def test_resume_missing_run_raises(self, tmp_path: Path) -> None:
        orch = ResumeOrchestrator(tmp_path)
        wf = FakeWorkflow()
        runner = WorkflowRunner()
        with pytest.raises(ResumeError):
            orch.resume("missing", wf, runner)

    def test_resume_replays_and_skips_completed(self, tmp_path: Path) -> None:
        # 1. Create a run where s1 completes
        ledger = RunLedger.create(tmp_path, "test-resume")
        ledger.emit_event(EventType.RUN_INITIATED, payload={"workflow_id": "test-resume"})
        ledger.emit_event(
            EventType.STATE_TRANSITION,
            step_id="s1",
            payload={"from": "running", "to": "completed", "output_preview": "done-s1"},
        )
        ledger.emit_event(
            EventType.CHECKPOINT_SAVED,
            payload={"sequence": 2},
        )

        # 2. Resume the workflow
        wf = FakeWorkflow(ledger=ledger)
        runner = WorkflowRunner()
        orch = ResumeOrchestrator(tmp_path)
        results = orch.resume(ledger.run_dir.name, wf, runner)

        # s1 should be skipped, s2 and s3 should execute
        assert "s1" not in wf.call_log
        assert "s2" in wf.call_log
        assert "s3" in wf.call_log

        # Verify RUN_RESUMED event was emitted
        events = ledger.read_ledger()
        resumed = [e for e in events if e.event_type == EventType.RUN_RESUMED]
        assert len(resumed) == 1
        assert resumed[0].payload["run_id"] == ledger.run_dir.name
        assert "s1" in resumed[0].payload["completed_steps"]

    def test_resume_from_failure_continues(self, tmp_path: Path) -> None:
        # 1. Create a run where s1 fails
        ledger = RunLedger.create(tmp_path, "test-resume-fail")
        ledger.emit_event(EventType.RUN_INITIATED, payload={"workflow_id": "test-resume"})
        ledger.emit_event(
            EventType.STATE_TRANSITION,
            step_id="s1",
            payload={"from": "running", "to": "failed", "reason": "error"},
        )

        # 2. Resume — s1 failed, so it should be RE-EXECUTED
        wf = FakeWorkflow(ledger=ledger)
        runner = WorkflowRunner()
        orch = ResumeOrchestrator(tmp_path)
        results = orch.resume(ledger.run_dir.name, wf, runner)

        # s1 should be re-executed because it failed
        assert "s1" in wf.call_log
        # s2 and s3 should also execute
        assert "s2" in wf.call_log
        assert "s3" in wf.call_log


class _FakeWorkflowEntry:
    @staticmethod
    def factory(*, model_registry, tool_registry, policy_engine, ledger):
        return FakeWorkflow(
            ledger=ledger,
            model_registry=model_registry,
            tool_registry=tool_registry,
            policy_engine=policy_engine,
        )


class TestCliResumeFallback:
    @pytest.fixture(autouse=True)
    def _patch_cli_deps(self, monkeypatch):
        monkeypatch.setattr("interfaces.cli.cli.get_workflow", lambda w: _FakeWorkflowEntry())
        monkeypatch.setattr("interfaces.cli.cli.load_team_config", lambda: None)
        monkeypatch.setattr(
            "interfaces.cli.cli.build_model_registry",
            lambda config: ModelRegistry({}, {}),
        )

    def test_resume_fallback_to_run_json_when_run_initiated_missing(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        # No RUN_INITIATED event
        (ledger.run_dir / "run.json").write_text(
            json.dumps({"workflow_id": "test-resume"}), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(
            app, ["resume", "--repo", str(tmp_path), "--run-id", ledger.run_dir.name]
        )
        assert result.exit_code == 0, result.output
        assert "test-resume" in result.output

    def test_resume_fallback_to_run_json_when_workflow_id_empty(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        ledger.emit_event(EventType.RUN_INITIATED, payload={"workflow_id": ""})
        (ledger.run_dir / "run.json").write_text(
            json.dumps({"workflow_id": "test-resume"}), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(
            app, ["resume", "--repo", str(tmp_path), "--run-id", ledger.run_dir.name]
        )
        assert result.exit_code == 0, result.output
        assert "test-resume" in result.output

    def test_resume_fails_when_neither_source_has_workflow_id(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        # No RUN_INITIATED event
        (ledger.run_dir / "run.json").write_text(
            json.dumps({"metadata": {}}), encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(
            app, ["resume", "--repo", str(tmp_path), "--run-id", ledger.run_dir.name]
        )
        assert result.exit_code == 1, result.output
        assert "no-run-initiated-event" in result.output or "missing-workflow-id" in result.output
