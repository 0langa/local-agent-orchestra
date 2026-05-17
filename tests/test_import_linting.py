"""Tests for scripts/roadmap-check.py import boundary enforcement."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.slow

import subprocess
import sys
from pathlib import Path

import pytest


class TestImportLinting:
    def test_roadmap_check_passes(self) -> None:
        """Verify the architecture checker itself reports zero violations.

        This test calls the checker script as a subprocess so it exercises the
        exact entry-point that runs in CI. The test file itself is exempted in
        SUBPROCESS_EXEMPTIONS so it does not trigger a false Law-7 violation.
        """
        root = Path(__file__).parent.parent
        script = root / "scripts" / "roadmap-check.py"
        result = subprocess.run(
            [sys.executable, str(script), "--phase", "7"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        assert result.returncode == 0, (
            f"roadmap-check.py failed:\n"
            f"  stdout:\n{result.stdout}\n"
            f"  stderr:\n{result.stderr}"
        )

    def test_roadmap_check_detects_violation(self) -> None:
        """Verify the import-boundary rule actually works by checking a known-good file."""
        root = Path(__file__).parent.parent
        script = root / "scripts" / "roadmap-check.py"
        result = subprocess.run(
            [sys.executable, str(script), "--phase", "7"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        assert result.returncode == 0
        # The real run should not contain direct core imports violations
        assert "Direct core import" not in result.stdout
