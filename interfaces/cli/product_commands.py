from __future__ import annotations

import json
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
from core.public_api import ConfigError, RunView, list_run_views
from interfaces.readiness import ReadinessState, build_readiness_state


product_app = typer.Typer(help="Beginner product commands.")
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