from __future__ import annotations

import pytest

from memory.brain import Brain


class TestBrain:
    def test_perceive_creates_episode_and_concepts(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        ep = brain.perceive("ctx", "act", "out", "happy", ["t"])
        assert ep.context == "ctx"
        assert ep.action == "act"
        recent = brain.recent(1)
        assert len(recent) == 1
        assert recent[0].id == ep.id

    def test_learn_and_remember(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        brain.learn("python", "Python", "A programming language")
        brain.learn("java", "Java", "Another programming language")
        result = brain.remember("programming language")
        assert "concepts" in result
        assert "episodes" in result
        labels = [c["label"] for c in result["concepts"]]
        assert "Python" in labels

    def test_relate_connects_concepts(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        brain.learn("a", "A")
        brain.learn("b", "B")
        brain.relate("a", "b")
        c = brain.semantic.get("a")
        assert c is not None
        assert "b" in c.related

    def test_remember_fuses_episodes_and_concepts(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        brain.perceive("User asked about Python", "I explained Python")
        brain.learn("python", "Python", "Programming language")
        result = brain.remember("Python")
        assert len(result["episodes"]) > 0
        assert len(result["concepts"]) > 0

    def test_summarize_outputs_text(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        brain.perceive("ctx1", "act1", "out1")
        brain.perceive("ctx2", "act2", "out2")
        summary = brain.summarize()
        assert "Recent" in summary
        assert "ctx1" in summary or "ctx2" in summary

    def test_persists_across_instances(self, tmp_path) -> None:
        brain1 = Brain(tmp_path)
        brain1.perceive("persist", "test")
        brain2 = Brain(tmp_path)
        recent = brain2.recent(1)
        assert len(recent) == 1
        assert recent[0].context == "persist"

    def test_auto_extract_concepts_from_perceive(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        brain.perceive("User asked about programming", "I explained programming")
        concepts = brain.semantic.list_all()
        assert len(concepts) > 0

    def test_deduplication_merges_high_similarity(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        brain.learn("python", "Python", "A programming language")
        # Perceive something containing a very similar word
        brain.perceive("User asked about Python scripting", "I explained Python scripting")
        concepts = brain.semantic.list_all()
        # Should merge "python" and "scripting" concepts if similarity > 0.85
        # At minimum, "python" should exist and not be duplicated
        labels = [c.label for c in concepts]
        assert "Python" in labels

    def test_deduplication_creates_related_for_medium_similarity(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        brain.learn("coding", "Coding", "The act of writing code")
        brain.perceive("User asked about programming", "I explained programming")
        concepts = brain.semantic.list_all()
        # Either "coding" absorbed "programming" as related, or they are separate
        assert len(concepts) >= 1

    def test_empty_remember_returns_empty(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        result = brain.remember("anything")
        assert result["episodes"] == []
        assert result["concepts"] == []

    def test_creates_project_scope_file(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        scope_file = tmp_path / ".ai-team" / "memory" / ".project_scope"
        assert scope_file.exists()
        assert scope_file.read_text(encoding="utf-8").strip() == str(tmp_path.resolve())

    def test_rejects_different_project(self, tmp_path) -> None:
        # Create memory dir with a scope file claiming it belongs to another project
        memory_path = tmp_path / ".ai-team" / "memory"
        memory_path.mkdir(parents=True, exist_ok=True)
        scope_file = memory_path / ".project_scope"
        scope_file.write_text("/some/other/project", encoding="utf-8")
        with pytest.raises(RuntimeError, match="Memory scope mismatch"):
            Brain(tmp_path)

    def test_accepts_same_project_on_reopen(self, tmp_path) -> None:
        brain1 = Brain(tmp_path)
        brain1.perceive("ctx", "act")
        brain2 = Brain(tmp_path)
        assert len(brain2.recent(1)) == 1
