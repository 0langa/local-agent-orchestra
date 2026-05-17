"""Phase 5: runs, artifacts, and recovery output tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from core.events import Event, EventType
from core.ledger import RunLedger
from core.public_api import CanonicalRunSummary, RunView, build_run_summary, build_run_view, list_run_views
from core.run_executor import RunExecutor, RunRecord, RunStatus
from core.run_summary import build_live_run_summary
from interfaces.cli.cli import app


runner = CliRunner()


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "AGENTHEIM_CONFIG_DIR": str(tmp_path / "config"),
        "AGENTHEIM_DATA_DIR": str(tmp_path / "data"),
    }


def _write_run_json(run_dir: Path, **fields) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(
        json.dumps({"run_id": run_dir.name, **fields}), encoding="utf-8"
    )


def _write_final_report(run_dir: Path, status: str, **fields) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "final_report.json").write_text(
        json.dumps({"status": status, **fields}), encoding="utf-8"
    )


def _write_ledger_with_initiated(run_dir: Path, workflow_id: str = "coding") -> RunLedger:
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger = RunLedger(repo_root=run_dir.parent.parent, run_dir=run_dir)
    ledger.append_event(
        EventType.RUN_INITIATED,
        payload={"workflow_id": workflow_id, "repo_root": str(run_dir.parent.parent)},
    )
    return ledger


class TestCanonicalSummaryFields:
    def test_report_path_and_artifact_dir_on_completed_run(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-1"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed", task_summary="Done")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        summary = build_run_summary(tmp_path, "run-1")
        assert summary.report_path == str(run_dir / "final_report.json")
        assert summary.artifact_dir == str(run_dir)

    def test_report_path_none_when_no_report(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-2"
        _write_run_json(run_dir, workflow_id="coding")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        summary = build_run_summary(tmp_path, "run-2")
        assert summary.report_path is None
        assert summary.artifact_dir == str(run_dir)

    def test_md_report_preferred_over_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-3"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed")
        (run_dir / "final_report.md").write_text("# Report", encoding="utf-8")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        summary = build_run_summary(tmp_path, "run-3")
        assert summary.report_path == str(run_dir / "final_report.md")

    def test_live_summary_has_none_for_missing_persisted_dir(self, tmp_path: Path) -> None:
        record = RunRecord(
            run_id="live-1",
            status=RunStatus.RUNNING,
            started_at=0.0,
        )
        summary = build_live_run_summary(tmp_path, "live-1", record)
        assert summary.report_path is None
        assert summary.artifact_dir is None


class TestRunViewOutput:
    def test_successful_run_output(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-ok"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed", task_summary="Auth fix")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")
        ledger = RunLedger(repo_root=tmp_path, run_dir=run_dir)
        ledger.append_event(EventType.RUN_COMPLETED, payload={"status": "completed"})

        view = build_run_view(tmp_path, "run-ok")
        assert view.status == "completed"
        assert view.summary == "Auth fix"
        assert view.report_path is not None
        assert view.artifact_dir == str(run_dir)
        assert any("report" in a.lower() for a in view.next_actions)

    def test_failed_run_output(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-fail"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "failed", task_summary="Auth fix failed")
        ledger = _write_ledger_with_initiated(run_dir, workflow_id="coding")
        ledger.append_event(EventType.RUN_FAILED, payload={"error_type": "ProviderError", "reason": "401"})

        view = build_run_view(tmp_path, "run-fail")
        assert view.status == "failed"
        assert view.resume_available is True
        assert any("doctor" in a.lower() for a in view.next_actions)
        assert any("resume" in a.lower() for a in view.next_actions)

    def test_blocked_run_output(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-blocked"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "blocked", task_summary="Blocked", remaining_risks=["high risk"])
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        view = build_run_view(tmp_path, "run-blocked")
        assert view.status == "blocked"
        assert view.resume_available is True
        assert any("resume" in a.lower() for a in view.next_actions)

    def test_resumable_run_output(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-resume"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "failed")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        view = build_run_view(tmp_path, "run-resume")
        assert view.resume_available is True
        assert view.status == "failed"

    def test_non_resumable_without_workflow(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-no-resume"
        _write_run_json(run_dir)
        _write_final_report(run_dir, "failed")
        ledger = RunLedger(repo_root=tmp_path, run_dir=run_dir)
        ledger.append_event(EventType.RUN_INITIATED, payload={})

        view = build_run_view(tmp_path, "run-no-resume")
        assert view.resume_available is False


class TestCliRunsShow:
    def test_runs_show_text_output(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-text"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed", task_summary="Done")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        result = runner.invoke(app, ["runs", "show", "run-text", "--repo", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "run id: run-text" in result.output
        assert "status: completed" in result.output
        assert "summary: Done" in result.output
        assert "artifact folder:" in result.output

    def test_runs_show_json_output(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-json"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        result = runner.invoke(app, ["runs", "show", "run-json", "--repo", str(tmp_path), "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["run_id"] == "run-json"
        assert "artifact_dir" in payload
        assert "report_path" in payload
        assert "next_actions" in payload

    def test_runs_show_failed_with_resume_guidance(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-fail-cli"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "failed")
        ledger = _write_ledger_with_initiated(run_dir, workflow_id="coding")
        ledger.append_event(EventType.RUN_FAILED, payload={"reason": "error"})

        result = runner.invoke(app, ["runs", "show", "run-fail-cli", "--repo", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "status: failed" in result.output
        assert any(word in result.output for word in ["resume", "doctor"])


class TestCliUseOutput:
    def test_use_outputs_run_view_fields(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        preset = MagicMock()
        preset.validate_inputs.return_value = {"task": "Fix bug", "repo": str(tmp_path)}
        view = RunView(
            run_id="run-use",
            status="completed",
            summary="Done",
            artifact_dir=str(tmp_path / ".ai-team" / "runs" / "run-use"),
            next_actions=["agentheim runs show run-use"],
        )
        with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
            "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("codebase-assistant")
        ), patch(
            "interfaces.cli.product_commands._run_preset_sync", return_value=view
        ):
            result = runner.invoke(
                app,
                ["use", "code", "--input", "task=Fix bug", "--repo", str(tmp_path), "--yes"],
                env=env,
            )
        assert result.exit_code == 0, result.output
        assert "task: code" in result.output
        assert "run id: run-use" in result.output
        assert "status:" in result.output
        assert "artifact folder:" in result.output

    def test_use_json_includes_run_view(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        preset = MagicMock()
        preset.validate_inputs.return_value = {"task": "Fix bug", "repo": str(tmp_path)}
        view = RunView(
            run_id="run-use-json",
            status="completed",
            summary="Done",
            artifact_dir=str(tmp_path / ".ai-team" / "runs" / "run-use-json"),
            next_actions=["agentheim runs show run-use-json"],
        )
        with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
            "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("codebase-assistant")
        ), patch(
            "interfaces.cli.product_commands._run_preset_sync", return_value=view
        ):
            result = runner.invoke(
                app,
                ["use", "code", "--input", "task=Fix bug", "--repo", str(tmp_path), "--json", "--yes"],
                env=env,
            )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["run_id"] == "run-use-json"
        assert "status" in payload
        assert "artifact_dir" in payload
        assert "next_actions" in payload
        assert payload["task_id"] == "code"


def _catalog_item(preset_id: str) -> MagicMock:
    item = MagicMock()
    item.preset_id = preset_id
    item.name = preset_id
    item.description = f"Description for {preset_id}"
    item.questions = []
    return item


def _record(status: str = "pending") -> MagicMock:
    record = MagicMock()
    record.status.value = status
    return record


class TestWatchBehavior:
    def test_runs_show_watch_waits_for_completion(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-watch"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        record = MagicMock()
        record.status = RunStatus.COMPLETED
        with patch("interfaces.cli.product_commands._RUN_EXECUTOR.get", return_value=record):
            result = runner.invoke(app, ["runs", "show", "run-watch", "--repo", str(tmp_path), "--watch"])
        assert result.exit_code == 0, result.output
        assert "status: completed" in result.output

    def test_use_watch_waits_for_completion(self, tmp_path: Path) -> None:
        env = _env(tmp_path)
        preset = MagicMock()
        preset.validate_inputs.return_value = {"task": "Fix bug", "repo": str(tmp_path)}
        record = MagicMock()
        record.status = RunStatus.COMPLETED
        view = RunView(
            run_id="run-use-watch",
            status="completed",
            summary="Done",
            artifact_dir=str(tmp_path / ".ai-team" / "runs" / "run-use-watch"),
            next_actions=["agentheim runs show run-use-watch"],
        )
        with patch("interfaces.cli.product_commands.PRESET_REGISTRY.get", return_value=preset), patch(
            "interfaces.cli.product_commands.CATALOG.get", return_value=_catalog_item("codebase-assistant")
        ), patch(
            "interfaces.cli.product_commands._run_preset_sync", return_value=view
        ):
            result = runner.invoke(
                app,
                ["use", "code", "--input", "task=Fix bug", "--repo", str(tmp_path), "--yes", "--watch"],
                env=env,
            )
        assert result.exit_code == 0, result.output
        assert "run id: run-use-watch" in result.output
        assert "status: completed" in result.output


class TestCliApiWebConsistency:
    def test_cli_runs_show_matches_run_view_schema(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-consistency"
        _write_run_json(run_dir, workflow_id="coding", preset_id="codebase-assistant")
        _write_final_report(run_dir, "completed", task_summary="Consistent")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        result = runner.invoke(app, ["runs", "show", "run-consistency", "--repo", str(tmp_path), "--json"])
        assert result.exit_code == 0, result.output
        cli_payload = json.loads(result.output)

        view = build_run_view(tmp_path, "run-consistency")
        view_payload = view.model_dump(mode="json")

        assert cli_payload == view_payload

    def test_canonical_summary_has_same_report_and_artifact_as_run_view(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-match"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        summary = build_run_summary(tmp_path, "run-match")
        view = build_run_view(tmp_path, "run-match")

        assert summary.report_path == view.report_path
        assert summary.artifact_dir == view.artifact_dir
        assert summary.status == view.status
        assert summary.summary == view.summary

    def test_list_run_views_matches_individual_build(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "run-list"
        _write_run_json(run_dir, workflow_id="coding")
        _write_final_report(run_dir, "completed")
        _write_ledger_with_initiated(run_dir, workflow_id="coding")

        views = list_run_views(tmp_path)
        assert len(views) == 1
        single = build_run_view(tmp_path, "run-list")
        assert views[0].model_dump(mode="json") == single.model_dump(mode="json")
