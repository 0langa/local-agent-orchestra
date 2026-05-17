"""Tests for core tool protocol including async variants."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.tool_protocol import (
    AsyncBaseTool,
    AsyncToolProtocol,
    BaseTool,
    ParamSchema,
    ReturnSchema,
    RiskLevel,
    ToolContext,
    ToolRegistry,
    ToolResult,
    ToolSchema,
)


class DummySyncTool(BaseTool):
    def __init__(self) -> None:
        schema = ToolSchema(
            description="A dummy sync tool",
            parameters={"x": ParamSchema(type="int", description="An int", required=True)},
            returns=ReturnSchema(type="int", description="The input"),
        )
        super().__init__("dummy.sync", schema, RiskLevel.LOW)

    def invoke(self, params: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(success=True, data=params.get("x"))


class DummyAsyncTool(AsyncBaseTool):
    def __init__(self) -> None:
        schema = ToolSchema(
            description="A dummy async tool",
            parameters={"y": ParamSchema(type="str", description="A string", required=True)},
            returns=ReturnSchema(type="str", description="The input"),
        )
        super().__init__("dummy.async", schema, RiskLevel.MEDIUM)

    async def ainvoke(self, params: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(success=True, data=params.get("y"))


class TestAsyncBaseTool:
    def test_cannot_instantiate_abstract(self):
        class Incomplete(AsyncBaseTool):
            def __init__(self):
                schema = ToolSchema(
                    description="incomplete",
                    parameters={},
                    returns=ReturnSchema(type="str", description=""),
                )
                super().__init__("incomplete", schema, RiskLevel.LOW)

        with pytest.raises(TypeError, match="abstract"):
            Incomplete()

    def test_validate_params_sync_on_async_tool(self):
        tool = DummyAsyncTool()
        valid, err = tool.validate_params({"y": "hello"})
        assert valid is True
        assert err == ""

        valid, err = tool.validate_params({})
        assert valid is False
        assert "Missing required parameter" in err


class TestToolRegistryMixed:
    def test_register_and_get_sync_tool(self):
        reg = ToolRegistry()
        tool = DummySyncTool()
        reg.register(tool)
        assert reg.get("dummy.sync") is tool

    def test_register_and_get_async_tool(self):
        reg = ToolRegistry()
        tool = DummyAsyncTool()
        reg.register(tool)
        assert reg.get("dummy.async") is tool

    def test_get_async_asserts_type(self):
        reg = ToolRegistry()
        sync_tool = DummySyncTool()
        async_tool = DummyAsyncTool()
        reg.register(sync_tool)
        reg.register(async_tool)

        assert reg.get_async("dummy.async") is async_tool
        with pytest.raises(TypeError, match="not an async tool"):
            reg.get_async("dummy.sync")

    def test_mixed_list_tools(self):
        reg = ToolRegistry()
        reg.register(DummySyncTool())
        reg.register(DummyAsyncTool())
        assert reg.list_tools() == ["dummy.async", "dummy.sync"]

    def test_discover_by_prefix_mixed(self):
        reg = ToolRegistry()
        reg.register(DummySyncTool())
        reg.register(DummyAsyncTool())
        assert len(reg.discover_by_prefix("dummy.")) == 2


class TestAsyncToolProtocol:
    def test_isinstance_check(self):
        tool = DummyAsyncTool()
        assert isinstance(tool, AsyncToolProtocol)


def _run_async(coro):
    """Run an async coroutine in a fresh thread with its own event loop.

    Needed because pytest-anyio keeps an event loop running in the main
    thread, which prevents ``asyncio.run()`` from being called directly.
    """
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


class TestAsyncMCPTool:
    def test_ainvoke_delegates_to_thread(self):
        from tools.mcp.tool_adapter import AsyncMCPTool

        mock_pool = MagicMock()
        mock_client = MagicMock()
        mock_client.call_tool.return_value = {"content": [{"text": "ok"}]}
        mock_pool.get_client.return_value = mock_client
        mock_server = MagicMock()
        mock_server.name = "test-server"

        tool = AsyncMCPTool(mock_pool, mock_server, {"name": "test_tool", "description": "Test", "inputSchema": {}})
        ctx = ToolContext()

        result = _run_async(tool.ainvoke({"arg": 1}, ctx))
        assert result.success is True
        mock_pool.get_client.assert_called_once()
        mock_pool.release_client.assert_called_once_with("test-server")


class TestAsyncBrowserTool:
    def test_ainvoke_create_session(self):
        from tools.browser import AsyncBrowserTool

        tool = AsyncBrowserTool()
        ctx = ToolContext(network_allowed=True)
        result = _run_async(tool.ainvoke({"operation": "create_session"}, ctx))
        assert result.success is True
        assert "session_id" in result.data

    def test_ainvoke_network_denied(self):
        from tools.browser import AsyncBrowserTool

        tool = AsyncBrowserTool()
        ctx = ToolContext(network_allowed=False)
        result = _run_async(tool.ainvoke({"operation": "navigate", "url": "https://example.com"}, ctx))
        assert result.success is False
        assert "policy" in result.error.lower()
