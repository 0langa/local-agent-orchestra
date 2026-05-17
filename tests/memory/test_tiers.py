from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from core.ledger import RunLedger
from memory.tiers.working import WorkingMemory
from memory.tiers.global_ import GlobalMemory


class TestWorkingMemory:
    def test_set_get(self) -> None:
        wm = WorkingMemory()
        wm.set("key", "value")
        assert wm.get("key") == "value"

    def test_get_missing_returns_default(self) -> None:
        wm = WorkingMemory()
        assert wm.get("missing") is None
        assert wm.get("missing", "default") == "default"

    def test_append_and_get_list(self) -> None:
        wm = WorkingMemory()
        wm.append("logs", "first")
        wm.append("logs", "second")
        assert wm.get_list("logs") == ["first", "second"]

    def test_snapshot(self) -> None:
        wm = WorkingMemory()
        wm.set("x", 1)
        wm.append("y", "a")
        snap = wm.snapshot()
        assert snap["store"] == {"x": 1}
        assert snap["lists"] == {"y": ["a"]}

    def test_clear(self) -> None:
        wm = WorkingMemory()
        wm.set("x", 1)
        wm.append("y", "a")
        wm.clear()
        assert wm.get("x") is None
        assert wm.get_list("y") == []

    def test_flush_without_ledger_is_noop(self) -> None:
        wm = WorkingMemory()
        wm.set("x", 1)
        wm.flush()  # should not raise

    def test_flush_writes_to_ledger(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test")
        wm = WorkingMemory(ledger=ledger)
        wm.set("agent", "planner")
        wm.append("messages", "hello")
        wm.flush()

        written = ledger.run_dir / "working_memory.json"
        assert written.exists()
        payload = json.loads(written.read_text(encoding="utf-8"))
        assert payload["store"]["agent"] == "planner"
        assert payload["lists"]["messages"] == ["hello"]


class TestGlobalMemory:
    def test_get_preference_default(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        assert gm.get_preference("theme") is None
        assert gm.get_preference("theme", "dark") == "dark"

    def test_set_and_get_preference(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        gm.set_preference("theme", "light")
        assert gm.get_preference("theme") == "light"

    def test_set_preference_overwrites(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        gm.set_preference("theme", "dark")
        gm.set_preference("theme", "light")
        assert gm.get_preference("theme") == "light"

    def test_preference_persists_across_instances(self, tmp_path: Path) -> None:
        gm1 = GlobalMemory(base_path=tmp_path)
        gm1.set_preference("lang", "python")
        gm2 = GlobalMemory(base_path=tmp_path)
        assert gm2.get_preference("lang") == "python"

    def test_preference_stores_complex_value(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        gm.set_preference("config", {"a": 1, "b": [2, 3]})
        assert gm.get_preference("config") == {"a": 1, "b": [2, 3]}

    def test_record_approval(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        gm.record_approval("approved", tool_name="write_file", context={"path": "test.py"})
        history = gm.get_approval_history()
        assert len(history) == 1
        assert history[0]["decision"] == "approved"
        assert history[0]["tool_name"] == "write_file"
        assert history[0]["context"]["path"] == "test.py"

    def test_approval_history_limit(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        for i in range(10):
            gm.record_approval("approved")
        history = gm.get_approval_history(limit=3)
        assert len(history) == 3

    def test_record_model_result_new(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        gm.record_model_result("model-a", "coding", success=True, latency_ms=150.0)
        profile = gm.get_model_profile("model-a")
        assert profile is not None
        assert profile["success_count"] == 1
        assert profile["fail_count"] == 0
        assert profile["avg_latency_ms"] == 150.0

    def test_record_model_result_updates(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        gm.record_model_result("model-a", "coding", success=True, latency_ms=100.0)
        gm.record_model_result("model-a", "coding", success=False, latency_ms=200.0)
        profile = gm.get_model_profile("model-a")
        assert profile is not None
        assert profile["success_count"] == 1
        assert profile["fail_count"] == 1
        assert profile["avg_latency_ms"] == 150.0

    def test_get_model_profile_missing(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        assert gm.get_model_profile("unknown") is None

    def test_wal_mode_enabled(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        with sqlite3.connect(str(gm.db_path)) as conn:
            row = conn.execute("PRAGMA journal_mode").fetchone()
        assert row is not None
        assert row[0].lower() == "wal"

    def test_preference_redaction(self, tmp_path: Path) -> None:
        gm = GlobalMemory(base_path=tmp_path)
        gm.set_preference("secret", "api_key: abc12345xyz")
        value = gm.get_preference("secret")
        assert "REDACTED" in value
