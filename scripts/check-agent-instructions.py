from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTRUCTIONS = ROOT / ".github" / "instructions"
AGENT_FILE = ROOT / ".github" / "agents" / "agentheim-autonomous-engineer.agent.md"
CHANGELOG = ROOT / "docs" / "CHANGELOG.md"
REQUIRED_INSTRUCTIONS = [
    "00-instruction-priority.md",
    "README.md",
    "01-doctrine.md",
    "02-forbidden-behaviors.md",
    "03-traceability.md",
    "04-AICtx-integration.md",
    "05-documentation-integrity.md",
    "06-tooling-and-verification.md",
    "07-chat-output.md",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_instruction_files() -> None:
    if not INSTRUCTIONS.is_dir():
        fail(".github/instructions directory is missing")
    for name in REQUIRED_INSTRUCTIONS:
        path = INSTRUCTIONS / name
        if not path.exists():
            fail(f"missing instruction file: {path.relative_to(ROOT)}")
        if not read(path).strip():
            fail(f"instruction file is empty: {path.relative_to(ROOT)}")


def check_agent_references() -> None:
    if not AGENT_FILE.exists():
        fail(f"missing main agent file: {AGENT_FILE.relative_to(ROOT)}")
    text = read(AGENT_FILE)
    for name in REQUIRED_INSTRUCTIONS:
        if name not in text:
            fail(f"main agent does not reference {name}")


def markdown_files() -> list[Path]:
    files = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "AGENTS.md",
    ]
    files += sorted((ROOT / "docs").glob("*.md"))
    files += sorted((ROOT / ".github").glob("*.md"))
    files += sorted((ROOT / ".github" / "agents").glob("*.md"))
    files += sorted((ROOT / ".github" / "instructions").glob("*.md"))
    files += sorted((ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.md"))
    return [path for path in files if path.exists()]


LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def check_markdown_links() -> None:
    broken: list[str] = []
    for path in markdown_files():
        text = read(path)
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = target.split("#", 1)[0].strip()
            if not target:
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if target.startswith("/"):
                candidate = ROOT / target.lstrip("/")
            else:
                candidate = path.parent / target
            if not candidate.resolve().exists():
                broken.append(f"{path.relative_to(ROOT)} -> {raw_target}")
    if broken:
        fail("broken local Markdown links:\n" + "\n".join(broken))


def check_no_active_roadmap_links() -> None:
    offenders: list[str] = []
    for path in markdown_files():
        if path == CHANGELOG:
            continue
        text = read(path)
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split("#", 1)[0].strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            normalized = target.replace("\\", "/").lstrip("/")
            if normalized.startswith("docs/roadmap") or normalized.startswith("roadmap/") or "/docs/roadmap/" in normalized:
                offenders.append(f"{path.relative_to(ROOT)} -> {raw_target}")
    if offenders:
        fail("active docs still link to deleted roadmap paths:\n" + "\n".join(offenders))


def check_changelog_policy() -> None:
    if not CHANGELOG.exists():
        fail("docs/CHANGELOG.md is missing")
    if (ROOT / "CHANGELOG.md").exists():
        fail("root CHANGELOG.md must not exist; docs/CHANGELOG.md is canonical")


def check_aictx_state() -> None:
    # Old local AICtx/ reference copy was removed; editable install from ../AICtx is now used.
    if (ROOT / "AICtx").exists():
        fail("AICtx/ local reference copy must be removed; use editable install from ../AICtx")


def main() -> int:
    check_required_instruction_files()
    check_agent_references()
    check_markdown_links()
    check_no_active_roadmap_links()
    check_changelog_policy()
    check_aictx_state()
    print("agent instruction checks ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
