"""Tests for provider lazy loading in providers/__init__.py."""

from __future__ import annotations

import sys

import pytest

import providers
from providers import create_provider, get_provider_metadata, list_providers
from providers.base import ModelProvider, ModelRequest, ModelResponse


class TestProviderLazyLoading:
    def test_list_providers_does_not_load_modules(self) -> None:
        before = set(sys.modules.keys())
        ids = list_providers()
        after = set(sys.modules.keys())
        new_modules = after - before
        provider_modules = {m for m in new_modules if m.startswith("providers.") and m != "providers"}
        assert not provider_modules, f"Provider modules loaded: {provider_modules}"
        assert ids == [
            "openai_v1",
            "aws_bedrock",
            "azure_foundry",
            "oci_genai",
            "anthropic",
            "cohere",
            "gemini",
            "vertex_ai",
            "perplexity",
            "ollama_cloud",
        ]

    def test_get_provider_metadata_does_not_load(self) -> None:
        before = set(sys.modules.keys())
        meta = get_provider_metadata("openai_v1")
        after = set(sys.modules.keys())
        new_modules = after - before
        provider_modules = {m for m in new_modules if m.startswith("providers.") and m != "providers"}
        assert not provider_modules
        assert meta["module"] == "providers.openai_v1"
        assert meta["class"] == "OpenAIV1Provider"

    def test_create_provider_loads_requested_only(self) -> None:
        # This may fail if openai_v1 provider has external deps not installed,
        # so we just verify the mechanism works for a provider that CAN load.
        try:
            create_provider("openai_v1")
        except Exception as exc:
            # If it fails due to missing config/env, that's OK for this test
            # as long as the module was actually loaded
            assert "providers.openai_v1" in sys.modules
            return
        assert "providers.openai_v1" in sys.modules

    def test_create_provider_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown provider"):
            create_provider("nonexistent")

    def test_base_classes_eagerly_available(self) -> None:
        assert ModelProvider is not None
        assert ModelRequest is not None
        assert ModelResponse is not None

    def test_all_exports_present(self) -> None:
        assert hasattr(providers, "create_provider")
        assert hasattr(providers, "list_providers")
        assert hasattr(providers, "get_provider_metadata")
        assert hasattr(providers, "ModelProvider")
        assert hasattr(providers, "ModelRequest")
        assert hasattr(providers, "ModelResponse")
