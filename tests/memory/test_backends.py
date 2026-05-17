from __future__ import annotations

import json
import pytest

from memory.backends.jsonl import JsonlBackend
from memory.backends.sqlite import SqliteBackend
from memory.backends.vector import VectorBackend


class TestJsonlBackend:
    def test_write_and_read(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("key1", {"data": "value1"})
        result = backend.read("key1")
        assert result == {"data": "value1"}

    def test_read_missing_key_returns_none(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        assert backend.read("missing") is None

    def test_overwrite_returns_latest(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("key1", {"version": 1})
        backend.write("key1", {"version": 2})
        result = backend.read("key1")
        assert result == {"version": 2}

    def test_scope_isolation(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("key1", {"scope": "global"}, scope="global")
        backend.write("key1", {"scope": "run"}, scope="run", run_id="r1")
        assert backend.read("key1", scope="global") == {"scope": "global"}
        assert backend.read("key1", scope="run", run_id="r1") == {"scope": "run"}

    def test_list_keys(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("a", {"v": 1})
        backend.write("b", {"v": 2})
        keys = backend.list_keys()
        assert sorted(keys) == ["a", "b"]

    def test_search_finds_matching_value(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("cat", {"animal": "feline", "sound": "meow"})
        backend.write("dog", {"animal": "canine", "sound": "woof"})
        results = backend.search("feline")
        assert len(results) == 1
        assert results[0]["key"] == "cat"

    def test_sanitize_key_blocks_dangerous_chars(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("../../etc/passwd", {"data": 1})
        # Should sanitize and write, not escape directory
        keys = backend.list_keys()
        assert "..etcpasswd" in keys or "../../etc/passwd" not in keys


class TestSqliteBackend:
    def test_write_and_read(self, tmp_path) -> None:
        backend = SqliteBackend(tmp_path)
        backend.write("key1", {"data": "value1"})
        result = backend.read("key1")
        assert result == {"data": "value1"}

    def test_read_missing_key_returns_none(self, tmp_path) -> None:
        backend = SqliteBackend(tmp_path)
        assert backend.read("missing") is None

    def test_upsert_overwrites(self, tmp_path) -> None:
        backend = SqliteBackend(tmp_path)
        backend.write("key1", {"version": 1})
        backend.write("key1", {"version": 2})
        result = backend.read("key1")
        assert result == {"version": 2}

    def test_scope_isolation(self, tmp_path) -> None:
        backend = SqliteBackend(tmp_path)
        backend.write("key1", {"scope": "global"}, scope="global")
        backend.write("key1", {"scope": "run"}, scope="run", run_id="r1")
        assert backend.read("key1", scope="global") == {"scope": "global"}
        assert backend.read("key1", scope="run", run_id="r1") == {"scope": "run"}

    def test_list_keys(self, tmp_path) -> None:
        backend = SqliteBackend(tmp_path)
        backend.write("a", {"v": 1})
        backend.write("b", {"v": 2})
        keys = backend.list_keys()
        assert sorted(keys) == ["a", "b"]

    def test_search_uses_like(self, tmp_path) -> None:
        backend = SqliteBackend(tmp_path)
        backend.write("cat", {"animal": "feline"})
        backend.write("dog", {"animal": "canine"})
        results = backend.search("fel")
        assert len(results) == 1
        assert results[0]["key"] == "cat"

    def test_persists_across_instances(self, tmp_path) -> None:
        backend1 = SqliteBackend(tmp_path)
        backend1.write("persist", {"test": True})
        backend2 = SqliteBackend(tmp_path)
        assert backend2.read("persist") == {"test": True}


class TestVectorBackend:
    def test_write_and_read(self, tmp_path) -> None:
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("key1", {"text": "hello world"})
        result = backend.read("key1")
        assert result == {"text": "hello world"}

    def test_search_ranking(self, tmp_path) -> None:
        backend = VectorBackend(tmp_path, dim=128)
        backend.write("cat", {"text": "feline animal meow"})
        backend.write("dog", {"text": "canine animal woof"})
        backend.write("car", {"text": "vehicle automobile drive"})
        results = backend.search("kitten cat", top_k=2)
        assert len(results) == 2
        # Cat should be most similar to kitten query
        assert results[0]["key"] == "cat"

    def test_search_returns_scores(self, tmp_path) -> None:
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("a", {"text": "apple banana"})
        results = backend.search("fruit", top_k=1)
        assert "score" in results[0]
        assert 0.0 <= results[0]["score"] <= 1.0

    def test_persists_across_instances(self, tmp_path) -> None:
        backend1 = VectorBackend(tmp_path, dim=64)
        backend1.write("persist", {"text": "test data"})
        backend2 = VectorBackend(tmp_path, dim=64)
        assert backend2.read("persist") == {"text": "test data"}

    def test_empty_search_returns_empty(self, tmp_path) -> None:
        backend = VectorBackend(tmp_path, dim=32)
        assert backend.search("anything") == []

    def test_corruption_recovery_skips_bad_lines(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("good", {"v": 1})
        # Inject a corrupted line directly into the file
        path = tmp_path / "global" / "good.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write("this is not json\n")
        backend.write("good", {"v": 2})
        result = backend.read("good")
        assert result == {"v": 2}

    def test_corruption_recovery_skips_bad_lines_in_search(self, tmp_path) -> None:
        backend = JsonlBackend(tmp_path)
        backend.write("cat", {"animal": "feline"})
        path = tmp_path / "global" / "cat.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write("{broken json\n")
        results = backend.search("feline")
        assert len(results) == 1
        assert results[0]["key"] == "cat"
