from __future__ import annotations

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock

from workflows.command_assistant.agents.generator import GeneratorAgent, GeneratedCommand
from workflows.command_assistant.agents.parser import ParserAgent, ParsedIntent


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def mock_role():
    m = MagicMock()
    m.role = "test_role"
    return m


class TestGeneratorAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = GeneratorAgent(mock_provider, mock_role, "sys", GeneratedCommand)
        raw = '{"command":["ls","-la"],"explanation":"list","safe":true}'
        result = agent._parse(raw)
        assert result.command == ["ls", "-la"]
        assert result.explanation == "list"
        assert result.safe is True

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = GeneratorAgent(mock_provider, mock_role, "sys", GeneratedCommand)
        raw = '```json\n{"command":["pwd"],"explanation":"cwd","safe":false}\n```'
        result = agent._parse(raw)
        assert result.command == ["pwd"]
        assert result.safe is False

    def test_parse_defaults(self, mock_provider, mock_role):
        agent = GeneratorAgent(mock_provider, mock_role, "sys", GeneratedCommand)
        raw = "{}"
        result = agent._parse(raw)
        assert result.command == []
        assert result.explanation == ""
        assert result.safe is True

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = GeneratorAgent(mock_provider, mock_role, "sys", GeneratedCommand)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("broken")


class TestParserAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = ParserAgent(mock_provider, mock_role, "sys", ParsedIntent)
        raw = '{"action":"delete","target":"file.txt","parameters":{"force":true}}'
        result = agent._parse(raw)
        assert result.action == "delete"
        assert result.target == "file.txt"
        assert result.parameters == {"force": True}

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = ParserAgent(mock_provider, mock_role, "sys", ParsedIntent)
        raw = '```json\n{"action":"move","target":"b"}\n```'
        result = agent._parse(raw)
        assert result.action == "move"
        assert result.target == "b"

    def test_parse_defaults(self, mock_provider, mock_role):
        agent = ParserAgent(mock_provider, mock_role, "sys", ParsedIntent)
        raw = '{"action":"run"}'
        result = agent._parse(raw)
        assert result.target == ""
        assert result.parameters == {}

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = ParserAgent(mock_provider, mock_role, "sys", ParsedIntent)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("err")

    def test_parse_missing_required_field_raises(self, mock_provider, mock_role):
        agent = ParserAgent(mock_provider, mock_role, "sys", ParsedIntent)
        with pytest.raises(ValidationError):
            agent._parse('{"target":"file.txt"}')
