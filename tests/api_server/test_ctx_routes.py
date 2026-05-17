"""API route tests for AICtx context operations."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from interfaces.api_server.app import create_api_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    mock_ops = MagicMock()
    mock_ops.init.return_value = None
    mock_inventory = MagicMock()
    mock_inventory.repo_root = str(tmp_path)
    mock_inventory.head_commit = "abc123"
    raw = MagicMock()
    raw.files = ["a.py", "b.py"]
    raw.manifests = ["manifest.json"]
    raw.branch = "main"
    raw.dirty_state = False
    mock_inventory.raw = raw
    mock_ops.scan.return_value = mock_inventory
    mock_ops.run_pipeline.return_value = MagicMock(
        generated_files=[],
        patch_text="",
        timing={},
        entropy={},
    )
    mock_ops.verify.return_value = MagicMock(
        result="PASS",
        is_pass=True,
    )
    mock_ops.status.return_value = MagicMock(
        is_stale=False,
        stale_sources=[],
        missing_sources=[],
        generated_mismatches=[],
        missing_generated=[],
        next_command=None,
    )
    mock_ops.clean.return_value = MagicMock(
        removed_count=0,
        kept_count=0,
        removed_paths=[],
    )
    mock_ops.public_docs_impact.return_value = MagicMock(
        entries=[],
    )
    mock_ops.public_docs_update.return_value = None

    with patch("interfaces.api_server.app.AictxContextOps") as MockClass:
        MockClass.return_value = mock_ops
        app = create_api_app(repo_root=tmp_path)
        yield TestClient(app)


class TestCtxRoutes:
    def test_ctx_init_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post("/api/ctx/init", json={"project": str(tmp_path)})
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ctx_scan_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post("/api/ctx/scan", json={"project": str(tmp_path)})
        assert response.status_code == 200
        data = response.json()
        assert data["repo_root"] == str(tmp_path)
        assert data["head_commit"] == "abc123"
        assert data["branch"] == "main"
        assert data["dirty_state"] is False
        assert data["file_count"] == 2
        assert data["manifest_count"] == 1

    def test_ctx_run_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post("/api/ctx/run", json={"project": str(tmp_path)})
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "generated_files" in data

    def test_ctx_verify_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post("/api/ctx/verify", json={"project": str(tmp_path)})
        assert response.status_code == 200
        data = response.json()
        assert data["is_pass"] is True
        assert data["result"] == "PASS"

    def test_ctx_status_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post("/api/ctx/status", json={"project": str(tmp_path)})
        assert response.status_code == 200
        data = response.json()
        assert data["is_stale"] is False

    def test_ctx_clean_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post(
            "/api/ctx/clean",
            json={"project": str(tmp_path), "keep_runs": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert "removed_count" in data
        assert "kept_count" in data

    def test_ctx_public_docs_impact_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post(
            "/api/ctx/public-docs/impact",
            json={"project": str(tmp_path)},
        )
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data

    def test_ctx_public_docs_update_route(self, client: TestClient, tmp_path: Path) -> None:
        response = client.post(
            "/api/ctx/public-docs/update",
            json={"project": str(tmp_path)},
        )
        assert response.status_code == 200
        data = response.json()
        assert "patch_path" in data

    def test_ctx_scan_structured_error(self, client: TestClient, tmp_path: Path) -> None:
        with patch.object(client.app, "state", create=True):
            # Re-patch the mock ops to raise ValueError
            from unittest.mock import patch as _patch
            with _patch("interfaces.api_server.app.AictxContextOps") as MockClass:
                mock_ops = MagicMock()
                mock_ops.scan.side_effect = ValueError("simulated scan failure")
                MockClass.return_value = mock_ops
                # Need to create a fresh client with the patched class
                from interfaces.api_server.app import create_api_app
                fresh_client = TestClient(create_api_app(repo_root=tmp_path))
                response = fresh_client.post("/api/ctx/scan", json={"project": str(tmp_path)})
        assert response.status_code == 400
        data = response.json()
        # FastAPI wraps dict detail under 'detail' key
        detail = data.get("detail", data)
        assert "type" in detail
        assert "category" in detail
        assert "retryable" in detail
        assert "next_action" in detail
