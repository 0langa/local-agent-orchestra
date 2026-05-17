"""Tests for core/step_budget.py — budget enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.events import EventType
from core.ledger import RunLedger
from core.step_budget import (
    BudgetExceededError,
    BudgetLimits,
    BudgetSnapshot,
    StepBudgetEnforcer,
)


class TestBudgetSnapshot:
    def test_default_values(self) -> None:
        snap = BudgetSnapshot()
        assert snap.tokens_used == 0
        assert snap.tool_calls_used == 0
        assert snap.agent_invocations_used == 0
        assert snap.time_elapsed_seconds == 0.0

    def test_to_dict(self) -> None:
        snap = BudgetSnapshot(tokens_used=100, time_elapsed_seconds=5.5)
        d = snap.to_dict()
        assert d["tokens_used"] == 100
        assert d["time_elapsed_seconds"] == 5.5


class TestBudgetLimits:
    def test_defaults_are_none(self) -> None:
        limits = BudgetLimits()
        assert limits.max_tokens is None
        assert limits.max_time_seconds is None
        assert limits.max_tool_calls is None
        assert limits.max_agent_invocations is None

    def test_to_dict(self) -> None:
        limits = BudgetLimits(max_tokens=1000)
        d = limits.to_dict()
        assert d["max_tokens"] == 1000
        assert d["max_time_seconds"] is None


class TestCheckBudget:
    def test_within_budget(self, tmp_path: Path) -> None:
        limits = BudgetLimits(max_tokens=100)
        enforcer = StepBudgetEnforcer(limits=limits)
        assert enforcer.check_budget("test_op") is True

    def test_exceed_tokens(self, tmp_path: Path) -> None:
        limits = BudgetLimits(max_tokens=10)
        enforcer = StepBudgetEnforcer(limits=limits)
        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.record_tokens(15)
        assert exc_info.value.limit_name == "max_tokens"

    def test_exceed_tool_calls(self, tmp_path: Path) -> None:
        limits = BudgetLimits(max_tool_calls=2)
        enforcer = StepBudgetEnforcer(limits=limits)
        enforcer.record_tool_call()
        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.record_tool_call()
        assert exc_info.value.limit_name == "max_tool_calls"

    def test_exceed_agent_invocations(self, tmp_path: Path) -> None:
        limits = BudgetLimits(max_agent_invocations=1)
        enforcer = StepBudgetEnforcer(limits=limits)
        with pytest.raises(BudgetExceededError) as exc_info:
            enforcer.record_agent_invocation()
        assert exc_info.value.limit_name == "max_agent_invocations"

    def test_no_limits_no_enforcement(self, tmp_path: Path) -> None:
        limits = BudgetLimits()
        enforcer = StepBudgetEnforcer(limits=limits)
        enforcer.record_tokens(999999)
        enforcer.record_tool_call()
        enforcer.record_agent_invocation()
        assert enforcer.check_budget("test_op") is True


class TestBudgetEvents:
    def test_budget_checked_emitted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "budget-events")
        limits = BudgetLimits(max_tokens=100)
        enforcer = StepBudgetEnforcer(limits=limits, ledger=ledger)
        enforcer.check_budget("step_1", step_id="s1")

        events = ledger.read_ledger()
        checked = [e for e in events if e.event_type == EventType.BUDGET_CHECKED]
        assert len(checked) == 1
        assert checked[0].payload["operation"] == "step_1"
        assert checked[0].payload["exceeded"] is False

    def test_budget_exceeded_emitted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "budget-exceeded")
        limits = BudgetLimits(max_tokens=5)
        enforcer = StepBudgetEnforcer(limits=limits, ledger=ledger)

        with pytest.raises(BudgetExceededError):
            enforcer.record_tokens(10)

        events = ledger.read_ledger()
        exceeded = [e for e in events if e.event_type == EventType.BUDGET_EXCEEDED]
        assert len(exceeded) == 1
        assert exceeded[0].payload["limit_name"] == "max_tokens"

    def test_record_events_emitted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "budget-record")
        limits = BudgetLimits(max_tool_calls=2)
        enforcer = StepBudgetEnforcer(limits=limits, ledger=ledger)
        enforcer.record_tool_call(step_id="s1")

        with pytest.raises(BudgetExceededError):
            enforcer.record_tool_call(step_id="s1")

        events = ledger.read_ledger()
        exceeded = [e for e in events if e.event_type == EventType.BUDGET_EXCEEDED]
        assert len(exceeded) >= 1


class TestBudgetSnapshotMethod:
    def test_snapshot_reflects_state(self, tmp_path: Path) -> None:
        limits = BudgetLimits(max_tokens=1000)
        enforcer = StepBudgetEnforcer(limits=limits)
        enforcer.record_tokens(50)
        enforcer.record_tool_call()
        snap = enforcer.snapshot()
        assert snap.tokens_used == 50
        assert snap.tool_calls_used == 1
