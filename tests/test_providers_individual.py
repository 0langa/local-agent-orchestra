"""Unit tests for individual provider adapters — all mock-based, no real network calls."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from config.config import AgentModelConfig, ModelRole
from core.errors import ProviderError
from providers.anthropic import AnthropicProvider
from providers.aws_bedrock import AWSBedrockProvider
from providers.azure_foundry import AzureFoundryProvider, normalize_azure_foundry_endpoint
from providers.base import ContentPart, ModelRequest
from providers.cohere import CohereProvider
from providers.gemini import GeminiProvider, VertexAIProvider
from providers.oci_genai import OCIGenAIProvider
from providers.ollama_cloud import OllamaCloudProvider
from providers.openai_v1 import OpenAIV1Provider
from providers.perplexity import PerplexityProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(**overrides: Any) -> AgentModelConfig:
    defaults: dict[str, Any] = {
        "role": ModelRole.PLANNER,
        "provider": "test-provider",
        "provider_type": "test",
        "endpoint": "https://api.test.com",
        "api_key": "test-key",
        "auth_mode": "api_key",
        "model": "test-model",
        "timeout_seconds": 30,
        "headers": {},
        "metadata": {},
    }
    defaults.update(overrides)
    return AgentModelConfig(**defaults)


def make_request(**overrides: Any) -> ModelRequest:
    defaults: dict[str, Any] = {
        "role": ModelRole.PLANNER,
        "user_prompt": "hello",
        "temperature": 0.0,
    }
    defaults.update(overrides)
    return ModelRequest(**defaults)


# ---------------------------------------------------------------------------
# OpenAIV1Provider
# ---------------------------------------------------------------------------

class TestOpenAIV1Provider:
    def test_init_sets_client_with_endpoint_and_headers(self) -> None:
        config = make_config(
            endpoint="https://api.openai.com/v1",
            api_key="sk-test",
            headers={"X-Custom": "val"},
        )
        with patch("providers.openai_v1.OpenAI") as mock_openai:
            provider = OpenAIV1Provider(config)

        mock_openai.assert_called_once_with(
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            timeout=30.0,
            default_headers={"X-Custom": "val"},
        )
        assert provider.config is config

    def test_invoke_success(self) -> None:
        config = make_config()
        mock_message = MagicMock()
        mock_message.content = "assistant reply"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 3
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.model_dump.return_value = {"id": "resp-1"}

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("providers.openai_v1.OpenAI", return_value=mock_client):
            provider = OpenAIV1Provider(config)
            request = make_request(system_prompt="sys")
            result = provider.invoke(request)

        assert result.content == "assistant reply"
        assert result.role == ModelRole.PLANNER
        assert result.model == "test-model"
        assert result.provider == "test-provider"
        assert result.raw == {"id": "resp-1"}

    def test_invoke_with_max_output_tokens(self) -> None:
        config = make_config()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_response.usage = None
        mock_response.model_dump.return_value = {"id": "resp-2"}
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("providers.openai_v1.OpenAI", return_value=mock_client):
            provider = OpenAIV1Provider(config)
            request = make_request(max_output_tokens=256)
            provider.invoke(request)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["max_completion_tokens"] == 256

    def test_invoke_retries_then_raises(self) -> None:
        config = make_config()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("boom")

        with (
            patch("providers.openai_v1.OpenAI", return_value=mock_client),
            patch("providers.openai_v1.time.sleep") as mock_sleep,
        ):
            provider = OpenAIV1Provider(config)
            request = make_request()
            with pytest.raises(ProviderError, match="Model invocation failed after retries"):
                provider.invoke(request)

        assert mock_client.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 2

    def test_auth_mode_none_uses_dummy_key(self) -> None:
        config = make_config(auth_mode="none", api_key="dummy")
        with patch("providers.openai_v1.OpenAI") as mock_openai:
            provider = OpenAIV1Provider(config)

        mock_openai.assert_called_once_with(
            api_key="no-key-required",
            base_url="https://api.test.com",
            timeout=30.0,
            default_headers=None,
        )
        assert provider.config is config

    def test_auth_error_raises_immediately(self) -> None:
        from openai import AuthenticationError

        config = make_config()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = AuthenticationError(
            "invalid key", response=MagicMock(), body=None
        )

        with patch("providers.openai_v1.OpenAI", return_value=mock_client):
            provider = OpenAIV1Provider(config)
            request = make_request()
            with pytest.raises(ProviderError, match="OpenAI request failed"):
                provider.invoke(request)

        assert mock_client.chat.completions.create.call_count == 1

    def test_rate_limit_is_retried(self) -> None:
        from openai import RateLimitError

        config = make_config()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "too many requests", response=MagicMock(), body=None
        )

        with (
            patch("providers.openai_v1.OpenAI", return_value=mock_client),
            patch("providers.openai_v1.time.sleep") as mock_sleep,
        ):
            provider = OpenAIV1Provider(config)
            request = make_request()
            with pytest.raises(ProviderError, match="Model invocation failed after retries"):
                provider.invoke(request)

        assert mock_client.chat.completions.create.call_count == 3
        assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------

class TestAnthropicProvider:
    def test_invoke_success(self) -> None:
        config = make_config(endpoint="https://api.anthropic.com", metadata={"anthropic_version": "2023-06-01"})
        provider = AnthropicProvider(config)
        request = make_request(user_prompt="hi")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"content": [{"type": "text", "text": "anthropic reply"}]}

        with patch("providers.anthropic.requests.post", return_value=mock_response) as mock_post:
            result = provider.invoke(request)

        assert result.content == "anthropic reply"
        call_args = mock_post.call_args
        url = call_args[0][0]
        headers = call_args[1]["headers"]
        assert url.endswith("/v1/messages")
        assert headers["x-api-key"] == "test-key"
        assert headers["anthropic-version"] == "2023-06-01"

    def test_invoke_with_image_url(self) -> None:
        config = make_config(endpoint="https://api.anthropic.com", metadata={"capabilities": ["vision"]})
        provider = AnthropicProvider(config)
        request = make_request(
            user_prompt="look",
            content=[ContentPart(type="image_url", image_url="https://example.com/img.png")],
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"content": [{"type": "text", "text": "ok"}]}

        with patch("providers.anthropic.requests.post", return_value=mock_response) as mock_post:
            provider.invoke(request)

        payload = mock_post.call_args[1]["json"]
        blocks = payload["messages"][0]["content"]
        image_block = [b for b in blocks if b.get("type") == "image"]
        assert len(image_block) == 1
        assert image_block[0]["source"]["url"] == "https://example.com/img.png"

    def test_invoke_retries_then_raises(self) -> None:
        config = make_config(endpoint="https://api.anthropic.com")
        provider = AnthropicProvider(config)
        request = make_request()

        with (
            patch("providers.anthropic.requests.post", side_effect=ConnectionError("net down")) as mock_post,
            patch("providers.anthropic.time.sleep") as mock_sleep,
        ):
            with pytest.raises(ProviderError, match="Anthropic invocation failed after retries"):
                provider.invoke(request)

        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# CohereProvider
# ---------------------------------------------------------------------------

class TestCohereProvider:
    def test_invoke_success(self) -> None:
        config = make_config(endpoint="https://api.cohere.com")
        provider = CohereProvider(config)
        request = make_request(user_prompt="hi", system_prompt="be nice")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": {"content": [{"text": "cohere reply"}]}}

        with patch("providers.cohere.requests.post", return_value=mock_response) as mock_post:
            result = provider.invoke(request)

        assert result.content == "cohere reply"
        payload = mock_post.call_args[1]["json"]
        assert payload["preamble"] == "be nice"

    def test_invoke_concatenates_content_parts(self) -> None:
        config = make_config(endpoint="https://api.cohere.com")
        provider = CohereProvider(config)
        request = make_request(
            user_prompt="hi",
            content=[
                ContentPart(type="text", text="extra1"),
                ContentPart(type="text", text="extra2"),
            ],
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": {"content": [{"text": "ok"}]}}

        with patch("providers.cohere.requests.post", return_value=mock_response) as mock_post:
            provider.invoke(request)

        payload = mock_post.call_args[1]["json"]
        assert payload["messages"][0]["content"] == "hi\nextra1 extra2"


# ---------------------------------------------------------------------------
# GeminiProvider
# ---------------------------------------------------------------------------

class TestGeminiProvider:
    def test_invoke_success(self) -> None:
        config = make_config(endpoint="https://generativelanguage.googleapis.com")
        provider = GeminiProvider(config)
        request = make_request(user_prompt="hi")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "gemini reply"}]}}]
        }

        with patch("providers.gemini.requests.post", return_value=mock_response) as mock_post:
            result = provider.invoke(request)

        assert result.content == "gemini reply"
        call_args = mock_post.call_args
        url = call_args[0][0]
        headers = call_args[1]["headers"]
        payload = call_args[1]["json"]
        assert ":generateContent" in url
        assert headers["x-goog-api-key"] == "test-key"
        assert "generationConfig" in payload

    def test_invoke_with_system_prompt(self) -> None:
        config = make_config(endpoint="https://generativelanguage.googleapis.com")
        provider = GeminiProvider(config)
        request = make_request(user_prompt="hi", system_prompt="sys")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }

        with patch("providers.gemini.requests.post", return_value=mock_response) as mock_post:
            provider.invoke(request)

        payload = mock_post.call_args[1]["json"]
        assert payload["systemInstruction"] == {"parts": [{"text": "sys"}]}

    def test_invoke_with_max_output_tokens(self) -> None:
        config = make_config(endpoint="https://generativelanguage.googleapis.com")
        provider = GeminiProvider(config)
        request = make_request(user_prompt="hi", max_output_tokens=100)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }

        with patch("providers.gemini.requests.post", return_value=mock_response) as mock_post:
            provider.invoke(request)

        payload = mock_post.call_args[1]["json"]
        assert payload["generationConfig"]["maxOutputTokens"] == 100


# ---------------------------------------------------------------------------
# AzureFoundryProvider
# ---------------------------------------------------------------------------

class TestAzureFoundryProvider:
    def test_endpoint_normalized(self) -> None:
        config = make_config(endpoint="https://my-resource.openai.azure.com")
        with patch("providers.openai_v1.OpenAI"):
            provider = AzureFoundryProvider(config)
        assert provider.config.endpoint == "https://my-resource.openai.azure.com/openai/v1"

    def test_endpoint_with_existing_suffix_unchanged(self) -> None:
        config = make_config(endpoint="https://my-resource.openai.azure.com/openai/v1")
        with patch("providers.openai_v1.OpenAI"):
            provider = AzureFoundryProvider(config)
        assert provider.config.endpoint == "https://my-resource.openai.azure.com/openai/v1"

    def test_api_key_header_injected(self) -> None:
        config = make_config(endpoint="https://my-resource.openai.azure.com", api_key="secret", auth_mode="api_key")
        with patch("providers.openai_v1.OpenAI"):
            provider = AzureFoundryProvider(config)
        assert provider.config.headers.get("api-key") == "secret"

    def test_endpoint_with_trailing_slash(self) -> None:
        config = make_config(endpoint="https://my-resource.openai.azure.com/")
        with patch("providers.openai_v1.OpenAI"):
            provider = AzureFoundryProvider(config)
        assert provider.config.endpoint == "https://my-resource.openai.azure.com/openai/v1"


# ---------------------------------------------------------------------------
# PerplexityProvider
# ---------------------------------------------------------------------------

class TestPerplexityProvider:
    def test_endpoint_normalized(self) -> None:
        config = make_config(endpoint="https://api.perplexity.ai/")
        with patch("providers.openai_v1.OpenAI"):
            provider = PerplexityProvider(config)
        assert not provider.config.endpoint.endswith("/")
        assert provider.config.endpoint == "https://api.perplexity.ai"


# ---------------------------------------------------------------------------
# OllamaCloudProvider
# ---------------------------------------------------------------------------

class TestOllamaCloudProvider:
    def test_invoke_success(self) -> None:
        config = make_config(endpoint="https://ollama.com/api")
        provider = OllamaCloudProvider(config)
        request = make_request(user_prompt="hi", system_prompt="sys")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": "ollama reply"}

        with patch("providers.ollama_cloud.requests.post", return_value=mock_response) as mock_post:
            result = provider.invoke(request)

        assert result.content == "ollama reply"
        payload = mock_post.call_args[1]["json"]
        assert payload["prompt"] == "sys\n\nhi"
        assert payload["stream"] is False

    def test_invoke_without_system_prompt(self) -> None:
        config = make_config(endpoint="https://ollama.com/api")
        provider = OllamaCloudProvider(config)
        request = make_request(user_prompt="hi")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": "ok"}

        with patch("providers.ollama_cloud.requests.post", return_value=mock_response) as mock_post:
            provider.invoke(request)

        payload = mock_post.call_args[1]["json"]
        assert payload["prompt"] == "hi"


# ---------------------------------------------------------------------------
# AWSBedrockProvider
# ---------------------------------------------------------------------------

class TestAWSBedrockProvider:
    def test_invoke_success(self) -> None:
        config = make_config(
            endpoint="-",
            headers={"aws-region": "us-east-1"},
            model="anthropic.claude-3-haiku",
        )
        provider = AWSBedrockProvider(config)
        request = make_request(user_prompt="hi", system_prompt="sys")

        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "bedrock reply"}]}},
            "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        }
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3_config = MagicMock()

        with patch.dict(
            "sys.modules",
            {"boto3": mock_boto3, "botocore.config": mock_boto3_config},
        ):
            result = provider.invoke(request)

        assert result.content == "bedrock reply"
        assert result.provider == "aws_bedrock"
        mock_boto3.client.assert_called_once()
        assert mock_boto3.client.call_args[0][0] == "bedrock-runtime"
        assert mock_boto3.client.call_args[1]["region_name"] == "us-east-1"

        converse_call = mock_client.converse.call_args[1]
        assert converse_call["system"] == [{"text": "sys"}]
        assert converse_call["messages"] == [{"role": "user", "content": [{"text": "hi"}]}]

    def test_resolve_region_from_metadata(self) -> None:
        config = make_config(headers={"aws-region": "ap-south-1"})
        provider = AWSBedrockProvider(config)
        assert provider._resolve_region() == "ap-south-1"

    def test_bedrock_api_key_env_set(self) -> None:
        config = make_config(auth_mode="bedrock_api_key", api_key="my-token")
        provider = AWSBedrockProvider(config)
        request = make_request()

        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "ok"}]}},
            "usage": {},
        }
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_boto3_config = MagicMock()

        with patch.dict(
            "sys.modules",
            {"boto3": mock_boto3, "botocore.config": mock_boto3_config},
        ):
            with patch.dict("os.environ", {}, clear=False):
                provider.invoke(request)
                import os
                assert os.environ.get("AWS_BEARER_TOKEN_BEDROCK") == "my-token"


# ---------------------------------------------------------------------------
# OCIGenAIProvider
# ---------------------------------------------------------------------------

class TestOCIGenAIProvider:
    def test_invoke_delegates_to_aictx_provider(self) -> None:
        config = make_config(model="oci-model")
        provider = OCIGenAIProvider(config)
        request = make_request(user_prompt="hi", system_prompt="sys", temperature=0.5, max_output_tokens=256)

        mock_chat_response = MagicMock()
        mock_chat_response.content = "oci reply"
        mock_chat_response.input_tokens = 4
        mock_chat_response.output_tokens = 2
        mock_chat_response.finish_reason = "stop"

        mock_aictx_provider = MagicMock()
        mock_aictx_provider.chat.return_value = mock_chat_response

        mock_aictx_cls = MagicMock(return_value=mock_aictx_provider)
        mock_chat_request_cls = MagicMock()

        mock_oci_mod = MagicMock()
        mock_oci_mod.OCIGenAIProvider = mock_aictx_cls
        mock_base_mod = MagicMock()
        mock_base_mod.ChatRequest = mock_chat_request_cls

        with patch.dict(
            "sys.modules",
            {
                "agentheim.vendor.aictx.llm.oci_genai": mock_oci_mod,
                "agentheim.vendor.aictx.llm.base": mock_base_mod,
            },
        ):
            result = provider.invoke(request)

        mock_aictx_cls.assert_called_once_with(
            compartment_id=None,
            model_id="oci-model",
            temperature=0.5,
        )
        mock_chat_request_cls.assert_called_once_with(
            system_prompt="sys",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.5,
            max_output_tokens=256,
        )
        mock_aictx_provider.chat.assert_called_once()
        assert result.content == "oci reply"
        assert result.provider == "oci_genai"
        assert result.raw["input_tokens"] == 4
        assert result.raw["output_tokens"] == 2
        assert result.raw["finish_reason"] == "stop"


# ---------------------------------------------------------------------------
# VertexAIProvider
# ---------------------------------------------------------------------------

class TestVertexAIProvider:
    def test_invoke_uses_google_auth(self) -> None:
        config = make_config(
            endpoint="-",
            metadata={"location": "us-central1", "project_id": "my-project"},
        )
        provider = VertexAIProvider(config)
        request = make_request(user_prompt="hi")

        mock_credentials = MagicMock()
        mock_credentials.token = "gcp-token"

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "vertex reply"}]}}]
        }

        mock_google_auth = MagicMock()
        mock_google_auth.default.return_value = (mock_credentials, "my-project")
        mock_transport = MagicMock()
        mock_request_cls = MagicMock()
        mock_transport.requests.Request = mock_request_cls

        mock_google = MagicMock()
        mock_google.auth = mock_google_auth

        with (
            patch.dict(
                "sys.modules",
                {
                    "google": mock_google,
                    "google.auth": mock_google_auth,
                    "google.auth.transport": mock_transport,
                    "google.auth.transport.requests": mock_transport,
                },
            ),
            patch("providers.gemini.requests.post", return_value=mock_response) as mock_post,
        ):
            result = provider.invoke(request)

        mock_google_auth.default.assert_called_once_with(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        mock_credentials.refresh.assert_called_once()
        assert result.content == "vertex reply"

        call_args = mock_post.call_args
        headers = call_args[1]["headers"]
        payload = call_args[1]["json"]
        assert headers["Authorization"] == "Bearer gcp-token"
        assert payload["contents"][0]["parts"][0]["text"] == "hi"
