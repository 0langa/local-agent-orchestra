from __future__ import annotations

import pytest

from config.config import AgentModelConfig, ModelConfig, ModelRole, ProviderConfig, TeamConfig
from core.model_registry import ModelDescriptor, ModelRegistry, ProviderDescriptor


class TestModelRegistry:
    def _make_registry(self) -> ModelRegistry:
        providers = {
            "openai": ProviderDescriptor(id="openai", import_path="providers.openai_v1:OpenAIV1Provider"),
        }
        models = {
            "planner-1": ModelDescriptor(
                id="planner-1",
                role="planner",
                capabilities=frozenset(["plan", "json"]),
                config=AgentModelConfig(
                    role=ModelRole.PLANNER,
                    provider="openai",
                    provider_type="openai_v1",
                    endpoint="http://test",
                    api_key="test-key",
                    model="gpt-4",
                ),
            ),
            "executor-1": ModelDescriptor(
                id="executor-1",
                role="executor",
                capabilities=frozenset(["code_edit", "json"]),
                config=AgentModelConfig(
                    role=ModelRole.EXECUTOR,
                    provider="openai",
                    provider_type="openai_v1",
                    endpoint="http://test",
                    api_key="test-key",
                    model="gpt-4",
                ),
            ),
        }
        return ModelRegistry(providers=providers, models=models)

    def test_resolve_model_by_capability(self) -> None:
        registry = self._make_registry()
        model = registry.resolve_model("planner", "plan")
        assert model.id == "planner-1"

    def test_resolve_model_second_capability(self) -> None:
        registry = self._make_registry()
        model = registry.resolve_model("executor", "code_edit")
        assert model.id == "executor-1"

    def test_resolve_model_not_found(self) -> None:
        registry = self._make_registry()
        with pytest.raises(ValueError, match="No model for role"):
            registry.resolve_model("planner", "verify")

    def test_resolve_model_wrong_role(self) -> None:
        registry = self._make_registry()
        with pytest.raises(ValueError, match="No model for role"):
            registry.resolve_model("verifier", "plan")

    def test_from_team_config(self) -> None:
        team = TeamConfig(
            providers={
                "default": ProviderConfig(
                    id="default",
                    provider_type="openai_compatible",
                    endpoint="http://test",
                    api_key="secret",
                ),
            },
            models={
                "p1": ModelConfig(
                    id="p1",
                    role=ModelRole.PLANNER,
                    provider="default",
                    model_name="test-model",
                    capabilities=["plan"],
                ),
            },
        )
        registry = ModelRegistry.from_team_config(team)
        model = registry.resolve_model("planner", "plan")
        assert model.id == "p1"
        assert model.config.model == "test-model"

    def test_create_provider_unsupported(self) -> None:
        registry = self._make_registry()
        config = AgentModelConfig(
            role=ModelRole.PLANNER,
            provider="unknown",
            provider_type="unsupported",
            endpoint="http://test",
            api_key="key",
            model="m",
        )
        with pytest.raises(ValueError, match="Unsupported provider type"):
            registry.create_provider(config)
