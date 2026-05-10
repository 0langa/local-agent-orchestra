from __future__ import annotations

from pathlib import Path
import subprocess

from pydantic import BaseModel, ConfigDict

from core.policies import can_auto_run, classify_command


class ShellResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


class ShellTool:
    SAFE_PREFIXES = {
        "python",
        "pytest",
        "dotnet",
        "cargo",
        "go",
        "git",
        "npm",
    }
    BLOCKED_TERMS = {"rm", "rmdir", "del", "format", "shutdown", "deploy", "publish", "terraform", "az"}

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def classify_risk(self, command: list[str]) -> str:
        return classify_command(command).value

    def run(self, command: list[str], timeout_seconds: int = 30) -> ShellResult:
        if not command:
            raise ValueError("Command cannot be empty.")
        if command[0].lower() not in self.SAFE_PREFIXES:
            raise ValueError(f"Command not allowed: {command[0]}")
        risk = self.classify_risk(command)
        if not can_auto_run(command):
            raise ValueError(f"Refusing to run non-safe command with risk '{risk}'.")

        result = subprocess.run(command, cwd=self.repo_root, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        return ShellResult(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)