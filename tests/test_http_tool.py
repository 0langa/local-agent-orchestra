"""Unit tests for tools.http.HttpTool — all mock-based, no real network calls."""

import socket
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from core.tool_protocol import RiskLevel, ToolContext, ToolResult
from tools.http import HttpTool
from tools.network import NetworkPolicy


@pytest.fixture
def allowed_context() -> ToolContext:
    return ToolContext(network_allowed=True)


@pytest.fixture
def denied_context() -> ToolContext:
    return ToolContext(network_allowed=False)


@pytest.fixture
def http_tool() -> HttpTool:
    return HttpTool(network_policy=NetworkPolicy(allowed=True))


class TestHttpToolSchemaAndRisk:
    def test_tool_id(self, http_tool: HttpTool) -> None:
        assert http_tool.tool_id == "http.request"

    def test_risk_level_is_high(self, http_tool: HttpTool) -> None:
        assert http_tool.risk_level == RiskLevel.HIGH


class TestHttpToolSuccess:
    def test_get_request_success(self, http_tool: HttpTool, allowed_context: ToolContext) -> None:
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read.return_value = b"hello"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = http_tool.invoke(
                {"method": "GET", "url": "https://1.1.1.1"},
                allowed_context,
            )

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == {"status": 200, "headers": {}, "body": "hello"}
        assert result.error is None

    def test_post_with_body(self, http_tool: HttpTool, allowed_context: ToolContext) -> None:
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.read.return_value = b'{"id": 1}'
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = http_tool.invoke(
                {"method": "POST", "url": "https://1.1.1.1/api", "body": "payload"},
                allowed_context,
            )

        assert result.success is True
        assert result.data["status"] == 201

        assert mock_urlopen.call_count == 1
        request_obj = mock_urlopen.call_args[0][0]
        assert request_obj.get_method() == "POST"
        assert request_obj.data == b"payload"


class TestHttpToolPolicyDenial:
    def test_default_tool_allows_network_when_context_allows(self, allowed_context: ToolContext) -> None:
        tool = HttpTool()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.read.return_value = b"hello"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            result = tool.invoke(
                {"method": "GET", "url": "https://1.1.1.1"},
                allowed_context,
            )

        assert result.success is True

    def test_network_policy_denies_private_ip(self, allowed_context: ToolContext) -> None:
        tool = HttpTool(
            network_policy=NetworkPolicy(
                allowed=True, allowed_schemes=("http", "https")
            )
        )
        result = tool.invoke(
            {"method": "GET", "url": "http://192.168.1.1/test"},
            allowed_context,
        )
        assert result.success is False
        assert "policy violation" in result.error.lower()
        assert "private" in result.error.lower()

    def test_network_policy_denies_http_scheme(self, allowed_context: ToolContext) -> None:
        tool = HttpTool(network_policy=NetworkPolicy(allowed=True))
        result = tool.invoke(
            {"method": "GET", "url": "http://example.com"},
            allowed_context,
        )
        assert result.success is False
        assert "scheme" in result.error.lower()
        assert "policy violation" in result.error.lower()

    def test_context_network_not_allowed(self, denied_context: ToolContext) -> None:
        tool = HttpTool(network_policy=NetworkPolicy(allowed=True))
        result = tool.invoke(
            {"method": "GET", "url": "https://example.com"},
            denied_context,
        )
        assert result.success is False
        assert "network access is not allowed by policy" in result.error.lower()


class TestHttpToolRequestFailures:
    def test_timeout_error(self, http_tool: HttpTool, allowed_context: ToolContext) -> None:
        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            result = http_tool.invoke(
                {"method": "GET", "url": "https://1.1.1.1"},
                allowed_context,
            )
        assert result.success is False
        assert "http request failed" in result.error.lower()
        assert "timed out" in result.error.lower()

    def test_http_error_404(self, http_tool: HttpTool, allowed_context: ToolContext) -> None:
        error = urllib.error.HTTPError(
            "https://example.com", 404, "Not Found", {}, None
        )
        with patch("urllib.request.urlopen", side_effect=error):
            result = http_tool.invoke(
                {"method": "GET", "url": "https://1.1.1.1"},
                allowed_context,
            )
        assert result.success is False
        assert "http request failed" in result.error.lower()
        assert "404" in result.error

    def test_invalid_url(self, http_tool: HttpTool, allowed_context: ToolContext) -> None:
        error = urllib.error.URLError("name or service not known")
        with patch("urllib.request.urlopen", side_effect=error):
            result = http_tool.invoke(
                {"method": "GET", "url": "https://1.1.1.1"},
                allowed_context,
            )
        assert result.success is False
        assert "http request failed" in result.error.lower()


class TestHttpToolValidation:
    def test_param_validation_rejects_missing_method(self, allowed_context: ToolContext) -> None:
        tool = HttpTool()
        result = tool.invoke(
            {"url": "https://example.com"},
            allowed_context,
        )
        assert result.success is False
        assert "missing required parameter: method" in result.error.lower()

    def test_param_validation_rejects_missing_url(self, allowed_context: ToolContext) -> None:
        tool = HttpTool()
        result = tool.invoke(
            {"method": "GET"},
            allowed_context,
        )
        assert result.success is False
        assert "missing required parameter: url" in result.error.lower()
