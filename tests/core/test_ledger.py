from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.events import EventType
from core.ledger import RunLedger


class TestRunLedger:
    def test_create_makes_directory(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        assert ledger.run_dir.exists()
        assert ledger.repo_root == tmp_path

    def test_create_makes_jsonl_files(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        assert (ledger.run_dir / "tool_calls.jsonl").exists()
        assert (ledger.run_dir / "state_transitions.jsonl").exists()

    def test_write_json(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        path = ledger.write_json("data.json", {"key": "value"})
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["key"] == "value"

    def test_write_text(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        path = ledger.write_text("notes.md", "# Hello")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "# Hello"

    def test_append_jsonl(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        ledger.append_jsonl("events.jsonl", {"event": "start"})
        ledger.append_jsonl("events.jsonl", {"event": "end"})
        lines = (ledger.run_dir / "events.jsonl").read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "start"
        assert json.loads(lines[1])["event"] == "end"

    def test_sanitize_value_replaces_repo_root(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        path = ledger.write_json("paths.json", {"root": str(tmp_path), "nested": str(tmp_path / "sub" / "file.txt")})
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["root"] == "${REPO_ROOT}"
        assert data["nested"] == "${REPO_ROOT}/sub/file.txt"

    def test_sanitize_value_no_repo_root(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-run")
        path = ledger.write_json("plain.json", {"name": "hello"})
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["name"] == "hello"


class TestRunLedgerUnified:
    def test_emit_event_creates_ledger_jsonl(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "unified")
        ledger.emit_event(EventType.RUN_INITIATED, payload={"purpose": "test"})
        assert (ledger.run_dir / "ledger.jsonl").exists()

    def test_emit_event_creates_hash_file(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "unified")
        ledger.emit_event(EventType.RUN_INITIATED)
        assert (ledger.run_dir / "ledger.hash").exists()

    def test_emit_event_returns_event(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "unified")
        event = ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell", payload={"cmd": "ls"})
        assert event.event_type == EventType.TOOL_CALLED
        assert event.tool_id == "shell"
        assert event.payload == {"cmd": "ls"}
        assert event.run_id == ledger.run_dir.name

    def test_emit_event_increments_sequence(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "unified")
        e1 = ledger.emit_event(EventType.RUN_INITIATED)
        e2 = ledger.emit_event(EventType.TOOL_CALLED)
        e3 = ledger.emit_event(EventType.RUN_COMPLETED)
        assert e1.sequence == 0
        assert e2.sequence == 1
        assert e3.sequence == 2

    def test_legacy_and_unified_coexist(self, tmp_path: Path) -> None:
        """Old append_jsonl and new emit_event can be used together."""
        ledger = RunLedger.create(tmp_path, "mixed")
        ledger.append_jsonl("tool_calls.jsonl", {"tool": "shell"})
        ledger.emit_event(EventType.TOOL_CALLED, tool_id="shell")

        # Legacy file exists and has the raw entry
        legacy = (ledger.run_dir / "tool_calls.jsonl").read_text(encoding="utf-8").strip()
        assert json.loads(legacy)["tool"] == "shell"

        # Unified ledger has the structured event
        events = ledger.read_ledger()
        assert len(events) == 1
        assert events[0].event_type == EventType.TOOL_CALLED
