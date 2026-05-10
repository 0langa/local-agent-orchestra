from __future__ import annotations

from pathlib import Path
from typing import Any


class MCPClientAdapter:
    def __init__(self, repo_root: str | Path, enabled: bool = False, allowlist: list[str] | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.enabled = enabled
        self.allowlist = set(allowlist or [])

    @property
    def available(self) -> bool:
        return self.enabled

    def call(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("MCP adapter is disabled.")
        if self.allowlist and tool_name not in self.allowlist:
            raise RuntimeError(f"MCP tool '{tool_name}' is not in allowlist.")
        return {"tool": tool_name, "payload": payload, "status": "stub"}