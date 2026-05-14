from __future__ import annotations

from pathlib import Path

import pytest

from core.tool_protocol import ToolContext
from tools.filesystem import FilesystemTool


@pytest.fixture
def tool(tmp_path: Path) -> FilesystemTool:
    return FilesystemTool(repo_root=tmp_path)


@pytest.fixture
def context() -> ToolContext:
    return ToolContext()


class TestCopy:
    def test_copy_file(self, tool: FilesystemTool, context: ToolContext) -> None:
        src = Path(tool.repo_root) / "src.txt"
        src.write_text("hello", encoding="utf-8")
        result = tool.invoke(
            {"operation": "copy", "path": "src.txt", "destination": "dst.txt"},
            context,
        )
        assert result.success is True
        assert result.data == "dst.txt"
        assert (Path(tool.repo_root) / "dst.txt").read_text() == "hello"

    def test_copy_directory(self, tool: FilesystemTool, context: ToolContext) -> None:
        src_dir = Path(tool.repo_root) / "src_dir"
        src_dir.mkdir()
        (src_dir / "a.txt").write_text("a", encoding="utf-8")
        result = tool.invoke(
            {"operation": "copy", "path": "src_dir", "destination": "dst_dir"},
            context,
        )
        assert result.success is True
        assert (Path(tool.repo_root) / "dst_dir" / "a.txt").read_text() == "a"

    def test_copy_source_missing(self, tool: FilesystemTool, context: ToolContext) -> None:
        result = tool.invoke(
            {"operation": "copy", "path": "missing.txt", "destination": "dst.txt"},
            context,
        )
        assert result.success is False
        assert "not found" in result.error.lower()

    def test_copy_destination_exists(self, tool: FilesystemTool, context: ToolContext) -> None:
        src = Path(tool.repo_root) / "src.txt"
        dst = Path(tool.repo_root) / "dst.txt"
        src.write_text("src", encoding="utf-8")
        dst.write_text("dst", encoding="utf-8")
        result = tool.invoke(
            {"operation": "copy", "path": "src.txt", "destination": "dst.txt"},
            context,
        )
        assert result.success is False
        assert "already exists" in result.error.lower()

    def test_copy_path_escape(self, tool: FilesystemTool, context: ToolContext) -> None:
        result = tool.invoke(
            {"operation": "copy", "path": "../escape.txt", "destination": "dst.txt"},
            context,
        )
        assert result.success is False
        assert "escapes" in result.error.lower()

    def test_copy_cli_command(self) -> None:
        from typer.testing import CliRunner
        from interfaces.cli.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["copy", "--help"])
        assert result.exit_code == 0
        assert "source" in result.output.lower()
        assert "destination" in result.output.lower()
