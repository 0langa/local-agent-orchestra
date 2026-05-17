from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from config.config import (
    ModelBinding,
    ModelRole,
    ProfilesDocument,
    TeamProfile,
    load_team_config,
    get_secret_store,
    load_profiles_document,
    make_secret_ref,
    provider_account_from_template,
    save_profiles_document,
)
from core.public_api import ConfigError, RunExecutor, RunStatus, RunView, list_run_views
from core.public_api import ResumeOrchestrator, ToolRegistry, WorkflowRunner, PolicyEngine, RunLedger, EventType, build_model_registry, get_workflow, load_run, build_run_view
from interfaces.run_hooks import register_default_run_hooks
from presets.base import PRESET_REGISTRY, PresetInputError
from presets.catalog import CATALOG, PresetCatalogItem, QuestionSchema
from interfaces.readiness import ReadinessState, build_readiness_state


product_app = typer.Typer(help="Beginner product commands.")
runs_app = typer.Typer(help="Inspect and recover runs.", invoke_without_command=True)
console = Console()

_BEGINNER_PROVIDER_CHOICES = {
    "openai-compatible": {
        "template": "openai_compatible",
        "provider_id": "openai-compatible",
        "default_endpoint": "https://example.com/v1",
        "default_model": "gpt-4o-mini",
        "local": False,
    },
    "openai": {
        "template": "openai_v1",
        "provider_id": "openai",
        "default_endpoint": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "local": False,
    },
    "azure": {
        "template": "azure_foundry",
        "provider_id": "azure",
        "default_endpoint": "https://YOUR-RESOURCE.openai.azure.com",
        "default_model": "gpt-4o-mini",
        "local": False,
    },
    "anthropic": {
        "template": "anthropic",
        "provider_id": "anthropic",
        "default_endpoint": "https://api.anthropic.com",
        "default_model": "claude-3-5-sonnet-latest",
        "local": False,
    },
    "gemini": {
        "template": "gemini",
        "provider_id": "gemini",
        "default_endpoint": "https://generativelanguage.googleapis.com",
        "default_model": "gemini-2.0-flash",
        "local": False,
    },
    "ollama": {
        "template": "ollama",
        "provider_id": "ollama",
        "default_endpoint": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "local": True,
    },
    "lm-studio": {
        "template": "lm_studio",
        "provider_id": "lm-studio",
        "default_endpoint": "http://localhost:1234/v1",
        "default_model": "local-model",
        "local": True,
    },
}
_CORE_ROLES = [
    ModelRole.PLANNER,
    ModelRole.EXECUTOR,
    ModelRole.VERIFIER,
    ModelRole.CONTEXT,
]
_RECOMMENDED_PRESET_ROLES = [
    ModelRole.GENERATOR,
    ModelRole.REVIEWER,
    ModelRole.TESTER,
    ModelRole.SUMMARIZER,
]
_TASK_ID_TO_PRESET_ID = {
    "code": "codebase-assistant",
    "docs-chat": "local-document-chat",
    "command": "command-assistant",
    "context": "context-maintainer",
    "research": "research-report",
    "docs-maintain": "docs-maintainer",
    "organize-files": "file-organizer",
    "github": "github-maintainer",
}
_RECOMMENDED_TASK_IDS = ["code", "docs-chat", "command", "context"]

_RUN_EXECUTOR = RunExecutor()
register_default_run_hooks(_RUN_EXECUTOR)


@dataclass(slots=True)
class SetupPlan:
    profile: str
    provider: str
    template: str
    provider_id: str
    model: str
    endpoint: str
    local: bool
    secret_ref: str | None
    auth_mode: str
    store_secret: bool


def _load_or_new() -> ProfilesDocument:
    try:
        return load_profiles_document()
    except ConfigError:
        return ProfilesDocument(profiles={})


def _profile(document: ProfilesDocument, name: str) -> TeamProfile:
    profile = document.profiles.get(name)
    if profile is None:
        profile = TeamProfile(name=name)
        document.profiles[name] = profile
    return profile


def _prompt_if_missing(value: str | None, text: str, *, default: str | None = None) -> str:
    if value:
        return value
    return typer.prompt(text, default=default).strip()


def _prompt_provider_choice(local: bool) -> str:
    choices = [name for name, spec in _BEGINNER_PROVIDER_CHOICES.items() if local or not spec["local"]]
    default = "ollama" if local else "openai"
    while True:
        entered = typer.prompt("Provider", default=default).strip().lower()
        if entered in choices:
            return entered
        console.print(f"Unsupported provider '{entered}'. Choose one of: {', '.join(choices)}")


def _confirm_if_needed(yes: bool, dry_run: bool, plan: SetupPlan) -> None:
    if yes or dry_run:
        return
    confirmed = typer.confirm(
        f"Configure profile '{plan.profile}' with provider '{plan.provider}' using model '{plan.model}'?",
        default=True,
    )
    if not confirmed:
        raise typer.Abort()


def _build_bindings(provider_id: str, model: str) -> dict[str, ModelBinding]:
    bindings: dict[str, ModelBinding] = {}
    for role in [*_CORE_ROLES, *_RECOMMENDED_PRESET_ROLES]:
        bindings[role.value] = ModelBinding(
            id=role.value,
            role=role,
            provider=provider_id,
            model=model,
            display_name=model,
            capabilities=["text", "json"],
        )
    return bindings


def _render_text_result(payload: dict[str, Any], readiness: ReadinessState) -> None:
    console.print(f"setup status: {payload['status']}")
    console.print(f"profile: {payload['profile']}")
    console.print(f"provider: {payload['provider']}")
    console.print(f"model: {payload['model']}")
    console.print(f"readiness: {readiness.status.value}")
    for action in payload["next_actions"]:
        console.print(action)


def _recent_runs(repo_root: Path) -> list[RunView]:
    try:
        return list_run_views(repo_root)[:5]
    except Exception:
        return []


def _status_payload(profile: str | None, repo_root: Path) -> dict[str, Any]:
    readiness = build_readiness_state()
    active_profile = readiness.profile_name

    if profile and profile != active_profile:
        config = load_team_config(profile=profile)
        active_profile = config.profile_name
        readiness = build_readiness_state()
        readiness.profile_name = active_profile

    recent_runs = _recent_runs(repo_root)
    return {
        "status": readiness.status.value,
        "profile": active_profile,
        "repo": str(repo_root),
        "readiness": readiness.model_dump(mode="json"),
        "provider_readiness": [provider.model_dump(mode="json") for provider in readiness.configured_providers],
        "missing_roles": readiness.missing_roles,
        "optional_integrations": [integration.model_dump(mode="json") for integration in readiness.optional_integrations],
        "recent_runs": [run.model_dump(mode="json") for run in recent_runs],
        "next_actions": readiness.next_actions,
    }


def _render_status_text(payload: dict[str, Any]) -> None:
    readiness = payload["readiness"]
    console.print(f"status: {payload['status']}")
    console.print(f"profile: {payload['profile']}")
    console.print(f"repo: {payload['repo']}")
    console.print(f"provider readiness: {readiness['status']}")
    if payload["missing_roles"]:
        console.print(f"missing roles: {', '.join(payload['missing_roles'])}")
    else:
        console.print("missing roles: none")

    if payload["optional_integrations"]:
        for integration in payload["optional_integrations"]:
            state = "available" if integration["available"] else "unavailable"
            console.print(f"optional integration {integration['integration_id']}: {state}")

    if payload["recent_runs"]:
        table = Table(title="Recent runs")
        table.add_column("Run")
        table.add_column("Status")
        table.add_column("Summary")
        for run in payload["recent_runs"]:
            table.add_row(run["run_id"], run["status"], run.get("summary", ""))
        console.print(table)
    else:
        console.print("recent runs: none")

    for action in payload["next_actions"]:
        console.print(action)


def _parse_input_args(input_args: list[str]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for arg in input_args:
        if "=" not in arg:
            raise typer.BadParameter(f"Input must be key=value: {arg}")
        key, value = arg.split("=", 1)
        lower = value.lower()
        if lower == "true":
            inputs[key] = True
        elif lower == "false":
            inputs[key] = False
        else:
            inputs[key] = value
    return inputs


def _task_catalog_item(task_id: str) -> PresetCatalogItem:
    preset_id = _TASK_ID_TO_PRESET_ID.get(task_id)
    if preset_id is None:
        supported = ", ".join(_TASK_ID_TO_PRESET_ID)
        raise typer.BadParameter(f"Unsupported task '{task_id}'. Supported: {supported}")
    return CATALOG.get(preset_id)


def _prompt_for_task() -> str:
    console.print("Recommended tasks:")
    for task_id in _RECOMMENDED_TASK_IDS:
        item = _task_catalog_item(task_id)
        console.print(f"- {task_id}: {item.name} — {item.description}")
    console.print("Advanced tasks:")
    for task_id, preset_id in _TASK_ID_TO_PRESET_ID.items():
        if task_id in _RECOMMENDED_TASK_IDS:
            continue
        item = CATALOG.get(preset_id)
        console.print(f"- {task_id}: {item.name} — {item.description}")
    return typer.prompt("Task ID", default="code").strip().lower()


def _collect_missing_inputs(item: PresetCatalogItem, provided: dict[str, Any], yes: bool) -> dict[str, Any]:
    inputs = dict(provided)
    for question in item.questions:
        if inputs.get(question.key) not in (None, ""):
            continue
        if yes:
            continue
        prompt_default = question.default if question.default is not None else None
        if question.type == "confirm":
            inputs[question.key] = typer.confirm(question.text, default=bool(prompt_default))
        else:
            inputs[question.key] = typer.prompt(question.text, default=prompt_default)
    return inputs


def _run_submission_payload(run_id: str, repo_root: Path) -> dict[str, Any]:
    record = _RUN_EXECUTOR.get(run_id)
    artifact_dir = str((repo_root / ".ai-team" / "runs" / run_id).resolve())
    report_path = str((repo_root / ".ai-team" / "runs" / run_id / "final_report.md").resolve())
    return {
        "run_id": run_id,
        "status": (record.status.value if record else RunStatus.PENDING.value),
        "report_path": report_path,
        "artifact_dir": artifact_dir,
        "next_action": f"agentheim runs show {run_id}",
    }


def _render_use_text(task_id: str, item: PresetCatalogItem, payload: dict[str, Any]) -> None:
    console.print(f"task: {task_id}")
    console.print(f"preset: {item.preset_id}")
    console.print(f"run id: {payload['run_id']}")
    console.print(f"status: {payload['status']}")
    console.print(f"report path: {payload['report_path']}")
    console.print(f"artifact folder: {payload['artifact_dir']}")
    console.print(payload["next_action"])


def _render_runs_list(views: list[RunView]) -> None:
    if not views:
        console.print("No runs found.")
        return
    table = Table(title="Runs")
    table.add_column("Run ID", style="green")
    table.add_column("Status")
    table.add_column("Summary")
    table.add_column("Resume")
    for view in views:
        table.add_row(view.run_id, view.status, view.summary, "yes" if view.resume_available else "no")
    console.print(table)


def _open_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
        return
    subprocess.run(["xdg-open", str(path)], check=False)


def _report_path_for_view(view: RunView) -> Path | None:
    if view.report_path:
        path = Path(view.report_path)
        if path.exists():
            return path
    return None


def _resume_run(repo_root: Path, run_id: str) -> dict[str, Any]:
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
        except Exception:
            run_data = {}
        if run_data:
            for key in ("workflow_id", "workflow", "action"):
                val = run_data.get(key)
                if isinstance(val, str) and val.strip():
                    workflow_id = val.strip()
                    break
            metadata = run_data.get("metadata") or {}

    if not workflow_id:
        raise typer.BadParameter(f"Run '{run_id}' is missing workflow metadata")

    workflow_entry = get_workflow(workflow_id)
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
    return {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "resumed_steps": [result.step_id for result in results],
        "all_success": all(result.success for result in results),
    }


@product_app.command("setup", rich_help_panel="Getting Started")
def setup_cmd(
    provider: str | None = typer.Option(None, "--provider", help="Beginner provider choice."),
    template: str | None = typer.Option(None, "--template", help="Override provider template."),
    model: str | None = typer.Option(None, "--model", help="Model or deployment id."),
    endpoint: str | None = typer.Option(None, "--endpoint", help="Provider endpoint override."),
    api_key: str | None = typer.Option(None, "--api-key", help="Provider secret value."),
    profile: str = typer.Option("default", "--profile", help="Profile name."),
    local: bool = typer.Option(False, "--local", help="Prefer local beginner providers."),
    yes: bool = typer.Option(False, "--yes", help="Accept prompts and confirmations."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show planned changes without writing."),
) -> None:
    """Configure one beginner provider, bind roles, and run readiness checks."""
    provider_name = provider
    if provider_name is None:
        provider_name = _prompt_provider_choice(local)
    provider_name = provider_name.lower()
    if provider_name not in _BEGINNER_PROVIDER_CHOICES:
        supported = ", ".join(sorted(_BEGINNER_PROVIDER_CHOICES))
        raise typer.BadParameter(f"Unsupported provider '{provider_name}'. Supported: {supported}")

    selected = _BEGINNER_PROVIDER_CHOICES[provider_name]
    template_id = template or selected["template"]
    model_name = model or (selected["default_model"] if yes or as_json else _prompt_if_missing(model, "Model", default=selected["default_model"]))
    endpoint_value = endpoint or (selected["default_endpoint"] if yes or as_json else _prompt_if_missing(endpoint, "Endpoint", default=selected["default_endpoint"]))

    provider_account = provider_account_from_template(
        selected["provider_id"],
        template_id,
        endpoint=endpoint_value,
        secret_ref=make_secret_ref(selected["provider_id"]) if provider_name not in {"ollama", "lm-studio"} else None,
    )
    needs_secret = provider_account.auth_mode not in {"none", "aws_chain", "google_adc", "oci_config"}
    secret_value = api_key
    if needs_secret and secret_value is None and not yes:
        secret_value = typer.prompt("API key", hide_input=True).strip()
    store_secret = needs_secret and bool(secret_value)

    plan = SetupPlan(
        profile=profile,
        provider=provider_name,
        template=template_id,
        provider_id=selected["provider_id"],
        model=model_name,
        endpoint=endpoint_value,
        local=local or selected["local"],
        secret_ref=provider_account.secret_ref,
        auth_mode=provider_account.auth_mode,
        store_secret=store_secret,
    )
    _confirm_if_needed(yes, dry_run, plan)

    if not dry_run:
        document = _load_or_new()
        profile_obj = _profile(document, profile)
        if store_secret and plan.secret_ref:
            get_secret_store().set(plan.secret_ref, secret_value or "")
        elif not needs_secret:
            provider_account = provider_account.model_copy(update={"secret_ref": None})

        profile_obj.providers[plan.provider_id] = provider_account
        profile_obj.models.update(_build_bindings(plan.provider_id, plan.model))
        document.default_profile = profile
        save_profiles_document(document)

    readiness = build_readiness_state(skip_connectivity=dry_run)
    payload = {
        "status": "dry-run" if dry_run else "ok",
        "profile": profile,
        "provider": provider_name,
        "model": model_name,
        "readiness": readiness.model_dump(mode="json"),
        "next_actions": [
            "Next: agentheim status",
            "Next: agentheim use",
        ],
    }
    if as_json:
        console.print_json(json.dumps(payload))
        return
    _render_text_result(payload, readiness)


@product_app.command("status", rich_help_panel="Getting Started")
def status_cmd(
    profile: str | None = typer.Option(None, "--profile", help="Profile name override."),
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for recent run lookup."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    """Show provider readiness, integrations, recent runs, and next actions."""
    repo_root = repo.resolve()
    payload = _status_payload(profile, repo_root)
    if as_json:
        console.print_json(json.dumps(payload))
        return
    _render_status_text(payload)


@product_app.command("use", rich_help_panel="Getting Started")
def use_cmd(
    task_id: str | None = typer.Argument(None, help="Task ID to run."),
    input_args: list[str] = typer.Option([], "--input", help="Key=value input pairs."),
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for the task."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
    yes: bool = typer.Option(False, "--yes", help="Accept defaults without interactive prompts."),
) -> None:
    """Launch a task by plain-language goal or direct task ID."""
    selected_task_id = (task_id or _prompt_for_task()).strip().lower()
    item = _task_catalog_item(selected_task_id)
    preset = PRESET_REGISTRY.get(item.preset_id)

    inputs = _parse_input_args(input_args)
    if "repo" not in inputs:
        inputs["repo"] = str(repo.resolve())
    if "project_path" not in inputs and item.preset_id == "context-maintainer":
        inputs["project_path"] = str(repo.resolve())

    inputs = _collect_missing_inputs(item, inputs, yes)
    try:
        validated_inputs = preset.validate_inputs(inputs)
    except PresetInputError as exc:
        raise typer.BadParameter(str(exc)) from exc

    run_id = _RUN_EXECUTOR.submit(preset.run, validated_inputs)
    payload = _run_submission_payload(run_id, repo.resolve())
    payload.update({"task_id": selected_task_id, "preset_id": item.preset_id})

    if as_json:
        console.print_json(json.dumps(payload))
        return
    _render_use_text(selected_task_id, item, payload)


@runs_app.callback(invoke_without_command=True)
def runs_cmd(
    ctx: typer.Context,
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for run lookup."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    """List, inspect, report, resume, or open run artifacts."""
    if ctx.invoked_subcommand is not None:
        return
    views = list_run_views(repo.resolve())
    if as_json:
        console.print_json(json.dumps([view.model_dump(mode="json") for view in views]))
        return
    _render_runs_list(views)


@runs_app.command("list")
def runs_list_cmd(
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for run lookup."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    views = list_run_views(repo.resolve())
    if as_json:
        console.print_json(json.dumps([view.model_dump(mode="json") for view in views]))
        return
    _render_runs_list(views)


@runs_app.command("show")
def runs_show_cmd(
    run_id: str,
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for run lookup."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    view = build_run_view(repo.resolve(), run_id)
    if as_json:
        console.print_json(json.dumps(view.model_dump(mode="json")))
        return
    console.print_json(json.dumps(view.model_dump(mode="json")))


@runs_app.command("report")
def runs_report_cmd(
    run_id: str,
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for run lookup."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    view = build_run_view(repo.resolve(), run_id)
    report_path = _report_path_for_view(view)
    if report_path is None:
        raise typer.BadParameter(f"No report found for run '{run_id}'")
    content = report_path.read_text(encoding="utf-8")
    if as_json:
        console.print_json(json.dumps({"run_id": run_id, "report_path": str(report_path), "content": content}))
        return
    console.print(content)


@runs_app.command("resume")
def runs_resume_cmd(
    run_id: str,
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for run lookup."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    summary = _resume_run(repo.resolve(), run_id)
    if as_json:
        console.print_json(json.dumps(summary))
        return
    console.print_json(json.dumps(summary))


@runs_app.command("open-folder")
def runs_open_folder_cmd(
    run_id: str,
    repo: Path = typer.Option(Path.cwd(), "--repo", help="Repository root for run lookup."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    view = build_run_view(repo.resolve(), run_id)
    artifact_dir = Path(view.artifact_dir)
    if as_json:
        console.print_json(json.dumps({"run_id": run_id, "artifact_dir": str(artifact_dir)}))
        return
    _open_path(artifact_dir)
    console.print(f"Opened: {artifact_dir}")


product_app.add_typer(runs_app, name="runs", rich_help_panel="Getting Started", help="Inspect and recover runs.")


@product_app.command("open", rich_help_panel="Getting Started")
def open_cmd(
    port: int = typer.Option(8765, "--port", help="Port for the local Web UI."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Start the Web UI without opening a browser."),
    desktop: bool = typer.Option(False, "--desktop", help="Launch the desktop wrapper instead."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    """Open the local Agentheim UI on localhost."""
    url = f"http://127.0.0.1:{port}"
    if desktop:
        from interfaces.desktop_ui.app import run_desktop_app

        if as_json:
            console.print_json(json.dumps({"mode": "desktop", "url": url, "port": port}))
            return
        run_desktop_app(port=port, use_tray=True)
        return

    if as_json:
        console.print_json(json.dumps({"mode": "web", "url": url, "port": port, "opened_browser": not no_browser}))
        return

    if not no_browser:
        webbrowser.open(url)
    console.print(f"Agentheim Web UI: {url}")
    console.print("Press Ctrl+C in the server terminal to stop it.")