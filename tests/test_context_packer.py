"""Tests for core/context_packer.py — context bundle and manifest generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.context_packer import ContextPacker, FileEntry
from core.tool_protocol import BaseTool, ParamSchema, ReturnSchema, RiskLevel, ToolRegistry, ToolSchema


class DummyTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            "dummy",
            ToolSchema(
                description="A dummy tool",
                parameters={},
                returns=ReturnSchema(type="string", description="result"),
            ),
            RiskLevel.LOW,
        )

    def invoke(self, params: dict, context: Any) -> Any:
        return {"result": "ok"}


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "src" / "main.py").parent.mkdir(parents=True)
    (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Test Repo\n\nHello.\n", encoding="utf-8")
    (tmp_path / "secret.env").write_text("API_KEY=supersecret12345678\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")
    return tmp_path


class TestContextPackerBasic:
    def test_packs_bundle_and_manifest(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        packer = ContextPacker(max_tokens=10_000)
        bundle, manifest = packer.pack(repo)

        assert "# Context Bundle:" in bundle
        assert manifest.repo_name == tmp_path.name
        assert manifest.total_files > 0

    def test_redacts_secrets(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        packer = ContextPacker(max_tokens=10_000)
        bundle, _ = packer.pack(repo)

        assert "supersecret12345678" not in bundle
        assert "REDACTED" in bundle

    def test_respects_budget(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        # Very tight budget: should exclude some files
        packer = ContextPacker(max_tokens=10, chars_per_token=4)
        bundle, manifest = packer.pack(repo)

        assert manifest.included_files < manifest.total_files
        assert manifest.included_tokens_estimate <= 10

    def test_readme_prioritized(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        packer = ContextPacker(max_tokens=10_000)
        _, manifest = packer.pack(repo)

        readme_entry = next((f for f in manifest.files if f.path == "README.md"), None)
        assert readme_entry is not None
        assert readme_entry.included is True

    def test_manifest_to_dict(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        packer = ContextPacker(max_tokens=10_000)
        _, manifest = packer.pack(repo)
        d = manifest.to_dict()
        assert d["repo_name"] == tmp_path.name
        assert "files" in d
        assert isinstance(d["files"], list)


class TestContextPackerWithTools:
    def test_includes_tools_section(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        registry = ToolRegistry()
        registry.register(DummyTool())
        packer = ContextPacker(max_tokens=10_000)
        bundle, _ = packer.pack(repo, tool_registry=registry)

        assert "## Available Tools" in bundle
        assert "dummy" in bundle


class TestContextPackerWithConfig:
    def test_includes_config_section(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        packer = ContextPacker(max_tokens=10_000)
        bundle, _ = packer.pack(repo, run_config={"mode": "test"})

        assert "## Run Configuration" in bundle
        assert '"mode": "test"' in bundle


class TestContextPackerExcludes:
    def test_excludes_binary_files(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        (repo / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        packer = ContextPacker(max_tokens=10_000)
        _, manifest = packer.pack(repo)

        assert not any(f.path == "image.png" for f in manifest.files)

    def test_excludes_venv(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        (repo / ".venv" / "lib.py").parent.mkdir()
        (repo / ".venv" / "lib.py").write_text("x = 1", encoding="utf-8")
        packer = ContextPacker(max_tokens=10_000)
        _, manifest = packer.pack(repo)

        assert not any(".venv" in f.path for f in manifest.files)


class TestContextPackerLanguageDetection:
    def test_detects_python(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        packer = ContextPacker(max_tokens=10_000)
        _, manifest = packer.pack(repo)

        py_entry = next((f for f in manifest.files if f.path == "src/main.py"), None)
        assert py_entry is not None
        assert py_entry.language == "python"
