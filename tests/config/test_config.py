"""Unit tests for config.config — all mock-based, no real keychain or network calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from config.config import (
    AgentModelConfig,
    ConfigError,
    EncryptedFileSecretStore,
    KeyringSecretStore,
    ModelBinding,
    ModelConfig,
    ModelRole,
    ProfilesDocument,
    ProviderAccount,
    ProviderConfig,
    TeamConfig,
    TeamProfile,
    get_secret_store,
    list_provider_templates,
    load_profiles_document,
    load_team_config,
    provider_account_from_template,
    redact_mapping,
    redact_secret,
    redact_secret_ref,
    resolve_profile_name,
    save_profiles_document,
    write_project_profile_pointer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_provider() -> ProviderConfig:
    """A sample provider with a secret api_key."""
    return ProviderConfig(
        id="openai",
        provider_type="openai_v1",
        endpoint="https://api.openai.com/v1",
        auth_mode="none",
        api_key="sk-secret",
    )


@pytest.fixture
def sample_model() -> ModelConfig:
    """A sample model bound to the ``openai`` provider."""
    return ModelConfig(
        id="m1",
        role=ModelRole.PLANNER,
        provider="openai",
        model_name="gpt-4",
    )


@pytest.fixture
def sample_team_config(sample_provider: ProviderConfig, sample_model: ModelConfig) -> TeamConfig:
    """A minimal ``TeamConfig`` using the sample provider and model."""
    return TeamConfig(
        providers={sample_provider.id: sample_provider},
        models={sample_model.id: sample_model},
        profile_name="default",
    )


@pytest.fixture
def keyring_store(monkeypatch: pytest.MonkeyPatch) -> KeyringSecretStore:
    """A ``KeyringSecretStore`` backed by a mocked keyring module."""
    mock_module = MagicMock()
    monkeypatch.setitem(sys.modules, "keyring", mock_module)
    return KeyringSecretStore()


@pytest.fixture
def encrypted_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EncryptedFileSecretStore:
    """An ``EncryptedFileSecretStore`` using a temporary file and fixed passphrase."""
    monkeypatch.delenv("AGENTHEIM_VAULT_PASSPHRASE", raising=False)
    return EncryptedFileSecretStore(path=tmp_path / "vault.enc", passphrase="correct")


# ---------------------------------------------------------------------------
# Redaction functions
# ---------------------------------------------------------------------------


class TestRedactSecret:
    """Tests for ``redact_secret``."""

    def test_empty_string(self) -> None:
        assert redact_secret("") == ""

    def test_short_string(self) -> None:
        assert redact_secret("ab") == "****"

    def test_long_string(self) -> None:
        assert redact_secret("abcdefghijklmnopqrstuvwxyz") == "ab***yz"


class TestRedactSecretRef:
    """Tests for ``redact_secret_ref``."""

    def test_none_returns_none(self) -> None:
        assert redact_secret_ref(None) is None

    def test_non_secret_ref_redacted(self) -> None:
        assert redact_secret_ref("my-secret") == redact_secret("my-secret")

    def test_secret_ref_preserved(self) -> None:
        ref = "secret://provider/openai/api_key"
        assert redact_secret_ref(ref) == ref


class TestRedactMapping:
    """Tests for ``redact_mapping``."""

    def test_sensitive_keys_redacted(self) -> None:
        mapping = {
            "api_key": "hide_me",
            "token": "abc",
            "secret": "shh",
            "password": "1234",
            "credential": "cred",
        }
        result = redact_mapping(mapping)
        assert result["api_key"] == redact_secret("hide_me")
        assert result["token"] == redact_secret("abc")
        assert result["secret"] == redact_secret("shh")
        assert result["password"] == redact_secret("1234")
        assert result["credential"] == redact_secret("cred")

    def test_nested_dicts_recurse(self) -> None:
        mapping = {"outer": {"inner_api_key": "hidden"}}
        result = redact_mapping(mapping)
        assert result["outer"]["inner_api_key"] == redact_secret("hidden")

    def test_other_values_pass_through(self) -> None:
        mapping = {"plain": "visible", "number": 42, "nested": {"foo": "bar"}}
        result = redact_mapping(mapping)
        assert result["plain"] == "visible"
        assert result["number"] == 42
        assert result["nested"]["foo"] == "bar"


# ---------------------------------------------------------------------------
# Provider templates
# ---------------------------------------------------------------------------


class TestListProviderTemplates:
    """Tests for ``list_provider_templates``."""

    def test_returns_non_empty_list(self) -> None:
        templates = list_provider_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0

    def test_each_has_kind_and_display_name(self) -> None:
        for template in list_provider_templates():
            assert "kind" in template
            assert "display_name" in template
            assert template["kind"]
            assert template["display_name"]

    def test_excludes_experimental_by_default(self) -> None:
        templates = list_provider_templates()
        states = {t["support_state"] for t in templates}
        assert "experimental" not in states, f"experimental templates leaked: {[t['kind'] for t in templates if t['support_state'] == 'experimental']}"

    def test_includes_experimental_when_requested(self) -> None:
        templates = list_provider_templates(include_experimental=True)
        states = {t["support_state"] for t in templates}
        assert "experimental" in states, "expected experimental templates when include_experimental=True"

    def test_all_templates_have_support_state(self) -> None:
        for template in list_provider_templates(include_experimental=True):
            assert "support_state" in template, f"template '{template['kind']}' missing support_state"
            assert template["support_state"] in {"stable", "beta", "stable_candidate", "experimental", "unknown"}


class TestProviderAccountFromTemplate:
    """Tests for ``provider_account_from_template``."""

    def test_valid_template_creates_provider_account(self) -> None:
        account = provider_account_from_template("my-openai", "openai_v1")
        assert account.id == "my-openai"
        assert account.kind == "openai_v1"
        assert account.endpoint == "https://api.openai.com/v1"
        assert account.auth_mode == "bearer"
        assert account.secret_ref is None
        assert account.timeout_seconds == 60

    def test_unknown_template_raises(self) -> None:
        with pytest.raises(ConfigError) as exc_info:
            provider_account_from_template("x", "unknown_template")
        assert "Unknown provider template" in str(exc_info.value)

    def test_custom_values_override_defaults(self) -> None:
        account = provider_account_from_template(
            "custom",
            "openai_v1",
            endpoint="http://localhost:8080",
            auth_mode="none",
            secret_ref="secret://custom/key",
            timeout_seconds=120,
            headers={"X-Custom": "1"},
            metadata={"region": "us-west"},
        )
        assert account.endpoint == "http://localhost:8080"
        assert account.auth_mode == "none"
        assert account.secret_ref == "secret://custom/key"
        assert account.timeout_seconds == 120
        assert account.headers == {"X-Custom": "1"}
        assert account.metadata["region"] == "us-west"
        assert account.metadata["template"] == "openai_v1"


# ---------------------------------------------------------------------------
# TeamConfig / resolve
# ---------------------------------------------------------------------------


class TestTeamConfigResolveRole:
    """Tests for ``TeamConfig.resolve_role``."""

    def test_happy_path(self, sample_team_config: TeamConfig) -> None:
        cfg = sample_team_config.resolve_role(ModelRole.PLANNER)
        assert isinstance(cfg, AgentModelConfig)
        assert cfg.role == ModelRole.PLANNER
        assert cfg.provider == "openai"

    def test_missing_role_raises(self, sample_team_config: TeamConfig) -> None:
        with pytest.raises(ConfigError) as exc_info:
            sample_team_config.resolve_role(ModelRole.RETRIEVER)
        assert "No model binding configured for role 'retriever'" in str(exc_info.value)


class TestTeamConfigResolveModel:
    """Tests for ``TeamConfig.resolve_model``."""

    def test_missing_model_id_raises(self, sample_team_config: TeamConfig) -> None:
        with pytest.raises(ConfigError) as exc_info:
            sample_team_config.resolve_model("nonexistent")
        assert "No model binding configured with id 'nonexistent'" in str(exc_info.value)

    def test_missing_provider_raises(self, sample_team_config: TeamConfig) -> None:
        bad_model = ModelConfig(
            id="bad",
            role=ModelRole.TESTER,
            provider="unknown",
            model_name="gpt-4",
        )
        team = sample_team_config.model_copy(
            update={"models": {**sample_team_config.models, "bad": bad_model}}
        )
        with pytest.raises(ConfigError) as exc_info:
            team.resolve_model("bad")
        assert "references unknown provider 'unknown'" in str(exc_info.value)

    def test_auth_mode_requires_secret_but_none_raises(self, sample_team_config: TeamConfig) -> None:
        provider = ProviderConfig(
            id="needs-secret",
            provider_type="openai_v1",
            endpoint="https://api.openai.com/v1",
            auth_mode="api_key",
            secret_ref=None,
            api_key=None,
        )
        model = ModelConfig(
            id="m1",
            role=ModelRole.GENERATOR,
            provider="needs-secret",
            model_name="gpt-4",
        )
        team = TeamConfig(
            providers={"needs-secret": provider},
            models={"m1": model},
        )
        with pytest.raises(ConfigError) as exc_info:
            team.resolve_model("m1")
        assert "requires a secret_ref" in str(exc_info.value)


class TestTeamConfigByRole:
    """Tests for ``TeamConfig.by_role``."""

    def test_returns_dict_mapping_roles(self, sample_team_config: TeamConfig) -> None:
        mapping = sample_team_config.by_role()
        assert isinstance(mapping, dict)
        assert ModelRole.PLANNER in mapping
        assert isinstance(mapping[ModelRole.PLANNER], AgentModelConfig)

    def test_duplicate_roles_keep_first(self, sample_team_config: TeamConfig) -> None:
        first_model = ModelConfig(
            id="first",
            role=ModelRole.PLANNER,
            provider="openai",
            model_name="gpt-3",
        )
        second_model = ModelConfig(
            id="second",
            role=ModelRole.PLANNER,
            provider="openai",
            model_name="gpt-4",
        )
        team = sample_team_config.model_copy(
            update={"models": {"first": first_model, "second": second_model}}
        )
        mapping = team.by_role()
        assert mapping[ModelRole.PLANNER].model == "gpt-3"


class TestTeamConfigDump:
    """Tests for ``TeamConfig.dump``."""

    def test_redacted_true_masks_secrets(self, sample_team_config: TeamConfig) -> None:
        dumped = sample_team_config.dump(redacted=True)
        assert dumped["providers"]["openai"]["api_key"] == redact_secret("sk-secret")

    def test_redacted_false_excludes_api_key(self, sample_team_config: TeamConfig) -> None:
        dumped = sample_team_config.dump(redacted=False)
        assert "api_key" not in dumped["providers"]["openai"]


# ---------------------------------------------------------------------------
# Secret stores
# ---------------------------------------------------------------------------


class TestKeyringSecretStore:
    """Tests for ``KeyringSecretStore`` using a mocked keyring module."""

    def test_set_and_get(self, keyring_store: KeyringSecretStore) -> None:
        keyring_store.set("ref1", "value1")
        assert keyring_store._keyring.set_password.call_count == 1
        keyring_store._keyring.get_password.return_value = "value1"
        assert keyring_store.get("ref1") == "value1"

    def test_get_missing_raises(self, keyring_store: KeyringSecretStore) -> None:
        keyring_store._keyring.get_password.return_value = None
        with pytest.raises(ConfigError) as exc_info:
            keyring_store.get("missing")
        assert "not found in OS keychain" in str(exc_info.value)

    def test_delete(self, keyring_store: KeyringSecretStore) -> None:
        keyring_store.delete("ref1")
        keyring_store._keyring.delete_password.assert_called_once_with(
            keyring_store.service_name, "ref1"
        )


class TestEncryptedFileSecretStore:
    """Tests for ``EncryptedFileSecretStore`` using temporary files."""

    def test_set_get_delete_roundtrip(self, encrypted_store: EncryptedFileSecretStore) -> None:
        encrypted_store.set("key1", "value1")
        assert encrypted_store.get("key1") == "value1"
        encrypted_store.set("key2", "value2")
        assert encrypted_store.get("key2") == "value2"
        encrypted_store.delete("key1")
        with pytest.raises(ConfigError) as exc_info:
            encrypted_store.get("key1")
        assert "not found in encrypted vault" in str(exc_info.value)

    def test_get_missing_raises(self, encrypted_store: EncryptedFileSecretStore) -> None:
        with pytest.raises(ConfigError) as exc_info:
            encrypted_store.get("missing")
        assert "not found in encrypted vault" in str(exc_info.value)

    def test_wrong_passphrase_raises(self, encrypted_store: EncryptedFileSecretStore) -> None:
        encrypted_store.set("key1", "value1")
        bad_store = EncryptedFileSecretStore(path=encrypted_store.path, passphrase="wrong")
        with pytest.raises(ConfigError) as exc_info:
            bad_store.get("key1")
        assert "Invalid Agentheim vault passphrase" in str(exc_info.value)


class TestGetSecretStore:
    """Tests for ``get_secret_store`` factory."""

    def test_env_file_returns_encrypted_file_store(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGENTHEIM_SECRET_BACKEND", "file")
        store = get_secret_store()
        assert isinstance(store, EncryptedFileSecretStore)

    def test_prefer_keyring_with_working_keyring(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGENTHEIM_SECRET_BACKEND", raising=False)
        mock_module = MagicMock()
        monkeypatch.setitem(sys.modules, "keyring", mock_module)
        store = get_secret_store(prefer_keyring=True)
        assert isinstance(store, KeyringSecretStore)

    def test_keyring_failure_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGENTHEIM_SECRET_BACKEND", raising=False)

        def failing_init(self: KeyringSecretStore) -> None:
            raise RuntimeError("keyring unavailable")

        monkeypatch.setattr(KeyringSecretStore, "__init__", failing_init)
        store = get_secret_store(prefer_keyring=True)
        assert isinstance(store, EncryptedFileSecretStore)


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------


class TestLoadProfilesDocument:
    """Tests for ``load_profiles_document``."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.json"
        with pytest.raises(ConfigError) as exc_info:
            load_profiles_document(missing)
        assert "No Agentheim provider profile found" in str(exc_info.value)

    def test_valid_json_loads(self, tmp_path: Path) -> None:
        doc = ProfilesDocument(
            version=1,
            default_profile="default",
            profiles={
                "default": TeamProfile(
                    name="default",
                    providers={"openai": ProviderAccount(id="openai", kind="openai_v1")},
                    models={
                        "m1": ModelBinding(
                            id="m1", role=ModelRole.PLANNER, provider="openai", model="gpt-4"
                        )
                    },
                )
            },
        )
        path = tmp_path / "providers.json"
        path.write_text(json.dumps(doc.model_dump(), indent=2), encoding="utf-8")
        loaded = load_profiles_document(path)
        assert loaded.default_profile == "default"
        assert "default" in loaded.profiles

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "providers.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            load_profiles_document(path)
        assert "Failed to load provider profiles" in str(exc_info.value)


class TestSaveProfilesDocument:
    """Tests for ``save_profiles_document``."""

    def test_writes_file_returns_path(self, tmp_path: Path) -> None:
        doc = ProfilesDocument(
            version=1,
            default_profile="default",
            profiles={},
        )
        path = tmp_path / "out" / "providers.json"
        returned = save_profiles_document(doc, path)
        assert returned == path
        assert path.exists()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["version"] == 1
        assert raw["default_profile"] == "default"


class TestResolveProfileName:
    """Tests for ``resolve_profile_name``."""

    def test_explicit_arg_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGENTHEIM_CONFIG_DIR", raising=False)
        assert resolve_profile_name(profile="explicit") == "explicit"

    def test_project_pointer_wins_next(self, tmp_path: Path) -> None:
        pointer_dir = tmp_path / "project"
        pointer_dir.mkdir()
        write_project_profile_pointer("from-pointer", project_root=pointer_dir)
        result = resolve_profile_name(profile=None, project_root=pointer_dir)
        assert result == "from-pointer"

    def test_falls_back_to_default_profile(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(tmp_path))
        doc = ProfilesDocument(
            version=1,
            default_profile="fallback",
            profiles={},
        )
        save_profiles_document(doc)
        result = resolve_profile_name(profile=None, project_root=tmp_path / "nonexistent")
        assert result == "fallback"


class TestWriteProjectProfilePointer:
    """Tests for ``write_project_profile_pointer``."""

    def test_writes_json_with_profile(self, tmp_path: Path) -> None:
        root = tmp_path / "proj"
        root.mkdir()
        path = write_project_profile_pointer("prod", project_root=root)
        assert path.exists()
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["profile"] == "prod"


class TestLoadTeamConfig:
    """Tests for ``load_team_config``."""

    def test_missing_profile_raises_with_available(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(tmp_path))
        doc = ProfilesDocument(
            version=1,
            default_profile="default",
            profiles={
                "default": TeamProfile(
                    name="default",
                    providers={"openai": ProviderAccount(id="openai", kind="openai_v1", auth_mode="none")},
                    models={"m1": ModelBinding(id="m1", role=ModelRole.PLANNER, provider="openai", model="gpt-4")},
                )
            },
        )
        save_profiles_document(doc)
        with pytest.raises(ConfigError) as exc_info:
            load_team_config(profile="missing")
        assert "not found" in str(exc_info.value)
        assert "default" in str(exc_info.value)

    def test_loads_and_converts(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("AGENTHEIM_CONFIG_DIR", str(tmp_path))
        doc = ProfilesDocument(
            version=1,
            default_profile="default",
            profiles={
                "default": TeamProfile(
                    name="default",
                    providers={"openai": ProviderAccount(id="openai", kind="openai_v1", auth_mode="none")},
                    models={"m1": ModelBinding(id="m1", role=ModelRole.PLANNER, provider="openai", model="gpt-4")},
                )
            },
        )
        save_profiles_document(doc)
        team = load_team_config()
        assert isinstance(team, TeamConfig)
        assert team.profile_name == "default"
        assert "openai" in team.providers
        assert "m1" in team.models


# ---------------------------------------------------------------------------
# TeamProfile / ProfilesDocument
# ---------------------------------------------------------------------------


class TestTeamProfileValidateRefs:
    """Tests for ``TeamProfile`` reference validation."""

    def test_model_referencing_unknown_provider_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            TeamProfile(
                name="bad",
                providers={},
                models={
                    "m1": ModelBinding(
                        id="m1", role=ModelRole.PLANNER, provider="missing", model="gpt-4"
                    )
                },
            )
        assert "unknown provider" in str(exc_info.value).lower()


class TestTeamProfileToTeamConfig:
    """Tests for ``TeamProfile.to_team_config``."""

    def test_converts_correctly(self) -> None:
        profile = TeamProfile(
            name="dev",
            providers={
                "openai": ProviderAccount(
                    id="openai", kind="openai_v1", endpoint="https://api.openai.com/v1"
                )
            },
            models={
                "m1": ModelBinding(
                    id="m1", role=ModelRole.GENERATOR, provider="openai", model="gpt-4"
                )
            },
        )
        team = profile.to_team_config()
        assert isinstance(team, TeamConfig)
        assert team.profile_name == "dev"
        assert team.providers["openai"].provider_type == "openai_v1"
        assert team.models["m1"].model_name == "gpt-4"
        assert team.models["m1"].role == ModelRole.GENERATOR
