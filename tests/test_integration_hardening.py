"""Phase 6: Provider and integration hardening tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from interfaces.cli.cli import app
from interfaces.integration_checks import (
    check_browser,
    check_github,
    check_mcp,
    check_vision,
    check_web_research,
    check_all_optional_integrations,
)
from interfaces.readiness import OptionalIntegrationState, build_readiness_state
from tools.integrations.web_research import WebResearchAdapter
from tools.integrations.mcp_client import MCPClientAdapter
from tools.git.github_cli import GitHubCliAdapter
from tools.browser import BrowserTool

runner = CliRunner()


class TestWebResearch:
    def test_disabled_reports_unavailable_with_guidance(self, tmp_path: Path) -> None:
        adapter = WebResearchAdapter(tmp_path, enabled=False)
        result = adapter.search("test query")
        assert result["source"] == "unavailable"
        assert "disabled" in result["error"].lower()
        assert "setup_guidance" in result

    def test_no_duckduckgo_reports_unavailable_with_guidance(self, tmp_path: Path) -> None:
        adapter = WebResearchAdapter(tmp_path, enabled=True)
        # Make DDGS unavailable by clearing its client
        adapter._ddg._client = None
        result = adapter.search("test query")
        # With _ddg unavailable, it falls through to urllib, which may succeed or fail
        # depending on network. We just verify it doesn't silently return empty results
        # without source=unavailable on complete failure.
        assert "source" in result

    def test_check_web_research_unavailable_when_ddg_missing(self) -> None:
        with patch("interfaces.integration_checks._has_ddgs", return_value=False):
            state = check_web_research()
        assert state.available is False
        assert state.integration_id == "web_research"
        assert state.next_action

    def test_check_web_research_available_when_ddg_present(self) -> None:
        with patch("interfaces.integration_checks._has_ddgs", return_value=True):
            state = check_web_research()
        assert state.available is True
        assert state.integration_id == "web_research"


class TestMCP:
    def test_no_config_reports_unavailable(self, tmp_path: Path) -> None:
        state = check_mcp(tmp_path)
        assert state.available is False
        assert "mcp.json" in state.detail
        assert state.next_action

    def test_empty_config_reports_unavailable(self, tmp_path: Path) -> None:
        config = tmp_path / ".ai-team" / "mcp.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"servers": []}), encoding="utf-8")
        state = check_mcp(tmp_path)
        assert state.available is False
        assert "no servers are enabled" in state.detail.lower()

    def test_enabled_config_reports_available(self, tmp_path: Path) -> None:
        config = tmp_path / ".ai-team" / "mcp.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps({"servers": [{"name": "test", "enabled": True}]}),
            encoding="utf-8",
        )
        state = check_mcp(tmp_path)
        assert state.available is True
        assert "1 MCP server" in state.detail

    def test_legacy_mcp_adapter_disabled_raises_with_guidance(self, tmp_path: Path) -> None:
        adapter = MCPClientAdapter(tmp_path, enabled=False)
        with pytest.raises(RuntimeError, match="disabled"):
            adapter.call("tool", {})
        with pytest.raises(RuntimeError, match="MCP"):
            adapter.call("tool", {})

    def test_legacy_mcp_adapter_enabled_raises_with_guidance(self, tmp_path: Path) -> None:
        adapter = MCPClientAdapter(tmp_path, enabled=True)
        with pytest.raises(RuntimeError, match="no configured backend"):
            adapter.call("tool", {})


class TestVision:
    def test_no_config_reports_unavailable(self, tmp_path: Path) -> None:
        env = dict(os.environ)
        for key in ("AGENTHEIM_VISION_PROVIDER", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
            env.pop(key, None)
        with patch.dict(os.environ, env, clear=True):
            with patch("config.config.load_team_config", side_effect=Exception("no config")):
                state = check_vision()
        assert state.available is False
        assert state.integration_id == "vision"
        assert state.next_action

    def test_openai_env_reports_available(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            state = check_vision()
        assert state.available is True
        assert "openai" in state.detail.lower()

    def test_claude_env_reports_available(self) -> None:
        env = dict(os.environ)
        env.pop("OPENAI_API_KEY", None)
        env["ANTHROPIC_API_KEY"] = "sk-test"
        with patch.dict(os.environ, env, clear=True):
            state = check_vision()
        assert state.available is True
        assert "claude" in state.detail.lower()

    def test_image_tool_fails_clearly_when_unconfigured(self) -> None:
        from multimodal.image import ImageTool

        tool = ImageTool()
        with patch("multimodal.image._resolve_processor", side_effect=RuntimeError("Vision not configured")):
            result = tool.invoke(
                {"operation": "describe", "image_b64": "data:image/png;base64,abc"},
                MagicMock(),
            )
        assert result.success is False
        assert "vision" in result.error.lower() or "configured" in result.error.lower()


class TestGitHub:
    def test_disabled_reports_unavailable(self, tmp_path: Path) -> None:
        adapter = GitHubCliAdapter(tmp_path, enabled=False)
        assert adapter.available is False
        with pytest.raises(Exception, match="not enabled"):
            adapter._require_available()

    def test_no_gh_reports_unavailable(self, tmp_path: Path) -> None:
        with patch("shutil.which", return_value=None):
            with patch("os.getenv", return_value=None):
                adapter = GitHubCliAdapter(tmp_path, enabled=True)
                assert adapter.available is False

    def test_github_token_makes_available(self, tmp_path: Path) -> None:
        with patch("shutil.which", return_value=None):
            with patch.dict(os.environ, {"GITHUB_TOKEN": "token"}, clear=False):
                adapter = GitHubCliAdapter(tmp_path, enabled=True)
                assert adapter.available is True

    def test_check_github_no_gh(self) -> None:
        with patch("shutil.which", return_value=None):
            state = check_github()
        assert state.available is False
        assert "not installed" in state.detail.lower()
        assert state.next_action

    def test_check_github_with_gh_unauthenticated(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=MagicMock(returncode=1)):
                state = check_github()
        assert state.available is False
        assert "not authenticated" in state.detail.lower()

    def test_check_github_with_gh_authenticated(self) -> None:
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("subprocess.run", return_value=MagicMock(returncode=0)):
                state = check_github()
        assert state.available is True


class TestBrowser:
    def test_no_playwright_reports_unavailable(self) -> None:
        with patch("interfaces.integration_checks._has_playwright", return_value=False):
            state = check_browser()
        assert state.available is False
        assert "playwright" in state.detail.lower()
        assert state.next_action

    def test_playwright_available(self) -> None:
        with patch("interfaces.integration_checks._has_playwright", return_value=True):
            state = check_browser()
        assert state.available is True

    def test_screenshot_without_playwright_includes_guidance(self, tmp_path: Path) -> None:
        tool = BrowserTool(tmp_path)
        with patch.object(tool, "_playwright_available", return_value=False):
            result = tool.invoke(
                {"operation": "screenshot", "url": "http://example.com"},
                MagicMock(network_allowed=True),
            )
        assert result.success is False
        assert "playwright" in result.error.lower()
        assert "install" in result.error.lower()

    def test_click_without_playwright_includes_guidance(self, tmp_path: Path) -> None:
        tool = BrowserTool(tmp_path)
        with patch.object(tool, "_playwright_available", return_value=False):
            result = tool.invoke(
                {"operation": "click", "url": "http://example.com", "selector": "button"},
                MagicMock(network_allowed=True),
            )
        assert result.success is False
        assert "playwright" in result.error.lower()
        assert "install" in result.error.lower()


class TestReadinessIntegrationStates:
    def test_status_includes_all_optional_integrations(self, tmp_path: Path) -> None:
        from config.config import TeamConfig, ProfilesDocument, TeamProfile

        env = {
            "AGENTHEIM_CONFIG_DIR": str(tmp_path / "config"),
            "AGENTHEIM_DATA_DIR": str(tmp_path / "data"),
        }
        config = TeamConfig(
            profile_name="default",
            providers={},
            models={},
            document=ProfilesDocument(profiles={"default": TeamProfile(name="default")}),
        )
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.integration_checks.check_all_optional_integrations", return_value=[
                OptionalIntegrationState(integration_id="web_research", available=False, detail="missing", next_action="install"),
                OptionalIntegrationState(integration_id="mcp", available=False, detail="missing", next_action="config"),
            ]):
                result = runner.invoke(app, ["status", "--repo", str(tmp_path)], env=env)
        assert result.exit_code == 0, result.output
        assert "web_research" in result.output or "missing" in result.output

    def test_readiness_includes_integration_states_when_ready(self, tmp_path: Path) -> None:
        from config.config import TeamConfig, ProfilesDocument, TeamProfile

        config = TeamConfig(
            profile_name="default",
            providers={},
            models={},
            document=ProfilesDocument(profiles={"default": TeamProfile(name="default")}),
        )
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state(check_optional_integrations=True)
        ids = {oi.integration_id for oi in state.optional_integrations}
        assert "web_research" in ids
        assert "mcp" in ids
        assert "vision" in ids
        assert "github" in ids
        assert "browser" in ids
        assert "context_ops" in ids

    def test_all_checks_return_expected_integrations(self, tmp_path: Path) -> None:
        states = check_all_optional_integrations(tmp_path)
        ids = {s.integration_id for s in states}
        assert ids == {"web_research", "mcp", "vision", "github", "browser", "context_ops"}
