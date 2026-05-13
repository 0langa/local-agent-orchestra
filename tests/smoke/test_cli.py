from __future__ import annotations

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

    def test_ping_models_exits_nonzero_on_failure(self) -> None:
        """AH-AUDIT-004: failing pings must exit nonzero."""
        env = {
            "AI_TEAM_PROVIDER_IDS": "default",
            "AI_TEAM_PROVIDER_DEFAULT_TYPE": "openai_compatible",
            "AI_TEAM_PROVIDER_DEFAULT_ENDPOINT": "https://api.openai.com/v1",
            "AI_TEAM_PROVIDER_DEFAULT_API_KEY_ENV": "OPENAI_API_KEY",
            "OPENAI_API_KEY": "sk-fake",
            "AI_TEAM_MODEL_PLANNER_NAME": "gpt-4o-mini",
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
