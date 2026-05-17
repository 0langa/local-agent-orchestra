from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.schemas import (
    AgentMessage,
    ArtifactRef,
    PolicyDecision,
    ToolCall,
    ToolResult,
    WorkflowStep,
    WorkflowStepStatus,
)


class TestAgentMessage:
    def test_valid_message(self) -> None:
        msg = AgentMessage(actor="planner", content="plan ready")
        assert msg.actor == "planner"
        assert msg.content == "plan ready"

    def test_empty_actor_fails(self) -> None:
        with pytest.raises(ValidationError):
            AgentMessage(actor="", content="plan ready")

    def test_empty_content_fails(self) -> None:
        with pytest.raises(ValidationError):
            AgentMessage(actor="planner", content="")


class TestArtifactRef:
    def test_valid_ref(self) -> None:
        ref = ArtifactRef(id="a1", kind="file", path="src/main.py")
        assert ref.id == "a1"

    def test_missing_fields_fails(self) -> None:
        with pytest.raises(ValidationError):
            ArtifactRef(id="a1", kind="file")


class TestPolicyDecision:
    def test_allowed(self) -> None:
        d = PolicyDecision(allowed=True, policy_name="safe", reason="low risk")
        assert d.allowed is True

    def test_denied(self) -> None:
        d = PolicyDecision(allowed=False, policy_name="unsafe", reason="high risk")
        assert d.allowed is False


class TestToolCall:
    def test_valid_call(self) -> None:
        tc = ToolCall(name="read", arguments={"path": "x"}, actor="agent", workflow_step_id="s1")
        assert tc.name == "read"


class TestToolResult:
    def test_success(self) -> None:
        tr = ToolResult(tool_name="read", success=True, output="content")
        assert tr.success is True

    def test_failure(self) -> None:
        tr = ToolResult(tool_name="read", success=False, error="not found")
        assert tr.success is False


class TestWorkflowStep:
    def test_default_status(self) -> None:
        ws = WorkflowStep(id="s1", name="step", actor="planner")
        assert ws.status == WorkflowStepStatus.PENDING

    def test_status_enum_values(self) -> None:
        assert WorkflowStepStatus.COMPLETED.value == "completed"
        assert WorkflowStepStatus.FAILED.value == "failed"
