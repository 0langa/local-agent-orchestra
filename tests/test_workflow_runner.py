"""Tests for core/workflow_runner.py — DAG execution engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.events import EventType
from core.ledger import RunLedger
from core.model_registry import ModelDescriptor, ModelRegistry, ProviderDescriptor
from core.policy_engine import PolicyEngine
from core.step_budget import BudgetLimits, BudgetExceededError
from core.tool_protocol import ToolRegistry
from core.workflow_runner import WorkflowRunner
from workflows.base import (
    AgentRole,
    ExecutionDAG,
    Step,
    StepContext,
    StepResult,
    Workflow,
)


def _make_registry() -> ModelRegistry:
    providers = {
        "openai_v1": ProviderDescriptor(id="openai_v1", import_path="providers.openai_v1:OpenAIV1Provider"),
    }
    models = {
        "planner": ModelDescriptor(id="planner", role="planner", capabilities=frozenset(["plan"]), config=MagicMock()),
    }
    return ModelRegistry(providers=providers, models=models)


class FakeWorkflow(Workflow):
    workflow_id = "fake"

    def __init__(self, ledger: RunLedger, steps: list[Step], behavior: dict[str, Any] | None = None) -> None:
        super().__init__(
            model_registry=_make_registry(),
            tool_registry=ToolRegistry(),
            policy_engine=PolicyEngine(),
            ledger=ledger,
        )
        self.dag = ExecutionDAG(steps)
        self._behavior = behavior or {}
        self.call_log: list[str] = []
        self.on_complete_called = False

    def execute_step(self, step: Step, context: StepContext) -> StepResult:
        self.call_log.append(step.id)
        if step.id in self._behavior:
            behavior = self._behavior[step.id]
            if callable(behavior):
                return behavior(step, context)
            if isinstance(behavior, Exception):
                raise behavior
            return behavior
        return StepResult(step_id=step.id, success=True, output=f"done:{step.id}")

    def on_run_complete(self, results: list[StepResult]) -> None:
        self.on_complete_called = True


class TestWorkflowRunnerBasic:
    def test_sequential_execution(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "seq")
        steps = [
            Step(id="s1", agent="a1", type="t1"),
            Step(id="s2", agent="a2", type="t2"),
            Step(id="s3", agent="a3", type="t3"),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner()
        results = runner.run(wf, tmp_path)

        assert len(results) == 3
        assert [r.step_id for r in results] == ["s1", "s2", "s3"]
        assert all(r.success for r in results)
        assert wf.on_complete_called

    def test_event_emission(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "events")
        steps = [Step(id="s1", agent="a1", type="t1")]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner()
        runner.run(wf, tmp_path)

        events = ledger.read_ledger()
        types = [e.event_type for e in events]
        assert EventType.RUN_INITIATED in types
        assert EventType.PHASE_TRANSITION in types
        assert EventType.AGENT_INVOKED in types
        assert EventType.STATE_TRANSITION in types
        assert EventType.RUN_COMPLETED in types

    def test_condition_skip(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cond")
        steps = [
            Step(id="s1", agent="a1", type="t1"),
            Step(id="s2", agent="a2", type="t2", condition="not s1"),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner()
        results = runner.run(wf, tmp_path)

        assert results[0].success
        assert results[1].output == "Skipped by condition"

    def test_condition_requires_success(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cond-ok")
        steps = [
            Step(id="s1", agent="a1", type="t1"),
            Step(id="s2", agent="a2", type="t2", condition="s1"),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner()
        results = runner.run(wf, tmp_path)

        assert results[0].success
        assert results[1].output == "done:s2"

    def test_halt_on_failure(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "halt")
        steps = [
            Step(id="s1", agent="a1", type="t1"),
            Step(id="s2", agent="a2", type="t2"),
            Step(id="s3", agent="a3", type="t3"),
        ]
        wf = FakeWorkflow(ledger, steps, behavior={"s2": StepResult(step_id="s2", success=False)})
        runner = WorkflowRunner()
        results = runner.run(wf, tmp_path)

        assert len(results) == 2  # s3 never runs
        assert results[0].success
        assert not results[1].success

    def test_run_failed_event_on_failure(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "fail-event")
        steps = [Step(id="s1", agent="a1", type="t1")]
        wf = FakeWorkflow(ledger, steps, behavior={"s1": StepResult(step_id="s1", success=False)})
        runner = WorkflowRunner()
        runner.run(wf, tmp_path)

        events = ledger.read_ledger()
        assert any(e.event_type == EventType.RUN_FAILED for e in events)

    def test_retry_success(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "retry")
        steps = [Step(id="s1", agent="a1", type="t1", max_iterations=3)]
        call_count = 0

        def flaky(step: Step, context: StepContext) -> StepResult:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return StepResult(step_id=step.id, success=True)

        wf = FakeWorkflow(ledger, steps, behavior={"s1": flaky})
        runner = WorkflowRunner()
        results = runner.run(wf, tmp_path)

        assert results[0].success
        assert call_count == 3

    def test_retry_exhausted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "retry-ex")
        steps = [Step(id="s1", agent="a1", type="t1", max_iterations=2)]

        def always_fails(step: Step, context: StepContext) -> StepResult:
            raise ConnectionError("transient")

        wf = FakeWorkflow(ledger, steps, behavior={"s1": always_fails})
        runner = WorkflowRunner()
        results = runner.run(wf, tmp_path)

        assert not results[0].success
        assert "error" in results[0].metadata

    def test_workspace_isolation(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "workspace")
        steps = [Step(id="s1", agent="a1", type="t1", workspace_isolation=True)]
        received_contexts: list[StepContext] = []

        def capture(step: Step, context: StepContext) -> StepResult:
            received_contexts.append(context)
            return StepResult(step_id=step.id, success=True)

        wf = FakeWorkflow(ledger, steps, behavior={"s1": capture})
        runner = WorkflowRunner()
        runner.run(wf, tmp_path)

        ws_path = ledger.run_dir / "workspaces" / "s1"
        assert ws_path.exists()
        assert received_contexts[0].repo_root == ws_path

    def test_no_workspace_isolation(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "no-ws")
        steps = [Step(id="s1", agent="a1", type="t1", workspace_isolation=False)]
        received_contexts: list[StepContext] = []

        def capture(step: Step, context: StepContext) -> StepResult:
            received_contexts.append(context)
            return StepResult(step_id=step.id, success=True)

        wf = FakeWorkflow(ledger, steps, behavior={"s1": capture})
        runner = WorkflowRunner()
        runner.run(wf, tmp_path)

        assert received_contexts[0].repo_root == tmp_path

    def test_working_memory_flushed(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "wm")
        steps = [Step(id="s1", agent="a1", type="t1")]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner()
        runner.run(wf, tmp_path)

        assert (ledger.run_dir / "working_memory.json").exists()

    def test_diagnostics_bundle_on_step_failure(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "diag-step")
        steps = [
            Step(id="s1", agent="a1", type="t1"),
            Step(id="s2", agent="a2", type="t2"),
        ]
        wf = FakeWorkflow(ledger, steps, behavior={"s2": StepResult(step_id="s2", success=False)})
        runner = WorkflowRunner()
        runner.run(wf, tmp_path)

        assert (ledger.run_dir / "run_summary.json").exists()
        assert (ledger.run_dir / "diagnostics.md").exists()
        text = (ledger.run_dir / "diagnostics.md").read_text(encoding="utf-8")
        assert "Run Diagnostics" in text
        assert "failed" in text.lower() or "error" in text.lower()

    def test_diagnostics_bundle_on_exception(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "diag-exc")
        steps = [Step(id="s1", agent="a1", type="t1")]
        wf = FakeWorkflow(ledger, steps, behavior={"s1": RuntimeError("boom")})
        runner = WorkflowRunner()
        with pytest.raises(RuntimeError, match="boom"):
            runner.run(wf, tmp_path)

        assert (ledger.run_dir / "run_summary.json").exists()
        assert (ledger.run_dir / "diagnostics.md").exists()


class TestWorkflowRunnerBudget:
    def test_budget_enforced(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "budget")
        steps = [Step(id="s1", agent="a1", type="t1")]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner(default_budget=BudgetLimits(max_agent_invocations=0))
        results = runner.run(wf, tmp_path)

        assert not results[0].success
        assert "budget" in results[0].output.lower() or "halt" in results[0].metadata.get("halt_reason", "")

    def test_budget_event_emitted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "budget-ev")
        steps = [Step(id="s1", agent="a1", type="t1")]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner(default_budget=BudgetLimits(max_agent_invocations=0))
        runner.run(wf, tmp_path)

        events = ledger.read_ledger()
        assert any(e.event_type == EventType.BUDGET_CHECKED for e in events)


class TestWorkflowRunnerLifecycle:
    def test_on_step_complete_called(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "lifecycle")
        steps = [Step(id="s1", agent="a1", type="t1")]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner()
        runner.run(wf, tmp_path)

        assert wf.call_log == ["s1"]
        assert wf.on_complete_called

    def test_dag_none_raises(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "no-dag")
        wf = FakeWorkflow(ledger, [])
        wf.dag = None
        runner = WorkflowRunner()
        with pytest.raises(RuntimeError, match="DAG not defined"):
            runner.run(wf, tmp_path)
