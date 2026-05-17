"""Phase 7: Packaging and installation tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import tomllib

from typer.testing import CliRunner

from interfaces.cli.cli import app

runner = CliRunner()


class TestPyprojectMetadata:
    def test_version_is_v1(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "1.0.0"' in pyproject

    def test_has_maintainers(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        assert "maintainers" in pyproject

    def test_has_end_user_and_developer_classifiers(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(pyproject)
        classifiers = data["project"]["classifiers"]
        assert "Development Status :: 5 - Production/Stable" in classifiers
        assert any("End Users" in c for c in classifiers)
        assert any("Developers" in c for c in classifiers)

    def test_spdx_license_metadata(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(pyproject)
        assert data["project"].get("license") == "MIT"
        assert data["project"].get("license-files") == ["LICENSE"]
        assert not any("License :: OSI Approved" in c for c in data["project"]["classifiers"])

    def test_runtime_dependencies_are_bounded(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(pyproject)
        deps = data["project"]["dependencies"]
        for dep in deps:
            assert "," in dep, f"Dependency '{dep}' should have an upper bound"

    def test_optional_dependencies_are_bounded(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(pyproject)
        extras = data["project"]["optional-dependencies"]
        for extra, deps in extras.items():
            for dep in deps:
                assert "," in dep, f"Optional dependency '{dep}' in extra '{extra}' should have an upper bound"

    def test_extras_defined(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(pyproject)
        extras = data["project"]["optional-dependencies"]
        required = {"web", "desktop", "browser", "mcp", "cloud-aws", "cloud-google", "cloud-oci", "dev"}
        assert required.issubset(set(extras.keys())), f"Missing extras: {required - set(extras.keys())}"

    def test_single_cli_script_entrypoint(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(pyproject)
        scripts = data["project"]["scripts"]
        assert "agentheim" in scripts
        assert scripts["agentheim"] == "interfaces.cli.cli:main"
        assert len(scripts) == 1

    def test_requires_python_is_3_12_plus(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
        data = tomllib.loads(pyproject)
        assert data["project"]["requires-python"] == ">=3.12"


@pytest.mark.slow
class TestBuildArtifacts:
    def test_wheel_builds(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        wheels = list(tmp_path.glob("*.whl"))
        assert len(wheels) == 1
        assert wheels[0].name.startswith("agentheim-")

    def test_sdist_builds(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--sdist", "--outdir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        sdists = list(tmp_path.glob("*.tar.gz"))
        assert len(sdists) == 1
        assert sdists[0].name.startswith("agentheim-")


class TestCliHelpSmoke:
    def test_agentheim_help_runs(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0, result.output
        assert "agentheim" in result.output.lower()

    def test_agentheim_status_json_runs(self) -> None:
        env = {
            "AGENTHEIM_CONFIG_DIR": "/tmp/agentheim-test-config",
            "AGENTHEIM_DATA_DIR": "/tmp/agentheim-test-data",
        }
        with patch("interfaces.cli.product_commands.build_readiness_state") as readiness:
            from interfaces.readiness import ReadinessState, ReadinessStatus
            readiness.return_value = ReadinessState(
                status=ReadinessStatus.needs_provider,
                next_actions=["Run agentheim setup"],
            )
            result = runner.invoke(app, ["status", "--json"], env=env)
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "status" in payload


class TestMockedFirstRunSmoke:
    def test_setup_status_use_runs_chain(self) -> None:
        """Simulate a first-run chain: setup -> status -> use --help."""
        env = {
            "AGENTHEIM_CONFIG_DIR": "/tmp/agentheim-test-config",
            "AGENTHEIM_DATA_DIR": "/tmp/agentheim-test-data",
        }
        with patch("interfaces.cli.product_commands.build_readiness_state") as readiness:
            from interfaces.readiness import ReadinessState, ReadinessStatus
            readiness.return_value = ReadinessState(
                status=ReadinessStatus.ready,
                next_actions=["Run agentheim use"],
            )
            result = runner.invoke(app, ["setup", "--help"], env=env)
            assert result.exit_code == 0
            result = runner.invoke(app, ["status", "--help"], env=env)
            assert result.exit_code == 0
            result = runner.invoke(app, ["use", "--help"], env=env)
            assert result.exit_code == 0
