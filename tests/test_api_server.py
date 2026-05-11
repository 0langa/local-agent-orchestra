from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interfaces.api_server import create_api_app
from interfaces.api_server.auth import _API_KEYS, _initialized


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    # Reset auth state for tests
    global _initialized
    _initialized = False
    _API_KEYS.clear()
    _API_KEYS.add("test-key")
    app = create_api_app(repo_root=tmp_path)
    return TestClient(app)


class TestHealth:
    def test_health_no_auth(self, client: TestClient) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "components" in data


class TestAuth:
    def test_missing_api_key(self, client: TestClient) -> None:
        response = client.post("/api/memory/jsonl/test", json={"value": {"x": 1}})
        assert response.status_code == 401

    def test_invalid_api_key(self, client: TestClient) -> None:
        response = client.post(
            "/api/memory/jsonl/test",
            json={"value": {"x": 1}},
            headers={"X-API-Key": "bad-key"},
        )
        assert response.status_code == 403

    def test_valid_api_key(self, client: TestClient) -> None:
        response = client.post(
            "/api/memory/jsonl/test",
            json={"value": {"x": 1}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200


class TestTools:
    def test_list_tools(self, client: TestClient) -> None:
        response = client.get("/api/tools")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        tool_ids = {t["tool_id"] for t in data}
        assert "filesystem" in tool_ids
        assert "local_db" in tool_ids

    def test_tool_schema_has_parameters(self, client: TestClient) -> None:
        response = client.get("/api/tools")
        data = response.json()
        fs_tool = next(t for t in data if t["tool_id"] == "filesystem")
        assert "parameters" in fs_tool
        assert "operation" in fs_tool["parameters"]

    def test_invoke_tool_not_found(self, client: TestClient) -> None:
        response = client.post(
            "/api/tools/nonexistent/invoke",
            json={"params": {}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 404

    def test_invoke_high_risk_blocked(self, client: TestClient) -> None:
        response = client.post(
            "/api/tools/shell.execute/invoke",
            json={"params": {"command": ["echo", "hi"]}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 403
        assert "high-risk" in response.json()["detail"].lower() or "CLI" in response.json()["detail"]

    def test_invoke_filesystem_read(self, tmp_path: Path, client: TestClient) -> None:
        test_file = tmp_path / "hello.txt"
        test_file.write_text("world", encoding="utf-8")
        response = client.post(
            "/api/tools/filesystem/invoke",
            json={"params": {"operation": "read", "path": "hello.txt"}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == "world"

    def test_invoke_browser_blocked(self, client: TestClient) -> None:
        response = client.post(
            "/api/tools/browser/invoke",
            json={"params": {"operation": "navigate", "url": "https://example.com"}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 403


class TestWorkflows:
    def test_list_workflows(self, client: TestClient) -> None:
        response = client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        workflow_ids = {w["workflow_id"] for w in data}
        assert "research" in workflow_ids

    def test_get_workflow_detail(self, client: TestClient) -> None:
        response = client.get("/api/workflows/research")
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "research"
        assert "name" in data

    def test_get_workflow_not_found(self, client: TestClient) -> None:
        response = client.get("/api/workflows/nonexistent")
        assert response.status_code == 404


class TestPresets:
    def test_list_presets(self, client: TestClient) -> None:
        response = client.get("/api/presets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        preset_ids = {p["preset_id"] for p in data}
        assert "research-report" in preset_ids


class TestMemory:
    def test_read_missing_key(self, client: TestClient) -> None:
        response = client.get("/api/memory/jsonl/nonexistent_key_12345")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False
        assert data["value"] is None

    def test_write_and_read(self, client: TestClient) -> None:
        key = "test_key_api"
        response = client.post(
            f"/api/memory/jsonl/{key}",
            json={"value": {"message": "hello"}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "written"

        response = client.get(f"/api/memory/jsonl/{key}")
        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert data["value"] == {"message": "hello"}


class TestModels:
    def test_list_models(self, client: TestClient) -> None:
        response = client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestProviders:
    def test_list_providers(self, client: TestClient) -> None:
        response = client.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        provider_ids = {p["provider_id"] for p in data}
        assert "openai_v1" in provider_ids


class TestRuns:
    def test_run_not_found(self, client: TestClient) -> None:
        response = client.get("/api/runs/nonexistent_run_12345")
        assert response.status_code == 404

    def test_run_found(self, tmp_path: Path, client: TestClient) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "test-run-1"
        run_dir.mkdir(parents=True)
        (run_dir / "final_report.md").write_text("# Report", encoding="utf-8")
        response = client.get("/api/runs/test-run-1")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-run-1"
        assert data["status"] == "completed"
        assert "final_report.md" in data["artifacts"]


class TestWorkflowExecution:
    def test_execute_workflow_not_found(self, client: TestClient) -> None:
        response = client.post(
            "/api/workflows/nonexistent/execute",
            json={"params": {}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 404

    def test_execute_workflow_returns_run_id(self, client: TestClient) -> None:
        from unittest.mock import patch
        from core.run_executor import RunExecutor
        RunExecutor.reset_instance()
        with patch("core.run_executor.RunExecutor.submit", return_value="test-run-123"):
            response = client.post(
                "/api/workflows/research/execute",
                json={"params": {"task": "test"}},
                headers={"X-API-Key": "test-key"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "pending"
        RunExecutor.reset_instance()


class TestPresetExecution:
    def test_run_preset_not_found(self, client: TestClient) -> None:
        response = client.post(
            "/api/presets/nonexistent/run",
            json={"inputs": {}},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 404

    def test_run_preset_returns_run_id(self, client: TestClient) -> None:
        from unittest.mock import patch
        from core.run_executor import RunExecutor
        RunExecutor.reset_instance()
        with patch("core.run_executor.RunExecutor.submit", return_value="test-run-456"):
            response = client.post(
                "/api/presets/research-report/run",
                json={"inputs": {"topic": "AI"}},
                headers={"X-API-Key": "test-key"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "pending"
        RunExecutor.reset_instance()


class TestRunStreaming:
    def test_stream_run_not_found(self, client: TestClient) -> None:
        response = client.get("/api/runs/nonexistent_run_12345/stream")
        assert response.status_code == 404


class TestRunWebSocket:
    def test_websocket_run_not_found(self, client: TestClient) -> None:
        from starlette.websockets import WebSocketDisconnect

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


class TestMetrics:
    def test_metrics_endpoint(self, client: TestClient) -> None:
        response = client.get("/api/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        body = response.text
        assert "agentheim" in body.lower() or "#" in body


class TestOpenAPI:
    def test_openapi_schema(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Agentheim API"
        paths = list(schema["paths"].keys())
        assert "/api/health" in paths
        assert "/api/tools" in paths
        assert "/api/workflows" in paths
        assert "/api/presets" in paths
        assert "/api/workflows/{workflow_id}/execute" in paths
        assert "/api/presets/{preset_id}/run" in paths
        assert "/api/runs/{run_id}/stream" in paths
        assert "/api/metrics" in paths

    def test_docs_endpoint(self, client: TestClient) -> None:
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
