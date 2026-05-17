"""Tests for agentheim.legacy_aictx_reader.LegacyAictxReader."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from agentheim.legacy_aictx_reader import LegacyAictxReader


class TestListRuns:
    def test_list_runs_empty(self, tmp_path: Path) -> None:
        reader = LegacyAictxReader(tmp_path)
        assert reader.list_runs() == []

    def test_list_runs_with_data(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / ".aictx" / "runs"
        runs_dir.mkdir(parents=True)

        run_a = runs_dir / "run-a"
        run_b = runs_dir / "run-b"
        run_a.mkdir()
        time.sleep(0.01)
        run_b.mkdir()

        reader = LegacyAictxReader(tmp_path)
        runs = reader.list_runs()

        assert len(runs) == 2
        assert runs[0]["run_id"] == "run-b"
        assert runs[1]["run_id"] == "run-a"
        assert runs[0]["created_at"] >= runs[1]["created_at"]


class TestReadRunReport:
    def test_read_run_report_missing(self, tmp_path: Path) -> None:
        reader = LegacyAictxReader(tmp_path)
        assert reader.read_run_report("missing-run") is None

    def test_read_run_report_present(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / ".aictx" / "runs" / "run-1"
        runs_dir.mkdir(parents=True)
        report = {"status": "ok", "files": ["a.py"]}
        (runs_dir / "run-report.json").write_text(json.dumps(report), encoding="utf-8")

        reader = LegacyAictxReader(tmp_path)
        assert reader.read_run_report("run-1") == report


class TestReadLockfile:
    def test_read_lockfile_missing(self, tmp_path: Path) -> None:
        reader = LegacyAictxReader(tmp_path)
        assert reader.read_lockfile("missing-run") is None

    def test_read_lockfile_present(self, tmp_path: Path) -> None:
        lock_path = (
            tmp_path
            / ".aictx"
            / "runs"
            / "run-1"
            / "out"
            / "docs"
            / "AIprojectcontext"
            / "context.lock.json"
        )
        lock_path.parent.mkdir(parents=True)
        lock = {"version": "1.0", "sources": []}
        lock_path.write_text(json.dumps(lock), encoding="utf-8")

        reader = LegacyAictxReader(tmp_path)
        assert reader.read_lockfile("run-1") == lock
