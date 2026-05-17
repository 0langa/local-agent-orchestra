#!/usr/bin/env python3
"""Live smoke for standalone tools and vision.

This is intentionally separate from pytest because it may use real network and
configured model calls. It is a release gate, not a unit test.
"""

from __future__ import annotations

import base64
import json
import sqlite3
import struct
import zlib
from pathlib import Path
from typing import Any
import sys

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.tool_protocol import ToolContext
from multimodal.image import ImageTool
from tools.integrations.mcp_client import MCPClientAdapter
from tools.integrations.web_research import WebResearchAdapter
from tools.registry import ToolRegistry


def _png_rgb(width: int, height: int, pixels: bytes) -> bytes:
    raw = b"".join(b"\x00" + pixels[y * width * 3 : (y + 1) * width * 3] for y in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _record(results: list[dict[str, Any]], name: str, result: Any, *, expect: bool = True) -> None:
    success = bool(getattr(result, "success", False))
    passed = success == expect
    results.append(
        {
            "name": name,
            "passed": passed,
            "success": success,
            "error": getattr(result, "error", None),
            "metadata": getattr(result, "metadata", {}),
        }
    )
    print(f"{name}: {'PASS' if passed else 'FAIL'}")


def main() -> int:
    repo = Path(".localtest/tool-live-smoke").resolve()
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "sample.txt").write_text("agentheim live tool smoke", encoding="utf-8")

    context = ToolContext(
        run_id="tool-live-smoke",
        workspace=repo,
        allowed_paths=[str(repo)],
        allowed_commands=["python"],
        network_allowed=True,
    )
    registry = ToolRegistry(repo)
    results: list[dict[str, Any]] = []

    fs = registry.filesystem
    _record(results, "filesystem.list", fs.invoke({"operation": "list", "path": "."}, context))
    _record(results, "filesystem.read", fs.invoke({"operation": "read", "path": "sample.txt"}, context))
    _record(results, "filesystem.write", fs.invoke({"operation": "write", "path": "written.txt", "content": "ok"}, context))
    copied = repo / "copied.txt"
    if copied.exists():
        copied.unlink()
    _record(results, "filesystem.copy", fs.invoke({"operation": "copy", "path": "written.txt", "destination": "copied.txt"}, context))
    _record(results, "filesystem.escape_denied", fs.invoke({"operation": "read", "path": "..\\outside.txt"}, context), expect=False)

    memory = registry.memory
    _record(results, "memory.write", memory.invoke({"operation": "write", "scope": "repository", "key": "smoke", "value": {"ok": True}}, context))
    _record(results, "memory.read", memory.invoke({"operation": "read", "scope": "repository", "key": "smoke"}, context))

    shell = registry.shell
    _record(results, "shell.allowed", shell.invoke({"command": ["python", "-c", 'print("agentheim-shell-ok")'], "timeout_seconds": 10}, context))
    _record(results, "shell.denied", shell.invoke({"command": ["cmd", "/c", "echo bad"], "timeout_seconds": 10}, context), expect=False)
    _record(results, "git.status", registry.git.invoke({"operation": "status"}, context))

    db_path = repo / "smoke.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("drop table if exists items")
        conn.execute("create table items(id integer primary key, name text)")
        conn.execute("insert into items(name) values (?)", ("alpha",))
        conn.commit()
    local_db = registry.local_db
    _record(results, "local_db.list_tables", local_db.invoke({"operation": "list_tables", "db_path": "smoke.db"}, context))
    _record(results, "local_db.query", local_db.invoke({"operation": "query", "db_path": "smoke.db", "sql": "select name from items", "limit": 5}, context))
    _record(results, "local_db.write_denied", local_db.invoke({"operation": "query", "db_path": "smoke.db", "sql": "delete from items"}, context), expect=False)

    http = registry.http_request
    _record(results, "http.denied_by_context", http.invoke({"method": "GET", "url": "https://example.com", "timeout": 10}, ToolContext(workspace=repo, network_allowed=False)), expect=False)
    _record(results, "http.example", http.invoke({"method": "GET", "url": "https://example.com", "timeout": 15}, context))
    _record(results, "browser.get_text", registry.browser.invoke({"operation": "get_text", "url": "https://example.com", "timeout": 15}, context))

    web_disabled = WebResearchAdapter(repo, enabled=False).search("agentheim smoke")
    results.append(
        {
            "name": "web_research.disabled",
            "passed": web_disabled.get("source") == "unavailable" and web_disabled.get("results") == [],
            "error": web_disabled.get("error"),
        }
    )
    print(f"web_research.disabled: {'PASS' if results[-1]['passed'] else 'FAIL'}")

    try:
        MCPClientAdapter(repo, enabled=True).call("x", {})
        mcp_ok = False
        mcp_error = ""
    except RuntimeError as exc:
        mcp_ok = "no configured backend" in str(exc)
        mcp_error = str(exc)
    results.append({"name": "mcp.enabled_no_backend", "passed": mcp_ok, "error": mcp_error})
    print(f"mcp.enabled_no_backend: {'PASS' if mcp_ok else 'FAIL'}")

    png = _png_rgb(8, 8, bytes([255, 0, 0]) * 64)
    image_b64 = base64.b64encode(png).decode("ascii")
    _record(results, "vision.describe_live", ImageTool().invoke({"operation": "describe", "image_b64": image_b64}, context))

    output = repo / "tool_live_smoke_summary.json"
    output.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    failed = [item for item in results if not item.get("passed")]
    print(f"Summary: {len(results) - len(failed)} passed, {len(failed)} failed")
    print(f"Evidence: {output}")
    if failed:
        print(json.dumps(failed, indent=2, default=str))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
