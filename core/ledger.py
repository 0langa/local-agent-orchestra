from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "run"


@dataclass(frozen=True)
class RunLedger:
    repo_root: Path
    run_dir: Path

    @classmethod
    def create(cls, repo_root: Path, purpose: str) -> "RunLedger":
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = repo_root / ".ai-team" / "runs" / f"{timestamp}-{slugify(purpose)}"
        run_dir.mkdir(parents=True, exist_ok=True)
        for filename in ("tool_calls.jsonl", "state_transitions.jsonl"):
            (run_dir / filename).touch(exist_ok=True)
        return cls(repo_root=repo_root, run_dir=run_dir)

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, str):
            repo_prefix = str(self.repo_root)
            if value == repo_prefix:
                return "${REPO_ROOT}"
            if value.startswith(repo_prefix + "\\") or value.startswith(repo_prefix + "/"):
                relative = value[len(repo_prefix) :].lstrip("\\/")
                return f"${{REPO_ROOT}}/{relative.replace('\\', '/')}"
        return value

    def write_json(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.run_dir / name
        sanitized = self._sanitize_value(payload)
        path.write_text(json.dumps(sanitized, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_text(self, name: str, content: str) -> Path:
        path = self.run_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def append_jsonl(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.run_dir / name
        sanitized = self._sanitize_value(payload)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sanitized, sort_keys=True) + "\n")
        return path
