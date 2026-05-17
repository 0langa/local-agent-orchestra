"""Tests for ledger checkpoints — save, load, list."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.events import EventType
from core.ledger import RunLedger


class TestCheckpoints:
    def test_save_checkpoint_creates_file(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cp-save")
        state = {"phase": "planning", "agents": ["planner"]}
        path = ledger.save_checkpoint(state, sequence_num=5)
        assert path.exists()
        assert path.name == "00000005.json"

    def test_load_last_checkpoint(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cp-load")
        ledger.save_checkpoint({"a": 1}, sequence_num=3)
        ledger.save_checkpoint({"b": 2}, sequence_num=7)

        result = ledger.load_last_checkpoint()
        assert result is not None
        state, seq = result
        assert state == {"b": 2}
        assert seq == 7

    def test_load_last_checkpoint_empty(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cp-empty")
        assert ledger.load_last_checkpoint() is None

    def test_list_checkpoints_sorted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cp-list")
        ledger.save_checkpoint({"s": 1}, sequence_num=10)
        ledger.save_checkpoint({"s": 2}, sequence_num=2)
        ledger.save_checkpoint({"s": 3}, sequence_num=50)

        checkpoints = ledger.list_checkpoints()
        assert len(checkpoints) == 3
        seqs = [seq for _, seq in checkpoints]
        assert seqs == [2, 10, 50]

    def test_checkpoint_includes_timestamp(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cp-ts")
        path = ledger.save_checkpoint({"x": 1}, sequence_num=0)
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "timestamp" in data
        assert "sequence" in data
        assert "state" in data

    def test_checkpoint_dir_created_on_emit(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "cp-dir")
        assert (ledger.run_dir / "checkpoints").exists()

    def test_sequence_restored_from_existing_ledger(self, tmp_path: Path) -> None:
        """When resuming, sequence should continue from existing ledger."""
        ledger = RunLedger.create(tmp_path, "cp-resume")
        for _ in range(5):
            ledger.emit_event(EventType.TOOL_CALLED)

        # Fresh instance pointing at same run_dir
        fresh = RunLedger(repo_root=tmp_path, run_dir=ledger.run_dir)
        fresh._restore_sequence_from_ledger()

        next_event = fresh.emit_event(EventType.TOOL_CALLED)
        assert next_event.sequence == 5

    def test_multiple_runs_independent_checkpoints(self, tmp_path: Path) -> None:
        ledger1 = RunLedger.create(tmp_path, "run-a")
        ledger2 = RunLedger.create(tmp_path, "run-b")

        ledger1.save_checkpoint({"run": "a"}, sequence_num=0)
        ledger2.save_checkpoint({"run": "b"}, sequence_num=0)

        cp1 = ledger1.list_checkpoints()
        cp2 = ledger2.list_checkpoints()

        assert len(cp1) == 1
        assert len(cp2) == 1
        assert ledger1.run_dir != ledger2.run_dir
