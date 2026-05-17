from __future__ import annotations

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock

from workflows.github_maintenance.agents.drafter import DrafterAgent, DraftResult
from workflows.github_maintenance.agents.summarizer import SummarizerAgent, SummaryResult


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def mock_role():
    m = MagicMock()
    m.role = "test_role"
    return m


class TestDrafterAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = DrafterAgent(mock_provider, mock_role, "sys", DraftResult)
        raw = '{"pr_title":"Fix bug","pr_body":"details","branch_name":"fix-bug"}'
        result = agent._parse(raw)
        assert result.pr_title == "Fix bug"
        assert result.pr_body == "details"
        assert result.branch_name == "fix-bug"

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = DrafterAgent(mock_provider, mock_role, "sys", DraftResult)
        raw = '```json\n{"pr_title":"T","pr_body":"B"}\n```'
        result = agent._parse(raw)
        assert result.pr_title == "T"
        assert result.pr_body == "B"
        assert result.branch_name == ""

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = DrafterAgent(mock_provider, mock_role, "sys", DraftResult)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("bad")

    def test_parse_missing_required_field_raises(self, mock_provider, mock_role):
        agent = DrafterAgent(mock_provider, mock_role, "sys", DraftResult)
        with pytest.raises(ValidationError):
            agent._parse('{"pr_title":"only title"}')


class TestSummarizerAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = SummarizerAgent(mock_provider, mock_role, "sys", SummaryResult)
        raw = '{"issues":[{"number":1,"title":"Bug","summary":"bad thing"}]}'
        result = agent._parse(raw)
        assert len(result.issues) == 1
        assert result.issues[0].number == 1
        assert result.issues[0].title == "Bug"
        assert result.issues[0].summary == "bad thing"

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = SummarizerAgent(mock_provider, mock_role, "sys", SummaryResult)
        raw = '```json\n{"issues":[]}\n```'
        result = agent._parse(raw)
        assert result.issues == []

    def test_parse_defaults(self, mock_provider, mock_role):
        agent = SummarizerAgent(mock_provider, mock_role, "sys", SummaryResult)
        raw = "{}"
        result = agent._parse(raw)
        assert result.issues == []

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = SummarizerAgent(mock_provider, mock_role, "sys", SummaryResult)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("bad")
