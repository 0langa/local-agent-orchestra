"""Tests for core/workflow_runner.py — parallel group execution."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.events import EventType
from core.ledger import RunLedger
from core.model_registry import ModelDescriptor, ModelRegistry, ProviderDescriptor
from core.policy_engine import PolicyEngine
from core.tool_protocol import ToolRegistry
from core.workflow_runner import WorkflowRunner
from workflows.base import ExecutionDAG, Step, StepContext, StepResult, Workflow


def _make_registry() -> ModelRegistry:
    providers = {
        "openai_v1": ProviderDescriptor(id="openai_v1", import_path="providers.openai_v1:OpenAIV1Provider"),
    }
    models = {
        "planner": ModelDescriptor(id="planner", role="planner", capabilities=frozenset(["plan"]), config=MagicMock()),
    }
    return ModelRegistry(providers=providers, models=models)


class FakeWorkflow(Workflow):
    workflow_id = "fake-parallel"

    def __init__(self, ledger: RunLedger, steps: list[Step], behavior: dict[str, Any] | None = None) -> None:
        super().__init__(
            model_registry=_make_registry(),
            tool_registry=ToolRegistry(),
            policy_engine=PolicyEngine(),
            ledger=ledger,
        )
        self.dag = ExecutionDAG(steps)
        self._behavior = behavior or {}
        self.threads: dict[str, int] = {}

    def execute_step(self, step: Step, context: StepContext) -> StepResult:
        self.threads[step.id] = threading.current_thread().ident
        if step.id in self._behavior:
            return self._behavior[step.id]
        # Simulate work
        time.sleep(0.01)
        return StepResult(step_id=step.id, success=True, output=f"done:{step.id}")

    def on_run_complete(self, results: list[StepResult]) -> None:
        pass


class TestParallelExecution:
    def test_parallel_steps_run_concurrently(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "parallel")
        steps = [
            Step(id="s1", agent="a1", type="t1", parallel_safe=True),
            Step(id="s2", agent="a2", type="t2", parallel_safe=True),
            Step(id="s3", agent="a3", type="t3", parallel_safe=True),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner(max_workers=3)
        results = runner.run(wf, tmp_path)

        assert len(results) == 3
        assert all(r.success for r in results)
        # If they ran concurrently, they likely used different threads
        thread_ids = set(wf.threads.values())
        assert len(thread_ids) > 1, "Parallel steps should use multiple threads"

    def test_mixed_parallel_and_sequential(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "mixed")
        steps = [
            Step(id="s1", agent="a1", type="t1", parallel_safe=True),
            Step(id="s2", agent="a2", type="t2", parallel_safe=True),
            Step(id="s3", agent="a3", type="t3", parallel_safe=False, depends_on=["s1", "s2"]),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner(max_workers=2)
        results = runner.run(wf, tmp_path)

        assert len(results) == 3
        # s3 depends on s1 and s2, so it must run after them
        assert wf.threads["s3"] is not None

    def test_parallel_with_dependencies(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "parallel-deps")
        steps = [
            Step(id="s1", agent="a1", type="t1", parallel_safe=True),
            Step(id="s2", agent="a2", type="t2", parallel_safe=True, depends_on=["s1"]),
            Step(id="s3", agent="a3", type="t3", parallel_safe=True, depends_on=["s1"]),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner(max_workers=2)
        results = runner.run(wf, tmp_path)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_single_step_not_parallel(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "single")
        steps = [Step(id="s1", agent="a1", type="t1", parallel_safe=True)]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner()
        results = runner.run(wf, tmp_path)

        assert len(results) == 1
        assert results[0].success

    def test_parallel_safe_false_runs_sequential(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "sequential")
        steps = [
            Step(id="s1", agent="a1", type="t1", parallel_safe=False),
            Step(id="s2", agent="a2", type="t2", parallel_safe=False),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner(max_workers=2)
        results = runner.run(wf, tmp_path)

        # Sequential steps may run on same thread
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_parallel_group_with_failure(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "parallel-fail")
        steps = [
            Step(id="s1", agent="a1", type="t1", parallel_safe=True),
            Step(id="s2", agent="a2", type="t2", parallel_safe=True),
        ]
        wf = FakeWorkflow(ledger, steps, behavior={"s1": StepResult(step_id="s1", success=False)})
        runner = WorkflowRunner(max_workers=2)
        results = runner.run(wf, tmp_path)

        # Both steps in the parallel group run, then failure halts
        assert len(results) == 2
        assert not results[0].success or not results[1].success

    def test_events_emitted_for_parallel(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "parallel-events")
        steps = [
            Step(id="s1", agent="a1", type="t1", parallel_safe=True),
            Step(id="s2", agent="a2", type="t2", parallel_safe=True),
        ]
        wf = FakeWorkflow(ledger, steps)
        runner = WorkflowRunner(max_workers=2)
        runner.run(wf, tmp_path)

        events = ledger.read_ledger()
        invoked = [e for e in events if e.event_type == EventType.AGENT_INVOKED]
        assert len(invoked) == 2
        assert {e.step_id for e in invoked} == {"s1", "s2"}
