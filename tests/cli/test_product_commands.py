from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from config.config import load_profiles_document, make_secret_ref
from interfaces.cli.cli import app
from interfaces.readiness import ReadinessState, ReadinessStatus


runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "AGENTHEIM_CONFIG_DIR": str(tmp_path / "config"),
        "AGENTHEIM_DATA_DIR": str(tmp_path / "data"),
        "AGENTHEIM_SECRET_BACKEND": "file",
        "AGENTHEIM_VAULT_PASSPHRASE": "test-passphrase",
    }


def _ready_state() -> ReadinessState:
    return ReadinessState(
        status=ReadinessStatus.ready,
        profile_name="default",
        model_count=8,
        next_actions=["Run `agentheim status`", "Run `agentheim use`"],
        detail="All checks passed.",
    )


def test_setup_help_shows_getting_started() -> None:
    result = runner.invoke(app, ["setup", "--help"])
    assert result.exit_code == 0
    assert "setup" in result.output


def test_setup_registers_under_root_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Getting Started" in result.output
    assert "setup" in result.output


def test_commands_json_has_no_empty_beginner_group() -> None:
    result = runner.invoke(app, ["commands", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    commands = [item["command"] for section in payload["sections"] for item in section["commands"]]
    assert "" not in commands
    assert {"setup", "status", "use", "open", "runs"}.issubset(set(commands))


def test_setup_supports_each_beginner_provider(tmp_path: Path) -> None:
    providers = {
        "openai-compatible": ["--endpoint", "https://example.test/v1", "--api-key", "sk-test"],
        "openai": ["--api-key", "sk-openai"],
        "azure": ["--endpoint", "https://example.openai.azure.com", "--api-key", "azure-key"],
        "anthropic": ["--api-key", "anthropic-key"],
        "gemini": ["--api-key", "gemini-key"],
        "ollama": [],
        "lm-studio": [],
    }
    for provider, extra in providers.items():
        env = _env(tmp_path / provider.replace("-", "_"))
        with patch("interfaces.cli.product_commands.build_readiness_state", return_value=_ready_state()):
            result = runner.invoke(
                app,
                ["setup", "--provider", provider, "--model", "test-model", "--yes", *extra],
                env=env,
            )
        assert result.exit_code == 0, result.output
        document = load_profiles_document(Path(env["AGENTHEIM_CONFIG_DIR"]) / "providers.json")
        profile = document.profiles["default"]
        assert profile.providers
        assert profile.models["planner"].model == "test-model"


def test_setup_dry_run_writes_nothing(tmp_path: Path) -> None:
    env = _env(tmp_path)
    result = runner.invoke(
        app,
        ["setup", "--provider", "openai", "--model", "gpt-test", "--api-key", "secret", "--yes", "--dry-run", "--json"],
        env=env,
    )
    assert result.exit_code == 0, result.output
    assert not (Path(env["AGENTHEIM_CONFIG_DIR"]) / "providers.json").exists()
    payload = json.loads(result.output)
    assert payload["readiness"]["profile_name"] == "default"
    assert payload["readiness"]["configured_providers"][0]["provider_id"] == "openai"
    assert payload["readiness"]["lane"] == "DRY-RUN"


def test_setup_stores_secret_in_existing_secret_store(tmp_path: Path) -> None:
    env = _env(tmp_path)
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=_ready_state()):
        result = runner.invoke(
            app,
            ["setup", "--provider", "openai", "--model", "gpt-test", "--api-key", "secret-value", "--yes"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    document = load_profiles_document(Path(env["AGENTHEIM_CONFIG_DIR"]) / "providers.json")
    provider = document.profiles["default"].providers["openai"]
    assert provider.secret_ref == make_secret_ref("openai")
    assert "secret-value" not in (Path(env["AGENTHEIM_CONFIG_DIR"]) / "providers.json").read_text(encoding="utf-8")


def test_setup_binds_core_and_beginner_roles(tmp_path: Path) -> None:
    env = _env(tmp_path)
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=_ready_state()):
        result = runner.invoke(
            app,
            ["setup", "--provider", "openai", "--model", "gpt-test", "--api-key", "secret", "--yes"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    profile = load_profiles_document(Path(env["AGENTHEIM_CONFIG_DIR"]) / "providers.json").profiles["default"]
    for role in ["planner", "executor", "verifier", "context", "generator", "reviewer", "tester", "summarizer"]:
        assert role in profile.models
        assert profile.models[role].provider == "openai"


def test_setup_prints_readiness_and_next_actions(tmp_path: Path) -> None:
    env = _env(tmp_path)
    state = _ready_state()
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=state):
        result = runner.invoke(
            app,
            ["setup", "--provider", "ollama", "--model", "llama3", "--yes"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    assert "readiness: ready" in result.output.lower()
    assert "agentheim status" in result.output
    assert "agentheim use" in result.output


def test_setup_json_shape(tmp_path: Path) -> None:
    env = _env(tmp_path)
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=_ready_state()):
        result = runner.invoke(
            app,
            ["setup", "--provider", "gemini", "--model", "gemini-test", "--api-key", "secret", "--yes", "--json"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(["status", "profile", "provider", "model", "readiness", "next_actions"]).issubset(payload)
    assert payload["status"] == "ok"
    assert payload["provider"] == "gemini"
    assert payload["model"] == "gemini-test"
    assert isinstance(payload["next_actions"], list)


def test_setup_interactive_prompt_path(tmp_path: Path) -> None:
    env = _env(tmp_path)
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=_ready_state()):
        result = runner.invoke(
            app,
            ["setup"],
            input="openai\ngpt-4o-mini\nhttps://api.openai.com/v1\ninteractive-secret\ny\n",
            env=env,
        )
    assert result.exit_code == 0, result.output
    profile = load_profiles_document(Path(env["AGENTHEIM_CONFIG_DIR"]) / "providers.json").profiles["default"]
    assert profile.providers["openai"].secret_ref == make_secret_ref("openai")
