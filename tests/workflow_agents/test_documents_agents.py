"""Tests for documents workflow agents' custom _parse() methods."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from config.config import AgentModelConfig, ModelRole
from workflows.documents.agents.indexer import IndexerAgent, IndexerOutput
from workflows.documents.agents.retriever import RetrieverAgent, RetrieverOutput


def _make_agent(agent_cls, schema_cls, role: ModelRole):
    provider = MagicMock()
    role_config = AgentModelConfig(
        role=role,
        provider="mock",
        provider_type="openai_compatible",
        endpoint="http://localhost",
        model="mock-model",
    )
    return agent_cls(
        provider=provider,
        role_config=role_config,
        system_prompt="test",
        output_schema=schema_cls,
    )


class TestIndexerAgent:
    @pytest.fixture
    def agent(self):
        return _make_agent(IndexerAgent, IndexerOutput, ModelRole.INDEXER)

    def test_normal_documents_array(self, agent):
        raw = json.dumps(
            {
                "documents": [
                    {"path": "/a.md", "summary": "sum A", "keywords": ["k1"]},
                    {"path": "/b.md", "summary": "sum B", "keywords": ["k2", "k3"]},
                ]
            }
        )
        result = agent._parse(raw)
        assert len(result.documents) == 2
        assert result.documents[0].path == "/a.md"
        assert result.documents[1].keywords == ["k2", "k3"]

    def test_alias_index_array_normalized(self, agent):
        raw = json.dumps(
            {
                "index": [
                    {
                        "file": "/f1.py",
                        "source": "/f2.py",
                        "description": "desc",
                        "tags": ["t1"],
                    },
                    {
                        "path": "/f3.py",
                        "summary": "sum",
                        "keywords": ["k1"],
                    },
                ]
            }
        )
        result = agent._parse(raw)
        paths = [d.path for d in result.documents]
        assert "/f1.py" in paths
        assert "/f3.py" in paths
        summaries = {d.path: d.summary for d in result.documents}
        assert summaries["/f1.py"] == "desc"
        assert summaries["/f3.py"] == "sum"

    def test_missing_documents_and_index_fallback_empty(self, agent):
        raw = json.dumps({})
        result = agent._parse(raw)
        assert result.documents == []


class TestRetrieverAgent:
    @pytest.fixture
    def agent(self):
        return _make_agent(RetrieverAgent, RetrieverOutput, ModelRole.RETRIEVER)

    def test_normal_chunks_array(self, agent):
        raw = json.dumps(
            {
                "chunks": [
                    {"path": "/a.md", "excerpt": "ex A", "relevance_score": 0.9},
                    {"path": "/b.md", "excerpt": "ex B", "relevance_score": 0.7},
                ]
            }
        )
        result = agent._parse(raw)
        assert len(result.chunks) == 2
        assert result.chunks[0].path == "/a.md"
        assert result.chunks[0].relevance_score == pytest.approx(0.9)
        assert result.chunks[1].relevance_score == pytest.approx(0.7)

    def test_alias_results_array_normalized(self, agent):
        raw = json.dumps(
            {
                "results": [
                    {
                        "file": "/f1.py",
                        "quote": "q1",
                        "score": 0.85,
                    },
                    {
                        "document": "/f2.py",
                        "text": "t2",
                        "relevance_score": 1.2,
                    },
                    {
                        "source": "/f3.py",
                        "excerpt": "e3",
                    },
                ]
            }
        )
        result = agent._parse(raw)
        paths = [c.path for c in result.chunks]
        assert "/f1.py" in paths
        assert "/f2.py" in paths
        assert "/f3.py" in paths
        scores = {c.path: c.relevance_score for c in result.chunks}
        assert scores["/f1.py"] == pytest.approx(0.85)
        assert scores["/f2.py"] == pytest.approx(1.0)  # clamped
        assert scores["/f3.py"] == pytest.approx(0.0)  # missing score

    def test_empty_results_fallback_empty(self, agent):
        raw = json.dumps({})
        result = agent._parse(raw)
        assert result.chunks == []
