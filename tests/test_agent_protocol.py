"""Tests for core/agent_protocol.py — agent communication schemas."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.agent_protocol import AgentContext, AgentMessage, AgentRequest, AgentResponse


class TestAgentMessage:
    def test_defaults(self) -> None:
        msg = AgentMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.metadata == {}

    def test_with_metadata(self) -> None:
        msg = AgentMessage(role="assistant", content="hi", metadata={"model": "gpt-4"})
        assert msg.metadata == {"model": "gpt-4"}

    def test_frozen(self) -> None:
        msg = AgentMessage(role="user", content="hello")
        with pytest.raises(AttributeError):
            msg.role = "assistant"


class TestAgentRequest:
    def test_defaults(self) -> None:
        req = AgentRequest(agent_id="planner")
        assert req.agent_id == "planner"
        assert req.messages == []
        assert req.context.run_id == ""

    def test_with_messages(self) -> None:
        req = AgentRequest(
            agent_id="coder",
            messages=[AgentMessage(role="user", content="write code")],
        )
        assert len(req.messages) == 1
        assert req.messages[0].role == "user"


class TestAgentResponse:
    def test_defaults(self) -> None:
        resp = AgentResponse()
        assert resp.content == ""
        assert resp.tool_calls == []
        assert resp.usage == {}
        assert resp.finish_reason == ""

    def test_with_data(self) -> None:
        resp = AgentResponse(
            content="done",
            tool_calls=[{"name": "shell"}],
            usage={"tokens": 42},
            finish_reason="stop",
        )
        assert resp.content == "done"
        assert resp.tool_calls == [{"name": "shell"}]


class TestAgentContext:
    def test_defaults(self) -> None:
        ctx = AgentContext()
        assert ctx.run_id == ""
        assert ctx.step_id == ""
        assert ctx.repo_root == Path(".")
        assert ctx.working_memory == {}
        assert ctx.prior_results == []

    def test_to_dict(self) -> None:
        ctx = AgentContext(
            run_id="run-1",
            step_id="step-1",
            repo_root=Path("/repo"),
            working_memory={"key": "value"},
            prior_results=[AgentMessage(role="assistant", content="result")],
        )
        d = ctx.to_dict()
        assert d["run_id"] == "run-1"
        assert d["step_id"] == "step-1"
        assert "repo" in d["repo_root"]
        assert d["working_memory"] == {"key": "value"}
        assert len(d["prior_results"]) == 1
        assert d["prior_results"][0]["role"] == "assistant"

    def test_from_step_context(self, tmp_path: Path) -> None:
        from workflows.base import Step, StepContext, StepResult

        step_ctx = StepContext(
            run_id="run-1",
            step_id="step-1",
            repo_root=tmp_path,
            prior_results={
                "s1": StepResult(step_id="s1", success=True, output="output1"),
            },
        )
        agent_ctx = AgentContext.from_step_context(step_ctx)
        assert agent_ctx.run_id == "run-1"
        assert agent_ctx.step_id == "step-1"
        assert agent_ctx.repo_root == tmp_path
        assert len(agent_ctx.prior_results) == 1
        assert agent_ctx.prior_results[0].content == "output1"
