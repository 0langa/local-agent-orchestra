from __future__ import annotations

import pytest

from memory.semantic import SemanticMemory, Concept


class TestSemanticMemory:
    def test_learn_creates_concept(self, tmp_path) -> None:
        mem = SemanticMemory(tmp_path)
        c = mem.learn("python", "Python", "A programming language")
        assert isinstance(c, Concept)
        assert c.id == "python"
        assert c.label == "Python"
        assert c.embedding is not None

    def test_get_retrieves_concept(self, tmp_path) -> None:
        mem = SemanticMemory(tmp_path)
        mem.learn("python", "Python", "A programming language")
        c = mem.get("python")
        assert c is not None
        assert c.label == "Python"

    def test_get_missing_returns_none(self, tmp_path) -> None:
        mem = SemanticMemory(tmp_path)
        assert mem.get("missing") is None

    def test_relate_adds_bidirectional_link(self, tmp_path) -> None:
        mem = SemanticMemory(tmp_path)
        mem.learn("python", "Python")
        mem.learn("java", "Java")
        mem.relate("python", "java")
        c = mem.get("python")
        assert c is not None
        assert "java" in c.related

    def test_query_finds_similar_concepts(self, tmp_path) -> None:
        mem = SemanticMemory(tmp_path)
        mem.learn("python", "Python", "A programming language for data science")
        mem.learn("cooking", "Cooking", "The art of preparing food")
        mem.learn("javascript", "JavaScript", "A web programming language")
        results = mem.query("programming language", top_k=2)
        assert len(results) == 2
        labels = [r.label for r in results]
        assert "Python" in labels
        assert "JavaScript" in labels

    def test_query_empty_returns_empty(self, tmp_path) -> None:
        mem = SemanticMemory(tmp_path)
        assert mem.query("anything") == []

    def test_persists_across_instances(self, tmp_path) -> None:
        mem1 = SemanticMemory(tmp_path)
        mem1.learn("persist", "Persist", "Test concept")
        mem2 = SemanticMemory(tmp_path)
        c = mem2.get("persist")
        assert c is not None
        assert c.label == "Persist"

    def test_learn_overwrites_existing(self, tmp_path) -> None:
        mem = SemanticMemory(tmp_path)
        mem.learn("x", "Old", "Old description")
        mem.learn("x", "New", "New description")
        c = mem.get("x")
        assert c is not None
        assert c.label == "New"
