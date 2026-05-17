"""Tests for ledger hash chain integrity and tamper detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.events import EventType
from core.ledger import RunLedger


class TestHashChain:
    def test_empty_ledger_verifies(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "empty")
        valid, broken = ledger.verify_chain()
        assert valid is True
        assert broken == []

    def test_single_event_verifies(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "single")
        ledger.emit_event(EventType.RUN_INITIATED, payload={"purpose": "test"})
        valid, broken = ledger.verify_chain()
        assert valid is True
        assert broken == []

    def test_chain_of_events_verifies(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "chain")
        for i in range(5):
            ledger.emit_event(EventType.TOOL_CALLED, step_id=f"step-{i}", payload={"idx": i})
        valid, broken = ledger.verify_chain()
        assert valid is True
        assert broken == []

    def test_tampered_event_detected(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "tamper")
        ledger.emit_event(EventType.RUN_INITIATED, payload={"original": True})
        ledger.emit_event(EventType.TOOL_CALLED, payload={"cmd": "ls"})

        # Tamper with the first event in ledger.jsonl
        ledger_path = ledger.run_dir / "ledger.jsonl"
        lines = ledger_path.read_text(encoding="utf-8").strip().split("\n")
        tampered = lines[0].replace('"original":true', '"original":false')
        lines[0] = tampered
        ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        valid, broken = ledger.verify_chain()
        assert valid is False
        assert len(broken) >= 1
        assert any("previous_hash" in msg for msg in broken)

    def test_tampered_hash_file_detected(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "tamper-hash")
        ledger.emit_event(EventType.RUN_INITIATED)
        ledger.emit_event(EventType.TOOL_CALLED)

        # Tamper with hash file
        hash_path = ledger.run_dir / "ledger.hash"
        lines = hash_path.read_text(encoding="utf-8").strip().split("\n")
        lines[0] = "0" * 64
        hash_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        valid, broken = ledger.verify_chain()
        assert valid is False
        assert len(broken) >= 1

    def test_first_event_previous_hash_is_none_or_zero(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "first")
        event = ledger.emit_event(EventType.RUN_INITIATED)
        # previous_hash should be None (no prior events)
        assert event.previous_hash is None

    def test_subsequent_event_links_previous(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "link")
        e1 = ledger.emit_event(EventType.RUN_INITIATED)
        e2 = ledger.emit_event(EventType.TOOL_CALLED)

        assert e2.previous_hash is not None
        assert e2.previous_hash == e1.compute_hash()

    def test_hash_file_matches_event_hashes(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "match")
        events = []
        for _ in range(3):
            events.append(ledger.emit_event(EventType.TOOL_CALLED))

        hash_path = ledger.run_dir / "ledger.hash"
        hash_lines = hash_path.read_text(encoding="utf-8").strip().split("\n")

        assert len(hash_lines) == len(events)
        for event, h in zip(events, hash_lines):
            assert event.compute_hash() == h.strip()


class TestLedgerRead:
    def test_read_ledger_returns_events_in_order(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "read")
        for i in range(3):
            ledger.emit_event(EventType.TOOL_CALLED, payload={"idx": i})

        events = ledger.read_ledger()
        assert len(events) == 3
        assert events[0].sequence == 0
        assert events[1].sequence == 1
        assert events[2].sequence == 2
        assert events[0].payload["idx"] == 0
        assert events[2].payload["idx"] == 2

    def test_read_ledger_empty(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "read-empty")
        assert ledger.read_ledger() == []
