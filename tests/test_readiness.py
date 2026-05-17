from __future__ import annotations

import json
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.config import ConfigError, ModelRole, TeamConfig, TeamProfile
from core.errors import ProviderError
from interfaces.readiness import (
    ReadinessState,
    ReadinessStatus,
    build_readiness_state,
)


def _make_config(
    *,
    providers: dict | None = None,
    models: dict | None = None,
    profile_name: str = "default",
) -> TeamConfig:
    return TeamConfig(
        providers=providers or {},
        models=models or {},
        profile_name=profile_name,
    )


def _make_provider(
    provider_id: str = "test",
    provider_type: str = "openai_v1",
    endpoint: str = "https://api.openai.com/v1",
    auth_mode: str = "bearer",
    secret_ref: str | None = "secret://provider/test/api_key",
    api_key: str | None = "test-key",
) -> dict:
    return {
        provider_id: {
            "id": provider_id,
            "provider_type": provider_type,
            "endpoint": endpoint,
            "auth_mode": auth_mode,
            "secret_ref": secret_ref,
            "api_key": api_key,
            "timeout_seconds": 60,
            "headers": {},
            "metadata": {},
        }
    }


def _make_model(
    model_id: str = "planner",
    role: ModelRole = ModelRole.PLANNER,
    provider: str = "test",
    model_name: str = "gpt-4o-mini",
) -> dict:
    return {
        model_id: {
            "id": model_id,
            "role": role,
            "provider": provider,
            "model_name": model_name,
            "capabilities": ["text", "json"],
        }
    }


class TestMissingProfile:
    def test_missing_profile_returns_needs_provider(self) -> None:
        with patch("interfaces.readiness.load_team_config") as mock_load:
            mock_load.side_effect = ConfigError(
                "No Agentheim provider profile found. Run `agentheim provider add` or `agentheim provider import-env`."
            )
            state = build_readiness_state()
        assert state.status == ReadinessStatus.needs_provider
        assert "provider profile" in state.detail.lower() or "agentheim provider add" in state.detail

    def test_profile_argument_passes_to_config_loader(self) -> None:
        config = _make_config(profile_name="work")
        with patch("interfaces.readiness.load_team_config", return_value=config) as mock_load:
            state = build_readiness_state(profile="work", skip_connectivity=True)
        mock_load.assert_called_once_with(profile="work")
        assert state.profile_name == "work"
        assert any("agentheim provider add" in action for action in state.next_actions)


class TestMissingProvider:
    def test_no_providers_returns_needs_provider(self) -> None:
        config = _make_config(providers={}, models={})
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state()
        assert state.status == ReadinessStatus.needs_provider
        assert state.profile_name == "default"
        assert "no providers" in state.detail.lower()


class TestMissingModel:
    def test_no_models_returns_needs_model(self) -> None:
        providers = _make_provider()
        config = _make_config(providers=providers, models={})
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state()
        assert state.status == ReadinessStatus.needs_model
        assert "no models" in state.detail.lower()


class TestMissingRoles:
    def test_missing_required_roles_returns_needs_roles(self) -> None:
        providers = _make_provider()
        models = _make_model(role=ModelRole.PLANNER)
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state()
        assert state.status == ReadinessStatus.needs_roles
        assert "executor" in state.missing_roles
        assert "verifier" in state.missing_roles
        assert any("assign" in action.lower() for action in state.next_actions)


class TestPlaceholderEndpoint:
    def test_placeholder_endpoint_returns_endpoint_unreachable(self) -> None:
        providers = _make_provider(endpoint="-")
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state()
        assert state.status == ReadinessStatus.endpoint_unreachable
        assert "placeholder" in state.detail.lower()

    def test_azure_placeholder_endpoint_returns_endpoint_unreachable(self) -> None:
        providers = _make_provider(
            provider_type="azure_foundry",
            endpoint="https://YOUR-RESOURCE.openai.azure.com",
        )
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state()
        assert state.status == ReadinessStatus.endpoint_unreachable


class TestMissingSecret:
    def test_missing_secret_ref_returns_needs_secret(self) -> None:
        providers = _make_provider(auth_mode="bearer", secret_ref=None)
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state()
        assert state.status == ReadinessStatus.needs_secret
        assert "missing" in state.detail.lower() and "secret" in state.detail.lower()


class TestMissingSecretDoesNotCrashRoleCheck:
    def test_needs_secret_without_config_error(self) -> None:
        """Role coverage must not resolve provider secrets.

        Regression: calling config.by_role() triggered resolve_model(),
        which raised ConfigError when secret_ref was missing. This
        prevented build_readiness_state() from ever returning needs_secret.
        """
        providers = _make_provider(auth_mode="bearer", secret_ref=None, api_key=None)
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            state = build_readiness_state(skip_connectivity=True)
        assert state.status == ReadinessStatus.needs_secret
        assert "missing" in state.detail.lower() and "secret" in state.detail.lower()


class TestLocalProviderUnavailable:
    def test_local_provider_unreachable_returns_endpoint_unreachable(self) -> None:
        providers = _make_provider(
            provider_type="openai_compatible",
            endpoint="http://localhost:11434/v1",
            auth_mode="none",
            secret_ref=None,
        )
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.socket.create_connection") as mock_conn:
                mock_conn.side_effect = OSError("Connection refused")
                state = build_readiness_state()
        assert state.status == ReadinessStatus.endpoint_unreachable
        assert "unreachable" in state.detail.lower() or "connection refused" in state.detail.lower()
        assert state.local_reachability_ok is False

    def test_local_provider_reachable_returns_ready(self) -> None:
        providers = _make_provider(
            provider_type="openai_compatible",
            endpoint="http://localhost:11434/v1",
            auth_mode="none",
            secret_ref=None,
        )
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.socket.create_connection") as mock_conn:
                mock_conn.return_value = MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
                with patch("interfaces.integration_checks.check_all_optional_integrations", return_value=[]):
                    state = build_readiness_state(skip_connectivity=True)
        assert state.status == ReadinessStatus.ready
        assert state.local_reachability_ok is True


class TestModelConnectivity:
    def _make_ready_config(self) -> TeamConfig:
        providers = _make_provider()
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        return _make_config(providers=providers, models=models)

    def test_auth_failure_returns_auth_failed(self) -> None:
        config = self._make_ready_config()
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.build_model_registry") as mock_registry:
                mock_provider = MagicMock()
                mock_provider.invoke.side_effect = Exception("401 Unauthorized: invalid api key")
                mock_model = MagicMock()
                mock_model.config.provider = "test"
                mock_model.config.model = "gpt-4o-mini"
                mock_model.config.role = ModelRole.PLANNER
                mock_registry.return_value.resolve_model.return_value = mock_model
                mock_registry.return_value.create_provider.return_value = mock_provider
                state = build_readiness_state()
        assert state.status == ReadinessStatus.auth_failed
        assert state.model_connectivity_ok is False
        assert "auth" in state.model_connectivity_detail.lower() or "401" in state.model_connectivity_detail

    def test_generic_model_failure_returns_model_failed(self) -> None:
        config = self._make_ready_config()
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.build_model_registry") as mock_registry:
                mock_provider = MagicMock()
                mock_provider.invoke.side_effect = Exception("500 Internal Server Error")
                mock_model = MagicMock()
                mock_model.config.provider = "test"
                mock_model.config.model = "gpt-4o-mini"
                mock_model.config.role = ModelRole.PLANNER
                mock_registry.return_value.resolve_model.return_value = mock_model
                mock_registry.return_value.create_provider.return_value = mock_provider
                state = build_readiness_state()
        assert state.status == ReadinessStatus.model_failed
        assert state.model_connectivity_ok is False
        assert "500" in state.model_connectivity_detail

    def test_successful_model_call_returns_ready(self) -> None:
        config = self._make_ready_config()
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.build_model_registry") as mock_registry:
                mock_provider = MagicMock()
                mock_provider.invoke.return_value = MagicMock(content="pong")
                mock_model = MagicMock()
                mock_model.config.provider = "test"
                mock_model.config.model = "gpt-4o-mini"
                mock_model.config.role = ModelRole.PLANNER
                mock_registry.return_value.resolve_model.return_value = mock_model
                mock_registry.return_value.create_provider.return_value = mock_provider
                with patch("interfaces.integration_checks.check_all_optional_integrations", return_value=[]):
                    state = build_readiness_state()
        assert state.status == ReadinessStatus.ready
        assert state.model_connectivity_ok is True

    def test_skip_connectivity_does_not_check_model(self) -> None:
        config = self._make_ready_config()
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.build_model_registry") as mock_registry:
                mock_registry.side_effect = Exception("should not be called")
                with patch("interfaces.integration_checks.check_all_optional_integrations", return_value=[]):
                    state = build_readiness_state(skip_connectivity=True)
        assert state.status == ReadinessStatus.ready
        assert state.model_connectivity_ok is None


class TestReadyProfile:
    def test_fully_configured_returns_ready(self) -> None:
        providers = _make_provider()
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models, profile_name="prod")
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.build_model_registry") as mock_registry:
                mock_provider = MagicMock()
                mock_provider.invoke.return_value = MagicMock(content="pong")
                mock_model = MagicMock()
                mock_model.config.provider = "test"
                mock_model.config.model = "gpt-4o-mini"
                mock_model.config.role = ModelRole.PLANNER
                mock_registry.return_value.resolve_model.return_value = mock_model
                mock_registry.return_value.create_provider.return_value = mock_provider
                with patch("interfaces.integration_checks.check_all_optional_integrations", return_value=[]):
                    state = build_readiness_state()
        assert state.status == ReadinessStatus.ready
        assert state.profile_name == "prod"
        assert len(state.configured_providers) == 1
        assert state.configured_providers[0].provider_id == "test"
        assert state.missing_roles == []
        assert state.model_connectivity_ok is True
        assert any("agentheim use" in action for action in state.next_actions)


class TestOptionalIntegrationUnavailable:
    def test_context_ops_failure_returns_optional_integration_unavailable(self) -> None:
        providers = _make_provider()
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.build_model_registry") as mock_registry:
                mock_provider = MagicMock()
                mock_provider.invoke.return_value = MagicMock(content="pong")
                mock_model = MagicMock()
                mock_model.config.provider = "test"
                mock_model.config.model = "gpt-4o-mini"
                mock_model.config.role = ModelRole.PLANNER
                mock_registry.return_value.resolve_model.return_value = mock_model
                mock_registry.return_value.create_provider.return_value = mock_provider
                with patch("builtins.__import__", side_effect=ImportError("No module named 'agentheim.context_ops_impl'")):
                    # The above patch is too broad; patch the specific import instead
                    pass

        # Patching the specific deferred import path
        import sys
        module_path = "agentheim.context_ops_impl"
        original = sys.modules.get(module_path)
        try:
            sys.modules[module_path] = MagicMock()
            sys.modules[module_path].AictxContextOps = MagicMock(side_effect=ImportError("context ops not available"))
            with patch("interfaces.readiness.load_team_config", return_value=config):
                with patch("interfaces.readiness.build_model_registry") as mock_registry:
                    mock_provider = MagicMock()
                    mock_provider.invoke.return_value = MagicMock(content="pong")
                    mock_model = MagicMock()
                    mock_model.config.provider = "test"
                    mock_model.config.model = "gpt-4o-mini"
                    mock_model.config.role = ModelRole.PLANNER
                    mock_registry.return_value.resolve_model.return_value = mock_model
                    mock_registry.return_value.create_provider.return_value = mock_provider
                    state = build_readiness_state()
            assert state.status == ReadinessStatus.optional_integration_unavailable
            assert any(oi.integration_id == "context_ops" and not oi.available for oi in state.optional_integrations)
        finally:
            if original is not None:
                sys.modules[module_path] = original
            elif module_path in sys.modules:
                del sys.modules[module_path]

    def test_skip_optional_integrations_returns_ready(self) -> None:
        providers = _make_provider()
        models = {
            **_make_model(role=ModelRole.PLANNER),
            **_make_model(model_id="executor", role=ModelRole.EXECUTOR),
            **_make_model(model_id="verifier", role=ModelRole.VERIFIER),
        }
        config = _make_config(providers=providers, models=models)
        with patch("interfaces.readiness.load_team_config", return_value=config):
            with patch("interfaces.readiness.build_model_registry") as mock_registry:
                mock_provider = MagicMock()
                mock_provider.invoke.return_value = MagicMock(content="pong")
                mock_model = MagicMock()
                mock_model.config.provider = "test"
                mock_model.config.model = "gpt-4o-mini"
                mock_model.config.role = ModelRole.PLANNER
                mock_registry.return_value.resolve_model.return_value = mock_model
                mock_registry.return_value.create_provider.return_value = mock_provider
                state = build_readiness_state(check_optional_integrations=False)
        assert state.status == ReadinessStatus.ready
        assert state.optional_integrations == []


class TestReadinessStateModel:
    def test_readiness_state_serializes_to_dict(self) -> None:
        state = ReadinessState(
            status=ReadinessStatus.ready,
            profile_name="test",
            model_count=3,
            missing_roles=[],
            configured_providers=[],
            next_actions=["Run agentheim use"],
        )
        data = state.model_dump()
        assert data["status"] == "ready"
        assert data["profile_name"] == "test"
        assert data["model_count"] == 3
