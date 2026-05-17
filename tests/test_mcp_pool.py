"""Tests for MCP connection pool."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.mcp.client import MCPClient
from tools.mcp.config import MCPServerConfig
from tools.mcp.pool import MCPConnectionPool


class TestMCPConnectionPoolCleanup:
    def test_atexit_cleanup_disconnects_all(self) -> None:
        pool = MCPConnectionPool()
        server = MCPServerConfig(name="test", command=["echo"])
        mock_client = MagicMock()
        mock_client._proc = MagicMock()
        mock_client._proc.poll.return_value = None
        with patch("tools.mcp.pool.MCPClient", return_value=mock_client):
            pool.get_client(server)
        # Simulate the atexit handler
        pool._atexit_cleanup()
        mock_client.disconnect.assert_called_once()



class TestMCPConnectionPool:
    def test_get_client_creates_new_connection(self) -> None:
        pool = MCPConnectionPool()
        server = MCPServerConfig(name="test", command=["echo"])
        with patch("tools.mcp.pool.MCPClient") as mock_cls:
            mock_client = MagicMock()
            mock_client._proc = MagicMock()
            mock_client._proc.poll.return_value = None
            mock_cls.return_value = mock_client
            client = pool.get_client(server)
            assert client is mock_client
            mock_client.connect.assert_called_once()

    def test_get_client_reuses_active_connection(self) -> None:
        pool = MCPConnectionPool()
        server = MCPServerConfig(name="test", command=["echo"])
        mock_client = MagicMock()
        mock_client._proc = MagicMock()
        mock_client._proc.poll.return_value = None
        with patch("tools.mcp.pool.MCPClient", return_value=mock_client):
            c1 = pool.get_client(server)
            c2 = pool.get_client(server)
            assert c1 is c2
            assert mock_client.connect.call_count == 1

    def test_disconnect_all_closes_all(self) -> None:
        pool = MCPConnectionPool()
        server = MCPServerConfig(name="test", command=["echo"])
        mock_client = MagicMock()
        mock_client._proc = MagicMock()
        mock_client._proc.poll.return_value = None
        with patch("tools.mcp.pool.MCPClient", return_value=mock_client):
            pool.get_client(server)
            pool.disconnect_all()
            mock_client.disconnect.assert_called_once()

    def test_context_manager_disconnects_on_exit(self) -> None:
        with MCPConnectionPool() as pool:
            server = MCPServerConfig(name="test", command=["echo"])
            mock_client = MagicMock()
            mock_client._proc = MagicMock()
            mock_client._proc.poll.return_value = None
            with patch("tools.mcp.pool.MCPClient", return_value=mock_client):
                pool.get_client(server)
        mock_client.disconnect.assert_called_once()
