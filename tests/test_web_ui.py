from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interfaces.web_ui import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app(repo_root=tmp_path)
    return TestClient(app)


class TestHealth:
    def test_health_ok(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestDashboard:
    def test_root_returns_html(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Agentheim" in response.text


class TestTools:
    def test_list_tools(self, client: TestClient) -> None:
        response = client.get("/api/tools")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        tool_ids = {t["tool_id"] for t in data}
        assert "filesystem" in tool_ids
        assert "local_db" in tool_ids
        assert "http.request" in tool_ids
        assert "memory" in tool_ids

    def test_list_tools_have_risk_levels(self, client: TestClient) -> None:
        response = client.get("/api/tools")
        data = response.json()
        for tool in data:
            assert "tool_id" in tool
            assert "risk_level" in tool
            assert "description" in tool

    def test_invoke_tool_not_found(self, client: TestClient) -> None:
        response = client.post("/api/tools/invoke", json={"tool_id": "nonexistent", "params": {}})
        assert response.status_code == 404

    def test_invoke_high_risk_tool_blocked(self, client: TestClient) -> None:
        response = client.post(
            "/api/tools/invoke",
            json={"tool_id": "shell.execute", "params": {"command": ["echo", "hi"]}},
        )
        assert response.status_code == 403
        assert "blocked" in response.json()["detail"].lower()

    def test_invoke_filesystem_read(self, tmp_path: Path, client: TestClient) -> None:
        test_file = tmp_path / "hello.txt"
        test_file.write_text("world", encoding="utf-8")
        response = client.post(
            "/api/tools/invoke",
            json={
                "tool_id": "filesystem",
                "params": {"operation": "read", "path": "hello.txt"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == "world"
        assert data["requires_approval"] is False

    def test_invoke_filesystem_stat(self, tmp_path: Path, client: TestClient) -> None:
        test_file = tmp_path / "hello.txt"
        test_file.write_text("world", encoding="utf-8")
        response = client.post(
            "/api/tools/invoke",
            json={
                "tool_id": "filesystem",
                "params": {"operation": "stat", "path": "hello.txt"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_file"] is True

    def test_invoke_filesystem_write_returns_approval_request(self, tmp_path: Path, client: TestClient) -> None:
        response = client.post(
            "/api/tools/invoke",
            json={
                "tool_id": "filesystem",
                "params": {"operation": "write", "path": "created.txt", "content": "new"},
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["requires_approval"] is True
        assert data["policy"]["decision"] == "ask"
        assert not (tmp_path / "created.txt").exists()


class TestWorkflows:
    def test_list_workflows(self, client: TestClient) -> None:
        response = client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        workflow_ids = {w["workflow_id"] for w in data}
        assert "research" in workflow_ids
        assert "coding" in workflow_ids, f"Expected 'coding' in workflow list, got {workflow_ids}"


class TestPresets:
    def test_list_presets(self, client: TestClient) -> None:
        response = client.get("/api/presets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        preset_ids = {p["preset_id"] for p in data}
        assert "research-report" in preset_ids


class TestRunWebSocket:
    def test_websocket_run_not_found(self, client: TestClient) -> None:
        from starlette.websockets import WebSocketDisconnect
        import pytest

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/api/runs/nonexistent_run_12345/ws") as ws:
                ws.receive_json()

    def test_websocket_receives_status_updates(self, client: TestClient) -> None:
        import threading
        import time
        from core.run_executor import RunExecutor

        # Use the existing singleton instance that the app factory captured.
        executor = RunExecutor()

        started = threading.Event()

        def _slow_task():
            started.set()
            time.sleep(0.5)
            return "done"

        run_id = executor.submit(_slow_task)
        started.wait(timeout=2.0)

        with client.websocket_connect(f"/api/runs/{run_id}/ws") as ws:
            msg1 = ws.receive_json()
            assert msg1["run_id"] == run_id
            assert msg1["status"] in ("pending", "running")

            msg2 = ws.receive_json()
            assert msg2["run_id"] == run_id
            assert msg2["status"] == "completed"
            assert msg2["artifacts"] == []


class TestMemory:
    def test_read_missing_key(self, client: TestClient) -> None:
        response = client.get("/api/memory/jsonl/nonexistent_key_12345")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False
        assert data["value"] is None

    def test_write_and_read(self, client: TestClient) -> None:
        key = "test_key_web_ui"
        response = client.post(
            f"/api/memory/jsonl/{key}",
            json={"value": {"message": "hello"}},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "written"

        response = client.get(f"/api/memory/jsonl/{key}")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["value"] == {"message": "hello"}
