"""Tests for VectorBackend scope/run_id isolation fix."""

from __future__ import annotations

import pytest

from memory.backends.vector import VectorBackend


class TestVectorBackendScopeIsolation:
    def test_write_read_same_scope(self, tmp_path):
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("key1", {"text": "hello"}, scope="global")
        assert backend.read("key1", scope="global") == {"text": "hello"}

    def test_read_different_scope_returns_none(self, tmp_path):
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("key1", {"text": "hello"}, scope="global")
        assert backend.read("key1", scope="repository") is None

    def test_list_keys_is_scoped(self, tmp_path):
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("a", {"v": 1}, scope="global")
        backend.write("b", {"v": 2}, scope="repository")
        assert backend.list_keys(scope="global") == ["a"]
        assert backend.list_keys(scope="repository") == ["b"]

    def test_search_is_scoped(self, tmp_path):
        backend = VectorBackend(tmp_path, dim=128)
        backend.write("cat", {"text": "feline"}, scope="global")
        backend.write("dog", {"text": "canine"}, scope="repository")
        global_results = backend.search("animal", scope="global", top_k=5)
        assert len(global_results) == 1
        assert global_results[0]["key"] == "cat"
        repo_results = backend.search("animal", scope="repository", top_k=5)
        assert len(repo_results) == 1
        assert repo_results[0]["key"] == "dog"

    def test_run_scope_with_run_id(self, tmp_path):
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("key1", {"text": "run-a"}, scope="run", run_id="abc")
        backend.write("key1", {"text": "run-b"}, scope="run", run_id="def")
        assert backend.read("key1", scope="run", run_id="abc") == {"text": "run-a"}
        assert backend.read("key1", scope="run", run_id="def") == {"text": "run-b"}

    def test_persists_across_instances_with_scope(self, tmp_path):
        backend1 = VectorBackend(tmp_path, dim=64)
        backend1.write("key1", {"text": "global-val"}, scope="global")
        backend1.write("key1", {"text": "repo-val"}, scope="repository")
        backend1.write("key1", {"text": "run-abc"}, scope="run", run_id="abc")

        backend2 = VectorBackend(tmp_path, dim=64)
        assert backend2.read("key1", scope="global") == {"text": "global-val"}
        assert backend2.read("key1", scope="repository") == {"text": "repo-val"}
        assert backend2.read("key1", scope="run", run_id="abc") == {"text": "run-abc"}
        assert backend2.read("key1", scope="run", run_id="xyz") is None

    def test_save_does_not_leak_across_scopes(self, tmp_path):
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("key1", {"text": "global"}, scope="global")
        backend.write("key2", {"text": "repo"}, scope="repository")

        # Verify files only contain their own entries
        global_path = tmp_path / "global" / "vector_index.json"
        repo_path = tmp_path / "repository" / "vector_index.json"
        global_data = __import__("json").loads(global_path.read_text())
        repo_data = __import__("json").loads(repo_path.read_text())

        assert len(global_data["entries"]) == 1
        assert global_data["entries"][0]["key"] == "key1"
        assert len(repo_data["entries"]) == 1
        assert repo_data["entries"][0]["key"] == "key2"

    def test_same_key_different_scopes_coexist(self, tmp_path):
        backend = VectorBackend(tmp_path, dim=64)
        backend.write("shared", {"text": "global"}, scope="global")
        backend.write("shared", {"text": "repo"}, scope="repository")
        assert backend.read("shared", scope="global") == {"text": "global"}
        assert backend.read("shared", scope="repository") == {"text": "repo"}
