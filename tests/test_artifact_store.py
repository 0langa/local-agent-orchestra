"""Tests for core/artifact_store.py — schema-managed artifact directory."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.artifact_store import ArtifactStore, RUN_ARTIFACTS


class TestArtifactStoreCreate:
    def test_create_run_makes_directory(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "test"
        store = ArtifactStore.create_run(run_dir, workflow_id="wf1", preset_id="p1")
        assert run_dir.exists()
        assert isinstance(store, ArtifactStore)

    def test_create_run_produces_run_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "test"
        store = ArtifactStore.create_run(run_dir, workflow_id="wf1", preset_id="p1")
        path = run_dir / "run.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["workflow_id"] == "wf1"
        assert data["preset_id"] == "p1"
        assert data["status"] == "initiated"

    def test_create_run_produces_config_redacted(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "runs" / "test"
        config = {"secret": "API_KEY=secret12345678", "endpoint": "http://test"}
        ArtifactStore.create_run(run_dir, config=config)
        path = run_dir / "config.redacted.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "REDACTED" in data["secret"]
        assert data["endpoint"] == "http://test"


class TestArtifactStoreValidation:
    def test_empty_run_is_not_complete(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path)
        missing = store.validate_completeness()
        assert len(missing) > 0

    def test_fresh_create_run_is_not_complete(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        store = ArtifactStore.create_run(run_dir)
        missing = store.validate_completeness()
        # Missing: context_bundle.md, context_manifest.json, ledger.jsonl, ledger.index, ledger.hash, checkpoints/
        assert len(missing) > 0

    def test_complete_run(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        store = ArtifactStore.create_run(run_dir)

        # Produce remaining required artifacts
        store.produce_context_artifacts("# bundle", {"files": []})
        (run_dir / "ledger.jsonl").write_text('{"event": "test"}\n', encoding="utf-8")
        (run_dir / "ledger.index").write_text('{}', encoding="utf-8")
        (run_dir / "ledger.hash").write_text("abcd" * 16 + "\n", encoding="utf-8")
        (run_dir / "checkpoints").mkdir(exist_ok=True)

        missing = store.validate_completeness()
        assert missing == []
        assert store.is_complete()

    def test_invalid_json_detected(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        store = ArtifactStore.create_run(run_dir)
        (run_dir / "run.json").write_text("not json", encoding="utf-8")
        missing = store.validate_completeness()
        assert any("run.json (invalid" in m for m in missing)

    def test_invalid_jsonl_detected(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        store = ArtifactStore.create_run(run_dir)
        (run_dir / "ledger.jsonl").write_text("not json\n", encoding="utf-8")
        missing = store.validate_completeness()
        assert any("ledger.jsonl (invalid" in m for m in missing)

    def test_missing_checkpoints_directory(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        store = ArtifactStore.create_run(run_dir)
        # All other required artifacts
        store.produce_context_artifacts("# bundle", {"files": []})
        (run_dir / "ledger.jsonl").write_text('{"event": "test"}\n', encoding="utf-8")
        (run_dir / "ledger.index").write_text('{}', encoding="utf-8")
        (run_dir / "ledger.hash").write_text("abcd" * 16 + "\n", encoding="utf-8")
        # No checkpoints directory
        missing = store.validate_completeness()
        assert any("checkpoints" in m for m in missing)


class TestArtifactStoreProducers:
    def test_produce_context_artifacts(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path)
        bundle_path, manifest_path = store.produce_context_artifacts("# Hello", {"x": 1})
        assert bundle_path.exists()
        assert manifest_path.exists()
        assert bundle_path.read_text(encoding="utf-8") == "# Hello"
        assert json.loads(manifest_path.read_text(encoding="utf-8")) == {"x": 1}

    def test_produce_plan(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path)
        path = store.produce_plan("# Plan\n\n1. Do thing")
        assert path.exists()
        assert path.name == "plan.md"

    def test_produce_final_report(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path)
        path = store.produce_final_report("# Report\n\nAll good.")
        assert path.exists()
        assert path.name == "final_report.md"

    def test_produce_verification(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path)
        path = store.produce_verification({"passed": True})
        assert path.exists()
        assert json.loads(path.read_text(encoding="utf-8")) == {"passed": True}

    def test_produce_patch(self, tmp_path: Path) -> None:
        store = ArtifactStore(tmp_path)
        path = store.produce_patch("diff --git a/file.txt b/file.txt\n+hello")
        assert path.exists()
        assert path.name == "patch.diff"


class TestArtifactStoreList:
    def test_list_artifacts(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run"
        store = ArtifactStore.create_run(run_dir)
        artifacts = store.list_artifacts()
        assert artifacts["run.json"] is True
        assert artifacts["config.redacted.json"] is True
        assert artifacts["final_report.md"] is False

    def test_run_artifacts_count(self) -> None:
        assert len(RUN_ARTIFACTS) == 17
        required = [a for a in RUN_ARTIFACTS if a.required]
        assert len(required) == 8  # run.json, config.redacted.json, context_bundle.md, context_manifest.json, ledger.jsonl, ledger.index, ledger.hash, checkpoints
