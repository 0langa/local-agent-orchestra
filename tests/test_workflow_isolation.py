"""Tests that workflow-facing modules import core through core.public_api only."""

from __future__ import annotations

import ast
from pathlib import Path


WORKFLOW_EXEMPTIONS = {
    "workflows/base.py",
}


def _workflow_files() -> list[Path]:
    root = Path(__file__).parent.parent / "workflows"
    files: list[Path] = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root.parent).as_posix()
        if rel in WORKFLOW_EXEMPTIONS:
            continue
        if "/agents/" in rel:
            continue
        files.append(path)
    return sorted(files)


def _collect_core_imports(source_path: Path) -> list[tuple[int, str]]:
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("core."):
            imports.append((node.lineno, node.module))
    return imports


class TestWorkflowIsolation:
    def test_workflow_facing_modules_use_public_api(self) -> None:
        repo_root = Path(__file__).parent.parent
        violations: list[tuple[str, int, str]] = []
        for path in _workflow_files():
            rel = path.relative_to(repo_root).as_posix()
            for line_no, module in _collect_core_imports(path):
                if module != "core.public_api":
                    violations.append((rel, line_no, module))

        assert not violations, f"Workflow-facing modules import core internals: {violations}"
