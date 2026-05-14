from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

from memory.brain import Brain


class TestCrossProcess:
    def test_concurrent_writes_no_corruption(self, tmp_path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        script_a = tmp_path / "writer_a.py"
        script_b = tmp_path / "writer_b.py"

        script_a.write_text(
            f"""
import sys
sys.path.insert(0, r'{Path.cwd()}')
from pathlib import Path
from memory.brain import Brain
brain = Brain(Path(r'{repo}'))
for i in range(50):
    brain.perceive(f"ctx_a_{{i}}", f"act_a_{{i}}")
""",
            encoding="utf-8",
        )
        script_b.write_text(
            f"""
import sys
sys.path.insert(0, r'{Path.cwd()}')
from pathlib import Path
from memory.brain import Brain
brain = Brain(Path(r'{repo}'))
for i in range(50):
    brain.perceive(f"ctx_b_{{i}}", f"act_b_{{i}}")
""",
            encoding="utf-8",
        )

        proc_a = subprocess.Popen([sys.executable, str(script_a)])
        proc_b = subprocess.Popen([sys.executable, str(script_b)])
        proc_a.wait(timeout=60)
        proc_b.wait(timeout=60)

        brain = Brain(repo)
        assert brain.episodic.count() == 100
        recent = brain.recent(100)
        contexts = {ep.context for ep in recent}
        assert any("ctx_a_" in c for c in contexts)
        assert any("ctx_b_" in c for c in contexts)

    def test_crash_recovery(self, tmp_path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        script = tmp_path / "crasher.py"
        script.write_text(
            f"""
import sys
import os
sys.path.insert(0, r'{Path.cwd()}')
from pathlib import Path
from memory.brain import Brain
brain = Brain(Path(r'{repo}'))
brain.perceive("before_crash", "action")
os._exit(1)  # Hard exit, no cleanup
""",
            encoding="utf-8",
        )

        proc = subprocess.Popen([sys.executable, str(script)])
        proc.wait(timeout=30)
        assert proc.returncode != 0

        brain = Brain(repo)
        assert brain.episodic.count() == 1
        recent = brain.recent(1)
        assert recent[0].context == "before_crash"

        # Verify no stale lock file remains
        lock_file = repo / ".ai-team" / "memory" / ".memory.bus.lock"
        assert not lock_file.exists()


class TestStress:
    def test_episodic_recall_performance(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        for i in range(2000):
            brain.perceive(f"context number {i}", f"action {i}", f"outcome {i}")
        assert brain.episodic.count() == 1000  # capped at max_episodes

        start = time.perf_counter()
        result = brain.remember("context number 500", top_k=10)
        elapsed = time.perf_counter() - start
        assert len(result["episodes"]) == 10
        assert elapsed < 2.0  # Generous threshold for random projections

    def test_semantic_query_performance(self, tmp_path) -> None:
        brain = Brain(tmp_path)
        for i in range(500):
            brain.learn(f"concept_{i}", f"Concept {i}", f"Description of concept {i}")
        assert brain.semantic.count() == 500

        start = time.perf_counter()
        concepts = brain.semantic.query("Concept 250", top_k=5)
        elapsed = time.perf_counter() - start
        assert len(concepts) == 5
        assert elapsed < 2.0

    def test_vector_search_performance(self, tmp_path) -> None:
        from memory.backends.vector import VectorBackend
        from memory.embeddings import get_engine
        import numpy as np
        backend = VectorBackend(tmp_path / "vector")
        engine = get_engine()
        # Bulk populate internal state directly, then save once
        for i in range(1000):
            text = f"document content {i} about various topics"
            backend._vectors[f"key_{i}"] = engine.encode(text)
            backend._metas[f"key_{i}"] = {"text": text}
        backend._save("global", None)

        start = time.perf_counter()
        results = backend.search("document content 500", top_k=5)
        elapsed = time.perf_counter() - start
        assert len(results) == 5
        assert elapsed < 2.0
