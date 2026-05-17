from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.tool_protocol import RiskLevel, ToolContext
from tools.mcp.client import MCPClient, MCPError
from tools.mcp.config import MCPServerConfig, load_mcp_config
from tools.mcp.config import MCPServerConfig
from tools.mcp.pool import MCPConnectionPool
from tools.mcp.tool_adapter import MCPTool, _convert_schema, _mcp_type_to_param_type


class TestMCPTypeMapping:
    def test_string_type(self) -> None:
        assert _mcp_type_to_param_type("string") == "str"

    def test_integer_type(self) -> None:
        assert _mcp_type_to_param_type("integer") == "int"

    def test_number_type(self) -> None:
        assert _mcp_type_to_param_type("number") == "float"

    def test_boolean_type(self) -> None:
        assert _mcp_type_to_param_type("boolean") == "bool"

    def test_unknown_type_defaults_to_str(self) -> None:
        assert _mcp_type_to_param_type("custom") == "str"


class TestSchemaConversion:
    def test_convert_simple_schema(self) -> None:
        mcp_schema = {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "count": {"type": "integer", "description": "How many"},
            },
            "required": ["path"],
        }
        params = _convert_schema(mcp_schema)
        assert "path" in params
        assert params["path"].required is True
        assert params["path"].type == "str"
        assert "count" in params
        assert params["count"].required is False
        assert params["count"].type == "int"

    def test_enum_preserved(self) -> None:
        mcp_schema = {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["read", "write"]},
            },
        }
        params = _convert_schema(mcp_schema)
        assert params["mode"].enum == ["read", "write"]


class TestMCPTool:
    def _make_tool(self, info: dict, mock_client: MagicMock | None = None):
        pool = MagicMock(spec=MCPConnectionPool)
        client = mock_client or MagicMock()
        pool.get_client.return_value = client
        server = MCPServerConfig(name="test", command=["echo"])
        return MCPTool(pool, server, info), pool, client

    def test_tool_id_prefixed(self) -> None:
        tool, _pool, _client = self._make_tool({"name": "read_file", "description": "Read a file"})
        assert tool.tool_id == "mcp.read_file"

    def test_schema_description(self) -> None:
        info = {
            "name": "read_file",
            "description": "Read a file",
            "inputSchema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
        tool, _pool, _client = self._make_tool(info)
        assert tool.schema.description == "Read a file"
        assert "path" in tool.schema.parameters

    def test_risk_level(self) -> None:
        tool, _pool, _client = self._make_tool({"name": "x", "description": "x"})
        assert tool.risk_level == RiskLevel.MEDIUM

    def test_invoke_success(self) -> None:
        client = MagicMock()
        client.call_tool.return_value = {"content": [{"type": "text", "text": "hello"}]}
        tool, pool, client = self._make_tool({"name": "echo", "description": "Echo"}, client)
        result = tool.invoke({"msg": "hi"}, ToolContext())
        assert result.success is True
        assert result.metadata.get("source") == "mcp"
        client.call_tool.assert_called_once_with("echo", {"msg": "hi"})
        pool.release_client.assert_called_once_with("test")

    def test_invoke_failure(self) -> None:
        client = MagicMock()
        client.call_tool.side_effect = RuntimeError("boom")
        tool, pool, client = self._make_tool({"name": "fail", "description": "Fail"}, client)
        result = tool.invoke({}, ToolContext())
        assert result.success is False
        assert "boom" in result.error
        pool.release_client.assert_called_once_with("test")


class TestMCPClient:
    def test_connect_command_not_found(self) -> None:
        client = MCPClient(["definitely_not_a_real_command_12345"])
        with pytest.raises(MCPError, match="not found"):
            client.connect()

    def test_disconnect_without_connect_is_noop(self) -> None:
        client = MCPClient(["echo", "hi"])
        client.disconnect()  # should not raise

    def test_kill_proc_tree_ignores_dead_process(self) -> None:
        client = MCPClient(["echo", "hi"])
        # PID 99999 is extremely unlikely to exist
        client._kill_proc_tree(99999)  # should not raise

    def test_disconnect_closes_pipes_and_kills_tree(self) -> None:
        client = MCPClient(["echo", "hi"])
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock(side_effect=subprocess.TimeoutExpired("cmd", 3))
        client._proc = mock_proc

        with patch.object(client, "_kill_proc_tree") as mock_kill_tree:
            client.disconnect()

        mock_proc.stdin.close.assert_called_once()
        mock_proc.stdout.close.assert_called_once()
        mock_proc.stderr.close.assert_called_once()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=3.0)
        mock_kill_tree.assert_called_once_with(1234)
        assert client._proc is None

    def test_list_tools_and_call_tool_mocked(self) -> None:
        client = MCPClient(["dummy"])
        client._proc = MagicMock()
        client._proc.poll.return_value = None
        client._proc.stdin = MagicMock()
        client._proc.stdout = MagicMock()

        # Simulate tools/list response (id will be 1 since connect() is bypassed)
        list_resp = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {"name": "read", "description": "Read file"},
                    {"name": "write", "description": "Write file"},
                ]
            },
        }
        # Simulate tools/call response (id will be 2)
        call_resp = {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "ok"}]}}

        client._proc.stdout.readline.side_effect = [
            json.dumps(list_resp) + "\n",
            json.dumps(call_resp) + "\n",
        ]

        # We need to bypass connect() since we're mocking _proc directly
        # Just test list_tools and call_tool directly
        tools = client.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "read"

        result = client.call_tool("read", {"path": "/tmp/x"})
        assert result["content"][0]["text"] == "ok"


class TestMCPConfig:
    def test_load_config_from_file(self, tmp_path: Path) -> None:
        path = tmp_path / "mcp.json"
        path.write_text(
            json.dumps({
                "servers": [
                    {"name": "fs", "command": ["npx", "fs"], "enabled": True},
                    {"name": "db", "command": ["uvx", "db"], "enabled": False},
                ]
            }),
            encoding="utf-8",
        )
        servers = load_mcp_config(path)
        assert len(servers) == 2
        assert servers[0].name == "fs"
        assert servers[0].enabled is True
        assert servers[1].enabled is False

    def test_load_config_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "AI_TEAM_MCP_SERVERS_JSON",
            json.dumps({"servers": [{"name": "env", "command": ["echo"]}]}),
        )
        servers = load_mcp_config(Path("/nonexistent"))
        assert len(servers) == 1
        assert servers[0].name == "env"

    def test_default_enabled(self, tmp_path: Path) -> None:
        path = tmp_path / "mcp.json"
        path.write_text(
            json.dumps({"servers": [{"name": "x", "command": ["echo"]}]}),
            encoding="utf-8",
        )
        servers = load_mcp_config(path)
        assert servers[0].enabled is True
