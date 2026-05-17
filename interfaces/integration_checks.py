"""Optional integration availability checks for readiness and diagnostics.

Each check returns an OptionalIntegrationState-compatible dict.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from interfaces.readiness import OptionalIntegrationState

logger = logging.getLogger(__name__)


def _has_ddgs() -> bool:
    try:
        from duckduckgo_search import DDGS

        DDGS()
        return True
    except Exception:
        return False


def check_web_research() -> OptionalIntegrationState:
    """Check if web research is available."""
    if _has_ddgs():
        return OptionalIntegrationState(
            integration_id="web_research",
            available=True,
            detail="duckduckgo-search is installed",
        )

    # urllib fallback is always "available" as a library, but we mark it
    # as limited because it may break due to HTML changes or network blocks.
    return OptionalIntegrationState(
        integration_id="web_research",
        available=False,
        detail="duckduckgo-search is not installed and urllib fallback is unreliable for production use",
        next_action="Install duckduckgo-search: pip install duckduckgo-search",
    )


def check_mcp(repo_root: Path | None = None) -> OptionalIntegrationState:
    """Check if MCP has a configured backend."""
    root = Path(repo_root or ".").resolve()
    config_path = root / ".ai-team" / "mcp.json"
    if not config_path.exists():
        return OptionalIntegrationState(
            integration_id="mcp",
            available=False,
            detail="No MCP config found at .ai-team/mcp.json",
            next_action="Create .ai-team/mcp.json to enable MCP servers.",
        )
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        servers = data.get("servers", data if isinstance(data, list) else [])
        enabled = [s for s in servers if s.get("enabled", True)]
        if not enabled:
            return OptionalIntegrationState(
                integration_id="mcp",
                available=False,
                detail="MCP config exists but no servers are enabled",
                next_action="Enable at least one server in .ai-team/mcp.json",
            )
        return OptionalIntegrationState(
            integration_id="mcp",
            available=True,
            detail=f"{len(enabled)} MCP server(s) configured",
        )
    except Exception as exc:
        return OptionalIntegrationState(
            integration_id="mcp",
            available=False,
            detail=f"Failed to read MCP config: {exc}",
            next_action="Validate .ai-team/mcp.json syntax.",
        )


def check_vision() -> OptionalIntegrationState:
    """Check if a vision provider is configured."""
    provider = os.getenv("AGENTHEIM_VISION_PROVIDER", "auto").lower()
    if provider == "openai" or os.getenv("OPENAI_API_KEY"):
        return OptionalIntegrationState(
            integration_id="vision",
            available=True,
            detail="OpenAI vision provider configured",
        )
    if provider == "claude" or os.getenv("ANTHROPIC_API_KEY"):
        return OptionalIntegrationState(
            integration_id="vision",
            available=True,
            detail="Claude vision provider configured",
        )
    if provider != "auto":
        return OptionalIntegrationState(
            integration_id="vision",
            available=False,
            detail=f"Unknown vision provider '{provider}'",
            next_action="Set AGENTHEIM_VISION_PROVIDER to openai or claude, or configure a provider with vision capability.",
        )
    # auto mode — try team config
    try:
        from config.config import load_team_config, ModelCapability

        team = load_team_config()
        for role, cfg in team.by_role().items():
            caps = [c.lower() for c in (cfg.metadata.get("capabilities") or [])]
            if ModelCapability.VISION.value in caps:
                return OptionalIntegrationState(
                    integration_id="vision",
                    available=True,
                    detail=f"Vision capability found on role {role}",
                )
    except Exception as exc:
        logger.debug("Vision auto-check via team config failed: %s", exc)

    return OptionalIntegrationState(
        integration_id="vision",
        available=False,
        detail="No vision provider configured",
        next_action="Set AGENTHEIM_VISION_PROVIDER=openai or claude, or configure a provider with vision capability.",
    )


def check_github() -> OptionalIntegrationState:
    """Check if GitHub CLI is available and authenticated."""
    if not shutil.which("gh"):
        return OptionalIntegrationState(
            integration_id="github",
            available=False,
            detail="GitHub CLI (gh) is not installed",
            next_action="Install GitHub CLI: https://cli.github.com/ and run `gh auth login`",
        )
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return OptionalIntegrationState(
                integration_id="github",
                available=True,
                detail="GitHub CLI is installed and authenticated",
            )
        return OptionalIntegrationState(
            integration_id="github",
            available=False,
            detail="GitHub CLI is installed but not authenticated",
            next_action="Run `gh auth login` to authenticate.",
        )
    except Exception as exc:
        return OptionalIntegrationState(
            integration_id="github",
            available=False,
            detail=f"GitHub CLI auth check failed: {exc}",
            next_action="Run `gh auth login` to authenticate.",
        )


def _has_playwright() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        return True
    except Exception:
        return False


def check_browser() -> OptionalIntegrationState:
    """Check if Playwright browser tooling is available."""
    if _has_playwright():
        return OptionalIntegrationState(
            integration_id="browser",
            available=True,
            detail="Playwright is installed",
        )
    return OptionalIntegrationState(
        integration_id="browser",
        available=False,
        detail="Playwright is not installed",
        next_action="Install Playwright: pip install playwright && playwright install chromium",
    )


def check_all_optional_integrations(repo_root: Path | None = None) -> list[OptionalIntegrationState]:
    """Run all optional integration checks and return their states."""
    checks = [
        check_web_research(),
        check_mcp(repo_root),
        check_vision(),
        check_github(),
        check_browser(),
    ]
    # Keep context_ops check inline for backward compatibility
    try:
        from agentheim.context_ops_impl import AictxContextOps
        from agentheim.vendor.aictx.config import AictxConfig

        AictxContextOps(AictxConfig())
        checks.append(
            OptionalIntegrationState(
                integration_id="context_ops",
                available=True,
                detail="AICtx-backed ContextOps import and initialization ok",
            )
        )
    except Exception as exc:
        checks.append(
            OptionalIntegrationState(
                integration_id="context_ops",
                available=False,
                detail=str(exc),
                next_action="ContextOps is an internal dependency; check vendor/aictx setup.",
            )
        )
    return checks
