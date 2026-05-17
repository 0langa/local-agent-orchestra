from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from memory.bus import MemoryBus


class TestMemoryBus:
    def test_singleton_per_repo_root(self, tmp_path) -> None:
        bus1 = MemoryBus(tmp_path)
        bus2 = MemoryBus(tmp_path)
        assert bus1 is bus2

    def test_different_repos_get_different_instances(self, tmp_path) -> None:
        bus1 = MemoryBus(tmp_path / "a")
        bus2 = MemoryBus(tmp_path / "b")
        assert bus1 is not bus2

    def test_write_and_read(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        bus.write("jsonl", "key1", {"data": "value1"})
        result = bus.read("jsonl", "key1")
        assert result == {"data": "value1"}

    def test_read_missing_returns_none(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        assert bus.read("jsonl", "missing") is None

    def test_list_keys(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        bus.write("sqlite", "a", {"v": 1})
        bus.write("sqlite", "b", {"v": 2})
        keys = bus.list_keys("sqlite")
        assert sorted(keys) == ["a", "b"]

    def test_search(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        bus.write("vector", "cat", {"text": "feline meow"})
        bus.write("vector", "dog", {"text": "canine woof"})
        results = bus.search("vector", "cat", top_k=1)
        assert len(results) == 1
        assert results[0]["key"] == "cat"

    def test_exclusive_lock_is_reentrant(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        with bus.exclusive():
            bus.write("jsonl", "key1", {"v": 1})
            with bus.exclusive():
                bus.write("jsonl", "key2", {"v": 2})
        assert bus.read("jsonl", "key1") == {"v": 1}
        assert bus.read("jsonl", "key2") == {"v": 2}

    def test_shared_lock_allows_concurrent_reads(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        bus.write("jsonl", "key", {"v": 1})
        results: list[dict] = []

        def reader() -> None:
            with bus.shared():
                results.append(bus.read("jsonl", "key"))

        t1 = threading.Thread(target=reader)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(results) == 2
        assert all(r == {"v": 1} for r in results)

    def test_exclusive_blocks_concurrent_writes(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        order: list[str] = []

        def writer(name: str) -> None:
            with bus.exclusive():
                order.append(f"{name}_start")
                time.sleep(0.05)
                bus.write("jsonl", name, {"writer": name})
                order.append(f"{name}_end")

        t1 = threading.Thread(target=writer, args=("a",))
        t2 = threading.Thread(target=writer, args=("b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Each writer should fully complete before the other starts
        starts = [i for i, x in enumerate(order) if "_start" in x]
        ends = [i for i, x in enumerate(order) if "_end" in x]
        assert len(starts) == 2
        assert len(ends) == 2
        # Verify no interleaving: starts and ends should be paired
        for i in range(0, len(order), 2):
            assert order[i].endswith("_start")
            assert order[i + 1].endswith("_end")

    def test_creates_memory_directory(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        assert bus.base_path.exists()
        assert bus.base_path == tmp_path / ".ai-team" / "memory"

    def test_backend_instances_are_reused(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        b1 = bus._get_backend("jsonl")
        b2 = bus._get_backend("jsonl")
        assert b1 is b2

    def test_all_backend_types_accessible(self, tmp_path) -> None:
        bus = MemoryBus(tmp_path)
        for name in ("jsonl", "sqlite", "vector"):
            bus.write(name, "test", {"ok": True})
            assert bus.read(name, "test") == {"ok": True}
