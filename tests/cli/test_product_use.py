from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from interfaces.cli.cli import app
from core.public_api import RunView
from presets.base import PresetInputError


runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "AGENTHEIM_CONFIG_DIR": str(tmp_path / "config"),
        "AGENTHEIM_DATA_DIR": str(tmp_path / "data"),
    }


def _record(status: str = "pending") -> MagicMock:
    record = MagicMock()
    record.status.value = status
    return record


def _catalog_item(preset_id: str) -> MagicMock:
    item = MagicMock()
    item.preset_id = preset_id
    item.name = preset_id
    item.description = f"Description for {preset_id}"
    item.questions = []
    return item


def _view(run_id: str, status: str = "completed") -> RunView:
    return RunView(
        run_id=run_id,
        status=status,
        summary="Run completed",
        artifact_dir=f"/tmp/{run_id}",
        next_actions=[f"agentheim runs show {run_id}"],
    )


def test_use_interactive_selection(tmp_path: Path) -> None:
    env = _env(tmp_path)
    preset = MagicMock()
    preset.validate_inputs.return_value = {"task": "Fix bug", "repo": str(tmp_path)}
    with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
        "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("codebase-assistant")
    ), patch(
        "interfaces.cli.product_commands._run_preset_sync", return_value=_view("run-123")
    ):
        result = runner.invoke(app, ["use"], input="code\nFix bug\n", env=env)
    assert result.exit_code == 0, result.output
    assert "run id: run-123" in result.output
    preset.validate_inputs.assert_called_once()


def test_use_direct_task_id(tmp_path: Path) -> None:
    env = _env(tmp_path)
    preset = MagicMock()
    preset.validate_inputs.return_value = {"query": "What changed?", "repo": str(tmp_path)}
    with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
        "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("local-document-chat")
    ), patch(
        "interfaces.cli.product_commands._run_preset_sync", return_value=_view("run-docs")
    ):
        result = runner.invoke(
            app,
            ["use", "docs-chat", "--input", "query=What changed?", "--repo", str(tmp_path), "--yes"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    assert "preset: local-document-chat" in result.output


def test_use_missing_input_fails(tmp_path: Path) -> None:
    env = _env(tmp_path)
    preset = MagicMock()
    preset.validate_inputs.side_effect = PresetInputError("codebase-assistant", ["task"])
    with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
        "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("codebase-assistant")
    ):
        result = runner.invoke(app, ["use", "code", "--yes"], env=env)
    assert result.exit_code != 0
    assert "Missing required input" in result.output


def test_use_advanced_task_execution(tmp_path: Path) -> None:
    env = _env(tmp_path)
    preset = MagicMock()
    preset.validate_inputs.return_value = {"topic": "Agents", "repo": str(tmp_path)}
    with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
        "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("research-report")
    ), patch(
        "interfaces.cli.product_commands._run_preset_sync", return_value=_view("run-research")
    ):
        result = runner.invoke(
            app,
            ["use", "research", "--input", "topic=Agents", "--repo", str(tmp_path), "--yes"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    assert "task: research" in result.output


def test_use_runs_preset_synchronously(tmp_path: Path) -> None:
    env = _env(tmp_path)
    preset = MagicMock()
    preset.validate_inputs.return_value = {"command_description": "List files", "repo": str(tmp_path)}
    with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
        "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("command-assistant")
    ), patch(
        "interfaces.cli.product_commands._run_preset_sync", return_value=_view("run-command")
    ) as run_sync:
        result = runner.invoke(
            app,
            ["use", "command", "--input", "command_description=List files", "--repo", str(tmp_path), "--yes"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    run_sync.assert_called_once()
    assert "agentheim runs show run-command" in result.output


def test_use_json_shape(tmp_path: Path) -> None:
    env = _env(tmp_path)
    preset = MagicMock()
    preset.validate_inputs.return_value = {"task": "Fix auth", "repo": str(tmp_path)}
    with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
        "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("codebase-assistant")
    ), patch(
        "interfaces.cli.product_commands._run_preset_sync", return_value=_view("run-json")
    ):
        result = runner.invoke(
            app,
            ["use", "code", "--input", "task=Fix auth", "--repo", str(tmp_path), "--json", "--yes"],
            env=env,
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert set(["task_id", "preset_id", "run_id", "status", "artifact_dir", "next_actions"]).issubset(payload)
    assert payload["task_id"] == "code"
    assert payload["run_id"] == "run-json"
