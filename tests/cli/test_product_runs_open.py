from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from core.public_api import RunView
from interfaces.cli.cli import app


runner = CliRunner()


def _view(run_id: str = "run-1") -> RunView:
    return RunView(
        run_id=run_id,
        status="completed",
        summary="Done",
        report_path=str(Path("C:/repo/.ai-team/runs") / run_id / "final_report.md"),
        artifact_dir=str(Path("C:/repo/.ai-team/runs") / run_id),
        resume_available=True,
        next_actions=["agentheim report --repo . --run-id run-1"],
    )


def test_runs_defaults_to_list() -> None:
    with patch("interfaces.cli.product_commands.list_run_views", return_value=[_view()]):
        result = runner.invoke(app, ["runs"])
    assert result.exit_code == 0
    assert "Runs" in result.output
    assert "run-1" in result.output


def test_runs_show_json() -> None:
    with patch("interfaces.cli.product_commands.build_run_view", return_value=_view("run-show")):
        result = runner.invoke(app, ["runs", "show", "run-show", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-show"


def test_runs_report_shows_human_report(tmp_path: Path) -> None:
    report_path = tmp_path / "final_report.md"
    report_path.write_text("# Human report", encoding="utf-8")
    view = _view("run-report")
    view.report_path = str(report_path)
    with patch("interfaces.cli.product_commands.build_run_view", return_value=view):
        result = runner.invoke(app, ["runs", "report", "run-report"])
    assert result.exit_code == 0
    assert "# Human report" in result.output


def test_runs_resume_delegates() -> None:
    with patch("interfaces.cli.product_commands._resume_run", return_value={"run_id": "run-r", "all_success": True}):
        result = runner.invoke(app, ["runs", "resume", "run-r"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["run_id"] == "run-r"


def test_runs_open_folder() -> None:
    with patch("interfaces.cli.product_commands.build_run_view", return_value=_view("run-folder")), patch(
        "interfaces.cli.product_commands._open_path"
    ) as open_path:
        result = runner.invoke(app, ["runs", "open-folder", "run-folder"])
    assert result.exit_code == 0
    open_path.assert_called_once()


def test_runs_empty_json_shape() -> None:
    with patch("interfaces.cli.product_commands.list_run_views", return_value=[]):
        result = runner.invoke(app, ["runs", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == []


def test_open_default_web_launch() -> None:
    with patch("interfaces.cli.product_commands.webbrowser.open") as browser:
        result = runner.invoke(app, ["open", "--port", "9010"])
    assert result.exit_code == 0
    browser.assert_called_once_with("http://127.0.0.1:9010")
    assert "http://127.0.0.1:9010" in result.output


def test_open_no_browser_mode() -> None:
    with patch("interfaces.cli.product_commands.webbrowser.open") as browser:
        result = runner.invoke(app, ["open", "--no-browser"])
    assert result.exit_code == 0
    browser.assert_not_called()


def test_open_desktop_delegates() -> None:
    with patch("interfaces.desktop_ui.app.run_desktop_app") as desktop_app:
        result = runner.invoke(app, ["open", "--desktop", "--port", "9020"])
    assert result.exit_code == 0
    desktop_app.assert_called_once_with(port=9020, use_tray=True)


def test_open_json_shape() -> None:
    result = runner.invoke(app, ["open", "--json", "--port", "9030"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["mode"] == "web"
    assert payload["url"] == "http://127.0.0.1:9030"