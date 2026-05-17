"""Tests for federation HTTP transport."""

from __future__ import annotations

from fastapi.testclient import TestClient

from federation.transport import create_federation_app


class TestFederationApp:
    def test_discover(self) -> None:
        app = create_federation_app("local-1", ["code", "test"])
        client = TestClient(app)
        response = client.post("/api/federation/discover", json={
            "peer_id": "peer-1",
            "capabilities": ["code"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["peer_id"] == "local-1"
        assert "code" in data["capabilities"]

    def test_list_peers(self) -> None:
        app = create_federation_app("local-1")
        client = TestClient(app)
        client.post("/api/federation/discover", json={"peer_id": "peer-1", "capabilities": []})
        response = client.get("/api/federation/peers")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_delegate_task(self) -> None:
        app = create_federation_app("local-1")
        client = TestClient(app)
        response = client.post("/api/federation/delegate", json={
            "task_id": "t1",
            "task_type": "code",
            "payload": {},
            "origin_peer": "peer-1",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_relay_result(self) -> None:
        app = create_federation_app("local-1")
        client = TestClient(app)
        response = client.post("/api/federation/relay", json={
            "task_id": "t1",
            "success": True,
            "data": "done",
            "origin_peer": "peer-1",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "received"
