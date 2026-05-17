from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from interfaces.cli.cli import app
from interfaces.readiness import OptionalIntegrationState, ReadinessState, ReadinessStatus
from core.run_view import RunView


runner = CliRunner()


def _status_env(tmp_path: Path) -> dict[str, str]:
    return {
        "AGENTHEIM_CONFIG_DIR": str(tmp_path / "config"),
        "AGENTHEIM_DATA_DIR": str(tmp_path / "data"),
    }


def _state(status: ReadinessStatus, **overrides) -> ReadinessState:
    data = {
        "status": status,
        "profile_name": "default",
        "model_count": 0,
        "missing_roles": [],
        "configured_providers": [],
        "optional_integrations": [],
        "next_actions": ["Next: agentheim setup"],
        "detail": "",
    }
    data.update(overrides)
    return ReadinessState(**data)


def _run(run_id: str, status: str, summary: str) -> RunView:
    return RunView(
        run_id=run_id,
        status=status,
        summary=summary,
        artifact_dir=f"C:/repo/.ai-team/runs/{run_id}",
        next_actions=[],
    )


def test_status_help_and_root_help_show_command() -> None:
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
    result_root = runner.invoke(app, ["--help"])
    assert result_root.exit_code == 0
    assert "status" in result_root.output
    assert "Getting Started" in result_root.output


def test_status_no_config(tmp_path: Path) -> None:
    env = _status_env(tmp_path)
    state = _state(ReadinessStatus.needs_provider, detail="No providers configured.")
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=state), patch(
        "interfaces.cli.product_commands.list_run_views", return_value=[]
    ):
        result = runner.invoke(app, ["status"], env=env)
    assert result.exit_code == 0
    assert "status: needs_provider" in result.output
    assert "recent runs: none" in result.output


def test_status_partial_config_shows_missing_roles(tmp_path: Path) -> None:
    env = _status_env(tmp_path)
    state = _state(ReadinessStatus.needs_roles, missing_roles=["executor", "verifier"])
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=state), patch(
        "interfaces.cli.product_commands.list_run_views", return_value=[]
    ):
        result = runner.invoke(app, ["status"], env=env)
    assert result.exit_code == 0
    assert "missing roles: executor, verifier" in result.output


def test_status_ready_config_with_runs(tmp_path: Path) -> None:
    env = _status_env(tmp_path)
    state = _state(ReadinessStatus.ready, next_actions=["Next: agentheim use"])
    runs = [_run("run-1", "completed", "Fixed auth"), _run("run-2", "failed", "Retry later")]
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=state), patch(
        "interfaces.cli.product_commands.list_run_views", return_value=runs
    ):
        result = runner.invoke(app, ["status"], env=env)
    assert result.exit_code == 0
    assert "Recent runs" in result.output
    assert "run-1" in result.output
    assert "run-2" in result.output
    assert "Next: agentheim use" in result.output


def test_status_optional_integration_unavailable(tmp_path: Path) -> None:
    env = _status_env(tmp_path)
    state = _state(
        ReadinessStatus.optional_integration_unavailable,
        optional_integrations=[
            OptionalIntegrationState(
                integration_id="context_ops",
                available=False,
                detail="missing vendor dependency",
                next_action="Check vendor setup.",
            )
        ],
    )
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=state), patch(
        "interfaces.cli.product_commands.list_run_views", return_value=[]
    ):
        result = runner.invoke(app, ["status"], env=env)
    assert result.exit_code == 0
    assert "optional integration context_ops: unavailable" in result.output


def test_status_empty_runs(tmp_path: Path) -> None:
    env = _status_env(tmp_path)
    state = _state(ReadinessStatus.ready)
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=state), patch(
        "interfaces.cli.product_commands.list_run_views", return_value=[]
    ):
        result = runner.invoke(app, ["status"], env=env)
    assert result.exit_code == 0
    assert "recent runs: none" in result.output


def test_status_json_shape(tmp_path: Path) -> None:
    env = _status_env(tmp_path)
    state = _state(ReadinessStatus.ready)
    runs = [_run("run-1", "completed", "ok")]
    with patch("interfaces.cli.product_commands.build_readiness_state", return_value=state), patch(
        "interfaces.cli.product_commands.list_run_views", return_value=runs
    ):
        result = runner.invoke(app, ["status", "--json"], env=env)
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(
        ["status", "profile", "repo", "readiness", "provider_readiness", "missing_roles", "optional_integrations", "recent_runs", "next_actions"]
    ).issubset(payload)
    assert isinstance(payload["recent_runs"], list)
    assert payload["recent_runs"][0]["run_id"] == "run-1"