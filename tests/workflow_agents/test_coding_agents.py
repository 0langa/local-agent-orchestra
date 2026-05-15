from __future__ import annotations

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock

from workflows.coding.agents.coder import CoderAgent
from workflows.coding.agents.orchestrator import OrchestratorAgent
from workflows.coding.agents.verifier import VerifierAgent
from core.schemas_runtime import AcceptanceCriterion, PatchPlan, ImplementationPlan, TaskGraph, TaskNode, TaskType, VerificationReport, WorkOrder


@pytest.fixture
def mock_provider():
    return MagicMock()


@pytest.fixture
def mock_role():
    m = MagicMock()
    m.role = "test_role"
    return m


class TestCoderAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = CoderAgent(mock_provider, mock_role, "sys", PatchPlan)
        raw = '{"summary":"fix bug","file_changes":[{"path":"a.py","patch":"diff"}]}'
        result = agent._parse(raw)
        assert result.summary == "fix bug"
        assert len(result.file_changes) == 1
        assert result.file_changes[0].path == "a.py"
        assert result.file_changes[0].patch == "diff"

    def test_parse_aliases(self, mock_provider, mock_role):
        agent = CoderAgent(mock_provider, mock_role, "sys", PatchPlan)
        raw = (
            '{"fileChanges":[{"filePath":"b.py","changeType":"add","Patch":"p"}],'
            '"testSuggestions":[],"notes":[]}'
        )
        result = agent._parse(raw)
        assert result.file_changes[0].path == "b.py"
        assert result.file_changes[0].change_type == "add"
        assert result.file_changes[0].patch == "p"

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = CoderAgent(mock_provider, mock_role, "sys", PatchPlan)
        raw = '```json\n{"summary":"md","file_changes":[]}\n```'
        result = agent._parse(raw)
        assert result.summary == "md"
        assert result.file_changes == []

    def test_parse_missing_fields_uses_defaults(self, mock_provider, mock_role):
        agent = CoderAgent(mock_provider, mock_role, "sys", PatchPlan)
        raw = "{}"
        result = agent._parse(raw)
        assert result.summary == "Apply bounded work order changes"
        assert result.file_changes == []
        assert result.test_suggestions == []
        assert result.notes == []

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = CoderAgent(mock_provider, mock_role, "sys", PatchPlan)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("not json")

    def test_parse_invalid_schema_raises(self, mock_provider, mock_role):
        agent = CoderAgent(mock_provider, mock_role, "sys", PatchPlan)
        with pytest.raises(ValidationError):
            agent._parse('{"summary":123}')


class TestOrchestratorAgent:
    def test_parse_valid(self, mock_provider, mock_role):
        agent = OrchestratorAgent(mock_provider, mock_role, "sys", ImplementationPlan)
        raw = (
            '{"summary":"plan","detected_repo_type":"python",'
            '"task_graph":{"ordered_tasks":['
            '{"id":"1","type":"edit","title":"t","work_order":'
            '{"id":"wo1","title":"wo","objective":"obj"}}]},'
            '"assumptions":[]}'
        )
        result = agent._parse(raw)
        assert result.summary == "plan"
        assert result.detected_repo_type == "python"
        assert len(result.task_graph.ordered_tasks) == 1

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = OrchestratorAgent(mock_provider, mock_role, "sys", ImplementationPlan)
        raw = (
            '```json\n{"summary":"m","detected_repo_type":"py",'
            '"task_graph":{"ordered_tasks":['
            '{"id":"1","type":"inspect","title":"t","work_order":'
            '{"id":"w","title":"w","objective":"o"}}]}}\n```'
        )
        result = agent._parse(raw)
        assert result.summary == "m"

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = OrchestratorAgent(mock_provider, mock_role, "sys", ImplementationPlan)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("bad")

    def test_parse_missing_required_field_raises(self, mock_provider, mock_role):
        agent = OrchestratorAgent(mock_provider, mock_role, "sys", ImplementationPlan)
        with pytest.raises(ValidationError):
            agent._parse('{"summary":"s"}')


class TestVerifierAgent:
    def test_prompt_mentions_cumulative_diff_for_fix_orders(self, mock_provider, mock_role):
        agent = VerifierAgent(mock_provider, mock_role, "sys", VerificationReport)
        work_order = WorkOrder(
            id="wo-1-fix-1",
            title="Add regression coverage",
            objective="Add a test for the already-applied fix.",
            relevant_files=["tests/test_main.py"],
            acceptance_criteria=[AcceptanceCriterion(description="pytest passes")],
        )
        plan = ImplementationPlan(
            summary="Fix bug",
            detected_repo_type="python",
            task_graph=TaskGraph(
                ordered_tasks=[
                    TaskNode(id="task-1", type=TaskType.EDIT, title="Add regression coverage", work_order=work_order)
                ]
            ),
        )

        prompt = agent.build_prompt("Fix bug", plan, work_order, "diff --git", ["pytest passed"], [])

        assert "git diff is cumulative" in prompt
        assert "earlier verifier step already accepted" in prompt

    def test_parse_valid(self, mock_provider, mock_role):
        agent = VerifierAgent(mock_provider, mock_role, "sys", VerificationReport)
        raw = (
            '{"work_order_id":"wo1","status":"pass",'
            '"passed_checks":["a"],"failed_checks":[],'
            '"commands_run":[["cmd"]]}'
        )
        result = agent._parse(raw)
        assert result.work_order_id == "wo1"
        assert result.status == "pass"
        assert result.passed_checks == ["a"]
        assert result.commands_run == [["cmd"]]

    def test_parse_aliases_and_normalizers(self, mock_provider, mock_role):
        agent = VerifierAgent(mock_provider, mock_role, "sys", VerificationReport)
        raw = (
            '{"workOrderId":"wo2","status":"fail",'
            '"passedChecks":"single","diffFindings":null,'
            '"missing_tests":null,"commands_run":"cmd"}'
        )
        result = agent._parse(raw)
        assert result.work_order_id == "wo2"
        assert result.passed_checks == ["single"]
        assert result.diff_findings == []
        assert result.missing_tests == []
        assert result.commands_run == [["cmd"]]

    def test_parse_markdown_wrapper(self, mock_provider, mock_role):
        agent = VerifierAgent(mock_provider, mock_role, "sys", VerificationReport)
        raw = '```json\n{"work_order_id":"wo","status":"ok"}\n```'
        result = agent._parse(raw)
        assert result.status == "ok"

    def test_parse_invalid_json_raises(self, mock_provider, mock_role):
        agent = VerifierAgent(mock_provider, mock_role, "sys", VerificationReport)
        with pytest.raises((ValueError, ValidationError)):
            agent._parse("nope")

    def test_parse_missing_required_field_raises(self, mock_provider, mock_role):
        agent = VerifierAgent(mock_provider, mock_role, "sys", VerificationReport)
        with pytest.raises(ValidationError):
            agent._parse('{"work_order_id":"wo"}')
