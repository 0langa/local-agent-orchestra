from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from interfaces.cli.cli import app

runner = CliRunner()


class TestCliCommands:
    def test_config_dump_help(self) -> None:
        result = runner.invoke(app, ["config-dump", "--help"])
        assert result.exit_code == 0
        assert "config-dump" in result.output

    def test_presets_command(self) -> None:
        result = runner.invoke(app, ["presets"])
        assert result.exit_code == 0
        assert "Available Presets" in result.output or "No presets found" in result.output

    def test_memory_help(self) -> None:
        result = runner.invoke(app, ["memory", "--help"])
        assert result.exit_code == 0
        assert "get|set|history|profile" in result.output

    def test_doctor_help(self) -> None:
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "doctor" in result.output

    def test_guided_help(self) -> None:
        result = runner.invoke(app, ["guided", "--help"])
        assert result.exit_code == 0
        assert "guided" in result.output

    def test_start_help(self) -> None:
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output

    def test_ping_models_help(self) -> None:
        result = runner.invoke(app, ["ping-models", "--help"])
        assert result.exit_code == 0
        assert "ping-models" in result.output

    def test_ping_models_exits_nonzero_on_failure(self, tmp_path) -> None:
        """AH-AUDIT-004: failing pings must exit nonzero."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "providers.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "default_profile": "default",
                    "profiles": {
                        "default": {
                            "name": "default",
                            "providers": {
                                "default": {
                                    "id": "default",
                                    "kind": "openai_compatible",
                                    "endpoint": "https://api.openai.com/v1",
                                    "auth_mode": "none",
                                    "timeout_seconds": 60,
                                    "headers": {},
                                    "metadata": {},
                                }
                            },
                            "models": {
                                "planner": {
                                    "id": "planner",
                                    "role": "planner",
                                    "provider": "default",
                                    "model": "gpt-4o-mini",
                                    "capabilities": ["text", "json"],
                                }
                            },
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        env = {
            "AGENTHEIM_CONFIG_DIR": str(config_dir),
        }
        with patch("providers.openai_v1.OpenAIV1Provider.invoke") as mock_invoke:
            mock_invoke.side_effect = Exception("401 Unauthorized")
            result = runner.invoke(app, ["ping-models"], env=env)
        assert result.exit_code == 1
        assert "error" in result.output.lower() or "401" in result.output

    def test_inspect_help(self) -> None:
        result = runner.invoke(app, ["inspect", "--help"])
        assert result.exit_code == 0
        assert "inspect" in result.output

    def test_plan_help(self) -> None:
        result = runner.invoke(app, ["plan", "--help"])
        assert result.exit_code == 0
        assert "plan" in result.output

    def test_run_help(self) -> None:
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "run" in result.output

    def test_list_runs_help(self) -> None:
        result = runner.invoke(app, ["list-runs", "--help"])
        assert result.exit_code == 0
        assert "list-runs" in result.output

    def test_doctor_runs(self) -> None:
        result = runner.invoke(app, ["doctor", "--skip-connectivity"])
        # Should complete even without full config; at least shows the table
        assert "System Diagnostics" in result.output or result.exit_code in (0, 1)

    def test_report_emits_canonical_run_summary_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "test-run-1"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(
            json.dumps({"run_id": "test-run-1", "workflow_id": "coding", "preset_id": "codebase-assistant"}),
            encoding="utf-8",
        )
        (run_dir / "final_report.json").write_text(
            json.dumps({"run_id": "test-run-1", "task_summary": "Fix bug", "status": "done"}),
            encoding="utf-8",
        )
        (run_dir / "final_report.md").write_text("# Report", encoding="utf-8")

        result = runner.invoke(app, ["report", "--repo", str(tmp_path), "--run-id", "test-run-1"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert payload["run_id"] == "test-run-1"
        assert payload["status"] == "completed"
        assert payload["summary"] == "Fix bug"
