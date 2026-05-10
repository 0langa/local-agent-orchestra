from __future__ import annotations

import json
import os
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.errors import ConfigError


class ModelRole(StrEnum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


class ProviderConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    api_key_env: str = Field(min_length=1)
    timeout_seconds: int = Field(default=60, ge=1)
    headers: dict[str, str] = Field(default_factory=dict)

    def redacted_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "provider_type": self.provider_type,
            "endpoint": self.endpoint,
            "api_key_env": self.api_key_env,
            "api_key": redact_secret(os.getenv(self.api_key_env, "")),
            "timeout_seconds": self.timeout_seconds,
            "headers": self.headers,
        }


class ModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    role: ModelRole
    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=list)

    def redacted_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "provider": self.provider,
            "model_name": self.model_name,
            "capabilities": self.capabilities,
        }


class AgentModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: ModelRole
    provider: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)
    timeout_seconds: int = Field(default=60, ge=1)
    headers: dict[str, str] = Field(default_factory=dict)

    def redacted_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "provider": self.provider,
            "provider_type": self.provider_type,
            "endpoint": self.endpoint,
            "api_key": redact_secret(self.api_key),
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "headers": self.headers,
        }


class TeamConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    providers: dict[str, ProviderConfig]
    models: dict[str, ModelConfig]

    def resolve_role(self, role: ModelRole) -> AgentModelConfig:
        by_role = [model for model in self.models.values() if model.role is role]
        if not by_role:
            raise ConfigError(f"No model binding configured for role '{role.value}'.")
        model = by_role[0]
        provider = self.providers.get(model.provider)
        if provider is None:
            raise ConfigError(f"Model '{model.id}' references unknown provider '{model.provider}'.")
        api_key = os.getenv(provider.api_key_env, "").strip()
        if not api_key:
            raise ConfigError(
                f"Missing API key env var '{provider.api_key_env}' for provider '{provider.id}' (model '{model.id}')."
            )
        return AgentModelConfig(
            role=role,
            provider=provider.id,
            provider_type=provider.provider_type,
            endpoint=provider.endpoint,
            api_key=api_key,
            model=model.model_name,
            timeout_seconds=provider.timeout_seconds,
            headers=provider.headers,
        )

    def by_role(self) -> dict[ModelRole, AgentModelConfig]:
        return {
            ModelRole.PLANNER: self.resolve_role(ModelRole.PLANNER),
            ModelRole.EXECUTOR: self.resolve_role(ModelRole.EXECUTOR),
            ModelRole.VERIFIER: self.resolve_role(ModelRole.VERIFIER),
        }

    def dump(self, redacted: bool = True) -> dict[str, Any]:
        providers = {
            pid: (provider.redacted_dict() if redacted else provider.model_dump())
            for pid, provider in self.providers.items()
        }
        models = {
            mid: (model.redacted_dict() if redacted else model.model_dump())
            for mid, model in self.models.items()
        }
        return {"providers": providers, "models": models}


def redact_secret(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _provider_env_prefix(provider_id: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "_", provider_id.upper()).strip("_")
    return f"AI_TEAM_PROVIDER_{slug}"


def _load_provider(provider_id: str) -> ProviderConfig:
    prefix = _provider_env_prefix(provider_id)
    provider_type = os.getenv(f"{prefix}_TYPE", "openai_compatible").strip() or "openai_compatible"
    endpoint = os.getenv(f"{prefix}_ENDPOINT", "").strip()
    api_key_env = os.getenv(f"{prefix}_API_KEY_ENV", f"{prefix}_API_KEY").strip()
    timeout_value = os.getenv(f"{prefix}_TIMEOUT_SECONDS", "60").strip()
    headers_json = os.getenv(f"{prefix}_HEADERS_JSON", "{}").strip() or "{}"

    if not endpoint:
        raise ConfigError(f"Missing required environment variable: {prefix}_ENDPOINT")
    try:
        timeout_seconds = int(timeout_value)
    except ValueError as exc:
        raise ConfigError(f"Invalid integer for {prefix}_TIMEOUT_SECONDS: '{timeout_value}'") from exc
    try:
        headers = json.loads(headers_json)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {prefix}_HEADERS_JSON") from exc
    if not isinstance(headers, dict):
        raise ConfigError(f"{prefix}_HEADERS_JSON must be a JSON object.")
    str_headers = {str(k): str(v) for k, v in headers.items()}

    return ProviderConfig(
        id=provider_id,
        provider_type=provider_type,
        endpoint=endpoint,
        api_key_env=api_key_env,
        timeout_seconds=timeout_seconds,
        headers=str_headers,
    )


def _load_registry_config() -> TeamConfig:
    provider_ids_raw = os.getenv("AI_TEAM_PROVIDER_IDS", "default").strip()
    provider_ids = [item.strip() for item in provider_ids_raw.split(",") if item.strip()]
    if not provider_ids:
        raise ConfigError("AI_TEAM_PROVIDER_IDS must include at least one provider id.")

    providers = {provider_id: _load_provider(provider_id) for provider_id in provider_ids}

    models_json = os.getenv("AI_TEAM_MODELS_JSON", "").strip()
    models: dict[str, ModelConfig] = {}
    if models_json:
        try:
            parsed = json.loads(models_json)
        except json.JSONDecodeError as exc:
            raise ConfigError("Invalid JSON in AI_TEAM_MODELS_JSON") from exc
        if not isinstance(parsed, list):
            raise ConfigError("AI_TEAM_MODELS_JSON must be a JSON array.")
        for item in parsed:
            if not isinstance(item, dict):
                raise ConfigError("Each AI_TEAM_MODELS_JSON item must be an object.")
            try:
                model = ModelConfig.model_validate(item)
            except Exception as exc:
                raise ConfigError(f"Invalid model entry in AI_TEAM_MODELS_JSON: {item}") from exc
            models[model.id] = model
    else:
        model_defaults = {
            "planner": ("planner", "default", "replace-with-planner-model", ["plan", "reasoning", "json"]),
            "executor": ("executor", "default", "replace-with-executor-model", ["code_edit", "json"]),
            "verifier": ("verifier", "default", "replace-with-verifier-model", ["verify", "json"]),
        }
        for model_id, (role_value, provider_default, name_default, capabilities_default) in model_defaults.items():
            role = ModelRole(role_value)
            provider = os.getenv(f"AI_TEAM_MODEL_{model_id.upper()}_PROVIDER", provider_default).strip() or provider_default
            model_name = os.getenv(f"AI_TEAM_MODEL_{model_id.upper()}_NAME", name_default).strip() or name_default
            cap_json = os.getenv(f"AI_TEAM_MODEL_{model_id.upper()}_CAPABILITIES_JSON", "")
            capabilities = capabilities_default
            if cap_json.strip():
                try:
                    parsed = json.loads(cap_json)
                except json.JSONDecodeError as exc:
                    raise ConfigError(f"Invalid JSON in AI_TEAM_MODEL_{model_id.upper()}_CAPABILITIES_JSON") from exc
                if not isinstance(parsed, list) or not all(isinstance(item, str) and item.strip() for item in parsed):
                    raise ConfigError(f"AI_TEAM_MODEL_{model_id.upper()}_CAPABILITIES_JSON must be a JSON array of strings.")
                capabilities = [item.strip() for item in parsed]
            models[model_id] = ModelConfig(id=model_id, role=role, provider=provider, model_name=model_name, capabilities=capabilities)

    return TeamConfig(providers=providers, models=models)


def _load_legacy_grok_config() -> TeamConfig:
    # Deprecated compatibility path for older GROK_* env layouts.
    legacy_roles = {
        "planner": ("GROK_ORCHESTRATOR", "AZURE_GROK", "GROK_REASONER", "grok-4-20-reasoning", ModelRole.PLANNER, ["plan", "reasoning", "json"]),
        "executor": ("GROK_CODER", "GROK_CODER", "GROK_CODER", "grok-4-1-fast-reasoning", ModelRole.EXECUTOR, ["code_edit", "json"]),
        "verifier": ("GROK_VERIFIER", "GROK_VERIFY", "GROK_VERIFY", "grok-4-20-non-reasoning", ModelRole.VERIFIER, ["verify", "json"]),
    }
    providers: dict[str, ProviderConfig] = {}
    models: dict[str, ModelConfig] = {}

    for model_id, (primary, alias_one, alias_two, default_model, role, default_capabilities) in legacy_roles.items():
        endpoint = (
            os.getenv(f"{primary}_ENDPOINT")
            or os.getenv(f"{alias_one}_ENDPOINT")
            or os.getenv(f"{alias_two}_ENDPOINT")
            or ""
        ).strip()
        api_key = (
            os.getenv(f"{primary}_KEY")
            or os.getenv(f"{alias_one}_KEY")
            or os.getenv(f"{alias_two}_KEY")
            or ""
        ).strip()
        model_name = (
            os.getenv(f"{primary}_MODEL")
            or os.getenv(f"{alias_one}_MODEL")
            or os.getenv(f"{alias_two}_MODEL")
            or default_model
        ).strip()
        provider_name = (os.getenv(f"{primary}_PROVIDER", "azure_foundry").strip() or "azure_foundry")

        if not endpoint or not api_key:
            raise ConfigError(
                "Missing legacy GROK_* env vars. Migrate to AI_TEAM_PROVIDER_* and AI_TEAM_MODEL_* configuration."
            )
        provider_id = f"legacy-{model_id}"
        api_key_env = f"AI_TEAM_LEGACY_{model_id.upper()}_API_KEY"
        os.environ[api_key_env] = api_key
        providers[provider_id] = ProviderConfig(
            id=provider_id,
            provider_type="openai_compatible" if provider_name in {"openai_v1", "azure_foundry"} else provider_name,
            endpoint=endpoint,
            api_key_env=api_key_env,
            timeout_seconds=60,
            headers={},
        )
        models[model_id] = ModelConfig(
            id=model_id,
            role=role,
            provider=provider_id,
            model_name=model_name,
            capabilities=default_capabilities,
        )
    return TeamConfig(providers=providers, models=models)


def load_team_config() -> TeamConfig:
    if os.getenv("AI_TEAM_PROVIDER_IDS"):
        return _load_registry_config()
    return _load_legacy_grok_config()
