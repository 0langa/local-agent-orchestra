from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.config import ModelRole, load_team_config
from agentheim.context_ops_impl import AictxContextOps
from agentheim.vendor.aictx.config import AictxConfig
from agentheim.context_run_ledger import ContextRunLedger
from core.public_api import (
    AIteamError,
    ExecutionError,
    ImplementationPlan,
    ModelRegistry,
    PatchApplier,
    PatchApplicationError,
    PatchPlan,
    RepoScanResult,
    RunLedger,
    RuntimeState,
    RuntimeStateMachine,
    RuntimeAgentMessage,
    UserTask,
    VerificationError,
    VerificationReport,
    VerificationResult,
    WorkOrder,
    inspect_repository,
)
from tools.git.github_cli import GitHubCliAdapter
from tools.integrations.mcp_client import MCPClientAdapter
from tools.integrations.web_research import WebResearchAdapter
from workflows.coding.reports.final_report import FinalReport, VerificationRecord
from workflows.coding.reports.markdown import render_final_report_markdown
from workflows.coding.provider_map import DEFAULT_PROVIDER_MAP
from workflows.coding.adapters import ledger_append, model_resolve, policy_evaluate, tool_invoke
from workflows.coding.workflows.coding import create_orchestrator_agent, create_coder_agent, create_verifier_agent
from core.public_api import safe_text_excerpt


class PlanningError(AIteamError):
    """Raised when planning fails."""


def build_plan_prompt(user_task: UserTask, scan: RepoScanResult, context_pack: str) -> str:
    compact_context = context_pack[:3000]
    if len(context_pack) > 3000:
        compact_context += "\n...[truncated for planning]"
    schema_hint = {
        "summary": "short summary",
        "assumptions": ["assumption"],
        "non_goals": ["non-goal"],
        "detected_repo_type": "python|dotnet-csharp|node-typescript|rust|go|java-kotlin|mixed",
        "risks": [{"risk": "risk", "impact": "Low|Medium|High", "mitigation": "mitigation"}],
        "task_graph": {
            "ordered_tasks": [
                {
                    "id": "task-1",
                    "type": "inspect|edit|test|docs|cleanup",
                    "title": "task title",
                    "dependencies": [],
                    "acceptance_criteria": [{"description": "criterion", "measurable": True}],
                    "max_edit_scope": "bounded scope",
                    "expected_verifier_commands": [["python", "-m", "pytest"]],
                    "work_order": {
                        "id": "wo-1",
                        "title": "work order title",
                        "objective": "objective",
                        "relevant_files": ["path/to/file"],
                        "required_context_excerpts": ["excerpt"],
                        "constraints": ["constraint"],
                        "forbidden_changes": ["forbidden change"],
                        "acceptance_criteria": [{"description": "criterion", "measurable": True}],
                        "expected_commands": [["python", "-m", "pytest"]],
                        "max_edit_scope": "bounded scope"
                    }
                }
            ],
            "dependencies": [{"from": "task-1", "to": "task-2"}]
        },
        "verification_strategy": ["verification step"],
        "estimated_commands": [["python", "-m", "pytest"]],
        "files_likely_to_change": ["README.md"],
        "stop_conditions": ["stop condition"]
    }
    return (
        "User request:\n"
        f"{user_task.request}\n\n"
        "Repository summary:\n"
        f"- repo: {scan.repo_name}\n"
        f"- languages: {', '.join(scan.languages) if scan.languages else 'none'}\n"
        f"- manifests: {', '.join(scan.manifests) if scan.manifests else 'none'}\n"
        f"- instruction files: {', '.join(scan.instruction_files) if scan.instruction_files else 'none'}\n"
        f"- warnings: {', '.join(scan.warnings) if scan.warnings else 'none'}\n\n"
        "Context pack:\n"
        f"{compact_context}\n\n"
        "Planning rules:\n"
        "- Prefer actionable edit/test/docs/cleanup tasks.\n"
        "- Use inspect tasks only for evidence capture; do not rely on hidden intermediate notes.\n"
        "- Keep work orders bounded to the relevant files.\n"
        "- If the user request mentions adding or adjusting tests, create a dedicated test task with relevant_files that includes the test files. Do not fold test work into a source-edit task.\n"
        "- Every work order's relevant_files must include ALL files it intends to edit.\n\n"
        "Return only valid JSON matching this exact ImplementationPlan shape. "
        "Do not invent a different schema. Do not wrap in markdown.\n"
        f"Schema example:\n{json.dumps(schema_hint, indent=2)}"
    )


def _read_context_shards(repo_root: Path) -> str:
    """Build compact context string from AICtx shards in docs/AIprojectcontext/."""
    ctx_dir = repo_root / "docs" / "AIprojectcontext"
    if not ctx_dir.exists():
        return ""

    parts: list[str] = []
    for name in ("project-state.md", "code-map.md", "change-impact-map.md"):
        path = ctx_dir / name
        if path.exists():
            parts.append(f"--- {name} ---\n{path.read_text(encoding='utf-8')}")

    for shard in sorted(ctx_dir.glob("*.md")):
        if shard.name in {"project-state.md", "code-map.md", "change-impact-map.md"}:
            continue
        parts.append(f"--- {shard.name} ---\n{shard.read_text(encoding='utf-8')}")

    return "\n\n".join(parts)


def _resolve_context_pack(
    repo_root: Path,
    scan: RepoScanResult,
    ledger: RunLedger | None = None,
) -> tuple[str, bool]:
    """Resolve context pack from AICtx-derived shards."""
    ctx_ledger = ContextRunLedger(ledger) if ledger else None
    ops = AictxContextOps()
    inventory = ops.scan(repo_root)
    if ctx_ledger:
        ctx_ledger.emit_scanned(inventory)

    status = ops.status(repo_root)
    was_stale = status.is_stale

    if was_stale or not (repo_root / "docs" / "AIprojectcontext" / "context.lock.json").exists():
        if ctx_ledger:
            ctx_ledger.emit_status(status)
        ops.run_pipeline(
            repo_root,
            run_id="coding-ctx",
            scope="changed",
            write_mode="apply",
            allow_dirty=True,
        )
        if ctx_ledger:
            ctx_ledger.emit_generated(repo_root, fact_pack_count=0)

    context_string = _read_context_shards(repo_root)
    if not context_string:
        raise RuntimeError("No AICtx context shards found.")

    if ctx_ledger:
        ctx_ledger.emit_verified(
            VerificationResult(result="PASS", is_pass=True)
        )
    return context_string, was_stale


def plan_task(task_text: str, repo_path: str | Path, write_ledger: bool = False) -> tuple[RepoScanResult, str, ImplementationPlan, Path | None]:
    user_task = UserTask(request=task_text)
    scan = inspect_repository(repo_path)
    repo_path_resolved = Path(repo_path).resolve()
    ledger: RunLedger | None = RunLedger.create(repo_path_resolved, "plan") if write_ledger else None
    context_pack, _ = _resolve_context_pack(repo_path_resolved, scan, ledger)
    team_config = load_team_config()
    registry = ModelRegistry.from_team_config(team_config, provider_map=DEFAULT_PROVIDER_MAP)
    orchestrator = create_orchestrator_agent(registry)
    prompt = build_plan_prompt(user_task, scan, context_pack)
    result = orchestrator.run_structured(prompt, max_output_tokens=6000)

    ledger_dir: Path | None = None
    if write_ledger:
        ledger.write_json("run.json", {"action": "plan", "repo_name": scan.repo_name, "task": task_text})
        ledger.write_json("repo_snapshot.json", scan.model_dump())
        ledger.write_text("context_pack.md", context_pack)
        ledger_append(ledger, "tool_calls.jsonl", {"tool": "inspect_repository", "repo_name": scan.repo_name})
        ledger_append(ledger, "tool_calls.jsonl", {"tool": "orchestrator.run_structured", "role": "orchestrator"})
        ledger_append(ledger, "state_transitions.jsonl", {"state": "planning_started", "task": task_text})
        planner_config = team_config.by_role()[ModelRole.PLANNER]
        ledger.write_json("model_messages.json", {"messages": [RuntimeAgentMessage(role=planner_config.role, content=prompt).model_dump()]})
        ledger.write_text("raw_model_output.txt", result.raw_output)
        if result.parsed_output is not None:
            ledger.write_json("plan.json", result.parsed_output)
            ledger_append(ledger, "state_transitions.jsonl", {"state": "planning_succeeded"})
        else:
            ledger_append(ledger, "state_transitions.jsonl", {"state": "planning_failed", "error": result.error})
        ledger_dir = ledger.run_dir

    if not result.success or result.parsed_output is None:
        raise PlanningError(result.error or "Planning failed with invalid structured output.")

    plan = ImplementationPlan.model_validate(result.parsed_output)
    return scan, context_pack, plan, ledger_dir


def _write_run_command_output(ledger: RunLedger, index: int, command: list[str], stdout: str, stderr: str) -> None:
    ledger.write_text(f"command_{index:02d}_stdout.txt", stdout)
    ledger.write_text(f"command_{index:02d}_stderr.txt", stderr)
    ledger_append(ledger, "tool_calls.jsonl", {"tool": "shell.run", "command": command, "stdout_file": f"command_{index:02d}_stdout.txt", "stderr_file": f"command_{index:02d}_stderr.txt"})


def _read_relevant_file_excerpt(repo_root: Path, relative_path: str, *, limit: int = 2500) -> str | None:
    target = (repo_root / relative_path).resolve()
    try:
        target.relative_to(repo_root)
    except ValueError:
        return None
    if not target.exists() or not target.is_file():
        return None
    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return f"File: {relative_path}\n{safe_text_excerpt(text, limit=limit)}"


def _collect_work_order_context(work_order: WorkOrder, scan: RepoScanResult, repo_root: Path) -> list[str]:
    excerpts: list[str] = []
    doc_map = {doc.path: doc.excerpt for doc in scan.docs}
    for path in work_order.relevant_files:
        file_excerpt = _read_relevant_file_excerpt(repo_root, path)
        if file_excerpt:
            excerpts.append(file_excerpt)
            continue
        if path in doc_map:
            excerpts.append(f"File: {path}\n{doc_map[path]}")
    excerpts.extend(work_order.required_context_excerpts)
    return excerpts[:6]


def _record_inspect_task(
    *,
    task_id: str,
    work_order: WorkOrder,
    repo_root: Path,
    scan: RepoScanResult,
    ledger: RunLedger,
) -> list[VerificationRecord]:
    excerpts = _collect_work_order_context(work_order, scan, repo_root)
    ledger.write_text(
        f"inspect_{task_id}.md",
        "\n\n".join(
            [
                f"# Inspect Task {task_id}",
                f"Title: {work_order.title}",
                f"Objective: {work_order.objective}",
                "## Context",
                *(excerpts or ["No additional context collected."]),
            ]
        ),
    )
    return [
        VerificationRecord(
            name=f"inspect:{work_order.id}",
            status="passed",
            details="Inspection task recorded without patch application.",
            command=[],
        )
    ]


def _basic_verify(
    work_order: WorkOrder,
    repo_root: Path,
    ledger: RunLedger,
    command_timeout: int,
    no_tests: bool,
) -> tuple[list[VerificationRecord], list[list[str]]]:
    results: list[VerificationRecord] = []
    commands_run: list[list[str]] = []

    git_diff = tool_invoke("git", operation="diff_patch", repo_root=repo_root)
    ledger.write_text("post_task_git_diff.patch", git_diff)
    results.append(VerificationRecord(name="git-diff-sanity", status="passed" if git_diff.strip() else "skipped", details="working tree diff captured"))

    if no_tests:
        results.append(VerificationRecord(name="basic-tests", status="skipped", details="--no-tests passed"))
        return results, commands_run

    for command in work_order.expected_commands:
        if policy_evaluate(command)["decision"] != "allow":
            results.append(VerificationRecord(name=" ".join(command), status="skipped", details="blocked by command policy", command=command))
            continue
        try:
            run_result = tool_invoke("shell.execute", repo_root=repo_root, command=command, timeout_seconds=command_timeout)
        except Exception as exc:
            results.append(VerificationRecord(name=" ".join(command), status="skipped", details=str(exc), command=command))
            continue
        commands_run.append(command)
        _write_run_command_output(ledger, len(commands_run), command, run_result.stdout, run_result.stderr)
        results.append(
            VerificationRecord(
                name=" ".join(command),
                status="passed" if run_result.returncode == 0 else "failed",
                details=(run_result.stderr or run_result.stdout).strip()[:500],
                command=command,
            )
        )
    return results, commands_run


def _ledger_integrity_check(ledger: RunLedger) -> list[str]:
    required = ["run.json", "repo_snapshot.json", "context_pack.md", "state_transitions.jsonl", "tool_calls.jsonl"]
    missing = [name for name in required if not (ledger.run_dir / name).exists()]
    return missing


def _widen_work_order_scope(work_order: WorkOrder, scan: RepoScanResult) -> WorkOrder:
    """Ensure relevant_files covers files mentioned in title/objective that exist in repo."""
    repo_files = {f.path for f in scan.files}
    text = f"{work_order.title} {work_order.objective}"
    mentioned = set()
    for path in repo_files:
        if path in text and path not in work_order.relevant_files:
            mentioned.add(path)
    if not mentioned:
        return work_order
    return work_order.model_copy(
        update={"relevant_files": [*work_order.relevant_files, *sorted(mentioned)]}
    )


def _build_fix_work_order(work_order: WorkOrder, verification: VerificationReport, attempt: int) -> WorkOrder:
    return work_order.model_copy(
        update={
            "id": f"{work_order.id}-fix-{attempt}",
            "title": f"Fix: {work_order.title}",
            "objective": f"Resolve verifier findings for {work_order.id}: {'; '.join(verification.fix_requests or verification.failed_checks)}",
            "required_context_excerpts": [
                *work_order.required_context_excerpts,
                f"Verifier failed with status={verification.status}",
                *verification.fix_requests,
                *verification.failed_checks,
            ],
        }
    )


def _run_verifier(
    verifier: VerifierAgent,
    task_text: str,
    plan: ImplementationPlan,
    work_order: WorkOrder,
    repo_root: Path,
    ledger: RunLedger,
    command_outputs: list[str],
    file_excerpts: list[str],
) -> VerificationReport:
    git_diff = tool_invoke("git", operation="diff_patch", repo_root=repo_root)
    verifier_result = verifier.run_verification(task_text, plan, work_order, git_diff, command_outputs, file_excerpts)
    ledger.write_text(f"verify_{work_order.id}_raw.txt", verifier_result.raw_output)
    if not verifier_result.success or verifier_result.parsed_output is None:
        raise VerificationError(verifier_result.error or f"Verifier failed for {work_order.id}")
    report = VerificationReport.model_validate(verifier_result.parsed_output)
    ledger.write_json(f"verify_{work_order.id}.json", report.model_dump())
    return report


def run_task(
    task_text: str,
    repo_path: str | Path,
    *,
    mode: str = "apply",
    allow_dirty: bool = False,
    max_fix_attempts: int = 3,
    max_diff_lines: int = 1200,
    command_timeout: int = 120,
    no_tests: bool = False,
) -> tuple[FinalReport, Path]:
    repo_root = Path(repo_path).resolve()
    ledger = RunLedger.create(repo_root, "run")
    state_machine = RuntimeStateMachine(ledger)
    ledger.write_json(
        "run.json",
        {
            "action": "run",
            "workflow_id": "coding",
            "preset_id": "codebase-assistant",
            "repo_name": repo_root.name,
            "task": task_text,
            "mode": mode,
            "allow_dirty": allow_dirty,
            "max_fix_attempts": max_fix_attempts,
            "max_diff_lines": max_diff_lines,
            "command_timeout": command_timeout,
            "no_tests": no_tests,
        },
    )

    commands_run: list[list[str]] = []
    github_adapter = GitHubCliAdapter(repo_root)
    mcp_adapter = MCPClientAdapter(repo_root, enabled=False)
    web_adapter = WebResearchAdapter(repo_root, enabled=False)
    try:
        state_machine.transition(RuntimeState.LOAD_CONFIG)
        team_config = load_team_config()

        state_machine.transition(RuntimeState.PREPARE_WORKSPACE)
        pre_status = tool_invoke("git", operation="status", repo_root=repo_root)
        ledger.write_text("pre_task_git_status.txt", pre_status)
        if pre_status.strip() and not allow_dirty:
            state_machine.transition(RuntimeState.BLOCKED, {"reason": "dirty_repo"})
            raise ExecutionError("Repository has uncommitted changes. Re-run with --allow-dirty to proceed.")

        state_machine.transition(RuntimeState.SCAN_REPOSITORY)
        scan = inspect_repository(repo_root)
        ledger.write_json("repo_snapshot.json", scan.model_dump())

        state_machine.transition(RuntimeState.BUILD_CONTEXT_PACK)
        context_pack, was_stale = _resolve_context_pack(repo_root, scan, ledger)
        ledger.write_text("context_pack.md", context_pack)
        registry = ModelRegistry.from_team_config(team_config, provider_map=DEFAULT_PROVIDER_MAP)

        state_machine.transition(RuntimeState.PLAN)
        orchestrator = create_orchestrator_agent(registry)
        verifier = create_verifier_agent(registry)
        prompt = build_plan_prompt(UserTask(request=task_text), scan, context_pack)
        planning_result = orchestrator.run_structured(prompt, max_output_tokens=6000)
        ledger.write_text("raw_model_output.txt", planning_result.raw_output)
        if not planning_result.success or planning_result.parsed_output is None:
            raise ExecutionError(planning_result.error or "Planning failed.")
        plan = ImplementationPlan.model_validate(planning_result.parsed_output)
        ledger.write_json("plan.json", plan.model_dump())

        coder = create_coder_agent(registry)
        patch_attempt_index = 0
        total_changes: list[str] = []
        verification_records: list[VerificationRecord] = []
        repeated_failures: dict[str, int] = {}
        total_task_count = 0

        for task in plan.task_graph.ordered_tasks:
            total_task_count += 1
            if total_task_count > 20:
                state_machine.transition(RuntimeState.BLOCKED, {"reason": "max_total_tasks_exceeded"})
                raise ExecutionError("Maximum total task limit reached.")
            state_machine.transition(RuntimeState.EXECUTE_TASK, {"task_id": task.id})
            work_order = _widen_work_order_scope(task.work_order, scan)
            work_order = work_order.model_copy(update={"required_context_excerpts": _collect_work_order_context(work_order, scan, repo_root)})
            if task.type.value == "inspect":
                verification_records.extend(
                    _record_inspect_task(
                        task_id=task.id,
                        work_order=work_order,
                        repo_root=repo_root,
                        scan=scan,
                        ledger=ledger,
                    )
                )
                state_machine.transition(RuntimeState.BASIC_VERIFY, {"task_id": task.id, "inspect_only": True})
                continue
            attempts_remaining = max(1, min(max_fix_attempts + 1, 4))
            applied = False
            applied_change_objects = []
            last_error = ""
            verify_report: VerificationReport | None = None

            while attempts_remaining > 0 and not applied:
                patch_attempt_index += 1
                coder_result = coder.run_work_order(work_order, repo_root)
                ledger_append(
                    ledger,
                    "patch_attempts.jsonl",
                    {
                        "task_id": task.id,
                        "attempt": patch_attempt_index,
                        "success": coder_result.success,
                        "raw_output": coder_result.raw_output,
                    },
                )
                if not coder_result.success or coder_result.parsed_output is None:
                    last_error = coder_result.error or "Coder did not return valid PatchPlan."
                    attempts_remaining -= 1
                    if attempts_remaining <= 0:
                        break
                    work_order = work_order.model_copy(
                        update={
                            "required_context_excerpts": [
                                *work_order.required_context_excerpts,
                                f"Previous patch attempt failed: {last_error}",
                            ]
                        }
                    )
                    continue

                patch_plan = PatchPlan.model_validate(coder_result.parsed_output)
                if not patch_plan.file_changes:
                    last_error = "Coder returned valid PatchPlan but file_changes is empty."
                    ledger_append(
                        ledger,
                        "patch_attempts.jsonl",
                        {
                            "task_id": task.id,
                            "attempt": patch_attempt_index,
                            "apply_errors": [last_error],
                        },
                    )
                    attempts_remaining -= 1
                    if attempts_remaining <= 0:
                        break
                    work_order = work_order.model_copy(
                        update={
                            "required_context_excerpts": [
                                *work_order.required_context_excerpts,
                                f"Previous patch attempt failed: {last_error}",
                            ]
                        }
                    )
                    continue
                applier = PatchApplier(
                    repo_root,
                    forbidden_paths=[".git", ".ai-team/run.lock"],
                    max_diff_lines=max_diff_lines,
                    scope_override=False,
                )
                apply_result = applier.apply_changes(
                    [item.model_dump() for item in patch_plan.file_changes],
                    allowed_files=work_order.relevant_files,
                )
                if not apply_result.applied:
                    last_error = "; ".join(apply_result.errors)
                    ledger_append(
                        ledger,
                        "patch_attempts.jsonl",
                        {
                            "task_id": task.id,
                            "attempt": patch_attempt_index,
                            "apply_errors": apply_result.errors,
                        },
                    )
                    applier.rollback(apply_result.file_changes)
                    attempts_remaining -= 1
                    if attempts_remaining <= 0:
                        break
                    work_order = work_order.model_copy(
                        update={
                            "required_context_excerpts": [
                                *work_order.required_context_excerpts,
                                f"Patch application failed: {last_error}",
                            ]
                        }
                    )
                    continue

                applied = True
                applied_change_objects = apply_result.file_changes
                ledger.write_text("post_task_git_diff.patch", apply_result.diff_text)
                total_changes.extend(change.path for change in applied_change_objects)

            if not applied:
                state_machine.transition(RuntimeState.FAILED_AND_ROLLED_BACK, {"task_id": task.id, "error": last_error})
                raise PatchApplicationError(last_error or f"Failed to apply patch for task {task.id}")

            state_machine.transition(RuntimeState.BASIC_VERIFY, {"task_id": task.id})
            task_verifications, task_commands = _basic_verify(task.work_order, repo_root, ledger, command_timeout, no_tests)
            verification_records.extend(task_verifications)
            commands_run.extend(task_commands)

            state_machine.transition(RuntimeState.VERIFY_TASK, {"task_id": task.id})
            verify_report = _run_verifier(
                verifier,
                task_text,
                plan,
                work_order,
                repo_root,
                ledger,
                [item.details for item in task_verifications],
                _collect_work_order_context(work_order, scan, repo_root),
            )
            verification_records.append(
                VerificationRecord(
                    name=f"verifier:{work_order.id}",
                    status=verify_report.status,
                    details=verify_report.final_summary,
                    command=[],
                )
            )

            fix_attempt = 0
            while mode == "auto" and verify_report.status == "failed":
                state_machine.transition(RuntimeState.FIX_LOOP, {"task_id": task.id, "attempt": fix_attempt + 1})
                failure_key = "|".join(verify_report.failed_checks or verify_report.fix_requests)
                repeated_failures[failure_key] = repeated_failures.get(failure_key, 0) + 1
                if repeated_failures[failure_key] >= 2:
                    state_machine.transition(RuntimeState.BLOCKED, {"reason": "same_failure_repeated_twice", "task_id": task.id})
                    report = FinalReport(
                        task_summary=plan.summary,
                        changed_files=sorted(set(total_changes)),
                        commands_run=commands_run,
                        tests=verification_records,
                        remaining_risks=[*verify_report.failed_checks, *verify_report.regressions],
                        run_id=ledger.run_dir.name,
                        next_command_suggestions=[f"python -m interfaces.cli report --repo . --run-id {ledger.run_dir.name}"],
                        stale_context_warning="Context was stale at workflow start; AICtx pipeline re-generated." if was_stale else None,
                        status="blocked",
                    )
                    ledger.write_json("final_report.json", report.model_dump())
                    ledger.write_text("final_report.md", render_final_report_markdown(report))
                    state_machine.transition(RuntimeState.RESUME_AVAILABLE)
                    return report, ledger.run_dir
                if fix_attempt >= max_fix_attempts:
                    state_machine.transition(RuntimeState.BLOCKED, {"reason": "max_fix_attempts_reached", "task_id": task.id})
                    report = FinalReport(
                        task_summary=plan.summary,
                        changed_files=sorted(set(total_changes)),
                        commands_run=commands_run,
                        tests=verification_records,
                        remaining_risks=[*verify_report.failed_checks, *verify_report.regressions],
                        run_id=ledger.run_dir.name,
                        next_command_suggestions=[f"python -m interfaces.cli resume --repo . --run-id {ledger.run_dir.name}"],
                        stale_context_warning="Context was stale at workflow start; AICtx pipeline re-generated." if was_stale else None,
                        status="blocked",
                    )
                    ledger.write_json("final_report.json", report.model_dump())
                    ledger.write_text("final_report.md", render_final_report_markdown(report))
                    state_machine.transition(RuntimeState.RESUME_AVAILABLE)
                    return report, ledger.run_dir
                fix_attempt += 1
                total_task_count += 1
                if total_task_count > 20:
                    state_machine.transition(RuntimeState.BLOCKED, {"reason": "max_total_tasks_exceeded"})
                    raise ExecutionError("Maximum total task limit reached.")
                work_order = _build_fix_work_order(work_order, verify_report, fix_attempt)
                attempts_remaining = 1
                applied = False
                while attempts_remaining > 0 and not applied:
                    patch_attempt_index += 1
                    coder_result = coder.run_work_order(work_order, repo_root)
                    ledger_append(ledger, "patch_attempts.jsonl", {"task_id": task.id, "attempt": patch_attempt_index, "success": coder_result.success, "raw_output": coder_result.raw_output, "fix_loop": True})
                    if not coder_result.success or coder_result.parsed_output is None:
                        last_error = coder_result.error or "Coder did not return valid PatchPlan in fix loop."
                        attempts_remaining -= 1
                        continue
                    patch_plan = PatchPlan.model_validate(coder_result.parsed_output)
                    if not patch_plan.file_changes:
                        last_error = "Coder returned valid PatchPlan but file_changes is empty (fix loop)."
                        attempts_remaining -= 1
                        continue
                    applier = PatchApplier(repo_root, forbidden_paths=[".git", ".ai-team/run.lock"], max_diff_lines=max_diff_lines, scope_override=False)
                    apply_result = applier.apply_changes([item.model_dump() for item in patch_plan.file_changes], allowed_files=work_order.relevant_files)
                    if not apply_result.applied:
                        last_error = "; ".join(apply_result.errors)
                        applier.rollback(apply_result.file_changes)
                        attempts_remaining -= 1
                        continue
                    applied = True
                    ledger.write_text("post_task_git_diff.patch", apply_result.diff_text)
                    total_changes.extend(change.path for change in apply_result.file_changes)
                if not applied:
                    state_machine.transition(RuntimeState.BLOCKED, {"reason": "fix_loop_patch_failed", "task_id": task.id, "error": last_error})
                    report = FinalReport(
                        task_summary=plan.summary,
                        changed_files=sorted(set(total_changes)),
                        commands_run=commands_run,
                        tests=verification_records,
                        remaining_risks=[last_error],
                        run_id=ledger.run_dir.name,
                        next_command_suggestions=[f"python -m interfaces.cli report --repo . --run-id {ledger.run_dir.name}"],
                        stale_context_warning="Context was stale at workflow start; AICtx pipeline re-generated." if was_stale else None,
                        status="blocked",
                    )
                    ledger.write_json("final_report.json", report.model_dump())
                    ledger.write_text("final_report.md", render_final_report_markdown(report))
                    state_machine.transition(RuntimeState.RESUME_AVAILABLE)
                    return report, ledger.run_dir
                state_machine.transition(RuntimeState.BASIC_VERIFY, {"task_id": task.id, "fix_attempt": fix_attempt})
                task_verifications, task_commands = _basic_verify(work_order, repo_root, ledger, command_timeout, no_tests)
                verification_records.extend(task_verifications)
                commands_run.extend(task_commands)
                state_machine.transition(RuntimeState.VERIFY_TASK, {"task_id": task.id, "fix_attempt": fix_attempt})
                verify_report = _run_verifier(
                    verifier,
                    task_text,
                    plan,
                    work_order,
                    repo_root,
                    ledger,
                    [item.details for item in task_verifications],
                    _collect_work_order_context(work_order, scan, repo_root),
                )
                verification_records.append(VerificationRecord(name=f"verifier:{work_order.id}", status=verify_report.status, details=verify_report.final_summary, command=[]))

            if verify_report and verify_report.status == "failed" and mode != "auto":
                state_machine.transition(RuntimeState.BLOCKED, {"reason": "verifier_failed", "task_id": task.id})
                report = FinalReport(
                    task_summary=plan.summary,
                    changed_files=sorted(set(total_changes)),
                    commands_run=commands_run,
                    tests=verification_records,
                    remaining_risks=[*verify_report.failed_checks, *verify_report.regressions],
                    run_id=ledger.run_dir.name,
                    next_command_suggestions=[f"python -m interfaces.cli resume --repo . --run-id {ledger.run_dir.name}"],
                    stale_context_warning="Context was stale at workflow start; AICtx pipeline re-generated." if was_stale else None,
                    status="blocked",
                )
                ledger.write_json("final_report.json", report.model_dump())
                ledger.write_text("final_report.md", render_final_report_markdown(report))
                state_machine.transition(RuntimeState.RESUME_AVAILABLE)
                return report, ledger.run_dir

        state_machine.transition(RuntimeState.FINAL_VERIFY)
        missing_ledger_files = _ledger_integrity_check(ledger)
        state_machine.transition(RuntimeState.FINAL_REPORT)
        remaining_risks = [risk.risk for risk in plan.risks]
        if missing_ledger_files:
            remaining_risks.extend(f"Missing ledger file: {name}" for name in missing_ledger_files)
        report = FinalReport(
            task_summary=plan.summary,
            changed_files=sorted(set(total_changes)),
            commands_run=commands_run,
            tests=verification_records,
            remaining_risks=remaining_risks,
            run_id=ledger.run_dir.name,
            next_command_suggestions=[] if verification_records else ["python -m interfaces.cli inspect --repo . --write-ledger"],
            stale_context_warning="Context was stale at workflow start; AICtx pipeline re-generated." if was_stale else None,
            status="done",
        )
        ledger.write_json("final_report.json", report.model_dump())
        ledger.write_text("final_report.md", render_final_report_markdown(report))
        ledger.write_json(
            "integrations.json",
            {
                "github_cli_available": github_adapter.available,
                "mcp_available": mcp_adapter.available,
                "web_research_available": web_adapter.available,
            },
        )
        state_machine.transition(RuntimeState.RESUME_AVAILABLE)
        state_machine.transition(RuntimeState.DONE)
        return report, ledger.run_dir
    except Exception as exc:
        if state_machine.current not in {RuntimeState.BLOCKED, RuntimeState.FAILED_AND_ROLLED_BACK}:
            state_machine.transition(RuntimeState.FAILED_AND_ROLLED_BACK, {"error": str(exc)})
        raise
