"""Unit tests for adapter classes in tools/integrations and tools/git."""

from __future__ import annotations

import subprocess
import shutil
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from tools.integrations.web_research import WebResearchAdapter, DuckDuckGoSearchAdapter, UrllibSearchAdapter
from tools.git.github_cli import GitHubCliAdapter
from tools.integrations.mcp_client import MCPClientAdapter
from core.errors import IntegrationError

# duckduckgo_search is an optional dependency; inject a mock module so patches work.
if "duckduckgo_search" not in sys.modules:
    sys.modules["duckduckgo_search"] = MagicMock()


# ---------------------------------------------------------------------------
# WebResearchAdapter
# ---------------------------------------------------------------------------

class TestWebResearchAdapter:
    def test_disabled_returns_unavailable_with_guidance(self):
        adapter = WebResearchAdapter(repo_root="/tmp", enabled=False)
        result = adapter.search("test query")
        assert result["query"] == "test query"
        assert result["source"] == "unavailable"
        assert "disabled" in result["error"].lower()
        assert "setup_guidance" in result
        assert result["results"] == []

    def test_ddg_available_uses_ddg(self):
        with patch("duckduckgo_search.DDGS") as MockDDGS:
            mock_client = MagicMock()
            mock_client.text.return_value = [
                {"title": "T", "href": "U", "body": "S"}
            ]
            MockDDGS.return_value = mock_client
            with patch.object(DuckDuckGoSearchAdapter, "available", True):
                adapter = WebResearchAdapter(repo_root="/tmp", enabled=True)
                result = adapter.search("query")
        assert result["source"] == "duckduckgo"
        assert result["query"] == "query"
        assert result["results"] == [{"title": "T", "url": "U", "snippet": "S"}]

    def test_ddg_fails_returns_unavailable_with_guidance(self):
        with patch("duckduckgo_search.DDGS") as MockDDGS:
            mock_client = MagicMock()
            mock_client.text.side_effect = Exception("DDG boom")
            MockDDGS.return_value = mock_client
            with patch.object(DuckDuckGoSearchAdapter, "available", True):
                adapter = WebResearchAdapter(repo_root="/tmp", enabled=True)
                result = adapter.search("query")
        assert result["source"] == "unavailable"
        assert "duckduckgo-search failed" in result["error"].lower()
        assert "setup_guidance" in result
        assert result["results"] == []

    def test_both_fail_returns_unavailable_error(self):
        with patch("duckduckgo_search.DDGS") as MockDDGS:
            mock_client = MagicMock()
            mock_client.text.side_effect = Exception("DDG boom")
            MockDDGS.return_value = mock_client
            with patch.object(DuckDuckGoSearchAdapter, "available", True):
                adapter = WebResearchAdapter(repo_root="/tmp", enabled=True)
                with patch.object(UrllibSearchAdapter, "search", side_effect=Exception("urllib boom")):
                    result = adapter.search("query")
        assert result["source"] == "unavailable"
        assert "error" in result
        assert result["results"] == []
        assert result["query"] == "query"


# ---------------------------------------------------------------------------
# GitHubCliAdapter
# ---------------------------------------------------------------------------

class TestGitHubCliAdapter:
    def test_available_when_gh_installed(self):
        with patch("tools.git.github_cli.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/gh"
            adapter = GitHubCliAdapter(repo_root="/tmp")
            assert adapter.available is True

    def test_not_available_when_gh_missing(self):
        with patch("tools.git.github_cli.shutil.which") as mock_which:
            mock_which.return_value = None
            with patch("tools.git.github_cli.os.getenv", return_value=None):
                adapter = GitHubCliAdapter(repo_root="/tmp")
                assert adapter.available is False

    def test_view_issue_runs_gh_command(self):
        with patch("tools.git.github_cli.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/gh"
            adapter = GitHubCliAdapter(repo_root="/tmp")
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
                adapter.view_issue("123")
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs.get("cwd") == Path("/tmp")
        assert args[0] == ["gh", "issue", "view", "123"]

    def test_run_raises_on_nonzero_exit(self):
        with patch("tools.git.github_cli.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/gh"
            adapter = GitHubCliAdapter(repo_root="/tmp")
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
                with pytest.raises(IntegrationError, match="error msg"):
                    adapter.view_issue("123")


# ---------------------------------------------------------------------------
# MCPClientAdapter
# ---------------------------------------------------------------------------

class TestMCPClientAdapter:
    def test_call_when_disabled_raises(self):
        adapter = MCPClientAdapter(repo_root="/tmp", enabled=False)
        with pytest.raises(RuntimeError, match="MCP adapter is disabled."):
            adapter.call("tool_a", {})

    def test_call_with_allowlist_blocks_unknown(self):
        adapter = MCPClientAdapter(repo_root="/tmp", enabled=True, allowlist=["tool_a"])
        with pytest.raises(RuntimeError, match="MCP tool 'tool_b' is not in allowlist."):
            adapter.call("tool_b", {})

    def test_call_with_allowlist_allows_known(self):
        adapter = MCPClientAdapter(repo_root="/tmp", enabled=True, allowlist=["tool_a"])
        with pytest.raises(RuntimeError, match="MCP client adapter has no configured backend."):
            adapter.call("tool_a", {"x": 1})

    def test_call_without_allowlist_allows_any(self):
        adapter = MCPClientAdapter(repo_root="/tmp", enabled=True, allowlist=[])
        with pytest.raises(RuntimeError, match="MCP client adapter has no configured backend."):
            adapter.call("any_tool", {})
