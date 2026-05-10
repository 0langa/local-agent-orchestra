from __future__ import annotations

from pathlib import Path
import subprocess


class GitTool:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def _run(self, args: list[str]) -> str:
        result = subprocess.run(args, cwd=self.repo_root, capture_output=True, text=True, timeout=15, check=False)
        if result.returncode != 0:
            return result.stderr.strip()
        return result.stdout.strip()

    def status(self) -> str:
        return self._run(["git", "status", "--short"])

    def branch(self) -> str:
        return self._run(["git", "branch", "--show-current"])

    def diff(self) -> str:
        return self._run(["git", "diff", "--stat"])

    def diff_patch(self) -> str:
        return self._run(["git", "diff", "--no-ext-diff", "--binary"])