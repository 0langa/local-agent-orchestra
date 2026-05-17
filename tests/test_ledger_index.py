"""Tests for ledger indexing — query by event_type, phase, agent_id, tool_id, step_id."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.events import EventType
from core.ledger import RunLedger


class TestIndexQuery:
    def test_query_by_event_type(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-type")
        ledger.emit_event(EventType.RUN_INITIATED)
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="git")
        ledger.emit_event(EventType.RUN_COMPLETED)

        tool_events = ledger.query_index(event_type=EventType.TOOL_CALLED)
        assert len(tool_events) == 2
        assert all(e.event_type == EventType.TOOL_CALLED for e in tool_events)

        run_events = ledger.query_index(event_type=EventType.RUN_INITIATED)
        assert len(run_events) == 1

    def test_query_by_phase(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-phase")
        ledger.emit_event(EventType.PHASE_TRANSITION, phase="planning")
        ledger.emit_event(EventType.TOOL_CALLED, phase="planning")
        ledger.emit_event(EventType.PHASE_TRANSITION, phase="execution")
        ledger.emit_event(EventType.TOOL_CALLED, phase="execution")

        planning = ledger.query_index(phase="planning")
        assert len(planning) == 2

        execution = ledger.query_index(phase="execution")
        assert len(execution) == 2

    def test_query_by_agent_id(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-agent")
        ledger.emit_event(EventType.AGENT_INVOKED, agent_id="planner")
        ledger.emit_event(EventType.AGENT_INVOKED, agent_id="coder")
        ledger.emit_event(EventType.AGENT_INVOKED, agent_id="planner")

        planner = ledger.query_index(agent_id="planner")
        assert len(planner) == 2

        coder = ledger.query_index(agent_id="coder")
        assert len(coder) == 1

    def test_query_by_tool_id(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-tool")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="git")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell")

        shell = ledger.query_index(tool_id="shell")
        assert len(shell) == 2

        git = ledger.query_index(tool_id="git")
        assert len(git) == 1

    def test_query_by_step_id(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-step")
        for i in range(4):
            ledger.emit_event(EventType.TOOL_CALLED, step_id=f"step-{i % 2}")

        step0 = ledger.query_index(step_id="step-0")
        assert len(step0) == 2

        step1 = ledger.query_index(step_id="step-1")
        assert len(step1) == 2

    def test_query_combined_filters(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-combo")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell", phase="setup")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell", phase="build")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="git", phase="setup")

        # Intersection: shell AND setup
        result = ledger.query_index(tool_id="shell", phase="setup")
        assert len(result) == 1
        assert result[0].tool_id == "shell"
        assert result[0].phase == "setup"

    def test_query_no_match(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-none")
        ledger.emit_event(EventType.RUN_INITIATED)
        assert ledger.query_index(event_type=EventType.TOOL_CALLED) == []
        assert ledger.query_index(phase="nonexistent") == []

    def test_query_returns_empty_for_empty_ledger(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-empty")
        assert ledger.query_index(event_type=EventType.RUN_INITIATED) == []

    def test_query_by_string_event_type(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-str")
        ledger.emit_event(EventType.RUN_INITIATED)
        result = ledger.query_index(event_type="run_initiated")
        assert len(result) == 1

    def test_index_persists_and_loads(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-persist")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="git")
        ledger.save_checkpoint({}, 1)

        # Simulate fresh instance loading from disk
        fresh = RunLedger(repo_root=tmp_path, run_dir=ledger.run_dir)
        fresh._load_index()

        shell = fresh.query_index(tool_id="shell")
        assert len(shell) == 1


class TestIndexRebuild:
    def test_index_is_incrementally_updated(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "index-incr")
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="t1")
        assert len(ledger.query_index(tool_id="t1")) == 1

        ledger.emit_event(EventType.TOOL_CALLED, tool_id="t1")
        assert len(ledger.query_index(tool_id="t1")) == 2
