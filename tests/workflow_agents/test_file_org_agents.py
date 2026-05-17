"""Tests for file-organization workflow agents' custom _parse() methods."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from config.config import AgentModelConfig, ModelRole
from workflows.file_organization.agents.analyzer import AnalyzerAgent, AnalyzerResult
from workflows.file_organization.agents.applier import ApplierAgent, ApplierResult
from workflows.file_organization.agents.proposer import ProposerAgent, ProposerResult


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


class TestAnalyzerAgent:
    @pytest.fixture
    def agent(self):
        return _make_agent(AnalyzerAgent, AnalyzerResult, ModelRole.PLANNER)

    def test_normal_files_array(self, agent):
        raw = json.dumps(
            {
                "files": [
                    {"path": "/a.txt", "category": "text", "confidence": 0.9},
                    {"path": "/b.png", "category": "image", "confidence": 0.8},
                ],
                "summary": "2 files",
            }
        )
        result = agent._parse(raw)
        assert len(result.files) == 2
        assert result.files[0].path == "/a.txt"
        assert result.files[1].category == "image"
        assert result.summary == "2 files"

    def test_dict_with_path_keys_fallback(self, agent):
        raw = json.dumps(
            {
                "/a.txt": {"category": "text", "confidence": 0.95},
                "/b.jpg": {"category": "image", "confidence": 0.7},
                "/c.zip": {"category": "archive"},
            }
        )
        result = agent._parse(raw)
        assert len(result.files) == 3
        paths = [f.path for f in result.files]
        assert "/a.txt" in paths
        assert "/b.jpg" in paths
        assert "/c.zip" in paths
        cats = {f.path: f.category for f in result.files}
        assert cats["/a.txt"] == "text"
        assert cats["/c.zip"] == "archive"
        confs = {f.path: f.confidence for f in result.files}
        assert confs["/c.zip"] == pytest.approx(0.5)

    def test_invalid_json_raises(self, agent):
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("not json")


class TestApplierAgent:
    @pytest.fixture
    def agent(self):
        return _make_agent(ApplierAgent, ApplierResult, ModelRole.EXECUTOR)

    def test_normal_moves(self, agent):
        raw = json.dumps(
            {
                "moves": [
                    {"source": "/a.txt", "target": "/b/a.txt", "success": True},
                    {"source": "/c.txt", "target": "/d/c.txt", "success": False, "error": "perm"},
                ],
                "summary": "done",
            }
        )
        result = agent._parse(raw)
        assert len(result.moves) == 2
        assert result.moves[0].source == "/a.txt"
        assert result.moves[0].success is True
        assert result.moves[1].error == "perm"

    def test_destination_alias(self, agent):
        raw = json.dumps(
            {
                "moves": [
                    {"source": "/a.txt", "destination": "/b/a.txt", "success": True}
                ]
            }
        )
        result = agent._parse(raw)
        assert result.moves[0].target == "/b/a.txt"

    def test_status_string_mapping(self, agent):
        raw = json.dumps(
            {
                "moves": [
                    {"source": "/a.txt", "target": "/b/a.txt", "status": "ok"},
                    {"source": "/c.txt", "target": "/d/c.txt", "status": "Success"},
                    {"source": "/e.txt", "target": "/f/e.txt", "status": "done"},
                    {"source": "/g.txt", "target": "/h/g.txt", "status": "applied"},
                    {"source": "/i.txt", "target": "/j/i.txt", "status": "failed"},
                ]
            }
        )
        result = agent._parse(raw)
        successes = [m.success for m in result.moves]
        assert successes == [True, True, True, True, False]

    def test_status_bool_mapping(self, agent):
        raw = json.dumps(
            {
                "moves": [
                    {"source": "/a.txt", "target": "/b/a.txt", "status": 1},
                    {"source": "/c.txt", "target": "/d/c.txt", "status": 0},
                ]
            }
        )
        result = agent._parse(raw)
        assert result.moves[0].success is True
        assert result.moves[1].success is False

    def test_missing_success_defaults_false(self, agent):
        raw = json.dumps(
            {
                "moves": [
                    {"source": "/a.txt", "target": "/b/a.txt"}
                ]
            }
        )
        result = agent._parse(raw)
        assert result.moves[0].success is False
        assert result.moves[0].error == ""


class TestProposerAgent:
    @pytest.fixture
    def agent(self):
        return _make_agent(ProposerAgent, ProposerResult, ModelRole.PLANNER)

    def test_normal_actions(self, agent):
        raw = json.dumps(
            {
                "actions": [
                    {"source": "/a.txt", "target": "/b/a.txt", "reason": "r1"},
                    {"source": "/c.txt", "target": "/d/c.txt", "reason": "r2"},
                ],
                "new_structure_summary": "sum",
                "preview": "pre",
                "warnings": ["w1"],
            }
        )
        result = agent._parse(raw)
        assert len(result.actions) == 2
        assert result.actions[0].source == "/a.txt"
        assert result.actions[1].reason == "r2"
        assert result.new_structure_summary == "sum"
        assert result.preview == "pre"
        assert result.warnings == ["w1"]

    def test_moves_alias(self, agent):
        raw = json.dumps(
            {
                "moves": [
                    {"source": "/a.txt", "target": "/b/a.txt", "reason": "r1"}
                ]
            }
        )
        result = agent._parse(raw)
        assert len(result.actions) == 1
        assert result.actions[0].source == "/a.txt"

    def test_destination_alias(self, agent):
        raw = json.dumps(
            {
                "actions": [
                    {"source": "/a.txt", "destination": "/b/a.txt"}
                ]
            }
        )
        result = agent._parse(raw)
        assert result.actions[0].target == "/b/a.txt"

    def test_summary_alias(self, agent):
        raw = json.dumps(
            {
                "actions": [],
                "summary": "the summary",
            }
        )
        result = agent._parse(raw)
        assert result.new_structure_summary == "the summary"

    def test_missing_reason_defaults_empty(self, agent):
        raw = json.dumps(
            {
                "actions": [
                    {"source": "/a.txt", "target": "/b/a.txt"}
                ]
            }
        )
        result = agent._parse(raw)
        assert result.actions[0].reason == ""
