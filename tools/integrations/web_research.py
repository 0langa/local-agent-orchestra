from __future__ import annotations

from pathlib import Path


class WebResearchAdapter:
    def __init__(self, repo_root: str | Path, enabled: bool = False) -> None:
        self.repo_root = Path(repo_root)
        self.enabled = enabled

    @property
    def available(self) -> bool:
        return self.enabled

    def search(self, query: str) -> dict[str, str]:
        if not self.enabled:
            raise RuntimeError("Web research adapter is disabled.")
        return {"query": query, "result": "stub"}