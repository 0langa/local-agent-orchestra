"""Tests for agentheim.provider_adapter.AgentheimToAictxAdapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agentheim.provider_adapter import AgentheimToAictxAdapter
from agentheim.vendor.aictx.llm.base import ChatRequest, ChatResponse
from config.config import AgentModelConfig, ModelRole
from providers.base import ModelRequest, ModelResponse


@pytest.fixture
def mock_provider() -> MagicMock:
    config = AgentModelConfig(
        role=ModelRole.PLANNER,
        provider="test",
        provider_type="openai_compatible",
        endpoint="http://localhost",
        api_key="secret",
        model="gpt-test",
    )
    provider = MagicMock()
    provider.config = config
    return provider


class TestChatRequestConversion:
    def test_chat_request_conversion(self, mock_provider: MagicMock) -> None:
        mock_provider.invoke.return_value = ModelResponse(
            role=ModelRole.PLANNER,
            model="gpt-test",
            provider="test",
            content="hello",
            raw={"input_tokens": 3, "output_tokens": 1},
        )
        adapter = AgentheimToAictxAdapter(mock_provider)

        request = ChatRequest(
            system_prompt="You are a planner",
            messages=[
                {"role": "system", "content": "You are a planner"},
                {"role": "user", "content": "Plan this"},
            ],
            temperature=0.7,
            max_output_tokens=512,
        )
        response = adapter.chat(request)

        assert isinstance(response, ChatResponse)
        assert response.content == "hello"
        assert response.input_tokens == 3
        assert response.output_tokens == 1

        call_args = mock_provider.invoke.call_args[0][0]
        assert isinstance(call_args, ModelRequest)
        assert call_args.role == ModelRole.PLANNER
        assert call_args.system_prompt == "You are a planner"
        assert call_args.user_prompt == "Plan this"
        assert call_args.temperature == 0.7
        assert call_args.max_output_tokens == 512


class TestChatResponseConversion:
    def test_chat_response_conversion(self, mock_provider: MagicMock) -> None:
        mock_provider.invoke.return_value = ModelResponse(
            role=ModelRole.PLANNER,
            model="gpt-test",
            provider="test",
            content="generated content",
            raw={"input_tokens": 10, "output_tokens": 5},
        )
        adapter = AgentheimToAictxAdapter(mock_provider)

        request = ChatRequest(messages=[{"role": "user", "content": "hi"}])
        response = adapter.chat(request)

        assert response.content == "generated content"
        assert response.finish_reason == "stop"
        assert response.input_tokens == 10
        assert response.output_tokens == 5


class TestCountTokensFallback:
    def test_count_tokens_fallback(self, mock_provider: MagicMock) -> None:
        del mock_provider.count_tokens
        adapter = AgentheimToAictxAdapter(mock_provider)

        text = "abcd" * 10  # 40 chars
        assert adapter.count_tokens(text) == 10

    def test_count_tokens_when_present(self, mock_provider: MagicMock) -> None:
        mock_provider.count_tokens.return_value = 99
        adapter = AgentheimToAictxAdapter(mock_provider)

        assert adapter.count_tokens("hello") == 99

    def test_count_tokens_none_result_fallback(self, mock_provider: MagicMock) -> None:
        mock_provider.count_tokens.return_value = None
        adapter = AgentheimToAictxAdapter(mock_provider)

        text = "abcd" * 5  # 20 chars
        assert adapter.count_tokens(text) == 5


class TestMetadataFallback:
    def test_metadata_fallback(self, mock_provider: MagicMock) -> None:
        del mock_provider.metadata
        adapter = AgentheimToAictxAdapter(mock_provider)

        assert adapter.metadata() == {"provider": "agentheim_adapter"}

    def test_metadata_when_present(self, mock_provider: MagicMock) -> None:
        mock_provider.metadata.return_value = {"provider": "custom"}
        adapter = AgentheimToAictxAdapter(mock_provider)

        assert adapter.metadata() == {"provider": "custom"}
