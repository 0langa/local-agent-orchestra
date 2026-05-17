from __future__ import annotations

import sqlite3

import pytest

from memory.episodic import EpisodicMemory, Episode


class TestEpisodicMemory:
    def test_record_creates_episode(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path)
        ep = mem.record("ctx", "act", "out", "happy", ["tag"])
        assert isinstance(ep, Episode)
        assert ep.context == "ctx"
        assert ep.action == "act"
        assert ep.outcome == "out"
        assert ep.emotion == "happy"
        assert ep.tags == ["tag"]
        assert ep.embedding is not None

    def test_recent_returns_latest_first(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path)
        mem.record("first", "a")
        mem.record("second", "b")
        mem.record("third", "c")
        recent = mem.recent(2)
        assert len(recent) == 2
        assert recent[0].context == "third"
        assert recent[1].context == "second"

    def test_recall_finds_similar_episodes(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path)
        mem.record("User asked about Python", "Explained variables")
        mem.record("User asked about cooking", "Explained recipes")
        mem.record("User asked about Python loops", "Explained for loops")
        results = mem.recall("Python programming", top_k=2)
        assert len(results) == 2
        assert all("Python" in r.context for r in results)

    def test_recall_empty_memory_returns_empty(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path)
        assert mem.recall("anything") == []

    def test_persists_across_instances(self, tmp_path) -> None:
        mem1 = EpisodicMemory(tmp_path)
        mem1.record("persist", "test")
        mem2 = EpisodicMemory(tmp_path)
        recent = mem2.recent(1)
        assert len(recent) == 1
        assert recent[0].context == "persist"

    def test_record_without_optional_fields(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path)
        ep = mem.record("ctx", "act")
        assert ep.outcome == ""
        assert ep.emotion == "neutral"
        assert ep.tags == []

    def test_importance_scoring_emotion(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path)
        mem.record("ctx", "act", emotion="happy")
        with sqlite3.connect(str(mem.db_path)) as conn:
            row = conn.execute("SELECT importance FROM episodes").fetchone()
        assert row[0] == 1

    def test_importance_scoring_outcome_error(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path)
        mem.record("ctx", "act", outcome="test failed with error")
        with sqlite3.connect(str(mem.db_path)) as conn:
            row = conn.execute("SELECT importance FROM episodes").fetchone()
        assert row[0] == 1

    def test_eviction_respects_importance(self, tmp_path) -> None:
        mem = EpisodicMemory(tmp_path, max_episodes=3)
        mem.record("a", "act", emotion="neutral")  # importance 0
        mem.record("b", "act", outcome="error")    # importance 1
        mem.record("c", "act", emotion="neutral")  # importance 0
        mem.record("d", "act", emotion="neutral")  # importance 0, triggers eviction
        assert mem.count() == 3
        recent = mem.recent(3)
        contexts = [ep.context for ep in recent]
        assert "b" in contexts  # important episode should survive
