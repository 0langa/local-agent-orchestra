from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.errors import IntegrationError


class GitHubCliAdapter:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)

    @property
    def available(self) -> bool:
        return shutil.which("gh") is not None

    def _run(self, args: list[str]) -> str:
        if not self.available:
            raise IntegrationError("GitHub CLI not available.")
        result = subprocess.run(["gh", *args], cwd=self.repo_root, capture_output=True, text=True, check=False, timeout=20)
        if result.returncode != 0:
            raise IntegrationError(result.stderr.strip() or "GitHub CLI command failed.")
        return result.stdout.strip()

    def view_issue(self, issue: str) -> str:
        return self._run(["issue", "view", issue])

    def view_pr(self, pr: str) -> str:
        return self._run(["pr", "view", pr])

    def view_workflow_run(self, run_id: str) -> str:
        return self._run(["run", "view", run_id])