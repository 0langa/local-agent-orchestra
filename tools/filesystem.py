from __future__ import annotations

from pathlib import Path


class RepoSandbox:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def resolve(self, relative_path: str | Path) -> Path:
        candidate = (self.repo_root / relative_path).resolve()
        if candidate != self.repo_root and self.repo_root not in candidate.parents:
            raise ValueError(f"Path escapes repo root: {relative_path}")
        return candidate


class FilesystemTool:
    def __init__(self, repo_root: str | Path) -> None:
        self.sandbox = RepoSandbox(repo_root)

    def list_dir(self, relative_path: str = ".") -> list[str]:
        path = self.sandbox.resolve(relative_path)
        return sorted(item.name for item in path.iterdir())

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str:
        path = self.sandbox.resolve(relative_path)
        return path.read_text(encoding=encoding)

    def search(self, needle: str, relative_path: str = ".") -> list[str]:
        base = self.sandbox.resolve(relative_path)
        matches: list[str] = []
        for file_path in base.rglob("*"):
            if file_path.is_file():
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if needle in text:
                    matches.append(str(file_path.relative_to(self.sandbox.repo_root)).replace("\\", "/"))
        return sorted(matches)