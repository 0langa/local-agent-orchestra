"""Tests for research workflow agents' custom _parse() methods."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from config.config import AgentModelConfig, ModelRole
from workflows.research.agents.gatherer import GathererAgent, GatherResult
from workflows.research.agents.reporter import ReporterAgent
from workflows.research.agents.summarizer import SummarizerAgent, SummaryResult
from workflows.research.reports.final_report import ResearchReport


def _make_agent(agent_cls, schema_cls):
    provider = MagicMock()
    role_config = AgentModelConfig(
        role=ModelRole.GATHERER,
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


class TestGathererAgent:
    @pytest.fixture
    def agent(self):
        return _make_agent(GathererAgent, GatherResult)

    def test_normal_sources_array(self, agent):
        raw = json.dumps(
            {
                "sources": [
                    {
                        "url": "https://example.com",
                        "title": "Example",
                        "snippet": "An example site.",
                        "relevance_score": 7,
                    }
                ],
                "search_queries": ["example query"],
                "raw_findings": "found stuff",
            }
        )
        result = agent._parse(raw)
        assert len(result.sources) == 1
        assert result.sources[0].url == "https://example.com"
        assert result.sources[0].title == "Example"
        assert result.sources[0].snippet == "An example site."
        assert result.sources[0].relevance_score == 7
        assert result.search_queries == ["example query"]
        assert result.raw_findings == "found stuff"

    @pytest.mark.parametrize(
        "label, expected",
        [
            ("high", 8),
            ("HIGH", 8),
            ("medium", 6),
            ("MEDIUM", 6),
            ("low", 4),
            ("LOW", 4),
            ("unknown", 4),
        ],
    )
    def test_relevance_label_mapping(self, agent, label, expected):
        raw = json.dumps(
            {
                "sources": [
                    {
                        "url": "https://x.com",
                        "title": "X",
                        "snippet": "s",
                        "relevance": label,
                    }
                ]
            }
        )
        result = agent._parse(raw)
        assert result.sources[0].relevance_score == expected

    def test_title_fallbacks(self, agent):
        raw = json.dumps(
            {
                "sources": [
                    {"url": "https://a.com", "snippet": "s", "relevance_score": 5},
                    {"name": "Named", "snippet": "s", "relevance_score": 5},
                    {"snippet": "s", "relevance_score": 5},
                ]
            }
        )
        result = agent._parse(raw)
        titles = [s.title for s in result.sources]
        assert titles[0] == "https://a.com"
        assert titles[1] == "Named"
        assert titles[2] == "Untitled source"

    def test_snippet_fallbacks(self, agent):
        raw = json.dumps(
            {
                "sources": [
                    {"url": "u", "title": "T", "relevance_score": 5},
                    {
                        "url": "u",
                        "title": "T2",
                        "description": "Desc",
                        "relevance_score": 5,
                    },
                    {
                        "url": "u",
                        "title": "T3",
                        "summary": "Summ",
                        "relevance_score": 5,
                    },
                    {
                        "url": "u",
                        "title": "T4",
                        "raw_findings": "Raw",
                        "relevance_score": 5,
                    },
                ]
            }
        )
        result = agent._parse(raw)
        snippets = [s.snippet for s in result.sources]
        assert snippets[0] == "T"
        assert snippets[1] == "Desc"
        assert snippets[2] == "Summ"
        assert snippets[3] == "Raw"

    def test_search_queries_alias(self, agent):
        raw = json.dumps({"queries": ["q1", "q2"]})
        result = agent._parse(raw)
        assert result.search_queries == ["q1", "q2"]

    def test_raw_findings_list_of_dicts(self, agent):
        raw = json.dumps(
            {
                "raw_findings": [
                    {"source": "A", "content": "content A"},
                    {"source": "B", "content": "content B"},
                ]
            }
        )
        result = agent._parse(raw)
        assert "A: content A" in result.raw_findings
        assert "B: content B" in result.raw_findings

    def test_raw_findings_dict(self, agent):
        raw = json.dumps({"raw_findings": {"key": "value"}})
        result = agent._parse(raw)
        assert json.loads(result.raw_findings) == {"key": "value"}

    def test_raw_findings_missing_uses_summary(self, agent):
        raw = json.dumps({"summary": "the summary"})
        result = agent._parse(raw)
        assert result.raw_findings == "the summary"

    def test_missing_sources_empty_list(self, agent):
        raw = json.dumps({"search_queries": ["q"]})
        result = agent._parse(raw)
        assert result.sources == []


class TestSummarizerAgent:
    @pytest.fixture
    def agent(self):
        return _make_agent(SummarizerAgent, SummaryResult)

    def test_normal_input(self, agent):
        raw = json.dumps(
            {
                "summaries": [
                    {
                        "url": "https://a.com",
                        "key_points": ["p1", "p2"],
                        "credibility": "high",
                    }
                ],
                "comparisons": [
                    {"dimension": "cost", "findings": ["f1"]}
                ],
                "conflicts": ["c1", "c2"],
                "gaps": ["g1"],
            }
        )
        result = agent._parse(raw)
        assert len(result.summaries) == 1
        assert result.summaries[0].url == "https://a.com"
        assert result.summaries[0].key_points == ["p1", "p2"]
        assert result.summaries[0].credibility == "high"
        assert len(result.comparisons) == 1
        assert result.comparisons[0].dimension == "cost"
        assert result.conflicts == ["c1", "c2"]
        assert result.gaps == ["g1"]

    def test_alias_fields_in_summaries(self, agent):
        raw = json.dumps(
            {
                "summaries": [
                    {
                        "link": "https://l.com",
                        "source": "https://s.com",
                        "summary": "sum",
                        "findings": ["f1"],
                        "description": "desc",
                        "points": ["p1"],
                        "trustworthiness": "medium",
                        "reliability": "low",
                    }
                ]
            }
        )
        result = agent._parse(raw)
        s = result.summaries[0]
        assert s.url == "https://l.com"
        assert s.key_points == ["sum"]
        assert s.credibility == "medium"

    def test_comparison_dict_converted_to_list(self, agent):
        raw = json.dumps(
            {
                "comparison": {
                    "speed": {"fast": "yes", "slow": "no"},
                    "cost": ["cheap", "expensive"],
                    "quality": "good",
                }
            }
        )
        result = agent._parse(raw)
        dims = {c.dimension: c.findings for c in result.comparisons}
        assert "speed" in dims
        assert any("fast: yes" in f for f in dims["speed"])
        assert dims["cost"] == ["cheap", "expensive"]
        assert dims["quality"] == ["good"]

    def test_conflicts_as_dict(self, agent):
        raw = json.dumps({"conflicts": {"a": {"x": 1}, "b": "plain"}})
        result = agent._parse(raw)
        assert any("a: x=1" in c for c in result.conflicts)
        assert any("b: plain" in c for c in result.conflicts)

    def test_conflicts_as_list_of_dicts(self, agent):
        raw = json.dumps({"conflicts": [{"x": 1, "y": 2}, "plain"]})
        result = agent._parse(raw)
        assert any("x=1; y=2" in c for c in result.conflicts)
        assert "plain" in result.conflicts

    def test_gaps_as_dict(self, agent):
        raw = json.dumps({"gaps": {"area1": "missing data", "area2": "no sources"}})
        result = agent._parse(raw)
        assert "area1: missing data" in result.gaps
        assert "area2: no sources" in result.gaps

    def test_gaps_as_list_of_dicts(self, agent):
        raw = json.dumps({"gaps": [{"topic": "t1", "reason": "r1"}, "plain gap"]})
        result = agent._parse(raw)
        assert any("topic=t1; reason=r1" in g for g in result.gaps)
        assert "plain gap" in result.gaps


class TestReporterAgent:
    @pytest.fixture
    def agent(self):
        provider = MagicMock()
        role_config = AgentModelConfig(
            role=ModelRole.REPORTER,
            provider="mock",
            provider_type="openai_compatible",
            endpoint="http://localhost",
            model="mock-model",
        )
        return ReporterAgent(
            provider=provider,
            role_config=role_config,
            system_prompt="test",
            output_schema=ResearchReport,
        )

    def test_normal_input_with_topic(self, agent):
        raw = json.dumps(
            {
                "topic": "AI Trends",
                "executive_summary": "Summary text",
                "sections": [
                    {"heading": "Intro", "content": "intro content"}
                ],
                "sources": ["src1"],
                "confidence": "high",
                "recommendations": ["rec1"],
            }
        )
        result = agent._parse(raw)
        assert result.topic == "AI Trends"
        assert result.executive_summary == "Summary text"
        assert len(result.sections) == 1
        assert result.sections[0].heading == "Intro"
        assert result.sections[0].content == "intro content"
        assert result.sources == ["src1"]
        assert result.confidence == "high"
        assert result.recommendations == ["rec1"]

    def test_missing_topic_reconstructs_from_detailed_sections(self, agent):
        raw = json.dumps(
            {
                "executive_summary": "exec",
                "detailed_sections": {
                    "section_one": {
                        "description": "desc1",
                        "details": {"sub": "detail"},
                    },
                    "section_two": "plain text",
                },
                "confidence_assessment": {"overall_confidence": "low"},
                "recommendations": ["rec1"],
            }
        )
        result = agent._parse(raw)
        assert result.topic == "research topic"
        assert result.executive_summary == "exec"
        headings = [s.heading for s in result.sections]
        assert "section one" in headings
        assert "section two" in headings
        assert result.confidence == "low"

    def test_sources_list_of_dicts_normalized(self, agent):
        raw = json.dumps(
            {
                "topic": "T",
                "executive_summary": "exec",
                "sources": [
                    {"title": "Title", "url": "https://u.com"},
                    {"name": "Name", "link": "https://l.com"},
                    {"url": "https://bare.com"},
                    "plain string",
                ],
            }
        )
        result = agent._parse(raw)
        assert "Title (https://u.com)" in result.sources
        assert "Name (https://l.com)" in result.sources
        assert "Source (https://bare.com)" in result.sources
        assert "plain string" in result.sources

    def test_sources_alias_source_list_when_topic_missing(self, agent):
        raw = json.dumps(
            {
                "executive_summary": "exec",
                "detailed_sections": {"h": "c"},
                "source_list": ["s1", "s2"],
            }
        )
        result = agent._parse(raw)
        assert result.sources == ["s1", "s2"]

    def test_object_summary_and_recommendations_normalized(self, agent):
        raw = json.dumps(
            {
                "topic": "Repo summary",
                "executive_summary": {
                    "topic": "Repo summary",
                    "summary": "Repository needs clearer evidence.",
                    "scope": "local project",
                },
                "sections": [{"heading": "Evidence", "content": "Some details"}],
                "recommendations": [
                    {"priority": "high", "recommendation": "Run pytest."},
                    {"priority": "medium", "action": "Update docs."},
                ],
            }
        )
        result = agent._parse(raw)
        assert "Repository needs clearer evidence." in result.executive_summary
        assert any("high" in rec and "Run pytest." in rec for rec in result.recommendations)
        assert any("medium" in rec and "Update docs." in rec for rec in result.recommendations)

    def test_confidence_fallback_medium(self, agent):
        raw = json.dumps(
            {
                "topic": "T",
                "executive_summary": "exec",
            }
        )
        result = agent._parse(raw)
        assert result.confidence == "medium"
