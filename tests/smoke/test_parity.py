"""Cross-interface parity tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from interfaces.api_server.app import create_api_app
from interfaces.cli.cli import app as cli_app


def _extract_md_table_commands(md_path: Path) -> set[str]:
    """Parse CLI-COMMANDS.md for command/sub-typer names from relevant tables."""
    text = md_path.read_text(encoding="utf-8")
    commands = set()
    # Track which section we're in
    in_relevant_section = False
    section_header_pattern = re.compile(r"^##\s+(Root Commands|Context Operations|Provider Management)")
    table_row_pattern = re.compile(r"^\|\s*`([^`]+)`")
    for line in text.splitlines():
        if section_header_pattern.match(line):
            in_relevant_section = True
            continue
        if in_relevant_section and line.startswith("## "):
            in_relevant_section = False
            continue
        if in_relevant_section:
            m = table_row_pattern.match(line)
            if m:
                raw = m.group(1).strip()
                commands.add(raw.split()[0])
    return commands


def _extract_md_api_routes(md_path: Path) -> set[str]:
    """Parse API_REFERENCE.md for documented API routes (excluding meta/docs)."""
    text = md_path.read_text(encoding="utf-8")
    routes = set()
    for line in text.splitlines():
        # Match lines like "GET /api/health" or "POST /api/ctx/init"
        m = re.match(r"```\s*(GET|POST|PUT|DELETE|PATCH|WS)\s+(/[^\s`]+)", line.strip())
        if m:
            routes.add(m.group(2))
        # Also match lines without code blocks like "GET /api/health"
        m2 = re.match(r"(GET|POST|PUT|DELETE|PATCH|WS)\s+(/[^\s`]+)", line.strip())
        if m2:
            routes.add(m2.group(2))
    # Exclude FastAPI meta endpoints and WebSocket routes (not in OpenAPI)
    routes.discard("/docs")
    routes.discard("/redoc")
    routes.discard("/openapi.json")
    routes.discard("/api/runs/{run_id}/ws")
    return routes


class TestPresetRegistryParity:
    def test_preset_registry_matches_api_preset_list(self, tmp_path: Path) -> None:
        from presets import PRESET_REGISTRY

        registry_ids = {p.preset_id for p in PRESET_REGISTRY.list()}

        mock_ops = MagicMock()
        mock_ops.init.return_value = None
        with patch("interfaces.api_server.app.AictxContextOps") as MockClass:
            MockClass.return_value = mock_ops
            client = TestClient(create_api_app(repo_root=tmp_path))
            response = client.get("/api/presets")

        assert response.status_code == 200
        api_ids = {item["preset_id"] for item in response.json()}
        assert registry_ids == api_ids, f"Registry: {registry_ids}, API: {api_ids}"


class TestWorkflowRegistryParity:
    def test_workflow_registry_matches_api_workflow_list(self, tmp_path: Path) -> None:
        from workflows.registry import register_builtin_workflows
        from core.public_api import list_workflows

        register_builtin_workflows()
        registry_ids = {w.id for w in list_workflows()}

        mock_ops = MagicMock()
        mock_ops.init.return_value = None
        with patch("interfaces.api_server.app.AictxContextOps") as MockClass:
            MockClass.return_value = mock_ops
            client = TestClient(create_api_app(repo_root=tmp_path))
            response = client.get("/api/workflows")

        assert response.status_code == 200
        api_ids = {item["workflow_id"] for item in response.json()}
        assert registry_ids == api_ids, f"Registry: {registry_ids}, API: {api_ids}"


class TestCliDocsParity:
    def test_cli_commands_match_docs_reference(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        md_path = repo_root / "docs" / "CLI-COMMANDS.md"
        assert md_path.exists(), "CLI-COMMANDS.md missing"
        docs_commands = _extract_md_table_commands(md_path)

        # Introspect Typer app for registered commands (including sub-typers)
        cli_commands = set()
        for cmd in cli_app.registered_commands:
            if cmd.name:
                cli_commands.add(cmd.name)
        for typer_info in cli_app.registered_groups:
            if typer_info.name:
                cli_commands.add(typer_info.name)

        missing_in_docs = cli_commands - docs_commands
        missing_in_cli = docs_commands - cli_commands
        assert not missing_in_docs, f"CLI commands not in docs: {missing_in_docs}"
        assert not missing_in_cli, f"Docs commands not in CLI: {missing_in_cli}"


class TestApiDocsParity:
    def test_api_openapi_paths_match_docs_reference(self, tmp_path: Path) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        md_path = repo_root / "docs" / "API_REFERENCE.md"
        assert md_path.exists(), "API_REFERENCE.md missing"
        docs_routes = _extract_md_api_routes(md_path)

        mock_ops = MagicMock()
        mock_ops.init.return_value = None
        with patch("interfaces.api_server.app.AictxContextOps") as MockClass:
            MockClass.return_value = mock_ops
            client = TestClient(create_api_app(repo_root=tmp_path))
            response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        openapi_paths = set(schema.get("paths", {}).keys())

        # Only check routes that are documented in API_REFERENCE.md exist in OpenAPI
        missing_in_openapi = docs_routes - openapi_paths
        assert not missing_in_openapi, f"Docs routes missing from OpenAPI: {missing_in_openapi}"
