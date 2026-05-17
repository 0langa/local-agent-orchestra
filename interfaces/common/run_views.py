"""Shared run view helpers for CLI, API, and Web UI."""

from __future__ import annotations

from pathlib import Path

from core.public_api import build_live_run_summary, build_run_summary
from core.public_api import RunRecord


def run_status_payload(repo_root: Path, run_id: str, record: RunRecord | None = None):
    """Build a canonical run status payload used by API and Web UI."""
    if record is not None:
        return build_live_run_summary(repo_root, run_id, record)
    return build_run_summary(repo_root, run_id)
