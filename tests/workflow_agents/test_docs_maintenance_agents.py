from __future__ import annotations

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock

from workflows.docs_maintenance.agents.aligner import AlignerAgent, AlignmentResult
from workflows.docs_maintenance.agents.detector import DetectorAgent, DetectionResult
from workflows.docs_maintenance.agents.updater import UpdaterAgent, UpdateResult


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def mock_role():
    m = MagicMock()
    m.role = "test_role"
    return m


class TestAlignerAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = AlignerAgent(mock_provider, mock_role, "sys", AlignmentResult)
        raw = (
            '{"aligned":false,"issues":['
            '{"path":"README.md","issue":"stale","suggestion":"update"}]}'
        )
        result = agent._parse(raw)
        assert result.aligned is False
        assert len(result.issues) == 1
        assert result.issues[0].path == "README.md"

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = AlignerAgent(mock_provider, mock_role, "sys", AlignmentResult)
        raw = '```json\n{"aligned":true}\n```'
        result = agent._parse(raw)
        assert result.aligned is True

    def test_parse_defaults(self, mock_provider, mock_role):
        agent = AlignerAgent(mock_provider, mock_role, "sys", AlignmentResult)
        raw = "{}"
        result = agent._parse(raw)
        assert result.aligned is True
        assert result.issues == []

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = AlignerAgent(mock_provider, mock_role, "sys", AlignmentResult)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("bad")


class TestDetectorAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = DetectorAgent(mock_provider, mock_role, "sys", DetectionResult)
        raw = '{"stale_docs":[{"path":"doc.md","reason":"old"}]}'
        result = agent._parse(raw)
        assert len(result.stale_docs) == 1
        assert result.stale_docs[0].path == "doc.md"
        assert result.stale_docs[0].reason == "old"

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = DetectorAgent(mock_provider, mock_role, "sys", DetectionResult)
        raw = '```json\n{"stale_docs":[]}\n```'
        result = agent._parse(raw)
        assert result.stale_docs == []

    def test_parse_defaults(self, mock_provider, mock_role):
        agent = DetectorAgent(mock_provider, mock_role, "sys", DetectionResult)
        raw = "{}"
        result = agent._parse(raw)
        assert result.stale_docs == []

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = DetectorAgent(mock_provider, mock_role, "sys", DetectionResult)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("nope")


class TestUpdaterAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = UpdaterAgent(mock_provider, mock_role, "sys", UpdateResult)
        raw = '{"updates":[{"path":"doc.md","new_content":"# Hello"}]}'
        result = agent._parse(raw)
        assert len(result.updates) == 1
        assert result.updates[0].path == "doc.md"
        assert result.updates[0].new_content == "# Hello"

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = UpdaterAgent(mock_provider, mock_role, "sys", UpdateResult)
        raw = '```json\n{"updates":[]}\n```'
        result = agent._parse(raw)
        assert result.updates == []

    def test_parse_defaults(self, mock_provider, mock_role):
        agent = UpdaterAgent(mock_provider, mock_role, "sys", UpdateResult)
        raw = "{}"
        result = agent._parse(raw)
        assert result.updates == []

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = UpdaterAgent(mock_provider, mock_role, "sys", UpdateResult)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("bad")
