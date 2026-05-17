"""Tests for M6 path migration in AictxContextOps."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentheim.context_ops import CleanResult, ContextPlan, GeneratedContext
from agentheim.context_ops_impl import AictxContextOps
from agentheim.vendor.aictx.models.inventory import FileEntry, RepositoryInventory
from agentheim.vendor.aictx.verify.verifier import determine_changed_source_paths


class TestWriteUsesAiTeamRuns:
    def test_write_uses_ai_team_runs(self, tmp_path: Path) -> None:
        ops = AictxContextOps()
        context = GeneratedContext(
            plan=ContextPlan(raw={"selected_files": ["a.py"]}),
            repo_root=tmp_path,
        )

        mock_inventory = MagicMock()
        mock_lock = MagicMock()

        with (
            patch("agentheim.context_ops_impl.scan_repository", return_value=mock_inventory),
            patch("agentheim.context_ops_impl.write_context_scaffold", return_value=[]),
            patch("agentheim.context_ops_impl.build_context_lock", return_value=mock_lock),
            patch("agentheim.context_ops_impl.write_lockfile") as mock_write_lockfile,
            patch("agentheim.vendor.aictx.context.pipeline._build_patch", return_value="patch text"),
            patch("agentheim.vendor.aictx.io.files.safe_write") as mock_safe_write,
        ):
            report = ops.write(tmp_path, context)

        ai_team_runs = tmp_path / ".ai-team" / "runs" / "agentheim-ctx"
        assert ai_team_runs.exists()
        assert (ai_team_runs / "out").exists()
        assert report.lockfile_path.endswith("context.lock.json")
        mock_write_lockfile.assert_called_once()
        mock_safe_write.assert_called_once()


class TestCleanUsesAiTeamRuns:
    def test_clean_uses_ai_team_runs(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / ".ai-team" / "runs"
        run1 = runs_dir / "run1"
        run2 = runs_dir / "run2"
        run1.mkdir(parents=True)
        run2.mkdir(parents=True)
        (run1 / "file.txt").write_text("keep", encoding="utf-8")

        ops = AictxContextOps()
        result = ops.clean(tmp_path, keep_runs=0)

        assert not run1.exists()
        assert not run2.exists()
        assert result.removed_count == 2
        assert sorted(result.removed_paths) == ["run1", "run2"]
        assert result.kept_count == 0

    def test_clean_with_run_id(self, tmp_path: Path) -> None:
        runs_dir = tmp_path / ".ai-team" / "runs"
        run1 = runs_dir / "run1"
        run2 = runs_dir / "run2"
        run1.mkdir(parents=True)
        run2.mkdir(parents=True)

        ops = AictxContextOps()
        result = ops.clean(tmp_path, run_id="run1")

        assert not run1.exists()
        assert run2.exists()
        assert result.removed_count == 1
        assert result.removed_paths == ["run1"]
        assert result.kept_count == 1


class TestCleanIgnoresAictxRuns:
    def test_clean_ignores_aictx_runs(self, tmp_path: Path) -> None:
        aictx_runs = tmp_path / ".aictx" / "runs"
        legacy_run = aictx_runs / "legacy-run"
        legacy_run.mkdir(parents=True)
        (legacy_run / "artifact.json").write_text("{}", encoding="utf-8")

        ai_team_runs = tmp_path / ".ai-team" / "runs"
        ai_run = ai_team_runs / "ai-run"
        ai_run.mkdir(parents=True)

        ops = AictxContextOps()
        result = ops.clean(tmp_path, keep_runs=0)

        # M6: legacy .aictx/runs/ is also cleaned during migration
        assert not legacy_run.exists()
        assert not ai_run.exists()
        assert result.removed_count == 2
        assert "ai-run" in result.removed_paths


class TestRuntimeArtifactsExcludedFromChanged:
    """AH-AUDIT-002: .ai-team and other runtime artifacts must not poison changed-file detection."""

    def _inventory(self, files: list[FileEntry]) -> RepositoryInventory:
        return RepositoryInventory(
            repo_root=".",
            branch="main",
            head_commit="abc123",
            dirty_state=False,
            git_status={"is_dirty": False, "tracked_files": [], "untracked_files": [], "modified_files": [], "deleted_files": [], "renamed_files": []},
            files=files,
        )

    def _entry(self, path: str, sha256: str = "abc123", **kwargs: object) -> FileEntry:
        return FileEntry(
            path=path,
            kind="source",
            size_bytes=1,
            sha256=sha256,
            is_source=True,
            **kwargs,
        )

    def test_ai_team_files_excluded(self) -> None:
        inventory = self._inventory(
            files=[
                self._entry("src/main.py"),
                self._entry(".ai-team/runs/inspect/repo_snapshot.json"),
                self._entry(".ai-team/memory/state.json"),
            ],
        )
        changed = determine_changed_source_paths(inventory, lock=None)
        assert changed == ["src/main.py"]

    def test_aictx_files_excluded(self) -> None:
        inventory = self._inventory(
            files=[
                self._entry("src/main.py"),
                self._entry(".aictx/runs/2024-01-01/context.json"),
            ],
        )
        changed = determine_changed_source_paths(inventory, lock=None)
        assert changed == ["src/main.py"]

    def test_pytest_cache_and_coverage_excluded(self) -> None:
        inventory = self._inventory(
            files=[
                self._entry("src/main.py"),
                self._entry(".pytest_cache/v/cache/nodeids"),
                self._entry(".coverage"),
            ],
        )
        changed = determine_changed_source_paths(inventory, lock=None)
        assert changed == ["src/main.py"]

    def test_normal_source_included(self) -> None:
        inventory = self._inventory(
            files=[
                self._entry("src/main.py"),
                self._entry("tests/test_main.py"),
            ],
        )
        changed = determine_changed_source_paths(inventory, lock=None)
        assert sorted(changed) == ["src/main.py", "tests/test_main.py"]
