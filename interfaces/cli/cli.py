from __future__ import annotations

import json
import os
import socket
import sys
from urllib.parse import urlparse
from pathlib import Path
from typing import Any

# Ensure repo root is on sys.path when running this script directly
_repo_root = Path(__file__).resolve().parents[2]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from rich.console import Console
from rich.table import Table
import typer

from config.config import ModelRole, load_team_config
from core.public_api import (
    AIteamError,
    ApprovalRequest,
    ApprovalWorkflow,
    CanonicalRunSummary,
    ConfigError,
    EventType,
    ProviderError,
    PolicyEngine,
    ResumeError,
    RunLedger,
    ToolInvoker,
    build_run_summary,
    build_model_registry,
    interface_policy_config,
    ResumeOrchestrator,
    ToolRegistry,
    WorkflowRunner,
    get_workflow,
    inspect_repository,
    list_resume_runs as list_runs,
    load_run,
)
import importlib.util

from memory.tiers.global_ import GlobalMemory
from presets import PRESET_REGISTRY
from providers.base import ModelRequest
from tools.mcp.client import MCPClient
from tools.mcp.config import load_mcp_config
from workflows.coding.runtime import plan_task, run_task

from interfaces.cli.ctx_commands import ctx_app
from interfaces.cli.provider_commands import provider_app

app = typer.Typer(help="Local-first three-agent runtime.", pretty_exceptions_show_locals=False)
app.add_typer(ctx_app, name="ctx", rich_help_panel="Context")
app.add_typer(provider_app, name="provider", rich_help_panel="Getting Started")
console = Console()

_DOCTOR_REQUIRED_ROLES = (ModelRole.PLANNER, ModelRole.EXECUTOR, ModelRole.VERIFIER)
_DOCTOR_SECRET_AUTH_MODES = {"api_key", "bearer", "x_api_key", "bedrock_api_key"}
_DOCTOR_OPENAI_TYPES = {"openai_v1", "openai_compatible", "azure_foundry"}
_DOCTOR_GOOGLE_TYPES = {"gemini", "vertex_ai"}


def _doctor_is_local_host(host: str | None) -> bool:
    return host in {"localhost", "127.0.0.1", "::1"}


def _doctor_endpoint_target(endpoint: str) -> tuple[str | None, int | None]:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        return None, None
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return parsed.hostname, port


def _doctor_role_coverage(config) -> tuple[str, str]:
    bound_roles = set(config.by_role())
    missing = [role.value for role in _DOCTOR_REQUIRED_ROLES if role not in bound_roles]
    if missing:
        return "WARN", f"missing roles: {', '.join(missing)}"
    return "PASS", "planner, executor, verifier bound"


def _doctor_first_class_lane(config) -> tuple[str, str]:
    providers = list(config.providers.values())
    bound_roles = set(config.by_role())
    missing_roles = [role.value for role in _DOCTOR_REQUIRED_ROLES if role not in bound_roles]
    if missing_roles:
        return "WARN", f"first-class lane blocked by missing roles: {', '.join(missing_roles)}"

    provider_types = {provider.provider_type for provider in providers}
    lane = "advanced/experimental"
    detail = ""

    if provider_types & _DOCTOR_OPENAI_TYPES:
        lane = "openai-compatible"
        detail = ", ".join(sorted(provider.id for provider in providers if provider.provider_type in _DOCTOR_OPENAI_TYPES))
    elif provider_types & _DOCTOR_GOOGLE_TYPES:
        lane = "google"
        detail = ", ".join(sorted(provider.id for provider in providers if provider.provider_type in _DOCTOR_GOOGLE_TYPES))
    else:
        local_compatible = []
        for provider in providers:
            host, _port = _doctor_endpoint_target(provider.endpoint)
            if provider.provider_type == "openai_compatible" and _doctor_is_local_host(host):
                local_compatible.append(provider.id)
        if local_compatible:
            lane = "self-hosted"
            detail = ", ".join(sorted(local_compatible))

    if lane == "advanced/experimental":
        return "WARN", "no OpenAI-compatible, Google, or localhost self-hosted first-class lane configured"

    google_warnings = []
    if lane == "google":
        for provider in providers:
            if provider.provider_type != "vertex_ai":
                continue
            if not provider.metadata.get("project_id"):
                google_warnings.append(f"{provider.id}: missing metadata.project_id")
            if not provider.metadata.get("location"):
                google_warnings.append(f"{provider.id}: missing metadata.location")
        if google_warnings:
            return "WARN", "; ".join(google_warnings)

    placeholder_warnings = []
    for provider in providers:
        if provider.provider_type not in _DOCTOR_OPENAI_TYPES | _DOCTOR_GOOGLE_TYPES:
            continue
        if provider.endpoint in {"-", "https://example.com/v1", "https://YOUR-RESOURCE.openai.azure.com"}:
            placeholder_warnings.append(f"{provider.id}: endpoint still placeholder")
        if provider.auth_mode in _DOCTOR_SECRET_AUTH_MODES and not provider.secret_ref:
            placeholder_warnings.append(f"{provider.id}: missing secret_ref")
    if placeholder_warnings:
        return "WARN", "; ".join(placeholder_warnings)

    return "PASS", f"{lane} lane ready for smoke checks via: {detail}"


def _doctor_local_reachability(config) -> tuple[str, str]:
    local_targets: list[tuple[str, str, int]] = []
    for provider in config.providers.values():
        host, port = _doctor_endpoint_target(provider.endpoint)
        if host and port and _doctor_is_local_host(host):
            local_targets.append((provider.id, host, port))

    if not local_targets:
        return "SKIP", "no localhost providers configured"

    failures: list[str] = []
    for provider_id, host, port in local_targets:
        try:
            with socket.create_connection((host, port), timeout=1.5):
                pass
        except OSError as exc:
            failures.append(f"{provider_id}@{host}:{port} ({exc})")

    if failures:
        return "WARN", "; ".join(failures)
    return "PASS", ", ".join(f"{provider_id}@{host}:{port}" for provider_id, host, port in local_targets)


def _doctor_context_ops() -> tuple[str, str]:
    try:
        from agentheim.context_ops_impl import AictxContextOps
        from agentheim.vendor.aictx.config import AictxConfig

        AictxContextOps(AictxConfig())
    except Exception as exc:
        return "WARN", str(exc)
    return "PASS", "AICtx-backed ContextOps import and initialization ok"


@app.command("config-dump", rich_help_panel="Advanced")
def config_dump(redacted: bool = typer.Option(True, "--redacted/--raw", help="Redact secrets in output.")) -> None:
    """Print loaded config."""
    config = load_team_config()
    console.print_json(json.dumps(config.dump(redacted=redacted)))


@app.command("ping-models", rich_help_panel="Getting Started")
def ping_models() -> None:
    """Ping configured models with tiny deterministic request."""
    config = load_team_config()
    registry = build_model_registry(config)
    table = Table(title="Model Ping Results")
    table.add_column("role")
    table.add_column("provider")
    table.add_column("model")
    table.add_column("endpoint")
    table.add_column("status")

    any_failed = False
    for role, model_config in config.by_role().items():
        try:
            provider = registry.create_provider(model_config)
        except ValueError as exc:
            raise ProviderError(str(exc)) from exc
        request = ModelRequest(
            role=role,
            system_prompt="Reply with exactly: pong",
            user_prompt="ping",
            temperature=0.0,
        )
        try:
            response = provider.invoke(request)
            status = "ok" if response.content.strip() else "empty-response"
        except NotImplementedError as exc:
            status = f"not-implemented: {exc}"
            any_failed = True
        except Exception as exc:
            status = f"error: {exc}"
            any_failed = True
        table.add_row(
            role.value,
            model_config.provider,
            model_config.model,
            model_config.endpoint,
            status,
        )

    console.print(table)
    if any_failed:
        raise typer.Exit(code=1)


@app.command("inspect", rich_help_panel="Repository Work")
def inspect(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
    write_ledger: bool = typer.Option(False, "--write-ledger", help="Write inspection ledger under target repo."),
) -> None:
    """Inspect repo and produce compact context summary."""
    repo_root = Path(repo).resolve()
    scan = inspect_repository(repo_root)
    _context_lines = [
        f"# Context Pack: {scan.repo_name}",
        "",
        "## Repo Summary",
        f"- Repo: `{scan.repo_name}`",
        f"- Languages: {', '.join(scan.languages) if scan.languages else 'none detected'}",
        f"- Git dirty: {'yes' if scan.git.dirty else 'no'}",
        f"- Docs: {len(scan.docs)}",
        f"- Instruction files: {len(scan.instruction_files)}",
        "",
        "## Detected Commands",
    ]
    if scan.commands:
        for command in scan.commands:
            _context_lines.append(f"- `{ ' '.join(command.command) }` [{command.risk_level}] — {command.reason}")
    else:
        _context_lines.append("- none")
    _context_lines.append("")
    _context_lines.append("## Key Docs")
    if scan.docs:
        for doc in scan.docs:
            _context_lines.append(f"### `{doc.path}`")
            _context_lines.append("")
            _context_lines.append(doc.excerpt)
            _context_lines.append("")
    else:
        _context_lines.append("- none")
    _context_lines.append("## Instruction Files")
    if scan.instruction_files:
        for path in scan.instruction_files:
            _context_lines.append(f"- `{path}`")
    else:
        _context_lines.append("- none")
    _context_lines.append("")
    _context_lines.append("## Warnings")
    for warning in scan.warnings or ["none"]:
        _context_lines.append(f"- {warning}")
    context_pack = "\n".join(_context_lines) + "\n"
    ledger_path: Path | None = None

    if write_ledger:
        ledger = RunLedger.create(repo_root, "inspect")
        ledger.write_json(
            "run.json",
            {"action": "inspect", "repo_name": scan.repo_name},
        )
        ledger.write_json("repo_snapshot.json", scan.model_dump())
        ledger.write_text("context_pack.md", context_pack)
        ledger.append_jsonl("tool_calls.jsonl", {"tool": "inspect_repository", "repo_name": scan.repo_name})
        ledger.append_jsonl("state_transitions.jsonl", {"state": "inspected", "repo_name": scan.repo_name})
        ledger_path = ledger.run_dir / "context_pack.md"

    if as_json:
        payload = scan.model_dump()
        if ledger_path is not None:
            payload["context_pack_file"] = ledger_path.name
        console.print_json(json.dumps(payload))
        return

    console.print(f"[bold]Repo:[/bold] {scan.repo_name}")
    console.print(f"[bold]Languages:[/bold] {', '.join(scan.languages) if scan.languages else 'none'}")
    console.print(f"[bold]Docs:[/bold] {len(scan.docs)}")
    console.print(f"[bold]Instruction files:[/bold] {len(scan.instruction_files)}")
    console.print(f"[bold]Git dirty:[/bold] {'yes' if scan.git.dirty else 'no'}")

    command_table = Table(title="Detected Commands")
    command_table.add_column("name")
    command_table.add_column("command")
    command_table.add_column("risk")
    command_table.add_column("reason")
    for command in scan.commands:
        command_table.add_row(command.name, " ".join(command.command), command.risk_level, command.reason)
    if scan.commands:
        console.print(command_table)
    else:
        console.print("No commands detected.")

    if scan.instruction_files:
        console.print("[bold]Instruction files:[/bold]")
        for path in scan.instruction_files:
            console.print(f"- {path}")

    if scan.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in scan.warnings:
            console.print(f"- {warning}")

    if ledger_path is not None:
        console.print(f"[bold]Context pack:[/bold] .ai-team/runs/{ledger_path.parent.name}/{ledger_path.name}")


@app.command("plan", rich_help_panel="Repository Work")
def plan(
    task_text: str,
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    write_ledger: bool = typer.Option(False, "--write-ledger", help="Write planning ledger under target repo."),
    out: str | None = typer.Option(None, "--out", help="Write parsed plan JSON to file."),
) -> None:
    """Build structured implementation plan without editing files."""
    scan, _context_pack, plan_result, ledger_dir = plan_task(task_text, repo, write_ledger=write_ledger)

    console.print(f"[bold]Plan summary:[/bold] {plan_result.summary}")
    console.print(f"[bold]Repo type:[/bold] {plan_result.detected_repo_type}")
    console.print(f"[bold]Likely files:[/bold] {', '.join(plan_result.files_likely_to_change) if plan_result.files_likely_to_change else 'none'}")

    table = Table(title="Planned Work Orders")
    table.add_column("id")
    table.add_column("type")
    table.add_column("title")
    table.add_column("max scope")
    for task in plan_result.task_graph.ordered_tasks:
        table.add_row(task.id, task.type.value, task.title, task.max_edit_scope)
    console.print(table)

    if plan_result.risks:
        console.print("[bold]Risks:[/bold]")
        for risk in plan_result.risks:
            console.print(f"- {risk.risk}: {risk.mitigation}")

    if ledger_dir is not None:
        console.print(f"[bold]Ledger:[/bold] {ledger_dir}")

    if out:
        out_path = Path(out)
        out_path.write_text(json.dumps(plan_result.model_dump(), indent=2), encoding="utf-8")
        console.print(f"[bold]Plan JSON:[/bold] {out_path}")


@app.command("run", rich_help_panel="Repository Work")
def run(
    task_text: str,
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    mode: str = typer.Option("apply", "--mode", help="Execution mode."),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Allow execution on dirty repo."),
    max_fix_attempts: int = typer.Option(3, "--max-fix-attempts", help="Additional coder retry attempts after first failure."),
    max_diff_lines: int = typer.Option(1200, "--max-diff-lines", help="Maximum allowed diff lines per patch."),
    command_timeout: int = typer.Option(120, "--command-timeout", help="Timeout for safe verification commands in seconds."),
    no_tests: bool = typer.Option(False, "--no-tests", help="Skip verification commands."),
) -> None:
    """Plan and apply bounded work orders without auto-commit."""
    if mode not in {"apply", "auto", "ci"}:
        raise typer.BadParameter("Mode must be one of: apply, auto, ci.")

    report, ledger_dir = run_task(
        task_text,
        repo,
        mode=mode,
        allow_dirty=allow_dirty,
        max_fix_attempts=max_fix_attempts,
        max_diff_lines=max_diff_lines,
        command_timeout=command_timeout,
        no_tests=no_tests,
    )

    console.print(f"[bold]Task summary:[/bold] {report.task_summary}")
    console.print(f"[bold]Changed files:[/bold] {', '.join(report.changed_files) if report.changed_files else 'none'}")
    console.print(f"[bold]Ledger:[/bold] {ledger_dir}")
    if report.commands_run:
        console.print("[bold]Commands run:[/bold]")
        for command in report.commands_run:
            console.print(f"- {' '.join(command)}")
    if report.tests:
        console.print("[bold]Verification:[/bold]")
        for item in report.tests:
            console.print(f"- {item.name}: {item.status}")


@app.command("list-runs", rich_help_panel="Repository Work")
def list_runs_cmd(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
) -> None:
    """List persisted runs under the repository."""
    runs = list_runs(repo)
    if not runs:
        console.print("No runs found.")
        return
    for item in runs:
        console.print(f"- {item}")


@app.command("report", rich_help_panel="Repository Work")
def report(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    run_id: str = typer.Option(..., "--run-id", help="Run id under .ai-team/runs."),
) -> None:
    """Emit canonical run summary JSON for a run."""
    try:
        summary = build_run_summary(repo, run_id)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print_json(json.dumps(summary.model_dump(mode="json")))


@app.command("resume", rich_help_panel="Repository Work")
def resume(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    run_id: str = typer.Option(..., "--run-id", help="Run id under .ai-team/runs."),
) -> None:
    """Resume a run from its ledger."""
    repo_root = Path(repo).resolve()
    run_dir = repo_root / ".ai-team" / "runs" / run_id
    if not run_dir.exists():
        raise typer.BadParameter(f"Run '{run_id}' not found under {repo_root}")

    ledger = RunLedger(repo_root=repo_root, run_dir=run_dir)
    events = ledger.read_ledger()
    started = next((event for event in events if event.event_type == EventType.RUN_INITIATED), None)

    workflow_id = ""
    metadata = {}
    if started is not None:
        workflow_id = str(started.payload.get("workflow_id", "")).strip()
        metadata = started.payload.get("metadata") or {}

    if not workflow_id:
        try:
            run_data = load_run(repo_root, run_id)
        except ResumeError:
            run_data = {}

        if run_data:
            for key in ("workflow_id", "workflow", "action"):
                val = run_data.get(key)
                if isinstance(val, str) and val.strip():
                    workflow_id = val.strip()
                    break
            metadata = run_data.get("metadata") or {}

    if not workflow_id:
        if started is None:
            console.print_json(json.dumps({"run_id": run_id, "status": "no-run-initiated-event"}))
        else:
            console.print_json(json.dumps({"run_id": run_id, "status": "missing-workflow-id"}))
        raise typer.Exit(code=1)

    is_valid, _broken = ledger.verify_chain()
    if not is_valid:
        console.print("[yellow]Warning: ledger chain verification failed[/yellow]")

    from workflows.registry import register_builtin_workflows

    register_builtin_workflows()
    try:
        workflow_entry = get_workflow(workflow_id)
    except KeyError as exc:
        raise typer.BadParameter(f"Workflow '{workflow_id}' is not registered") from exc

    config = load_team_config()
    registry = build_model_registry(config)
    workflow = workflow_entry.factory(
        model_registry=registry,
        tool_registry=ToolRegistry(),
        policy_engine=PolicyEngine(),
        ledger=ledger,
    )

    runner = WorkflowRunner()
    resume_manager = ResumeOrchestrator(repo_root)
    results = resume_manager.resume(run_id, workflow, runner, metadata=metadata)
    summary = {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "resumed_steps": [result.step_id for result in results],
        "all_success": all(result.success for result in results),
    }
    console.print_json(json.dumps(summary))


@app.command("presets", rich_help_panel="Presets")
def list_presets_cmd() -> None:
    """List all available presets."""
    presets = PRESET_REGISTRY.list()
    if not presets:
        console.print("No presets found.")
        return
    table = Table(title="Available Presets")
    table.add_column("ID", style="green")
    table.add_column("Name")
    table.add_column("Workflow")
    table.add_column("Description")
    for preset in presets:
        table.add_row(preset.preset_id, preset.name, preset.workflow_id, preset.description)
    console.print(table)


@app.command("start", rich_help_panel="Presets")
def start_preset(
    preset_id: str = typer.Argument(..., help="Preset ID to run."),
    input_args: list[str] = typer.Option([], "--input", help="Key=value input pairs."),
) -> None:
    """Run a preset with the given inputs."""
    try:
        preset = PRESET_REGISTRY.get(preset_id)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc

    inputs: dict[str, Any] = dict(preset.default_config)
    for arg in input_args:
        if "=" not in arg:
            raise typer.BadParameter(f"Input must be key=value: {arg}")
        key, value = arg.split("=", 1)
        lower = value.lower()
        if lower == "true":
            value = True  # type: ignore[assignment]
        elif lower == "false":
            value = False  # type: ignore[assignment]
        inputs[key] = value

    # Validate required inputs
    for question in preset.guided_questions:
        if question.key not in inputs and question.default is None:
            raise typer.BadParameter(f"Missing required input: {question.key}")
        if question.key not in inputs and question.default is not None:
            inputs[question.key] = question.default

    console.print(f"[bold]Running preset:[/bold] {preset.name}")
    result = preset.run(inputs)
    console.print(result)


@app.command("guided", rich_help_panel="Presets")
def guided() -> None:
    """Launch the guided TUI preset picker."""
    from interfaces.guided_tui.app import run_guided_tui

    run_guided_tui()


@app.command("memory", rich_help_panel="Advanced")
def memory_cmd(
    action: str = typer.Argument(..., help="get|set|history|profile"),
    key: str = typer.Option(None, "--key", help="Preference key for get/set."),
    value: str = typer.Option(None, "--value", help="JSON value for set."),
    model_id: str = typer.Option(None, "--model-id", help="Model ID for profile."),
) -> None:
    """Interact with global memory (Tier 3)."""
    gm = GlobalMemory()
    if action == "get":
        if not key:
            raise typer.BadParameter("--key required for get")
        result = gm.get_preference(key)
        console.print_json(json.dumps({"key": key, "value": result}))
    elif action == "set":
        if not key or value is None:
            raise typer.BadParameter("--key and --value required for set")
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value
        gm.set_preference(key, parsed)
        console.print(f"[green]Set preference[/green] {key}")
    elif action == "history":
        history = gm.get_approval_history()
        table = Table(title="Approval History")
        table.add_column("Decision")
        table.add_column("Tool")
        table.add_column("Timestamp")
        for item in history:
            table.add_row(item["decision"], item["tool_name"], item["timestamp"])
        console.print(table)
    elif action == "profile":
        if not model_id:
            raise typer.BadParameter("--model-id required for profile")
        profile = gm.get_model_profile(model_id)
        if profile is None:
            console.print(f"[yellow]No profile found for {model_id}")
        else:
            console.print_json(json.dumps(profile))
    else:
        raise typer.BadParameter(f"Unknown action: {action}")


@app.command("doctor", rich_help_panel="Getting Started")
def doctor_cmd(
    skip_connectivity: bool = typer.Option(False, "--skip-connectivity", help="Skip live model connectivity check."),
    oci: bool = typer.Option(False, "--oci", help="Include OCI readiness check."),
) -> None:
    """Diagnose common configuration and environment issues."""
    import platform
    import subprocess
    import sys

    table = Table(title="System Diagnostics")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    checks: list[tuple[str, str, str]] = []

    # Python version
    py_ok = sys.version_info >= (3, 12)
    checks.append(("Python version", "PASS" if py_ok else "FAIL", f"{platform.python_version()}"))

    # Required packages
    required = ["pydantic", "rich", "typer", "numpy", "filelock", "platformdirs"]
    missing: list[str] = []
    for pkg in required:
        spec = importlib.util.find_spec(pkg)
        if spec is None:
            missing.append(pkg)
    pkg_status = "PASS" if not missing else "FAIL"
    pkg_detail = "all present" if not missing else f"missing: {', '.join(missing)}"
    checks.append(("Required packages", pkg_status, pkg_detail))

    # Provider profiles
    try:
        config = load_team_config()
        has_provider = bool(config.providers and config.models)
        detail = f"profile={config.profile_name}; providers={len(config.providers)}; models={len(config.models)}"
    except Exception as exc:
        has_provider = False
        detail = str(exc)
    checks.append(("Provider profile", "PASS" if has_provider else "WARN", detail))

    if has_provider:
        role_status, role_detail = _doctor_role_coverage(config)
        checks.append(("Role coverage", role_status, role_detail))
        lane_status, lane_detail = _doctor_first_class_lane(config)
        checks.append(("First-class lane", lane_status, lane_detail))
        local_status, local_detail = _doctor_local_reachability(config)
        checks.append(("Local endpoint reachability", local_status, local_detail))
    else:
        checks.append(("Role coverage", "WARN", "provider profile missing"))
        checks.append(("First-class lane", "WARN", "provider profile missing"))
        checks.append(("Local endpoint reachability", "SKIP", "provider profile missing"))

    # Writable .ai-team/
    ai_team_path = Path(".ai-team")
    try:
        ai_team_path.mkdir(exist_ok=True)
        test_file = ai_team_path / ".doctor_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        writable = True
    except Exception as exc:
        writable = False
    checks.append(("Workspace writable", "PASS" if writable else "FAIL", str(ai_team_path.resolve()) if writable else str(exc)))

    # Git available
    git_ok = False
    git_detail = ""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        git_ok = result.returncode == 0
        git_detail = result.stdout.strip() if git_ok else "git not found"
    except Exception as exc:
        git_detail = str(exc)
    checks.append(("Git available", "PASS" if git_ok else "WARN", git_detail))

    # Model connectivity (optional)
    if not skip_connectivity and has_provider and not missing:
        try:
            config = load_team_config()
            registry = build_model_registry(config)
            by_role = config.by_role()
            first_role = next(iter(by_role))
            model = registry.resolve_model(first_role.value, "json")
            provider = registry.create_provider(model.config)
            response = provider.invoke(
                ModelRequest(
                    role=model.config.role,
                    system_prompt="Reply with exactly: pong",
                    user_prompt="ping",
                    temperature=0.0,
                )
            )
            conn_ok = bool(response.content.strip())
            conn_detail = f"{model.config.provider} / {model.config.model} responded"
        except Exception as exc:
            conn_ok = False
            conn_detail = str(exc)
        checks.append(("Model connectivity", "PASS" if conn_ok else "FAIL", conn_detail))
    else:
        checks.append(("Model connectivity", "SKIP", "--skip-connectivity or missing config"))

    context_status, context_detail = _doctor_context_ops()
    checks.append(("ContextOps availability", context_status, context_detail))

    # OCI readiness (optional)
    if oci:
        try:
            from agentheim.vendor.aictx.oci.doctor import run_oci_doctor

            report = run_oci_doctor()
            if not report.sdk_available:
                console.print("OCI check skipped — install agentheim[oci]")
                checks.append(("OCI readiness", "SKIP", "OCI SDK not installed"))
            else:
                oci_status = "PASS" if report.ready else "FAIL"
                oci_detail = "OCI ready" if report.ready else f"missing: {', '.join(report.missing)}"
                checks.append(("OCI readiness", oci_status, oci_detail))
        except Exception as exc:
            console.print("OCI check skipped — install agentheim[oci]")
            checks.append(("OCI readiness", "SKIP", str(exc)))

    for check, status, detail in checks:
        color = {"PASS": "[green]", "FAIL": "[red]", "WARN": "[yellow]", "SKIP": "[dim]"}.get(status, "")
        table.add_row(check, f"{color}{status}[/]{color}", detail)

    console.print(table)

    fail_count = sum(1 for _, s, _ in checks if s == "FAIL")
    warn_count = sum(1 for _, s, _ in checks if s == "WARN")
    if fail_count:
        console.print(f"[red]{fail_count} check(s) failed.[/red]")
        raise typer.Exit(code=1)
    if warn_count:
        console.print(f"[yellow]{warn_count} check(s) warned. Review above.[/yellow]")
        raise typer.Exit(code=1)
    console.print("[green]All checks passed.[/green]")


@app.command("mcp-list", rich_help_panel="Advanced")
def mcp_list_cmd(
    config: str = typer.Option(".ai-team/mcp.json", "--config", help="Path to MCP config file."),
) -> None:
    """List MCP tools from configured servers."""
    config_path = Path(config)
    if not config_path.exists():
        console.print(f"[yellow]MCP config not found:[/yellow] {config_path}")
        console.print("No MCP servers configured.")
        return

    try:
        servers = load_mcp_config(config_path)
    except Exception as exc:
        console.print(f"[red]Failed to load MCP config:[/red] {exc}")
        raise typer.Exit(code=1)

    table = Table(title="MCP Tools")
    table.add_column("Server")
    table.add_column("Tool")
    table.add_column("Description")

    for server in servers:
        if not server.enabled:
            table.add_row(server.name, "[dim]disabled", "")
            continue
        try:
            with MCPClient(server.command, env=server.env) as client:
                tools = client.list_tools()
                for tool in tools:
                    table.add_row(server.name, tool.get("name", "?"), tool.get("description", "")[:50])
        except Exception as exc:
            table.add_row(server.name, f"[red]error: {exc}", "")

    console.print(table)


@app.command("mcp-call", rich_help_panel="Advanced")
def mcp_call_cmd(
    tool_name: str = typer.Argument(..., help="MCP tool name (format: server.tool or just tool)."),
    args: list[str] = typer.Option([], "--arg", help="Key=value arguments."),
    config: str = typer.Option(".ai-team/mcp.json", "--config", help="Path to MCP config file."),
) -> None:
    """Invoke an MCP tool directly."""
    config_path = Path(config)
    if not config_path.exists():
        console.print(f"[yellow]MCP config not found:[/yellow] {config_path}")
        raise typer.Exit(code=1)

    arguments: dict[str, Any] = {}
    for arg in args:
        if "=" not in arg:
            raise typer.BadParameter(f"Argument must be key=value: {arg}")
        key, value = arg.split("=", 1)
        # Try JSON parse first, then fall back to string
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        arguments[key] = value

    try:
        servers = load_mcp_config(config_path)
    except Exception as exc:
        console.print(f"[red]Failed to load MCP config:[/red] {exc}")
        raise typer.Exit(code=1)

    for server in servers:
        if not server.enabled:
            continue
        try:
            with MCPClient(server.command, env=server.env) as client:
                tools = client.list_tools()
                names = {t.get("name", "") for t in tools}
                if tool_name in names:
                    result = client.call_tool(tool_name, arguments)
                    console.print_json(json.dumps(result, ensure_ascii=False))
                    return
        except Exception as exc:
            console.print(f"[dim]{server.name}: {exc}[/dim]")

    console.print(f"[red]Tool '{tool_name}' not found on any enabled MCP server.[/red]")
    raise typer.Exit(code=1)


@app.command("desktop", rich_help_panel="Advanced")
def desktop_cmd(
    port: int = typer.Option(8765, "--port", help="Port for the web server."),
    no_tray: bool = typer.Option(False, "--no-tray", help="Disable system tray icon."),
) -> None:
    """Launch the Agentheim desktop UI."""
    from interfaces.desktop_ui.app import run_desktop_app

    run_desktop_app(port=port, use_tray=not no_tray)


@app.command("copy", rich_help_panel="Advanced")
def copy_cmd(
    source: str = typer.Argument(..., help="Source path within workspace."),
    destination: str = typer.Argument(..., help="Destination path within workspace."),
) -> None:
    """Copy a file or directory within the workspace."""
    from core.public_api import ToolContext
    from tools.registry import create_core_tool_registry

    registry = create_core_tool_registry(".")
    invoker = ToolInvoker(registry=registry, policy_config=interface_policy_config())
    ctx = ToolContext()
    params = {"operation": "copy", "path": source, "destination": destination}
    result = invoker.invoke("filesystem", params, ctx)

    if result.requires_approval:
        workflow = ApprovalWorkflow()
        req = workflow.request(result.policy, "filesystem", params)
        console.print(
            f"[yellow]Approval required[/yellow]: {req.action} {req.target}\n"
            f"  Risk: {req.risk_level.value}\n"
            f"  Reason: {req.justification}"
        )
        answer = typer.prompt("Grant approval? [y/N]", default="n", show_default=False)
        if answer.lower() in ("y", "yes"):
            workflow.grant(req.request_id)
            result = invoker.invoke("filesystem", params, ctx, granted_request=req)
        else:
            workflow.deny(req.request_id)
            console.print("[red]Denied[/red]")
            raise typer.Exit(code=1)

    if result.success:
        console.print(f"[green]Copied[/green] {source} -> {result.data}")
    else:
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(code=1)


def main() -> None:
    try:
        app()
    except (ConfigError, AIteamError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
