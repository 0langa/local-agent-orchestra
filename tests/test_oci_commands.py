"""CLI help tests for the ``agentheim ctx oci`` namespace."""

from __future__ import annotations

from typer.testing import CliRunner

from interfaces.cli.cli import app

runner = CliRunner()


def _assert_help(result, *terms: str) -> None:
    assert result.exit_code == 0
    output = result.output.lower()
    assert "usage:" in output
    for term in terms:
        assert term.lower() in output


def test_oci_doctor_help() -> None:
    result = runner.invoke(app, ["ctx", "oci", "doctor", "--help"])
    _assert_help(result, "doctor")


def test_oci_snapshot_create_help() -> None:
    result = runner.invoke(app, ["ctx", "oci", "snapshot", "create", "--help"])
    _assert_help(result, "create")


def test_oci_bundle_create_help() -> None:
    result = runner.invoke(app, ["ctx", "oci", "bundle", "create", "--help"])
    _assert_help(result, "create")
