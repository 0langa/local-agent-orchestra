from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.path_security import safe_child_path, safe_project_path, safe_run_id
from interfaces.api_server import create_api_app
from interfaces.web_ui.app import create_app as create_web_app


def test_safe_run_id_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        safe_run_id("../secret")
    with pytest.raises(ValueError):
        safe_run_id(".hidden")


def test_safe_child_path_rejects_escape(tmp_path) -> None:
    with pytest.raises(ValueError):
        safe_child_path(tmp_path, "..", "outside.txt")


def test_safe_project_path_requires_directory(tmp_path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        safe_project_path(file_path)


def test_api_rejects_traversal_run_id(tmp_path) -> None:
    client = TestClient(create_api_app(repo_root=tmp_path))
    response = client.get("/api/runs/bad:run")
    assert response.status_code == 400


def test_web_ui_rejects_traversal_run_id(tmp_path) -> None:
    client = TestClient(create_web_app(repo_root=tmp_path))
    response = client.get("/api/runs/bad:run")
    assert response.status_code == 400
