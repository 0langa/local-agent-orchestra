from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from config.config import (
    ModelRole,
    EncryptedFileSecretStore,
    get_profiles_path,
    load_team_config,
    make_secret_ref,
)
from core.errors import ConfigError
from interfaces.cli.cli import app
from providers.base import ContentPart, ModelRequest, ModelProvider, ModelResponse


runner = CliRunner()


def _write_profile(config_dir: Path, *, secret_ref: str | None = None) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "providers.json").write_text(
        json.dumps(
            {
                "version": 1,
                "default_profile": "default",
                "profiles": {
                    "default": {
                        "name": "default",
                        "providers": {
                            "local": {
                                "id": "local",
                                "kind": "openai_compatible",
                                "endpoint": "http://localhost:11434/v1",
                                "auth_mode": "none" if secret_ref is None else "bearer",
                                "secret_ref": secret_ref,
                                "timeout_seconds": 60,
                                "headers": {},
                                "metadata": {"template": "ollama"},
                            }
                        },
                        "models": {
                            "planner": {
                                "id": "planner",
                                "role": "planner",
                                "provider": "local",
                                "model": "llama3",
                                "capabilities": ["text", "json"],
                            }
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_load_team_config_uses_profile_not_legacy_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_profile(config_dir)
    monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("AI_TEAM_PROVIDER_IDS", "legacy")
    monkeypatch.setenv("AI_TEAM_PROVIDER_LEGACY_ENDPOINT", "https://should-not-load.invalid")
    config = load_team_config(project_root=tmp_path / "no-project-pointer")
    resolved = config.resolve_role(ModelRole.PLANNER)
    assert resolved.provider == "local"
    assert resolved.endpoint == "http://localhost:11434/v1"
    assert resolved.api_key == "-"


def test_missing_profile_gives_setup_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(tmp_path / "missing"))
    with pytest.raises(ConfigError, match="agentheim provider add"):
        load_team_config()


def test_encrypted_file_secret_store_roundtrip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AGENTHEIM_VAULT_PASSPHRASE", "correct horse battery staple")
    store = EncryptedFileSecretStore(path=tmp_path / "vault.enc")
    ref = make_secret_ref("openai")
    store.set(ref, "sk-secret")
    assert store.get(ref) == "sk-secret"
    assert b"sk-secret" not in (tmp_path / "vault.enc").read_bytes()


def test_provider_add_ollama_auth_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(config_dir))
    result = runner.invoke(
        app,
        ["provider", "add", "ollama", "--template", "ollama", "--model", "llama3", "--role", "planner"],
    )
    assert result.exit_code == 0, result.output
    config = load_team_config(project_root=tmp_path / "no-project-pointer")
    resolved = config.resolve_role(ModelRole.PLANNER)
    assert resolved.provider == "ollama"
    assert resolved.auth_mode == "none"
    assert get_profiles_path().exists()


def test_vision_request_rejected_without_capability() -> None:
    class DummyProvider(ModelProvider):
        def invoke(self, request: ModelRequest) -> ModelResponse:
            self.validate_request(request)
            return ModelResponse(role=request.role, model=self.config.model, provider=self.config.provider, content="ok")

    from config.config import AgentModelConfig

    provider = DummyProvider(
        AgentModelConfig(
            role=ModelRole.PLANNER,
            provider="local",
            provider_type="openai_compatible",
            endpoint="http://localhost",
            api_key="-",
            auth_mode="none",
            model="text-only",
            metadata={"capabilities": ["text", "json"]},
        )
    )
    with pytest.raises(ValueError, match="vision capability"):
        provider.invoke(
            ModelRequest(
                role=ModelRole.PLANNER,
                user_prompt="describe",
                content=[ContentPart(type="image_url", image_url="https://example.com/image.png")],
            )
        )
