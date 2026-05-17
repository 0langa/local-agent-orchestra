"""Smoke test verifying all provider adapters work through localhost-shaped configs.

Starts the mock AI server in a background thread and runs provider smoke
against every generated local profile.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def mock_server_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(autouse=True)
def _mock_server_env(monkeypatch: pytest.MonkeyPatch, mock_server_port: int) -> None:
    monkeypatch.setenv("MOCK_ALLOW_FAKE", "1")
    monkeypatch.setenv("MOCK_PORT", str(mock_server_port))
    monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(
        Path(__file__).resolve().parents[2] / ".localtest" / "config"
    ))
    monkeypatch.setenv("AGENTHEIM_DATA_DIR", str(
        Path(__file__).resolve().parents[2] / ".localtest" / "data"
    ))
    monkeypatch.setenv("AGENTHEIM_SECRET_BACKEND", "file")
    monkeypatch.setenv("AGENTHEIM_VAULT_PASSPHRASE", "localtest")


def _wait_for_server(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            import urllib.request

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _run_mock_server(port: int) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    localtest_server = str(repo_root / ".localtest" / "mock-ai-server")
    if not (Path(localtest_server) / "server.py").exists():
        pytest.skip("local mock AI server fixture is not present")
    if localtest_server not in sys.path:
        sys.path.insert(0, localtest_server)
    from server import app

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


class TestMockServerProviderSmoke:
    @pytest.mark.slow
    def test_all_local_provider_profiles_respond(self, mock_server_port: int) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        server_py = repo_root / ".localtest" / "mock-ai-server" / "server.py"
        if not server_py.exists():
            pytest.skip("local mock AI server fixture is not present")

        server_thread = threading.Thread(
            target=_run_mock_server, args=(mock_server_port,), daemon=True
        )
        server_thread.start()

        reached = _wait_for_server(mock_server_port, timeout=10.0)
        assert reached is True, "Mock AI server did not start within timeout"

        from config.config import ModelRole, load_profiles_document
        from core.model_registry import build_model_registry
        from providers.base import ModelRequest

        doc = load_profiles_document()
        failures: list[str] = []
        for profile_name in sorted(name for name in doc.profiles if name != "mock-all"):
            profile = doc.profiles[profile_name]
            for provider_id, provider in list(profile.providers.items()):
                profile.providers[provider_id] = provider.model_copy(
                    update={
                        "endpoint": provider.endpoint.replace("127.0.0.1:8787", f"127.0.0.1:{mock_server_port}"),
                        "timeout_seconds": 3,
                    }
                )
            team = profile.to_team_config()
            registry = build_model_registry(team)
            config = team.resolve_role(ModelRole.PLANNER)
            provider = registry.create_provider(config)
            try:
                response = provider.invoke(
                    ModelRequest(
                        role=ModelRole.PLANNER,
                        system_prompt="Reply briefly.",
                        user_prompt=f"ping {profile_name}",
                    )
                )
                ok = bool(response.content.strip())
                if not ok:
                    failures.append(f"{profile_name}: empty response")
            except Exception as exc:
                failures.append(f"{profile_name}: {exc}")

        assert not failures, f"Provider smoke failures: {failures}"
