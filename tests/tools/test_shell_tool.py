"""Unit tests for tools.shell.ShellTool — all mock-based, no real process execution."""

from unittest.mock import MagicMock, patch

import pytest

from core.tool_protocol import RiskLevel, ToolContext, ToolResult
from tools.shell import ShellTool
from tools.shell.sandbox import SandboxViolation


@pytest.fixture
def context() -> ToolContext:
    return ToolContext()


class TestShellToolSchemaAndRisk:
    def test_tool_id_is_shell_execute(self) -> None:
        with patch("tools.shell.ShellSandbox"):
            tool = ShellTool()
        assert tool.tool_id == "shell.execute"

    def test_risk_level_is_high(self) -> None:
        with patch("tools.shell.ShellSandbox"):
            tool = ShellTool()
        assert tool.risk_level == RiskLevel.HIGH


class TestShellToolExecution:
    def test_empty_command_returns_error(self, context: ToolContext) -> None:
        with patch("tools.shell.ShellSandbox"):
            tool = ShellTool()
        result = tool.invoke({"command": []}, context)
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "cannot be empty" in result.error.lower()

    def test_command_blocked_by_policy_returns_error(self, context: ToolContext) -> None:
        with patch("tools.shell.ShellSandbox"):
            tool = ShellTool()
        context.command_allowed = MagicMock(return_value=False)  # type: ignore[method-assign]
        result = tool.invoke({"command": ["ls"]}, context)
        assert result.success is False
        assert "blocked by policy" in result.error.lower()

    def test_sandbox_violation_returns_error(self, context: ToolContext) -> None:
        with patch("tools.shell.ShellSandbox") as MockSandbox:
            mock_sandbox = MagicMock()
            mock_sandbox.execute.side_effect = SandboxViolation("unsafe command")
            MockSandbox.return_value = mock_sandbox
            tool = ShellTool()
        result = tool.invoke({"command": ["rm", "-rf", "/"]}, context)
        assert result.success is False
        assert "unsafe command" in result.error

    def test_successful_execution(self, context: ToolContext) -> None:
        with patch("tools.shell.ShellSandbox") as MockSandbox:
            mock_sandbox = MagicMock()
            mock_sandbox.execute.return_value = MagicMock(
                returncode=0, stdout="ok", stderr=""
            )
            MockSandbox.return_value = mock_sandbox
            tool = ShellTool()
        result = tool.invoke({"command": ["echo", "ok"]}, context)
        assert result.success is True
        assert result.data.returncode == 0
        assert result.data.stdout == "ok"
        assert result.data.stderr == ""
        assert result.metadata == {"returncode": 0}

    def test_nonzero_returncode_still_success(self, context: ToolContext) -> None:
        with patch("tools.shell.ShellSandbox") as MockSandbox:
            mock_sandbox = MagicMock()
            mock_sandbox.execute.return_value = MagicMock(
                returncode=1, stdout="fail", stderr="err"
            )
            MockSandbox.return_value = mock_sandbox
            tool = ShellTool()
        result = tool.invoke({"command": ["false"]}, context)
        assert result.success is True
        assert result.data.returncode == 1
        assert result.data.stdout == "fail"
        assert result.data.stderr == "err"
        assert result.metadata == {"returncode": 1}

    def test_timeout_param_passed_to_sandbox(self, context: ToolContext) -> None:
        with patch("tools.shell.ShellSandbox") as MockSandbox:
            mock_sandbox = MagicMock()
            mock_sandbox.execute.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            MockSandbox.return_value = mock_sandbox
            tool = ShellTool()
        tool.invoke({"command": ["sleep", "10"], "timeout_seconds": 60}, context)
        mock_sandbox.execute.assert_called_once_with(["sleep", "10"], timeout=60)
