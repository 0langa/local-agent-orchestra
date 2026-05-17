from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.events import EventType
from core.ledger import RunLedger
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


class TestRuns:
    def test_run_not_found(self, client: TestClient) -> None:
        response = client.get("/api/runs/nonexistent_run_12345")
        assert response.status_code == 404

    def test_run_found(self, tmp_path: Path, client: TestClient) -> None:
        run_dir = tmp_path / ".ai-team" / "runs" / "test-run-1"
        run_dir.mkdir(parents=True)
        (run_dir / "run.json").write_text(
            json.dumps({"run_id": "test-run-1", "workflow_id": "research", "preset_id": "research-report"}),
            encoding="utf-8",
        )
        (run_dir / "final_report.json").write_text(
            json.dumps({"run_id": "test-run-1", "topic": "State machines", "status": "done"}),
            encoding="utf-8",
        )
        (run_dir / "final_report.md").write_text("# Report", encoding="utf-8")

        response = client.get("/api/runs/test-run-1")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "test-run-1"
        assert data["status"] == "completed"
        assert data["workflow_id"] == "research"
        assert data["preset_id"] == "research-report"
        assert data["summary"] == "Research topic: State machines"
        assert "final_report.json" in data["artifacts"]


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
        assert data["approval_request"]["request_id"]
        assert not (tmp_path / "created.txt").exists()

    def test_grant_filesystem_write_executes_and_records_ledger(self, tmp_path: Path, client: TestClient) -> None:
        response = client.post(
            "/api/tools/invoke",
            json={
                "tool_id": "filesystem",
                "params": {"operation": "write", "path": "created.txt", "content": "new"},
            },
        )
        request_id = response.json()["approval_request"]["request_id"]

        grant = client.post(f"/api/tools/approvals/{request_id}/grant")
        assert grant.status_code == 200
        data = grant.json()
        assert data["status"] == "granted"
        assert data["success"] is True
        assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "new"

        run_dirs = sorted((tmp_path / ".ai-team" / "runs").iterdir())
        ledger = RunLedger(repo_root=tmp_path, run_dir=run_dirs[-1])
        event_types = [event.event_type for event in ledger.read_ledger()]
        assert EventType.POLICY_EVALUATED in event_types
        assert EventType.APPROVAL_REQUESTED in event_types
        assert EventType.APPROVAL_GRANTED in event_types
        assert EventType.TOOL_RESULT_RECEIVED in event_types

    def test_deny_filesystem_write_records_denial(self, tmp_path: Path, client: TestClient) -> None:
        response = client.post(
            "/api/tools/invoke",
            json={
                "tool_id": "filesystem",
                "params": {"operation": "write", "path": "created.txt", "content": "new"},
            },
        )
        request_id = response.json()["approval_request"]["request_id"]

        deny = client.post(f"/api/tools/approvals/{request_id}/deny")
        assert deny.status_code == 200
        data = deny.json()
        assert data["status"] == "denied"
        assert data["error"] == "approval_denied"
        assert not (tmp_path / "created.txt").exists()

        run_dirs = sorted((tmp_path / ".ai-team" / "runs").iterdir())
        ledger = RunLedger(repo_root=tmp_path, run_dir=run_dirs[-1])
        event_types = [event.event_type for event in ledger.read_ledger()]
        assert EventType.APPROVAL_REQUESTED in event_types
        assert EventType.APPROVAL_DENIED in event_types


class TestWorkflows:
    def test_list_workflows(self, client: TestClient) -> None:
        response = client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        workflow_ids = {w["workflow_id"] for w in data}
        assert "research" in workflow_ids
        assert "coding" in workflow_ids, f"Expected 'coding' in workflow list, got {workflow_ids}"

    def test_list_workflows_have_support_state(self, client: TestClient) -> None:
        response = client.get("/api/workflows")
        data = response.json()
        for w in data:
            assert "support_state" in w
            assert w["support_state"] in ("stable_candidate", "beta", "experimental", "unknown")


class TestPresets:
    def test_list_presets(self, client: TestClient) -> None:
        response = client.get("/api/presets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        preset_ids = {p["preset_id"] for p in data}
        assert "research-report" in preset_ids

    def test_list_presets_have_support_state(self, client: TestClient) -> None:
        response = client.get("/api/presets")
        data = response.json()
        for p in data:
            assert "support_state" in p
            assert p["support_state"] in ("stable_candidate", "beta", "experimental", "unknown")


class TestProviderTemplates:
    def test_templates_exclude_experimental(self, client: TestClient) -> None:
        response = client.get("/api/providers/templates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for t in data:
            assert t["support_state"] != "experimental", (
                f"experimental template '{t['kind']}' leaked to Web UI"
            )


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

    def test_websocket_final_message_uses_canonical_run_summary(self, tmp_path: Path, client: TestClient) -> None:
        import threading
        import time
        from core.run_executor import RunExecutor

        executor = RunExecutor()
        started = threading.Event()

        class _Result:
            run_id = "persisted-run"

        def _task():
            started.set()
            run_dir = tmp_path / ".ai-team" / "runs" / "persisted-run"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "run.json").write_text(
                json.dumps({"run_id": "persisted-run", "workflow_id": "research"}),
                encoding="utf-8",
            )
            (run_dir / "final_report.json").write_text(
                json.dumps({"run_id": "persisted-run", "topic": "Canonical WS", "status": "done"}),
                encoding="utf-8",
            )
            (run_dir / "final_report.md").write_text("# Report", encoding="utf-8")
            time.sleep(0.2)
            return _Result()

        run_id = executor.submit(_task)
        started.wait(timeout=2.0)

        with client.websocket_connect(f"/api/runs/{run_id}/ws") as ws:
            _ = ws.receive_json()
            final = ws.receive_json()
            assert final["run_id"] == "persisted-run"
            assert final["tracking_run_id"] == run_id
            assert final["status"] == "completed"
            assert final["summary"] == "Research topic: Canonical WS"


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


class TestStructuredErrors:
    def test_ctx_route_returns_structured_error(self, tmp_path: Path, client: TestClient) -> None:
        from unittest.mock import patch

        with patch("interfaces.web_ui.app.AictxContextOps", side_effect=ValueError("bad path")):
            response = client.post("/api/ctx/init", json={"project_path": str(tmp_path)})
        assert response.status_code == 400
        data = response.json()
        assert data["type"] == "ValueError"
        assert "bad path" in data["message"]
        assert "category" in data
        assert "next_action" in data
        assert "troubleshooting_section" in data

    def test_global_exception_handler_returns_structured_diagnostics(self, tmp_path: Path, client: TestClient) -> None:
        from unittest.mock import patch

        with patch("interfaces.web_ui.app._import_workflows", side_effect=RuntimeError("registry corrupt")):
            response = client.get("/api/workflows")
        assert response.status_code == 500
        data = response.json()
        assert data["type"] == "RuntimeError"
        assert "registry corrupt" in data["message"]
        assert "category" in data
        assert "next_action" in data
        assert "troubleshooting_section" in data
