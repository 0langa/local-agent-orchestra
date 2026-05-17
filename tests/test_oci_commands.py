"""CLI help tests for the ``agentheim ctx oci`` namespace."""

from __future__ import annotations

from typer.testing import CliRunner

from interfaces.cli.cli import app

runner = CliRunner()


def test_oci_doctor_help() -> None:
    result = runner.invoke(app, ["ctx", "oci", "doctor", "--help"])
    assert result.exit_code == 0
    assert "--project" in result.output


def test_oci_snapshot_create_help() -> None:
    result = runner.invoke(app, ["ctx", "oci", "snapshot", "create", "--help"])
    assert result.exit_code == 0
    assert "--project" in result.output


def test_oci_bundle_create_help() -> None:
    result = runner.invoke(app, ["ctx", "oci", "bundle", "create", "--help"])
    assert result.exit_code == 0
    assert "--project" in result.output
    assert "--run-id" in result.output
