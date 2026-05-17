from __future__ import annotations

import numpy as np
import pytest

from memory.embeddings import EmbeddingEngine, get_engine


class TestEmbeddingEngine:
    def test_encode_produces_normalized_vector(self) -> None:
        engine = EmbeddingEngine(dim=128)
        vec = engine.encode("hello world")
        assert vec.shape == (128,)
        assert vec.dtype == np.float32
        norm = np.linalg.norm(vec)
        assert norm == pytest.approx(1.0, abs=1e-5)

    def test_encode_empty_text_is_zero_vector(self) -> None:
        engine = EmbeddingEngine(dim=64)
        vec = engine.encode("")
        assert np.allclose(vec, 0.0)

    def test_similarity_of_identical_text_is_one(self) -> None:
        engine = EmbeddingEngine(dim=128)
        a = engine.encode("test phrase")
        b = engine.encode("test phrase")
        assert engine.similarity(a, b) == pytest.approx(1.0, abs=1e-4)

    def test_similarity_of_unrelated_text_is_low(self) -> None:
        engine = EmbeddingEngine(dim=256)
        a = engine.encode("quantum physics")
        b = engine.encode("banana bread recipe")
        sim = engine.similarity(a, b)
        assert 0.0 <= sim <= 1.0
        # With random projections unrelated texts should have low similarity
        assert sim < 0.5

    def test_similarity_is_symmetric(self) -> None:
        engine = EmbeddingEngine(dim=128)
        a = engine.encode("hello")
        b = engine.encode("world")
        assert engine.similarity(a, b) == pytest.approx(engine.similarity(b, a))

    def test_tokenization_filters_short_words(self) -> None:
        engine = EmbeddingEngine(dim=64)
        vec = engine.encode("a i o u")
        assert np.allclose(vec, 0.0)

    def test_get_engine_returns_singleton(self) -> None:
        e1 = get_engine(dim=256)
        e2 = get_engine(dim=256)
        assert e1 is e2
