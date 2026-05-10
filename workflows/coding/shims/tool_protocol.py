"""Shim: tool_protocol.invoke(tool_name, **kwargs)

Delegates to tools.registry.ToolRegistry (and friends) until core/ grows a
first-class tool protocol.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.registry import ToolRegistry


_tool_registries: dict[Path, ToolRegistry] = {}


def _get_registry(repo_root: Path) -> ToolRegistry:
    repo_root = repo_root.resolve()
    if repo_root not in _tool_registries:
        _tool_registries[repo_root] = ToolRegistry(repo_root)
    return _tool_registries[repo_root]


def invoke(
    tool_name: str,
    *,
    repo_root: Path | None = None,
    **kwargs: Any,
) -> Any:
    """Invoke a tool by name.

    Supported tools:
        - filesystem.read    (path)
        - filesystem.write   (path, content)
        - shell.execute      (command, timeout_seconds)
        - git.status         ()
        - git.diff           ()
        - git.diff_patch     ()
    """
    if repo_root is None:
        raise ValueError("repo_root is required for tool invocation")

    registry = _get_registry(repo_root)
    parts = tool_name.split(".")

    if parts[0] == "filesystem":
        if parts[1] == "read":
            return registry.filesystem.read(kwargs["path"])
        if parts[1] == "write":
            return registry.filesystem.write(kwargs["path"], kwargs["content"])
        raise ValueError(f"Unknown filesystem tool: {parts[1]}")

    if parts[0] == "shell":
        if parts[1] == "execute":
            return registry.shell.run(
                kwargs["command"],
                timeout_seconds=kwargs.get("timeout_seconds", 120),
            )
        raise ValueError(f"Unknown shell tool: {parts[1]}")

    if parts[0] == "git":
        if parts[1] == "status":
            return registry.git.status()
        if parts[1] == "diff":
            return registry.git.diff()
        if parts[1] == "diff_patch":
            return registry.git.diff_patch()
        raise ValueError(f"Unknown git tool: {parts[1]}")

    raise ValueError(f"Unknown tool namespace: {parts[0]}")
