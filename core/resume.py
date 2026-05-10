from __future__ import annotations

import json
from pathlib import Path

from core.errors import ResumeError


def list_runs(repo_root: str | Path) -> list[str]:
    runs_dir = Path(repo_root) / ".ai-team" / "runs"
    if not runs_dir.exists():
        return []
    return sorted(item.name for item in runs_dir.iterdir() if item.is_dir())


def load_run(repo_root: str | Path, run_id: str) -> dict:
    run_dir = Path(repo_root) / ".ai-team" / "runs" / run_id
    run_json = run_dir / "run.json"
    if not run_json.exists():
        raise ResumeError(f"Run '{run_id}' not found.")
    return json.loads(run_json.read_text(encoding="utf-8"))


def load_final_report(repo_root: str | Path, run_id: str) -> dict:
    run_dir = Path(repo_root) / ".ai-team" / "runs" / run_id
    report_file = run_dir / "final_report.json"
    if not report_file.exists():
        raise ResumeError(f"Final report missing for run '{run_id}'.")
    return json.loads(report_file.read_text(encoding="utf-8"))