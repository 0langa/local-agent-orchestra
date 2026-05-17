"""Tests that interface files import only from core.public_api (not core internals)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


INTERFACE_FILES = [
    "interfaces/cli/cli.py",
    "interfaces/api_server/app.py",
    "interfaces/web_ui/app.py",
    "interfaces/desktop_ui/app.py",
    "interfaces/guided_tui/app.py",
]


def _collect_core_imports(source_path: Path) -> list[tuple[int, str]]:
    """Return (line_no, module_name) for all core.* imports in a file."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("core."):
                imports.append((node.lineno, node.module))
    return imports


class TestInterfaceIsolation:
    @pytest.mark.parametrize("rel_path", INTERFACE_FILES)
    def test_no_direct_core_imports(self, rel_path: str) -> None:
        path = Path(__file__).parent.parent / rel_path
        if not path.exists():
            pytest.skip(f"{rel_path} does not exist")

        core_imports = _collect_core_imports(path)

        # Allowed: core.public_api itself
        disallowed = [(line, mod) for line, mod in core_imports if mod != "core.public_api"]

        assert not disallowed, (
            f"{rel_path} imports directly from core internals: "
            f"{[(line, mod) for line, mod in disallowed]}"
        )

    def test_public_api_has_all_needed_symbols(self) -> None:
        """Smoke test: ensure public_api can be imported and has key symbols."""
        from core import public_api

        required = [
            "RunLedger",
            "ModelRegistry",
            "PolicyEngine",
            "ToolRegistry",
            "RunExecutor",
            "Event",
            "WorkflowRunner",
        ]
        for name in required:
            assert hasattr(public_api, name), f"core.public_api missing {name}"
