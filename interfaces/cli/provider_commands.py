from __future__ import annotations

import getpass
import json
import os
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
    get_secret_store,
    list_provider_templates,
    load_profiles_document,
    make_secret_ref,
    provider_account_from_template,
    save_profiles_document,
    write_project_profile_pointer,
)
from core.public_api import ConfigError, build_model_registry
from providers.base import ModelRequest


provider_app = typer.Typer(help="Manage AI provider profiles and vault-backed secrets.")
console = Console()


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


def _read_secret(value: str | None, auth_mode: str) -> str | None:
    if auth_mode in {"none", "aws_chain", "google_adc", "oci_config"}:
        return None
    if value is not None:
        return value
    entered = getpass.getpass("Provider secret: ")
    return entered.strip()


@provider_app.command("templates")
def templates() -> None:
    table = Table(title="Provider Templates")
    table.add_column("template")
    table.add_column("provider_type")
    table.add_column("auth")
    table.add_column("endpoint")
    table.add_column("capabilities")
    for item in list_provider_templates():
        table.add_row(item["kind"], item["provider_type"], item["auth_mode"], item["endpoint"], ", ".join(item["capabilities"]))
    console.print(table)


@provider_app.command("add")
def add_provider(
    provider_id: str = typer.Argument(..., help="Provider id inside this Agentheim profile."),
    template: str = typer.Option(..., "--template", "-t", help="Provider template id."),
    model: str = typer.Option(..., "--model", help="Initial model/deployment id."),
    role: ModelRole = typer.Option(ModelRole.PLANNER, "--role", help="Initial team role to bind."),
    profile: str = typer.Option("default", "--profile", help="Profile name."),
    endpoint: str | None = typer.Option(None, "--endpoint", help="Override template endpoint."),
    auth_mode: str | None = typer.Option(None, "--auth-mode", help="Override template auth mode."),
    api_key: str | None = typer.Option(None, "--api-key", help="Secret value. Omit to prompt."),
    capability: list[str] = typer.Option(["text", "json"], "--capability", "-c", help="Model capability."),
) -> None:
    document = _load_or_new()
    profile_obj = _profile(document, profile)
    secret_ref = make_secret_ref(provider_id)
    provider = provider_account_from_template(
        provider_id,
        template,
        endpoint=endpoint,
        auth_mode=auth_mode,  # type: ignore[arg-type]
        secret_ref=secret_ref,
    )
    secret = _read_secret(api_key, provider.auth_mode)
    if secret is not None:
        get_secret_store().set(secret_ref, secret)
    else:
        provider = provider.model_copy(update={"secret_ref": None})
    profile_obj.providers[provider_id] = provider
    profile_obj.models[role.value] = ModelBinding(
        id=role.value,
        role=role,
        provider=provider_id,
        model=model,
        display_name=model,
        capabilities=capability,
    )
    document.default_profile = profile
    save_profiles_document(document)
    console.print(f"provider added: {provider_id} profile={profile}")


@provider_app.command("list")
def list_providers(profile: str | None = typer.Option(None, "--profile", help="Profile name.")) -> None:
    document = load_profiles_document()
    profiles = [profile] if profile else sorted(document.profiles)
    for profile_name in profiles:
        profile_obj = document.profiles.get(profile_name)
        if profile_obj is None:
            raise typer.BadParameter(f"Unknown profile: {profile_name}")
        table = Table(title=f"Provider Profile: {profile_name}")
        table.add_column("provider")
        table.add_column("kind")
        table.add_column("auth")
        table.add_column("endpoint")
        table.add_column("secret")
        for provider in profile_obj.providers.values():
            table.add_row(provider.id, provider.kind, provider.auth_mode, provider.endpoint, provider.secret_ref or "-")
        console.print(table)
        role_table = Table(title=f"Role Bindings: {profile_name}")
        role_table.add_column("role")
        role_table.add_column("provider")
        role_table.add_column("model")
        role_table.add_column("capabilities")
        for binding in profile_obj.models.values():
            role_table.add_row(binding.role.value, binding.provider, binding.model, ", ".join(binding.capabilities))
        console.print(role_table)


@provider_app.command("use")
def use_profile(
    profile: str = typer.Argument(..., help="Profile name."),
    project: bool = typer.Option(False, "--project", help="Write project profile pointer."),
) -> None:
    document = load_profiles_document()
    if profile not in document.profiles:
        raise typer.BadParameter(f"Unknown profile: {profile}")
    if project:
        path = write_project_profile_pointer(profile)
        console.print(f"project profile set: {path}")
    else:
        document.default_profile = profile
        save_profiles_document(document)
        console.print(f"default profile set: {profile}")


@provider_app.command("assign")
def assign_model(
    role: ModelRole = typer.Argument(..., help="Team role."),
    provider_id: str = typer.Option(..., "--provider", help="Provider id."),
    model: str = typer.Option(..., "--model", help="Model/deployment id."),
    profile: str = typer.Option("default", "--profile", help="Profile name."),
    capability: list[str] = typer.Option(["text", "json"], "--capability", "-c", help="Model capability."),
) -> None:
    document = load_profiles_document()
    profile_obj = document.profiles.get(profile)
    if profile_obj is None:
        raise typer.BadParameter(f"Unknown profile: {profile}")
    if provider_id not in profile_obj.providers:
        raise typer.BadParameter(f"Unknown provider '{provider_id}' in profile '{profile}'")
    profile_obj.models[role.value] = ModelBinding(
        id=role.value,
        role=role,
        provider=provider_id,
        model=model,
        display_name=model,
        capabilities=capability,
    )
    save_profiles_document(document)
    console.print(f"assigned: {role.value} -> {provider_id}/{model}")


@provider_app.command("rotate-secret")
def rotate_secret(
    provider_id: str = typer.Argument(..., help="Provider id."),
    profile: str = typer.Option("default", "--profile", help="Profile name."),
    api_key: str | None = typer.Option(None, "--api-key", help="New secret value. Omit to prompt."),
) -> None:
    document = load_profiles_document()
    provider = document.profiles[profile].providers[provider_id]
    if not provider.secret_ref:
        provider = provider.model_copy(update={"secret_ref": make_secret_ref(provider_id)})
        document.profiles[profile].providers[provider_id] = provider
    secret = _read_secret(api_key, provider.auth_mode)
    if secret is None:
        raise typer.BadParameter(f"Provider '{provider_id}' auth mode does not use a secret.")
    get_secret_store().set(provider.secret_ref, secret)
    save_profiles_document(document)
    console.print(f"secret rotated: {provider_id}")


@provider_app.command("remove")
def remove_provider(provider_id: str, profile: str = typer.Option("default", "--profile")) -> None:
    document = load_profiles_document()
    profile_obj = document.profiles.get(profile)
    if profile_obj is None or provider_id not in profile_obj.providers:
        raise typer.BadParameter(f"Unknown provider '{provider_id}' in profile '{profile}'")
    provider = profile_obj.providers.pop(provider_id)
    profile_obj.models = {k: v for k, v in profile_obj.models.items() if v.provider != provider_id}
    if provider.secret_ref:
        get_secret_store().delete(provider.secret_ref)
    save_profiles_document(document)
    console.print(f"provider removed: {provider_id}")


@provider_app.command("test")
def test_provider(
    role: ModelRole = typer.Option(ModelRole.PLANNER, "--role", help="Role binding to test."),
    profile: str = typer.Option("default", "--profile", help="Profile name."),
) -> None:
    config = load_profiles_document().profiles[profile].to_team_config()
    registry = build_model_registry(config)
    model_config = config.resolve_role(role)
    provider = registry.create_provider(model_config)
    response = provider.invoke(ModelRequest(role=role, system_prompt="Reply with exactly: pong", user_prompt="ping"))
    console.print_json(json.dumps({"role": role.value, "provider": model_config.provider, "model": model_config.model, "ok": bool(response.content.strip())}))


@provider_app.command("import-env")
def import_env(profile: str = typer.Option("default", "--profile", help="Profile name.")) -> None:
    document = _load_or_new()
    profile_obj = _profile(document, profile)
    imported = 0

    def add_openai_like(provider_id: str, template: str, endpoint: str, key: str, model: str, roles: list[ModelRole]) -> None:
        nonlocal imported
        secret_ref = make_secret_ref(provider_id)
        get_secret_store().set(secret_ref, key)
        profile_obj.providers[provider_id] = provider_account_from_template(provider_id, template, endpoint=endpoint, secret_ref=secret_ref)
        for role in roles:
            profile_obj.models[role.value] = ModelBinding(id=role.value, role=role, provider=provider_id, model=model, capabilities=["text", "json"])
        imported += 1

    if os.getenv("OPENAI_API_KEY"):
        add_openai_like("openai", "openai_v1", "https://api.openai.com/v1", os.environ["OPENAI_API_KEY"], os.getenv("OPENAI_MODEL", "gpt-4o-mini"), [ModelRole.PLANNER, ModelRole.EXECUTOR, ModelRole.VERIFIER])
    if os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"):
        add_openai_like("xai", "xai_grok", "https://api.x.ai/v1", os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY", ""), os.getenv("GROK_MODEL", "grok-4"), [ModelRole.PLANNER, ModelRole.EXECUTOR, ModelRole.VERIFIER])
    if os.getenv("BEDROCK_MODEL_ID"):
        provider = provider_account_from_template("bedrock", "aws_bedrock", auth_mode="aws_chain")
        profile_obj.providers["bedrock"] = provider
        for role in (ModelRole.PLANNER, ModelRole.EXECUTOR, ModelRole.VERIFIER, ModelRole.CONTEXT):
            profile_obj.models[role.value] = ModelBinding(id=role.value, role=role, provider="bedrock", model=os.environ["BEDROCK_MODEL_ID"], capabilities=["text", "json"])
        imported += 1
    provider_ids = [item.strip() for item in os.getenv("AI_TEAM_PROVIDER_IDS", "").split(",") if item.strip()]
    for provider_id in provider_ids:
        slug = re_slug(provider_id)
        prefix = f"AI_TEAM_PROVIDER_{slug}"
        endpoint = os.getenv(f"{prefix}_ENDPOINT", "")
        provider_type = os.getenv(f"{prefix}_TYPE", "openai_compatible")
        api_key_env = os.getenv(f"{prefix}_API_KEY_ENV", f"{prefix}_API_KEY")
        key = os.getenv(api_key_env, "")
        if endpoint and (key or provider_type == "aws_bedrock"):
            template = provider_type if provider_type in {"openai_v1", "azure_foundry", "aws_bedrock", "oci_genai"} else "openai_compatible"
            secret_ref = make_secret_ref(provider_id) if key else None
            if key and secret_ref:
                get_secret_store().set(secret_ref, key)
            profile_obj.providers[provider_id] = provider_account_from_template(provider_id, template, endpoint=endpoint or "-", secret_ref=secret_ref)
            imported += 1
    document.default_profile = profile
    save_profiles_document(document)
    console.print(f"imported provider profiles: {imported}. Legacy provider env is migration-only and ignored at runtime.")


def re_slug(value: str) -> str:
    import re

    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")
