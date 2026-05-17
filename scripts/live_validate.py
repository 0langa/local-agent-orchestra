#!/usr/bin/env python3
r"""Live validation runner for Agentheim baseline evidence.

Records structured evidence for each check:
- command
- provider/profile
- model by role
- repo path
- run ID
- result (passed/failed/skipped)
- artifact path (stdout/stderr logs)
- timestamp
- failure category

Usage:
    python scripts/live_validate.py --repo-root . --test-repo .localtest/test-repo
    python scripts/live_validate.py --only doctor,ping-models --profile azure-real
    powershell -ExecutionPolicy Bypass -File .\devtest\live_validate.ps1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure repo root is on path when script is run directly
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RUN_ID_PATTERNS = [
    re.compile(r'"run_id"\s*:\s*"([^"]+)"'),
    re.compile(r"run_id='([^']+)'"),
    re.compile(r"Run id:\s*([^\r\n]+)"),
]

DEFAULT_MATRIX: dict[str, Any] = {
    "defaults": {
        "repo_root": ".",
        "test_repo": ".localtest/test-repo",
        "python": "python",
        "cli_module": "interfaces.cli.cli",
        "issues_file": "{test_repo}/issues.json",
        "messy_dir": "{test_repo}/messy_files",
    },
    "tests": [
        {
            "id": "doctor",
            "description": "Basic environment + provider health",
            "command": ["{python}", "-m", "{cli_module}", "doctor"],
            "must_contain": ["All checks passed."],
            "timeout_seconds": 120,
            "tags": ["core", "cli"],
        },
        {
            "id": "ping-models",
            "description": "All configured roles respond",
            "command": ["{python}", "-m", "{cli_module}", "ping-models"],
            "must_contain": ["ok"],
            "timeout_seconds": 120,
            "tags": ["core", "cli", "provider"],
        },
        {
            "id": "provider-planner",
            "description": "Planner role connectivity",
            "command": ["{python}", "-m", "{cli_module}", "provider", "test", "--role", "planner"],
            "must_contain": ['"ok": true'],
            "timeout_seconds": 120,
            "tags": ["core", "provider"],
        },
        {
            "id": "provider-executor",
            "description": "Executor role connectivity",
            "command": ["{python}", "-m", "{cli_module}", "provider", "test", "--role", "executor"],
            "must_contain": ['"ok": true'],
            "timeout_seconds": 120,
            "tags": ["core", "provider"],
        },
        {
            "id": "provider-verifier",
            "description": "Verifier role connectivity",
            "command": ["{python}", "-m", "{cli_module}", "provider", "test", "--role", "verifier"],
            "must_contain": ['"ok": true'],
            "timeout_seconds": 120,
            "tags": ["core", "provider"],
        },
        {
            "id": "command-assistant",
            "description": "Generate shell command from prompt",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "command-assistant",
                "--input", "command_description=List Python files under src recursively",
            ],
            "must_contain": ["status='done'"],
            "timeout_seconds": 180,
            "tags": ["preset", "stable"],
        },
        {
            "id": "local-document-chat",
            "description": "RAG over local repo docs",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "local-document-chat",
                "--input", "query=What does this repo do?",
                "--input", "repo={test_repo}",
            ],
            "must_contain": ["status='done'"],
            "timeout_seconds": 180,
            "tags": ["preset", "stable"],
        },
        {
            "id": "codebase-assistant",
            "description": "Coding workflow preset against dummy repo",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "codebase-assistant",
                "--input", "repo={test_repo}",
                "--input", "task=Fix a tiny bug if found and verify it",
                "--input", "mode=ci",
                "--input", "allow_dirty=true",
            ],
            "must_contain": ["status='done'"],
            "timeout_seconds": 240,
            "tags": ["preset", "stable"],
        },
        {
            "id": "context-maintainer",
            "description": "Context maintenance dry-run/patch path",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "context-maintainer",
                "--input", "repo={test_repo}",
            ],
            "must_contain": ["ContextRunReport(", "run_id='"],
            "timeout_seconds": 180,
            "tags": ["preset", "stable"],
        },
        {
            "id": "file-organizer-dry-run",
            "description": "File organizer preview mode",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "file-organizer",
                "--input", "goal=Move .txt files into text and .log files into logs. Do not move any other files.",
                "--input", "target_dir={messy_dir}",
                "--input", "dry_run=true",
            ],
            "must_contain": ["FileOrganizationReport(", "run_id='"],
            "timeout_seconds": 180,
            "tags": ["preset", "beta"],
        },
        {
            "id": "docs-maintainer-plan",
            "description": "Docs maintainer plan mode against dummy repo",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "docs-maintainer",
                "--input", "repo={test_repo}",
                "--input", "apply=false",
            ],
            "must_contain": ["pending_review", "run_id="],
            "timeout_seconds": 180,
            "tags": ["preset", "beta"],
        },
        {
            "id": "github-maintainer",
            "description": "Summarize issues file and draft PR body",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "github-maintainer",
                "--input", "issues_text={issues_file}",
            ],
            "must_contain": ["status='done'"],
            "timeout_seconds": 180,
            "tags": ["preset", "beta"],
        },
        {
            "id": "research-report",
            "description": "Research workflow against dummy repo",
            "command": [
                "{python}", "-m", "{cli_module}", "start", "research-report",
                "--input", "topic=Summarize this repository",
                "--input", "repo={test_repo}",
            ],
            "must_contain": ["ResearchReport(", "topic="],
            "timeout_seconds": 240,
            "tags": ["preset", "beta"],
        },
        {
            "id": "report-command-assistant",
            "description": "CLI report command on command-assistant run",
            "command": [
                "{python}", "-m", "{cli_module}", "report",
                "--repo", "{repo_root}",
                "--run-id", "{run_id:command-assistant}",
            ],
            "requires_run_id_from": "command-assistant",
            "must_contain": ['"status": "completed"'],
            "timeout_seconds": 60,
            "tags": ["followup", "cli"],
        },
        {
            "id": "resume-command-assistant",
            "description": "CLI resume command on command-assistant run",
            "command": [
                "{python}", "-m", "{cli_module}", "resume",
                "--repo", "{repo_root}",
                "--run-id", "{run_id:command-assistant}",
            ],
            "requires_run_id_from": "command-assistant",
            "must_contain": ['"all_success": true'],
            "timeout_seconds": 60,
            "tags": ["followup", "cli", "known-failing"],
        },
        {
            "id": "invalid-role",
            "description": "Provider test rejects invalid role",
            "command": [
                "{python}", "-m", "{cli_module}", "provider", "test",
                "--role", "nonexistent-role",
            ],
            "expect_failure": True,
            "must_contain": ["'nonexistent-role' is not one of"],
            "timeout_seconds": 30,
            "tags": ["safety-negative", "cli"],
        },
        {
            "id": "invalid-profile",
            "description": "Provider test rejects unknown profile",
            "command": [
                "{python}", "-m", "{cli_module}", "provider", "test",
                "--profile", "nonexistent-profile-12345",
                "--role", "planner",
            ],
            "expect_failure": True,
            "must_contain": ["Unknown profile"],
            "timeout_seconds": 30,
            "tags": ["safety-negative", "cli"],
        },
        {
            "id": "copy-denied",
            "description": "Filesystem copy outside workspace requires approval and aborts without stdin",
            "command": [
                "{python}", "-m", "{cli_module}", "copy",
                "/etc/passwd",
                "C:\\temp\\live_validate_denied_test.txt",
            ],
            "expect_failure": True,
            "must_contain": ["Approval required", "Aborted"],
            "timeout_seconds": 30,
            "tags": ["safety-negative", "cli"],
        },
    ],
}


@dataclass
class TestResult:
    test_id: str
    description: str
    status: str
    exit_code: int | None
    duration_seconds: float
    run_id: str | None
    missing_patterns: list[str]
    error: str | None
    stdout_path: str
    stderr_path: str
    tags: list[str]
    timestamp: str = ""
    provider_profile: str = ""
    provider_type: str = ""
    model: str = ""
    repo_path: str = ""
    artifact_path: str = ""
    failure_category: str = ""
    attempts: int = 0


def load_matrix(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return DEFAULT_MATRIX
    return json.loads(path.read_text(encoding="utf-8"))


def detect_provider_info() -> dict[str, str]:
    """Query current Agentheim config for active profile, provider type, and model."""
    info: dict[str, str] = {
        "profile": "unknown",
        "provider_type": "unknown",
        "model": "unknown",
    }
    try:
        from config.config import load_team_config, resolve_profile_name

        info["profile"] = resolve_profile_name(None)
        team = load_team_config()
        by_role = team.by_role()
        planner = by_role.get("planner")
        if planner:
            info["provider_type"] = str(planner.provider_type)
            info["model"] = str(planner.model)
    except Exception:
        pass
    return info


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live Agentheim validation and record structured evidence.")
    parser.add_argument("--matrix", default=None, help="Path to JSON matrix file (default: built-in matrix)")
    parser.add_argument("--output-root", default=str(Path(".localtest/runs")))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--test-repo", default=".localtest/test-repo")
    parser.add_argument("--profile", default="", help="Override provider profile name for evidence logging.")
    parser.add_argument("--only", default="", help="Comma-separated test ids to run.")
    parser.add_argument("--skip", default="", help="Comma-separated test ids to skip.")
    parser.add_argument("--include-tags", default="", help="Comma-separated tags to require.")
    parser.add_argument("--exclude-tags", default="destructive", help="Comma-separated tags to skip.")
    parser.add_argument("--max-attempts", type=int, default=2, help="Max attempts per test (default 2).")
    parser.add_argument("--delay-between-tests", type=int, default=0, help="Seconds to sleep between tests (default 0).")
    parser.add_argument("--delay-between-attempts", type=int, default=0, help="Seconds to sleep between retry attempts (default 0).")
    parser.add_argument("--list", action="store_true", help="List tests and exit.")
    return parser.parse_args()


def split_csv(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def should_run(test: dict[str, Any], only: set[str], skip: set[str], include_tags: set[str], exclude_tags: set[str]) -> bool:
    test_id = str(test["id"])
    tags = set(str(tag) for tag in test.get("tags", []))
    if only and test_id not in only:
        return False
    if test_id in skip:
        return False
    if include_tags and not include_tags.issubset(tags):
        return False
    if exclude_tags and tags.intersection(exclude_tags):
        return False
    return True


def resolve_text(value: str, context: dict[str, str], results_by_id: dict[str, TestResult]) -> str:
    pattern = re.compile(r"\{([^{}]+)\}")

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key.startswith("run_id:"):
            source_id = key.split(":", 1)[1]
            source = results_by_id.get(source_id)
            if source and source.run_id:
                return source.run_id
            raise KeyError(f"run id not available for test '{source_id}'")
        if key in context:
            return context[key]
        raise KeyError(f"unknown placeholder '{key}'")

    resolved = value
    for _ in range(8):
        updated = pattern.sub(repl, resolved)
        if updated == resolved:
            return resolved
        resolved = updated
    return resolved


def resolve_command(command: list[str], context: dict[str, str], results_by_id: dict[str, TestResult]) -> list[str]:
    return [resolve_text(part, context, results_by_id) for part in command]


def extract_run_id(text: str) -> str | None:
    for pattern in RUN_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def classify_failure(stdout: str, stderr: str, exit_code: int | None, missing_patterns: list[str], error: str | None) -> str:
    combined = (stdout or "") + "\n" + (stderr or "")
    if error and "timed out" in error.lower():
        return "timeout"
    if "AuthenticationError" in combined or ("auth" in combined.lower() and "fail" in combined.lower()):
        return "provider_auth"
    if "RateLimitError" in combined or "rate limit" in combined.lower() or "quota" in combined.lower() or "429" in combined or "too many requests" in combined.lower():
        return "provider_rate_limit"
    if "ProviderError" in combined or "provider error" in combined.lower():
        return "provider_error"
    if "PolicyDecision.denied" in combined or "policy_denied" in combined.lower():
        return "policy_denial"
    if "approval_required" in combined.lower() or "approval required" in combined.lower():
        return "approval_required"
    if "MalformedModelOutput" in combined or "json decode" in combined.lower():
        return "model_misformat"
    if missing_patterns:
        return "missing_output"
    if exit_code not in (0, None):
        return "exit_failure"
    return "unexpected_error"


def run_single_attempt(
    test: dict[str, Any],
    context: dict[str, str],
    results_by_id: dict[str, TestResult],
    repo_root: str,
    env: dict[str, str],
) -> tuple[str, str, int | None, float, str | None]:
    timeout_seconds = int(test.get("timeout_seconds", 120))
    start = time.perf_counter()
    try:
        command = resolve_command(test["command"], context, results_by_id)
        proc = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            env=env,
        )
        duration = time.perf_counter() - start
        return proc.stdout or "", proc.stderr or "", proc.returncode, duration, None
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - start
        return exc.stdout or "", exc.stderr or "", None, duration, f"timed out after {timeout_seconds}s"
    except Exception as exc:
        duration = time.perf_counter() - start
        return "", str(exc), None, duration, f"runner exception: {exc}"


def build_result(
    test: dict[str, Any],
    stdout_text: str,
    stderr_text: str,
    exit_code: int | None,
    duration: float,
    error: str | None,
    stdout_path: Path,
    stderr_path: Path,
) -> TestResult:
    test_id = str(test["id"])
    description = str(test.get("description", ""))
    tags = [str(tag) for tag in test.get("tags", [])]
    combined = stdout_text + "\n" + stderr_text
    run_id = extract_run_id(combined)
    missing_patterns = [
        pattern
        for pattern in [str(item) for item in test.get("must_contain", [])]
        if pattern not in combined
    ]
    expect_failure = test.get("expect_failure", False)
    if expect_failure:
        status = "passed" if not missing_patterns else "failed"
    else:
        status = "passed" if exit_code == 0 and not missing_patterns else "failed"
    if error is None and exit_code not in (0, None):
        error = f"exit code {exit_code}"
    elif error is None and missing_patterns:
        error = "missing expected output"

    category = classify_failure(stdout_text, stderr_text, exit_code, missing_patterns, error)
    if status == "passed":
        category = ""

    return TestResult(
        test_id=test_id,
        description=description,
        status=status,
        exit_code=exit_code,
        duration_seconds=duration,
        run_id=run_id,
        missing_patterns=missing_patterns,
        error=error,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        tags=tags,
        failure_category=category,
    )


def write_evidence_jsonl(path: Path, results: list[TestResult]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(asdict(r), default=str) + "\n")


def write_summary_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_summary_md(path: Path, payload: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Live Validation Summary")
    lines.append("")
    lines.append(f"- Started: `{payload['started_at']}`")
    lines.append(f"- Finished: `{payload['finished_at']}`")
    lines.append(f"- Profile: `{payload['provider_profile']}`")
    lines.append(f"- Provider type: `{payload['provider_type']}`")
    lines.append(f"- Model: `{payload['model']}`")
    lines.append(f"- Repo root: `{payload['repo_root']}`")
    lines.append(f"- Test repo: `{payload['test_repo']}`")
    lines.append(f"- Total: `{payload['counts']['total']}`")
    lines.append(f"- Passed: `{payload['counts']['passed']}`")
    lines.append(f"- Failed: `{payload['counts']['failed']}`")
    lines.append(f"- Skipped: `{payload['counts']['skipped']}`")
    lines.append("")
    lines.append("| Test | Status | Category | Seconds | Run ID | Attempts | Notes |")
    lines.append("|------|--------|----------|---------|--------|----------|-------|")
    for item in payload["results"]:
        notes: list[str] = []
        if item["missing_patterns"]:
            notes.append("missing: " + ", ".join(item["missing_patterns"]))
        if item["error"]:
            notes.append(item["error"])
        lines.append(
            f"| `{item['test_id']}` | `{item['status']}` | `{item['failure_category']}` | "
            f"`{item['duration_seconds']:.2f}` | `{item['run_id'] or ''}` | `{item['attempts']}` | {'; '.join(notes)} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _switch_profile(repo_root: str, profile: str | None) -> tuple[bool, str | None]:
    """Temporarily switch active provider profile for the project. Returns (switched, original_profile)."""
    if not profile:
        return False, None
    pointer_path = Path(repo_root) / ".ai-team" / "provider-profile.json"
    original: str | None = None
    if pointer_path.exists():
        try:
            original = json.loads(pointer_path.read_text(encoding="utf-8")).get("profile")
        except Exception:
            pass
    if original == profile:
        return False, original
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(json.dumps({"profile": profile}, indent=2) + "\n", encoding="utf-8")
    return True, original


def _restore_profile(repo_root: str, original: str | None) -> None:
    pointer_path = Path(repo_root) / ".ai-team" / "provider-profile.json"
    if original is None:
        if pointer_path.exists():
            pointer_path.unlink()
    else:
        pointer_path.write_text(json.dumps({"profile": original}, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    matrix_path = Path(args.matrix) if args.matrix else None
    matrix = load_matrix(matrix_path)
    defaults = dict(matrix.get("defaults", {}))

    repo_root = str(Path(args.repo_root or defaults.get("repo_root", ".")).resolve())
    test_repo = str(Path(args.test_repo or defaults.get("test_repo", ".localtest/test-repo")).resolve())
    defaults["repo_root"] = repo_root
    defaults["test_repo"] = test_repo

    tests = matrix.get("tests", [])
    only = split_csv(args.only)
    skip = split_csv(args.skip)
    include_tags = split_csv(args.include_tags)
    exclude_tags = split_csv(args.exclude_tags)

    if args.list:
        for test in tests:
            tags = ",".join(test.get("tags", []))
            print(f"{test['id']}: {test.get('description', '')} [{tags}]")
        return 0

    selected = [test for test in tests if should_run(test, only, skip, include_tags, exclude_tags)]
    output_root = Path(args.output_root).resolve()
    run_dir = output_root / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-live-validation")
    run_dir.mkdir(parents=True, exist_ok=True)

    context = {key: str(value) for key, value in defaults.items()}
    started_at = datetime.now(timezone.utc).isoformat()
    results: list[TestResult] = []
    results_by_id: dict[str, TestResult] = {}

    provider_info = detect_provider_info()
    switched, original_profile = _switch_profile(repo_root, args.profile)
    if args.profile:
        provider_info = detect_provider_info()

    print(f"Run dir: {run_dir}")
    print(f"Profile: {provider_info['profile']} | Provider: {provider_info['provider_type']} | Model: {provider_info['model']}")
    print(f"Selected tests: {len(selected)}")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        for index, test in enumerate(selected, start=1):
            test_id = str(test["id"])
            description = str(test.get("description", ""))
            print(f"[{index}/{len(selected)}] {test_id} :: {description}")

            stdout_path = run_dir / f"{index:02d}-{test_id}.stdout.log"
            stderr_path = run_dir / f"{index:02d}-{test_id}.stderr.log"

            requires_run_id_from = test.get("requires_run_id_from")
            if requires_run_id_from:
                source = results_by_id.get(str(requires_run_id_from))
                if not source or not source.run_id:
                    result = TestResult(
                        test_id=test_id,
                        description=description,
                        status="skipped",
                        exit_code=None,
                        duration_seconds=0.0,
                        run_id=None,
                        missing_patterns=[],
                        error=f"missing run_id from '{requires_run_id_from}'",
                        stdout_path=str(stdout_path),
                        stderr_path=str(stderr_path),
                        tags=[str(tag) for tag in test.get("tags", [])],
                        failure_category="skipped",
                        provider_profile=provider_info["profile"],
                        provider_type=provider_info["provider_type"],
                        model=provider_info["model"],
                        repo_path=repo_root,
                        artifact_path=str(run_dir),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    results.append(result)
                    results_by_id[test_id] = result
                    stdout_path.write_text("", encoding="utf-8")
                    stderr_path.write_text("", encoding="utf-8")
                    continue

            final_result: TestResult | None = None
            for attempt in range(1, args.max_attempts + 1):
                stdout_text, stderr_text, exit_code, duration, error = run_single_attempt(
                    test, context, results_by_id, repo_root, env
                )
                attempt_result = build_result(test, stdout_text, stderr_text, exit_code, duration, error, stdout_path, stderr_path)
                attempt_result.attempts = attempt
                final_result = attempt_result
                if attempt_result.status == "passed":
                    break
                if attempt < args.max_attempts and args.delay_between_attempts > 0:
                    time.sleep(args.delay_between_attempts)

            assert final_result is not None
            final_result.provider_profile = provider_info["profile"]
            final_result.provider_type = provider_info["provider_type"]
            final_result.model = provider_info["model"]
            final_result.repo_path = repo_root
            final_result.artifact_path = str(run_dir)
            final_result.timestamp = datetime.now(timezone.utc).isoformat()

            stdout_path.write_text(stdout_text, encoding="utf-8")
            stderr_path.write_text(stderr_text, encoding="utf-8")

            results.append(final_result)
            results_by_id[test_id] = final_result
            print(f"  -> {final_result.status} ({final_result.failure_category or 'ok'}) in {final_result.duration_seconds:.1f}s")
            if index < len(selected) and args.delay_between_tests > 0:
                time.sleep(args.delay_between_tests)
    finally:
        if switched:
            _restore_profile(repo_root, original_profile)

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "started_at": started_at,
        "finished_at": finished_at,
        "provider_profile": provider_info["profile"],
        "provider_type": provider_info["provider_type"],
        "model": provider_info["model"],
        "repo_root": repo_root,
        "test_repo": test_repo,
        "artifact_path": str(run_dir),
        "counts": {
            "total": len(results),
            "passed": sum(1 for item in results if item.status == "passed"),
            "failed": sum(1 for item in results if item.status == "failed"),
            "skipped": sum(1 for item in results if item.status == "skipped"),
        },
        "results": [
            {
                "test_id": item.test_id,
                "description": item.description,
                "status": item.status,
                "exit_code": item.exit_code,
                "duration_seconds": item.duration_seconds,
                "run_id": item.run_id,
                "missing_patterns": item.missing_patterns,
                "error": item.error,
                "stdout_path": item.stdout_path,
                "stderr_path": item.stderr_path,
                "tags": item.tags,
                "timestamp": item.timestamp,
                "provider_profile": item.provider_profile,
                "provider_type": item.provider_type,
                "model": item.model,
                "repo_path": item.repo_path,
                "artifact_path": item.artifact_path,
                "failure_category": item.failure_category,
                "attempts": item.attempts,
            }
            for item in results
        ],
    }
    write_summary_json(run_dir / "summary.json", summary)
    write_summary_md(run_dir / "summary.md", summary)
    write_evidence_jsonl(run_dir / "evidence.jsonl", results)

    print("")
    print(f"Passed: {summary['counts']['passed']}")
    print(f"Failed: {summary['counts']['failed']}")
    print(f"Skipped: {summary['counts']['skipped']}")
    print(f"Evidence: {run_dir / 'evidence.jsonl'}")
    print(f"Summary: {run_dir / 'summary.md'}")
    return 0 if summary["counts"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
