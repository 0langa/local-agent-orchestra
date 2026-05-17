from __future__ import annotations

from agents.self_improving import FeedbackLoop, PromptEvolutionStrategy
from agents.self_improving.strategies import ParameterTuningStrategy, ToolSelectionStrategy


class TestFeedbackLoop:
    def test_capture_and_summarize(self) -> None:
        loop = FeedbackLoop()
        loop.capture("r1", success=True)
        loop.capture("r2", success=False, correction="fix typo")
        loop.capture("r3", success=False, correction="fix typo")
        summary = loop.summarize()
        assert summary["total"] == 3
        assert summary["success_rate"] == 1 / 3
        assert summary["common_corrections"][0][0] == "fix typo"

    def test_empty_summarize(self) -> None:
        loop = FeedbackLoop()
        summary = loop.summarize()
        assert summary["total"] == 0
        assert summary["success_rate"] == 0.0

    def test_to_memory(self) -> None:
        loop = FeedbackLoop()
        loop.capture("r1", success=True, score=0.9)
        mem = loop.to_memory()
        assert len(mem) == 1
        assert mem[0]["run_id"] == "r1"
        assert mem[0]["success"] is True


class TestPromptEvolutionStrategy:
    def test_no_change_when_successful(self) -> None:
        s = PromptEvolutionStrategy()
        result = s.apply({"prompt": "Hello", "feedback": [{"success": True}]})
        assert result["prompt"] == "Hello"

    def test_appends_guidance_on_failures(self) -> None:
        s = PromptEvolutionStrategy()
        feedback = [{"success": False}] * 4 + [{"success": True}]
        result = s.apply({"prompt": "Hello", "feedback": feedback})
        assert "edge cases" in result["prompt"]


class TestParameterTuningStrategy:
    def test_increases_timeout(self) -> None:
        s = ParameterTuningStrategy()
        result = s.apply({"params": {"timeout": 30}, "metrics": {"timeout_rate": 0.2}})
        assert result["params"]["timeout"] == 45.0

    def test_no_change_when_low_timeout_rate(self) -> None:
        s = ParameterTuningStrategy()
        result = s.apply({"params": {"timeout": 30}, "metrics": {"timeout_rate": 0.05}})
        assert result["params"]["timeout"] == 30


class TestToolSelectionStrategy:
    def test_increases_score_on_success(self) -> None:
        s = ToolSelectionStrategy()
        result = s.apply({"tool_scores": {"shell": 0.5}, "feedback": [{"tool": "shell", "success": True}]})
        assert result["tool_scores"]["shell"] == 0.6

    def test_decreases_score_on_failure(self) -> None:
        s = ToolSelectionStrategy()
        result = s.apply({"tool_scores": {"shell": 0.5}, "feedback": [{"tool": "shell", "success": False}]})
        assert result["tool_scores"]["shell"] == 0.4

    def test_clamps_to_bounds(self) -> None:
        s = ToolSelectionStrategy()
        result = s.apply({"tool_scores": {"shell": 0.95}, "feedback": [{"tool": "shell", "success": True}]})
        assert result["tool_scores"]["shell"] == 1.0
