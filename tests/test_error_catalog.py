"""Tests for core/error_catalog.py — shared user-facing error catalog."""

from __future__ import annotations

import pytest

from core.error_catalog import (
    CATALOG,
    ErrorCatalogEntry,
    catalog_entry_for,
    format_api_response,
    format_cli_message,
)
from core.errors import (
    AIteamError,
    ConfigError,
    ExecutionError,
    IntegrationError,
    PatchApplicationError,
    PlanningError,
    ProviderError,
    RepoInspectionError,
    ResumeError,
    ToolSafetyError,
    VerificationError,
)


class TestCategories:
    """Every category has machine_code, human_message, exit_code, http_status, next_actions."""

    @pytest.mark.parametrize(
        "category",
        [
            "validation_error",
            "configuration_error",
            "provider_error",
            "auth_error",
            "policy_block",
            "integration_unavailable",
            "not_found",
            "run_failed",
            "unexpected_error",
        ],
    )
    def test_category_has_required_fields(self, category: str) -> None:
        entry = CATALOG[category]
        assert entry.category == category
        assert entry.machine_code.startswith("E")
        assert entry.human_message
        assert entry.exit_code >= 0
        assert 100 <= entry.http_status <= 599
        assert isinstance(entry.next_actions, list)
        assert all(isinstance(a, str) for a in entry.next_actions)

    def test_validation_exit_code(self) -> None:
        assert CATALOG["validation_error"].exit_code == 2

    def test_configuration_exit_code(self) -> None:
        assert CATALOG["configuration_error"].exit_code == 3

    def test_auth_exit_code(self) -> None:
        assert CATALOG["auth_error"].exit_code == 4

    def test_provider_exit_code(self) -> None:
        assert CATALOG["provider_error"].exit_code == 5

    def test_policy_block_exit_code(self) -> None:
        assert CATALOG["policy_block"].exit_code == 6

    def test_integration_unavailable_exit_code(self) -> None:
        assert CATALOG["integration_unavailable"].exit_code == 7

    def test_not_found_exit_code(self) -> None:
        assert CATALOG["not_found"].exit_code == 8

    def test_run_failed_exit_code(self) -> None:
        assert CATALOG["run_failed"].exit_code == 9

    def test_unexpected_exit_code(self) -> None:
        assert CATALOG["unexpected_error"].exit_code == 1


class TestExceptionMapping:
    def test_value_error_maps_to_validation(self) -> None:
        entry = catalog_entry_for(ValueError("bad"))
        assert entry.category == "validation_error"

    def test_config_error_maps_to_configuration(self) -> None:
        entry = catalog_entry_for(ConfigError("missing"))
        assert entry.category == "configuration_error"

    def test_key_error_maps_to_configuration(self) -> None:
        entry = catalog_entry_for(KeyError("key"))
        assert entry.category == "configuration_error"

    def test_import_error_maps_to_configuration(self) -> None:
        entry = catalog_entry_for(ImportError("mod"))
        assert entry.category == "configuration_error"

    def test_file_not_found_maps_to_configuration(self) -> None:
        entry = catalog_entry_for(FileNotFoundError("missing"))
        assert entry.category == "configuration_error"

    def test_provider_auth_maps_to_auth(self) -> None:
        entry = catalog_entry_for(ProviderError("Authentication failed"))
        assert entry.category == "auth_error"

    def test_provider_api_key_maps_to_auth(self) -> None:
        entry = catalog_entry_for(ProviderError("Invalid API key"))
        assert entry.category == "auth_error"

    def test_provider_permission_maps_to_auth(self) -> None:
        entry = catalog_entry_for(ProviderError("Permission denied"))
        assert entry.category == "auth_error"

    def test_provider_rate_limit_maps_to_provider(self) -> None:
        entry = catalog_entry_for(ProviderError("Rate limit exceeded"))
        assert entry.category == "provider_error"

    def test_provider_generic_maps_to_provider(self) -> None:
        entry = catalog_entry_for(ProviderError("Something broke"))
        assert entry.category == "provider_error"

    def test_permission_error_maps_to_auth(self) -> None:
        entry = catalog_entry_for(PermissionError("no access"))
        assert entry.category == "auth_error"

    def test_tool_safety_maps_to_policy_block(self) -> None:
        entry = catalog_entry_for(ToolSafetyError("unsafe"))
        assert entry.category == "policy_block"

    def test_integration_error_maps_to_integration_unavailable(self) -> None:
        entry = catalog_entry_for(IntegrationError("missing"))
        assert entry.category == "integration_unavailable"

    def test_resume_not_found_maps_to_not_found(self) -> None:
        entry = catalog_entry_for(ResumeError("Run not found"))
        assert entry.category == "not_found"

    def test_resume_other_maps_to_run_failed(self) -> None:
        entry = catalog_entry_for(ResumeError("Ledger corrupt"))
        assert entry.category == "run_failed"

    def test_execution_error_maps_to_run_failed(self) -> None:
        entry = catalog_entry_for(ExecutionError("exec failed"))
        assert entry.category == "run_failed"

    def test_planning_error_maps_to_run_failed(self) -> None:
        entry = catalog_entry_for(PlanningError("plan failed"))
        assert entry.category == "run_failed"

    def test_patch_error_maps_to_run_failed(self) -> None:
        entry = catalog_entry_for(PatchApplicationError("patch bad"))
        assert entry.category == "run_failed"

    def test_verification_error_maps_to_run_failed(self) -> None:
        entry = catalog_entry_for(VerificationError("verify failed"))
        assert entry.category == "run_failed"

    def test_repo_inspection_maps_to_run_failed(self) -> None:
        entry = catalog_entry_for(RepoInspectionError("scan failed"))
        assert entry.category == "run_failed"

    def test_runtime_error_maps_to_unexpected(self) -> None:
        entry = catalog_entry_for(RuntimeError("panic"))
        assert entry.category == "unexpected_error"

    def test_unmapped_custom_error_maps_to_unexpected(self) -> None:
        class CustomError(Exception):
            pass

        entry = catalog_entry_for(CustomError("?"))
        assert entry.category == "unexpected_error"

    def test_aitteam_base_maps_to_unexpected(self) -> None:
        entry = catalog_entry_for(AIteamError("generic"))
        assert entry.category == "unexpected_error"


class TestCliFormatting:
    def test_includes_machine_code_and_message(self) -> None:
        entry = CATALOG["configuration_error"]
        text = format_cli_message(entry, ConfigError("bad"))
        assert "E1002" in text
        assert entry.human_message in text
        assert "bad" in text

    def test_includes_next_actions(self) -> None:
        entry = CATALOG["not_found"]
        text = format_cli_message(entry)
        for action in entry.next_actions:
            assert action in text

    def test_omits_empty_exc(self) -> None:
        entry = CATALOG["unexpected_error"]
        text = format_cli_message(entry, ConfigError(""))
        lines = text.splitlines()
        assert lines[0] == f"Error ({entry.machine_code}): {entry.human_message}"


class TestApiFormatting:
    def test_includes_catalog_fields(self) -> None:
        entry = CATALOG["validation_error"]
        response = format_api_response(entry, ValueError("bad"))
        assert response["machine_code"] == "E1001"
        assert response["human_message"] == entry.human_message
        assert response["exit_code"] == 2
        assert "next_actions" in response

    def test_preserves_error_summary_shape(self) -> None:
        entry = CATALOG["configuration_error"]
        response = format_api_response(entry, ConfigError("missing"))
        assert response["type"] == "ConfigError"
        assert response["message"] == "missing"
        assert "category" in response
        assert "retryable" in response
        assert "halt" in response
        assert "next_action" in response
        assert "troubleshooting_doc" in response
        assert "troubleshooting_section" in response

    def test_http_status_matches_category(self) -> None:
        assert CATALOG["validation_error"].http_status == 400
        assert CATALOG["auth_error"].http_status == 401
        assert CATALOG["not_found"].http_status == 404
        assert CATALOG["policy_block"].http_status == 409
        assert CATALOG["provider_error"].http_status == 503
        assert CATALOG["integration_unavailable"].http_status == 503
        assert CATALOG["run_failed"].http_status == 500
        assert CATALOG["unexpected_error"].http_status == 500


class TestCatalogIntegrity:
    def test_all_machine_codes_unique(self) -> None:
        codes = [e.machine_code for e in CATALOG.values()]
        assert len(codes) == len(set(codes))

    def test_all_exit_codes_unique(self) -> None:
        codes = [e.exit_code for e in CATALOG.values()]
        assert len(codes) == len(set(codes))
