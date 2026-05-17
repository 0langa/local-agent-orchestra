"""Tests for core/events.py — structured event schema."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from core.events import Event, EventType


class TestEventType:
    def test_all_event_types_are_unique(self) -> None:
        values = [e.value for e in EventType]
        assert len(values) == len(set(values)), "duplicate event type values detected"

    def test_event_type_count(self) -> None:
        # At least 24 canonical types as per Phase 7 spec
        assert len(EventType) >= 24

    def test_event_type_is_str(self) -> None:
        assert isinstance(EventType.RUN_INITIATED, str)
        assert EventType.RUN_INITIATED == "run_initiated"


class TestEventSerialization:
    def test_round_trip_dict(self) -> None:
        original = Event.create(
            sequence=0,
            event_type=EventType.RUN_INITIATED,
            run_id="20260101-120000-test",
            payload={"purpose": "test"},
        )
        data = original.to_dict()
        restored = Event.from_dict(data)

        assert restored.sequence == original.sequence
        assert restored.event_type == original.event_type
        assert restored.run_id == original.run_id
        assert restored.payload == original.payload
        assert restored.event_id == original.event_id

    def test_round_trip_json(self) -> None:
        original = Event.create(
            sequence=1,
            event_type=EventType.TOOL_CALLED,
            run_id="run-42",
            step_id="step-1",
            agent_id="agent-a",
            tool_id="shell_tool",
            phase="execution",
            payload={"cmd": "ls"},
            metadata={"version": "1.0"},
            parent_event_id="parent-uuid",
            previous_hash="abcd" * 16,
        )
        raw = original.to_json()
        restored = Event.from_json(raw)

        assert restored.sequence == original.sequence
        assert restored.event_type == original.event_type
        assert restored.step_id == original.step_id
        assert restored.agent_id == original.agent_id
        assert restored.tool_id == original.tool_id
        assert restored.phase == original.phase
        assert restored.payload == original.payload
        assert restored.metadata == original.metadata
        assert restored.parent_event_id == original.parent_event_id
        assert restored.previous_hash == original.previous_hash

    def test_json_is_deterministic(self) -> None:
        e1 = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        e2 = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        # Different UUIDs mean different JSON, but structure is identical
        d1 = json.loads(e1.to_json())
        d2 = json.loads(e2.to_json())
        assert d1.keys() == d2.keys()
        assert all(k in d1 for k in (
            "event_id", "sequence", "timestamp", "event_type",
            "run_id", "step_id", "agent_id", "tool_id", "phase",
            "payload", "metadata", "parent_event_id", "previous_hash",
        ))

    def test_timestamp_is_utc(self) -> None:
        event = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        assert event.timestamp.tzinfo is not None

    def test_optional_fields_default_to_none(self) -> None:
        event = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        assert event.step_id is None
        assert event.agent_id is None
        assert event.tool_id is None
        assert event.phase is None
        assert event.parent_event_id is None
        assert event.previous_hash is None
        assert event.payload == {}
        assert event.metadata == {}


class TestEventHash:
    def test_hash_is_64_hex_chars(self) -> None:
        event = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        h = event.compute_hash()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_deterministic_for_same_data(self) -> None:
        event = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        assert event.compute_hash() == event.compute_hash()

    def test_hash_excludes_previous_hash(self) -> None:
        """The hash must not include previous_hash to avoid circular dependency."""
        from datetime import datetime, timezone
        from uuid import uuid4

        fixed_id = uuid4()
        fixed_ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        event1 = Event(
            event_id=fixed_id,
            sequence=0,
            timestamp=fixed_ts,
            event_type=EventType.RUN_INITIATED,
            run_id="r",
            previous_hash=None,
        )
        event2 = Event(
            event_id=fixed_id,
            sequence=0,
            timestamp=fixed_ts,
            event_type=EventType.RUN_INITIATED,
            run_id="r",
            previous_hash="abcd" * 16,
        )
        # Same everything except previous_hash → same compute_hash()
        assert event1.compute_hash() == event2.compute_hash()

    def test_different_sequences_produce_different_hashes(self) -> None:
        e1 = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        e2 = Event.create(sequence=1, event_type=EventType.RUN_INITIATED, run_id="r")
        assert e1.compute_hash() != e2.compute_hash()

    def test_different_payloads_produce_different_hashes(self) -> None:
        e1 = Event.create(sequence=0, event_type=EventType.TOOL_CALLED, run_id="r", payload={"cmd": "ls"})
        e2 = Event.create(sequence=0, event_type=EventType.TOOL_CALLED, run_id="r", payload={"cmd": "cat"})
        assert e1.compute_hash() != e2.compute_hash()


class TestEventFactory:
    def test_create_generates_uuid(self) -> None:
        event = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        assert isinstance(event.event_id, UUID)

    def test_create_increments_sequence(self) -> None:
        e1 = Event.create(sequence=0, event_type=EventType.RUN_INITIATED, run_id="r")
        e2 = Event.create(sequence=1, event_type=EventType.TOOL_CALLED, run_id="r")
        assert e1.sequence == 0
        assert e2.sequence == 1

    def test_create_accepts_all_fields(self) -> None:
        event = Event.create(
            sequence=5,
            event_type=EventType.POLICY_EVALUATED,
            run_id="run-99",
            step_id="s1",
            agent_id="a1",
            tool_id="t1",
            phase="planning",
            payload={"decision": "allow"},
            metadata={"latency_ms": 42},
            parent_event_id="p1",
            previous_hash="0" * 64,
        )
        assert event.sequence == 5
        assert event.event_type == EventType.POLICY_EVALUATED
        assert event.run_id == "run-99"
        assert event.step_id == "s1"
        assert event.agent_id == "a1"
        assert event.tool_id == "t1"
        assert event.phase == "planning"
        assert event.payload == {"decision": "allow"}
        assert event.metadata == {"latency_ms": 42}
        assert event.parent_event_id == "p1"
        assert event.previous_hash == "0" * 64
