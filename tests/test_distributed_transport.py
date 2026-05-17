"""Tests for distributed worker HTTP transport."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from workflows.distributed import create_coordinator_app
from workflows.distributed.protocol import TaskAssignment, WorkerRegistration, TaskResult
from workflows.distributed.transport import CoordinatorClient


class TestCoordinatorApp:
    def test_register_worker(self) -> None:
        app = create_coordinator_app()
        client = TestClient(app)
        response = client.post("/api/workers/register", json={
            "worker_id": "w1",
            "capabilities": ["code", "test"],
        })
        assert response.status_code == 200
        assert response.json()["status"] == "registered"

    def test_heartbeat(self) -> None:
        app = create_coordinator_app()
        client = TestClient(app)
        client.post("/api/workers/register", json={"worker_id": "w1", "capabilities": []})
        response = client.post("/api/workers/heartbeat", json={
            "worker_id": "w1",
            "status": "idle",
            "timestamp": 0.0,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_poll_task_no_task(self) -> None:
        app = create_coordinator_app()
        client = TestClient(app)
        client.post("/api/workers/register", json={"worker_id": "w1", "capabilities": []})
        response = client.get("/api/workers/w1/task")
        assert response.status_code == 200
        assert response.json()["task"] is None

    def test_submit_and_poll_task(self) -> None:
        app = create_coordinator_app()
        client = TestClient(app)
        client.post("/api/workers/register", json={"worker_id": "w1", "capabilities": ["code"]})
        client.post("/api/tasks/submit", json={
            "task_id": "t1",
            "task_type": "code",
            "payload": {"x": 1},
        })
        response = client.get("/api/workers/w1/task")
        assert response.status_code == 200
        task = response.json()["task"]
        assert task is not None
        assert task["task_id"] == "t1"

    def test_status_endpoint(self) -> None:
        app = create_coordinator_app()
        client = TestClient(app)
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "workers" in data
        assert "pending" in data


class TestCoordinatorClient:
    def test_register(self) -> None:
        client = CoordinatorClient("http://testserver")
        reg = WorkerRegistration(worker_id="w1", capabilities=["code"])
        with patch.object(client, "_request", return_value={"status": "registered"}):
            client.register(reg)

    def test_poll_task_no_task(self) -> None:
        client = CoordinatorClient("http://testserver")
        with patch.object(client, "_request", return_value={"task": None}):
            task = client.poll_task("w1")
            assert task is None

    def test_poll_task_with_task(self) -> None:
        client = CoordinatorClient("http://testserver")
        task_json = TaskAssignment(task_id="t1", task_type="code", payload={"x": 1}).to_json()
        with patch.object(client, "_request", return_value={"task": task_json}):
            task = client.poll_task("w1")
            assert task is not None
            assert task.task_id == "t1"

    def test_submit_result(self) -> None:
        client = CoordinatorClient("http://testserver")
        result = TaskResult(task_id="t1", success=True, data="done")
        with patch.object(client, "_request", return_value={"status": "ok"}):
            client.submit_result(result, "w1")
