"""Unit tests for tools.git.GitTool — all mock-based, no real git calls."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.tool_protocol import RiskLevel, ToolContext, ToolResult
from tools.git import GitTool


@pytest.fixture
def context() -> ToolContext:
    return ToolContext()


class TestGitToolSchemaAndRisk:
    def test_tool_id_is_git(self) -> None:
        tool = GitTool()
        assert tool.tool_id == "git"


class TestGitToolOperations:
    def test_status_returns_output(self, context: ToolContext) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="M file.py", stderr="")
            tool = GitTool()
            result = tool.invoke({"operation": "status"}, context)
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == "M file.py"
        mock_run.assert_called_once_with(
            ["git", "status", "--short"],
            cwd=tool.repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_diff_returns_stat(self, context: ToolContext) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=" file.py | 1 +", stderr="")
            tool = GitTool()
            result = tool.invoke({"operation": "diff"}, context)
        assert result.success is True
        assert result.data == " file.py | 1 +"
        mock_run.assert_called_once_with(
            ["git", "diff", "--stat"],
            cwd=tool.repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_diff_patch_returns_binary_diff(self, context: ToolContext) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="binary diff", stderr="")
            tool = GitTool()
            result = tool.invoke({"operation": "diff_patch"}, context)
        assert result.success is True
        assert result.data == "binary diff"
        mock_run.assert_called_once_with(
            ["git", "diff", "--no-ext-diff", "--binary"],
            cwd=tool.repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_commit_adds_and_commits(self, context: ToolContext) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),
                MagicMock(returncode=0, stdout="committed", stderr=""),
            ]
            tool = GitTool()
            result = tool.invoke(
                {"operation": "commit", "message": "test commit"}, context
            )
        assert result.success is True
        assert result.data == "committed"
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0][0][0] == ["git", "add", "-A"]
        assert mock_run.call_args_list[1][0][0] == ["git", "commit", "-m", "test commit"]

    def test_commit_add_failure(self, context: ToolContext) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="permission denied")
            tool = GitTool()
            result = tool.invoke(
                {"operation": "commit", "message": "test commit"}, context
            )
        assert result.success is False
        assert "git add failed" in result.error.lower()
        assert "permission denied" in result.error
        assert mock_run.call_count == 1

    def test_clone_missing_url(self, context: ToolContext) -> None:
        tool = GitTool()
        result = tool.invoke({"operation": "clone"}, context)
        assert result.success is False
        assert "url is required" in result.error.lower()

    def test_clone_target_escapes_workspace(self, context: ToolContext) -> None:
        tool = GitTool()
        result = tool.invoke(
            {
                "operation": "clone",
                "url": "https://github.com/user/repo.git",
                "target": "../../outside",
            },
            context,
        )
        assert result.success is False
        assert "escapes workspace" in result.error.lower()

    def test_clone_success(self, context: ToolContext) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Cloning", stderr="")
            tool = GitTool()
            result = tool.invoke(
                {
                    "operation": "clone",
                    "url": "https://github.com/user/repo.git",
                    "target": "repo",
                },
                context,
            )
        assert result.success is True
        assert result.data == "Cloning"
        mock_run.assert_called_once_with(
            ["git", "clone", "https://github.com/user/repo.git", str(tool.repo_root / "repo")],
            cwd=tool.repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_push_success(self, context: ToolContext) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="push ok", stderr="")
            tool = GitTool()
            result = tool.invoke({"operation": "push"}, context)
        assert result.success is True
        assert result.data == "push ok"
        mock_run.assert_called_once_with(
            ["git", "push"],
            cwd=tool.repo_root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_unknown_operation(self, context: ToolContext) -> None:
        tool = GitTool()
        result = tool.invoke({"operation": "rebase"}, context)
        assert result.success is False
        assert "unknown git operation" in result.error.lower()
