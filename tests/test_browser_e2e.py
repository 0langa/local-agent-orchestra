"""Real Playwright E2E browser tests (not mocked).

These tests hit real websites to verify the browser tool works end-to-end.
Use ``-m e2e`` to include them; by default they are skipped.

Requirements:
    pip install pytest-playwright
    playwright install chromium

Note:
    Playwright's sync API cannot run inside an asyncio event loop.
    pytest-anyio (installed via langsmith) creates a loop, so each
    browser operation is dispatched to a worker thread.
"""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from core.tool_protocol import ToolContext
from tools.browser import BrowserTool


def _invoke(browser: BrowserTool, params: dict, ctx: ToolContext) -> object:
    """Run browser.invoke in a fresh thread (no asyncio loop)."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(browser.invoke, params, ctx).result()


@pytest.fixture
def browser() -> BrowserTool:
    return BrowserTool()


@pytest.fixture
def ctx() -> ToolContext:
    return ToolContext(network_allowed=True)


# ------------------------------------------------------------------
# Basic operations
# ------------------------------------------------------------------

@pytest.mark.e2e
def test_browser_navigates_to_real_website(browser: BrowserTool, ctx: ToolContext) -> None:
    """Navigate to example.com and verify page title."""
    result = _invoke(browser, {"operation": "navigate", "url": "https://example.com"}, ctx)
    assert result.success is True
    assert "Example Domain" in result.data.get("title", "")


@pytest.mark.e2e
def test_browser_get_text(browser: BrowserTool, ctx: ToolContext) -> None:
    """Extract text from a known page."""
    result = _invoke(browser, {"operation": "get_text", "url": "https://example.com"}, ctx)
    assert result.success is True
    assert "Example Domain" in result.data


@pytest.mark.e2e
def test_browser_get_text_with_selector(browser: BrowserTool, ctx: ToolContext) -> None:
    """Extract text via CSS selector."""
    result = _invoke(
        browser, {"operation": "get_text", "url": "https://example.com", "selector": "h1"}, ctx
    )
    assert result.success is True
    assert "Example Domain" in result.data


@pytest.mark.e2e
def test_browser_get_links(browser: BrowserTool, ctx: ToolContext) -> None:
    """Extract links from a known page."""
    result = _invoke(browser, {"operation": "get_links", "url": "https://example.com"}, ctx)
    assert result.success is True
    assert isinstance(result.data, list)
    assert len(result.data) >= 1


# ------------------------------------------------------------------
# Screenshot
# ------------------------------------------------------------------

@pytest.mark.e2e
def test_browser_screenshot_base64(browser: BrowserTool, ctx: ToolContext) -> None:
    """Take a screenshot and return it as base64."""
    result = _invoke(browser, {"operation": "screenshot", "url": "https://example.com"}, ctx)
    assert result.success is True
    assert result.metadata.get("format") == "png"
    assert result.metadata.get("saved") is False
    png_bytes = base64.b64decode(result.data)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.e2e
def test_browser_screenshot_to_file(browser: BrowserTool, ctx: ToolContext) -> None:
    """Take a screenshot and save it to a repo-relative file."""
    save_path = ".ai-team/test-output/screenshot-e2e.png"
    result = _invoke(
        browser,
        {"operation": "screenshot", "url": "https://example.com", "save_path": save_path},
        ctx,
    )
    assert result.success is True
    assert result.metadata.get("saved") is True
    full_path = Path(save_path).resolve()
    assert full_path.exists()
    with open(full_path, "rb") as f:
        assert f.read()[:8] == b"\x89PNG\r\n\x1a\n"
    full_path.unlink(missing_ok=True)
    full_path.parent.rmdir()  # remove empty test-output dir


# ------------------------------------------------------------------
# Interaction
# ------------------------------------------------------------------

@pytest.mark.e2e
def test_browser_click(browser: BrowserTool, ctx: ToolContext) -> None:
    """Click a link on example.com."""
    result = _invoke(
        browser, {"operation": "click", "url": "https://example.com", "selector": "a"}, ctx
    )
    assert result.success is True
    assert result.data.get("clicked") == "a"


@pytest.mark.e2e
def test_browser_evaluate(browser: BrowserTool, ctx: ToolContext) -> None:
    """Run JavaScript on a page."""
    result = _invoke(
        browser,
        {"operation": "evaluate", "url": "https://example.com", "script": "document.title"},
        ctx,
    )
    assert result.success is True
    assert "Example Domain" in result.data


# ------------------------------------------------------------------
# Session lifecycle
# ------------------------------------------------------------------

@pytest.mark.e2e
def test_browser_session_lifecycle(browser: BrowserTool, ctx: ToolContext) -> None:
    """Create a session, navigate, and close it.

    All session operations must run in the *same* thread because
    Playwright page objects are bound to the thread that created them.
    """
    with ThreadPoolExecutor(max_workers=1) as pool:
        create_result = pool.submit(browser.invoke, {"operation": "create_session"}, ctx).result()
        assert create_result.success is True
        session_id = create_result.data["session_id"]

        nav_result = pool.submit(
            browser.invoke,
            {"operation": "navigate", "url": "https://example.com", "session_id": session_id},
            ctx,
        ).result()
        assert nav_result.success is True
        assert "Example Domain" in nav_result.data.get("title", "")

        text_result = pool.submit(
            browser.invoke, {"operation": "get_text", "session_id": session_id}, ctx
        ).result()
        assert text_result.success is True
        assert "Example Domain" in text_result.data

        close_result = pool.submit(
            browser.invoke, {"operation": "close_session", "session_id": session_id}, ctx
        ).result()
        assert close_result.success is True


# ------------------------------------------------------------------
# Policy
# ------------------------------------------------------------------

@pytest.mark.e2e
def test_browser_network_policy_denied(browser: BrowserTool) -> None:
    """Without network_allowed, operations should fail."""
    ctx = ToolContext(network_allowed=False)
    result = _invoke(browser, {"operation": "navigate", "url": "https://example.com"}, ctx)
    assert result.success is False
    assert "not allowed" in result.error.lower()
