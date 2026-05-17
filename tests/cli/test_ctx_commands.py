"""CLI help tests for the ``agentheim ctx`` namespace."""

from __future__ import annotations

from typing import Any
from typer.testing import CliRunner

from interfaces.cli.cli import app

runner = CliRunner()


def _assert_help(result: Any, *terms: str) -> None:
    assert result.exit_code == 0
    output = result.output.lower()
    assert "usage:" in output
    for term in terms:
        assert term.lower() in output


class TestCtxHelp:
    def test_ctx_help(self) -> None:
        result = runner.invoke(app, ["ctx", "--help"])
        _assert_help(result, "context operations")

    def test_ctx_init_help(self) -> None:
        result = runner.invoke(app, ["ctx", "init", "--help"])
        _assert_help(result, "initialize")

    def test_ctx_scan_help(self) -> None:
        result = runner.invoke(app, ["ctx", "scan", "--help"])
        _assert_help(result, "scan")

    def test_ctx_run_help(self) -> None:
        result = runner.invoke(app, ["ctx", "run", "--help"])
        _assert_help(result, "run")

    def test_ctx_verify_help(self) -> None:
        result = runner.invoke(app, ["ctx", "verify", "--help"])
        _assert_help(result, "verify")

    def test_ctx_status_help(self) -> None:
        result = runner.invoke(app, ["ctx", "status", "--help"])
        _assert_help(result, "status")

    def test_ctx_clean_help(self) -> None:
        result = runner.invoke(app, ["ctx", "clean", "--help"])
        _assert_help(result, "clean")

    def test_ctx_public_docs_impact_help(self) -> None:
        result = runner.invoke(app, ["ctx", "public-docs", "impact", "--help"])
        _assert_help(result, "impact")

    def test_ctx_public_docs_update_help(self) -> None:
        result = runner.invoke(app, ["ctx", "public-docs", "update", "--help"])
        _assert_help(result, "update")

    def test_ctx_oci_help(self) -> None:
        result = runner.invoke(app, ["ctx", "oci", "--help"])
        _assert_help(result, "doctor", "snapshot", "bundle")
