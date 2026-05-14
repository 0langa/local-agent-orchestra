"""Tests for AictxContextOps M2 implementation.

Covers scan, plan, generate, write, verify, status, public_docs_impact,
plus M2.5 additions: init, clean, run_pipeline, public_docs_update.
Uses dry_run LLM provider to avoid network calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

from agentheim.vendor.aictx.config import AictxConfig
from agentheim.vendor.aictx.llm.dry_run import DryRunProvider

from agentheim.context_ops_impl import AictxContextOps

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def ops() -> AictxContextOps:
    config = AictxConfig()
    config.llm.provider = "dry_run"
    config.llm.model = "dry_run"
    return AictxContextOps(config=config)


# ------------------------------------------------------------------
# init
# ------------------------------------------------------------------


def test_init_creates_lockfile(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "init_repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")
    import subprocess
    subprocess.run(["git", "init", str(repo)], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=False, capture_output=True)

    ops.init(repo)
    assert (repo / ".aictxignore").exists()
    assert (repo / "docs" / "AIprojectcontext" / "context.lock.json").exists()


# ------------------------------------------------------------------
# clean
# ------------------------------------------------------------------


def test_clean_by_run_id(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "clean_repo"
    repo.mkdir()
    runs_dir = repo / ".ai-team" / "runs"
    runs_dir.mkdir(parents=True)
    (runs_dir / "run-a").mkdir()
    (runs_dir / "run-b").mkdir()

    result = ops.clean(repo, run_id="run-a")
    assert result.removed_count == 1
    assert result.removed_paths == ["run-a"]
    assert result.kept_count == 1
    assert not (runs_dir / "run-a").exists()
    assert (runs_dir / "run-b").exists()


def test_clean_keep_runs(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "clean_repo"
    repo.mkdir()
    runs_dir = repo / ".ai-team" / "runs"
    runs_dir.mkdir(parents=True)
    (runs_dir / "run-1").mkdir()
    (runs_dir / "run-2").mkdir()
    (runs_dir / "run-3").mkdir()

    result = ops.clean(repo, keep_runs=1)
    assert result.removed_count == 2
    assert result.kept_count == 1
    assert (runs_dir / "run-3").exists()


def test_clean_no_runs_dir(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "clean_repo"
    repo.mkdir()
    result = ops.clean(repo, keep_runs=0)
    assert result.removed_count == 0
    assert result.kept_count == 0


def test_clean_requires_run_id_or_keep(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "clean_repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="clean requires"):
        ops.clean(repo)


# ------------------------------------------------------------------
# scan
# ------------------------------------------------------------------


def test_scan_returns_inventory(ops: AictxContextOps) -> None:
    inventory = ops.scan(REPO_ROOT)
    assert inventory.raw is not None
    assert inventory.repo_root == str(REPO_ROOT)
    assert len(inventory.raw.files) > 0


def test_inventory_has_manifests_and_docs(ops: AictxContextOps) -> None:
    inventory = ops.scan(REPO_ROOT)
    assert len(inventory.raw.manifests) > 0
    assert any(m.path == "pyproject.toml" for m in inventory.raw.manifests)
    assert len(inventory.raw.docs) > 0


# ------------------------------------------------------------------
# plan
# ------------------------------------------------------------------


def test_plan_returns_selected_files(ops: AictxContextOps) -> None:
    inventory = ops.scan(REPO_ROOT)
    plan = ops.plan(inventory, scope="full")
    assert len(plan.selected_files) > 0
    assert "pyproject.toml" in plan.selected_files or any(
        "pyproject" in f for f in plan.selected_files
    )


def test_plan_changed_scope(ops: AictxContextOps) -> None:
    inventory = ops.scan(REPO_ROOT)
    plan = ops.plan(inventory, scope="changed")
    # With no existing lockfile, changed scope falls back to changed_files=[]
    # so it may be empty or minimal
    assert isinstance(plan.selected_files, list)


# ------------------------------------------------------------------
# generate
# ------------------------------------------------------------------


def test_generate_with_dry_run(ops: AictxContextOps) -> None:
    inventory = ops.scan(REPO_ROOT)
    plan = ops.plan(inventory, scope="full")
    provider = DryRunProvider()
    context = ops.generate(REPO_ROOT, plan, provider=provider)
    assert len(context.fact_packs) > 0
    assert all("name" in pack for pack in context.fact_packs)


# ------------------------------------------------------------------
# write
# ------------------------------------------------------------------


def test_write_generates_files(ops: AictxContextOps, tmp_path: Path) -> None:
    # Use a minimal synthetic repo to avoid polluting the real one
    repo = tmp_path / "synthetic"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")
    (repo / "pyproject.toml").write_text('[project]\nname = "test"\n')
    src = repo / "src"
    src.mkdir()
    (src / "main.py").write_text("def main(): pass\n")
    import subprocess
    subprocess.run(["git", "init", str(repo)], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=False, capture_output=True)

    inventory = ops.scan(repo)
    plan = ops.plan(inventory, scope="full")
    provider = DryRunProvider()
    context = ops.generate(repo, plan, provider=provider)
    report = ops.write(repo, context, write_mode="patch")

    assert len(report.generated_files) > 0
    assert any("context.lock.json" in f for f in report.generated_files)
    assert report.patch_text is not None


# ------------------------------------------------------------------
# run_pipeline
# ------------------------------------------------------------------


def test_run_pipeline_end_to_end(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "pipeline_repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")
    (repo / "pyproject.toml").write_text('[project]\nname = "test"\n')
    src = repo / "src"
    src.mkdir()
    (src / "main.py").write_text("def main(): pass\n")
    import subprocess
    subprocess.run(["git", "init", str(repo)], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=False, capture_output=True)

    report = ops.run_pipeline(repo, run_id="test-run", scope="full", write_mode="patch")

    assert len(report.generated_files) > 0
    assert any("context.lock.json" in f for f in report.generated_files)
    # M2.5 telemetry enrichment
    assert report.run_report is not None
    assert report.timing is not None
    assert report.timing.total_duration_ms > 0
    assert report.entropy is not None


# ------------------------------------------------------------------
# verify
# ------------------------------------------------------------------


def test_verify_without_lockfile(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "no_lock"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")

    result = ops.verify(repo, strict=False)
    assert result.result == "FAIL_LOCK_MISMATCH"
    assert result.is_pass is False


def test_verify_with_lockfile(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "with_lock"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")
    import subprocess
    subprocess.run(["git", "init", str(repo)], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=False, capture_output=True)

    # Generate context first to create lockfile
    inventory = ops.scan(repo)
    plan = ops.plan(inventory, scope="full")
    provider = DryRunProvider()
    context = ops.generate(repo, plan, provider=provider)
    ops.write(repo, context, write_mode="apply")

    result = ops.verify(repo, strict=False)
    assert result.result == "PASS"
    assert result.is_pass is True


# ------------------------------------------------------------------
# status
# ------------------------------------------------------------------


def test_status_without_lockfile(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "status_no_lock"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")

    status = ops.status(repo, strict=False)
    assert status.is_stale is True
    assert status.next_command is not None


# ------------------------------------------------------------------
# public_docs_impact
# ------------------------------------------------------------------


def test_public_docs_impact(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "docs_repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")
    docs = repo / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n")
    import subprocess
    subprocess.run(["git", "init", str(repo)], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=False, capture_output=True)

    report = ops.public_docs_impact(repo, scope="full")
    assert len(report.entries) > 0


# ------------------------------------------------------------------
# public_docs_update
# ------------------------------------------------------------------


def test_public_docs_update_no_lockfile(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "pubdocs_repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")

    with pytest.raises(Exception):
        ops.public_docs_update(repo, scope="changed")


def test_public_docs_update_with_lockfile(ops: AictxContextOps, tmp_path: Path) -> None:
    repo = tmp_path / "pubdocs_repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Test\n")
    docs = repo / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n")
    import subprocess
    subprocess.run(["git", "init", str(repo)], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test.com"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=False, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=False, capture_output=True)

    # init to create lockfile
    ops.init(repo)
    patch_path = ops.public_docs_update(repo, scope="full", write_mode="patch")
    assert patch_path is not None
    assert patch_path.exists()
