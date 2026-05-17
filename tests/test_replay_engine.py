"""Tests for core/replay_engine.py — deterministic replay from ledger events."""

from __future__ import annotations

from core.events import Event, EventType
from core.replay_engine import ReplayEngine, RunState
from workflows.base import StepResult


def _make_event(
    sequence: int,
    event_type: EventType,
    step_id: str | None = None,
    payload: dict | None = None,
    run_id: str = "run-1",
) -> Event:
    return Event.create(
        sequence=sequence,
        event_type=event_type,
        run_id=run_id,
        step_id=step_id,
        payload=payload or {},
    )


class TestReplayEngineEmpty:
    def test_empty_events(self) -> None:
        engine = ReplayEngine()
        state = engine.replay([])
        assert state.prior_results == {}
        assert state.completed_steps == set()
        assert state.checkpoint_sequence == 0


class TestReplayEngineStateTransitions:
    def test_completed_step(self) -> None:
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.STATE_TRANSITION, "s1", {"to": "completed", "output_preview": "hello"}),
        ]
        state = engine.replay(events)
        assert state.completed_steps == {"s1"}
        assert state.prior_results["s1"].success is True
        assert state.prior_results["s1"].output == "hello"

    def test_failed_step(self) -> None:
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.STATE_TRANSITION, "s1", {"to": "failed", "reason": "oom"}),
        ]
        state = engine.replay(events)
        assert state.failed_steps == {"s1"}
        assert state.prior_results["s1"].success is False
        assert state.prior_results["s1"].metadata["error"] == "oom"

    def test_skipped_step(self) -> None:
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.STATE_TRANSITION, "s1", {"to": "skipped"}),
        ]
        state = engine.replay(events)
        assert state.skipped_steps == {"s1"}
        assert state.prior_results["s1"].success is True
        assert "Skipped" in state.prior_results["s1"].output

    def test_multiple_steps(self) -> None:
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.STATE_TRANSITION, "s1", {"to": "completed"}),
            _make_event(1, EventType.STATE_TRANSITION, "s2", {"to": "failed"}),
            _make_event(2, EventType.STATE_TRANSITION, "s3", {"to": "skipped"}),
        ]
        state = engine.replay(events)
        assert state.completed_steps == {"s1"}
        assert state.failed_steps == {"s2"}
        assert state.skipped_steps == {"s3"}
        assert set(state.prior_results.keys()) == {"s1", "s2", "s3"}

    def test_later_event_overwrites(self) -> None:
        """If a step is retried and later succeeds, the latest result wins."""
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.STATE_TRANSITION, "s1", {"to": "failed"}),
            _make_event(1, EventType.STATE_TRANSITION, "s1", {"to": "completed", "output_preview": "retry ok"}),
        ]
        state = engine.replay(events)
        assert state.prior_results["s1"].success is True
        assert state.prior_results["s1"].output == "retry ok"


class TestReplayEngineCheckpoints:
    def test_checkpoint_sequence_tracked(self) -> None:
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.CHECKPOINT_SAVED, payload={"sequence": 5}),
            _make_event(1, EventType.CHECKPOINT_SAVED, payload={"sequence": 10}),
        ]
        state = engine.replay(events)
        assert state.checkpoint_sequence == 10


class TestReplayEngineMetadata:
    def test_run_initiated_metadata(self) -> None:
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.RUN_INITIATED, payload={"workflow_id": "w1", "repo_root": "/tmp"}),
        ]
        state = engine.replay(events)
        assert state.metadata["workflow_id"] == "w1"
        assert state.metadata["repo_root"] == "/tmp"


class TestReplayEngineIdempotency:
    def test_replay_twice_same_result(self) -> None:
        engine = ReplayEngine()
        events = [
            _make_event(0, EventType.STATE_TRANSITION, "s1", {"to": "completed"}),
        ]
        state1 = engine.replay(events)
        state2 = engine.replay(events)
        assert state1.completed_steps == state2.completed_steps
        assert state1.prior_results["s1"].output == state2.prior_results["s1"].output
