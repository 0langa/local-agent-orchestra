"""CLI help tests for the ``agentheim ctx`` namespace."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from interfaces.cli.cli import app

runner = CliRunner()


class TestCtxHelp:
    def test_ctx_help(self) -> None:
        result = runner.invoke(app, ["ctx", "--help"])
        assert result.exit_code == 0
        assert "context operations" in result.output.lower()

    def test_ctx_init_help(self) -> None:
        result = runner.invoke(app, ["ctx", "init", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output

    def test_ctx_scan_help(self) -> None:
        result = runner.invoke(app, ["ctx", "scan", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output

    def test_ctx_run_help(self) -> None:
        result = runner.invoke(app, ["ctx", "run", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--scope" in result.output

    def test_ctx_verify_help(self) -> None:
        result = runner.invoke(app, ["ctx", "verify", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--strict" in result.output

    def test_ctx_status_help(self) -> None:
        result = runner.invoke(app, ["ctx", "status", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--strict" in result.output

    def test_ctx_clean_help(self) -> None:
        result = runner.invoke(app, ["ctx", "clean", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--run-id" in result.output

    def test_ctx_public_docs_impact_help(self) -> None:
        result = runner.invoke(app, ["ctx", "public-docs", "impact", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--scope" in result.output

    def test_ctx_public_docs_update_help(self) -> None:
        result = runner.invoke(app, ["ctx", "public-docs", "update", "--help"])
        assert result.exit_code == 0
        assert "--project" in result.output
        assert "--scope" in result.output

    def test_ctx_oci_help(self) -> None:
        result = runner.invoke(app, ["ctx", "oci", "--help"])
        assert result.exit_code == 0
        output = result.output.lower()
        assert "doctor" in output
        assert "snapshot" in output
        assert "bundle" in output
