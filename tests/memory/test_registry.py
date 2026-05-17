from __future__ import annotations

import pytest

from memory.registry import MemoryRegistry


class TestMemoryRegistry:
    def test_default_backends_registered(self, tmp_path) -> None:
        reg = MemoryRegistry(tmp_path)
        backends = reg.list_backends()
        assert "jsonl" in backends
        assert "sqlite" in backends
        assert "vector" in backends

    def test_get_backend(self, tmp_path) -> None:
        reg = MemoryRegistry(tmp_path)
        backend = reg.get("jsonl")
        assert backend is not None

    def test_get_missing_raises(self, tmp_path) -> None:
        reg = MemoryRegistry(tmp_path)
        with pytest.raises(KeyError):
            reg.get("missing")

    def test_register_custom_backend(self, tmp_path) -> None:
        reg = MemoryRegistry(tmp_path)
        from memory.backends.base import MemoryBackend

        class DummyBackend(MemoryBackend):
            def read(self, key, scope="global", run_id=None):
                return None
            def write(self, key, value, scope="global", run_id=None):
                pass
            def list_keys(self, scope="global", run_id=None):
                return []
            def search(self, query, scope="global", run_id=None):
                return []

        reg.register("dummy", DummyBackend(tmp_path / "dummy"))
        assert "dummy" in reg.list_backends()

    def test_read_write_through_registry(self, tmp_path) -> None:
        reg = MemoryRegistry(tmp_path)
        reg.write("jsonl", "key1", {"test": True})
        result = reg.read("jsonl", "key1")
        assert result == {"test": True}

    def test_search_through_registry(self, tmp_path) -> None:
        reg = MemoryRegistry(tmp_path)
        reg.write("sqlite", "key1", {"text": "hello world"})
        results = reg.search("sqlite", "hello")
        assert len(results) == 1
        assert results[0]["key"] == "key1"

    def test_default_registry_is_singleton(self, tmp_path) -> None:
        from memory.registry import get_default_registry
        r1 = get_default_registry(tmp_path)
        r2 = get_default_registry(tmp_path)
        assert r1 is r2

    def test_registry_uses_project_subpath(self, tmp_path) -> None:
        reg = MemoryRegistry(tmp_path)
        assert reg.base_path == tmp_path / ".ai-team" / "memory"
        assert reg.base_path.exists()

    def test_different_projects_get_different_registries(self, tmp_path) -> None:
        from memory.registry import get_default_registry
        project_a = tmp_path / "project_a"
        project_b = tmp_path / "project_b"
        r1 = get_default_registry(project_a)
        r2 = get_default_registry(project_b)
        assert r1 is not r2
        assert r1.base_path != r2.base_path
