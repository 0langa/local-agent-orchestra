"""Tests for core/error_classification.py — error taxonomy and classification."""

from __future__ import annotations

import socket
import ssl

import pytest

from core.error_classification import (
    ErrorCategory,
    backoff_for,
    classify_error,
    error_summary,
    error_summary_from_text,
    max_retries_for,
    should_halt,
    should_retry,
)
from core.errors import (
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


class TestClassifyError:
    def test_connection_error_is_transient(self) -> None:
        assert classify_error(ConnectionError("boom")) == ErrorCategory.TRANSIENT

    def test_timeout_error_is_transient(self) -> None:
        assert classify_error(TimeoutError("slow")) == ErrorCategory.TRANSIENT

    def test_socket_timeout_is_transient(self) -> None:
        assert classify_error(socket.timeout("slow")) == ErrorCategory.TRANSIENT

    def test_ssl_error_is_transient(self) -> None:
        assert classify_error(ssl.SSLError("cert")) == ErrorCategory.TRANSIENT

    def test_os_error_is_transient(self) -> None:
        assert classify_error(OSError("io")) == ErrorCategory.TRANSIENT

    def test_permission_error_is_permission(self) -> None:
        assert classify_error(PermissionError("no")) == ErrorCategory.PERMISSION

    def test_file_not_found_is_configuration(self) -> None:
        assert classify_error(FileNotFoundError("missing")) == ErrorCategory.CONFIGURATION

    def test_import_error_is_configuration(self) -> None:
        assert classify_error(ImportError("bad")) == ErrorCategory.CONFIGURATION

    def test_key_error_is_configuration(self) -> None:
        assert classify_error(KeyError("key")) == ErrorCategory.CONFIGURATION

    def test_value_error_is_configuration(self) -> None:
        assert classify_error(ValueError("bad")) == ErrorCategory.CONFIGURATION

    def test_assertion_error_is_verification(self) -> None:
        assert classify_error(AssertionError("fail")) == ErrorCategory.VERIFICATION

    def test_memory_error_is_fatal(self) -> None:
        assert classify_error(MemoryError("oom")) == ErrorCategory.FATAL

    def test_recursion_error_is_fatal(self) -> None:
        assert classify_error(RecursionError("deep")) == ErrorCategory.FATAL

    def test_not_implemented_is_fatal(self) -> None:
        assert classify_error(NotImplementedError("todo")) == ErrorCategory.FATAL

    def test_runtime_error_is_fatal(self) -> None:
        assert classify_error(RuntimeError("panic")) == ErrorCategory.FATAL

    def test_unmapped_exception_is_fatal(self) -> None:
        class CustomError(Exception):
            pass

        assert classify_error(CustomError("?")) == ErrorCategory.FATAL

    def test_subclass_inherits_parent(self) -> None:
        class MyConnectionError(ConnectionError):
            pass

        assert classify_error(MyConnectionError("boom")) == ErrorCategory.TRANSIENT

    def test_config_error_is_configuration(self) -> None:
        assert classify_error(ConfigError("bad config")) == ErrorCategory.CONFIGURATION

    def test_tool_safety_error_is_permission(self) -> None:
        assert classify_error(ToolSafetyError("unsafe")) == ErrorCategory.PERMISSION

    def test_planning_error_is_recoverable(self) -> None:
        assert classify_error(PlanningError("bad plan")) == ErrorCategory.RECOVERABLE

    def test_execution_error_is_fatal(self) -> None:
        assert classify_error(ExecutionError("exec failed")) == ErrorCategory.FATAL

    def test_patch_application_error_is_verification(self) -> None:
        assert classify_error(PatchApplicationError("patch bad")) == ErrorCategory.VERIFICATION

    def test_verification_error_is_verification(self) -> None:
        assert classify_error(VerificationError("verify failed")) == ErrorCategory.VERIFICATION

    def test_resume_error_is_configuration(self) -> None:
        assert classify_error(ResumeError("missing ledger")) == ErrorCategory.CONFIGURATION

    def test_integration_error_is_configuration(self) -> None:
        assert classify_error(IntegrationError("missing dep")) == ErrorCategory.CONFIGURATION

    def test_repo_inspection_error_is_configuration(self) -> None:
        assert classify_error(RepoInspectionError("bad repo")) == ErrorCategory.CONFIGURATION

    def test_provider_auth_error_is_configuration(self) -> None:
        assert classify_error(ProviderError("Authentication failed")) == ErrorCategory.CONFIGURATION

    def test_provider_permission_denied_is_permission(self) -> None:
        assert classify_error(ProviderError("Permission denied for deployment")) == ErrorCategory.PERMISSION

    def test_provider_forbidden_is_permission(self) -> None:
        assert classify_error(ProviderError("403 forbidden")) == ErrorCategory.PERMISSION

    def test_provider_rate_limit_is_transient(self) -> None:
        assert classify_error(ProviderError("Rate limit exceeded")) == ErrorCategory.TRANSIENT

    def test_provider_service_unavailable_is_transient(self) -> None:
        assert classify_error(ProviderError("Service unavailable")) == ErrorCategory.TRANSIENT

    def test_provider_timeout_is_transient(self) -> None:
        assert classify_error(ProviderError("Request timed out")) == ErrorCategory.TRANSIENT

    def test_provider_connection_is_transient(self) -> None:
        assert classify_error(ProviderError("Network unreachable")) == ErrorCategory.TRANSIENT

    def test_provider_model_error_is_configuration(self) -> None:
        assert classify_error(ProviderError("Model not found")) == ErrorCategory.CONFIGURATION

    def test_provider_generic_is_fatal(self) -> None:
        assert classify_error(ProviderError("something else")) == ErrorCategory.FATAL


class TestRetryStrategy:
    def test_should_retry_transient(self) -> None:
        assert should_retry(ErrorCategory.TRANSIENT) is True

    def test_should_retry_recoverable(self) -> None:
        assert should_retry(ErrorCategory.RECOVERABLE) is True

    def test_should_retry_verification(self) -> None:
        assert should_retry(ErrorCategory.VERIFICATION) is True

    def test_should_not_retry_configuration(self) -> None:
        assert should_retry(ErrorCategory.CONFIGURATION) is False

    def test_should_not_retry_permission(self) -> None:
        assert should_retry(ErrorCategory.PERMISSION) is False

    def test_should_not_retry_fatal(self) -> None:
        assert should_retry(ErrorCategory.FATAL) is False


class TestHaltStrategy:
    def test_should_halt_configuration(self) -> None:
        assert should_halt(ErrorCategory.CONFIGURATION) is True

    def test_should_halt_permission(self) -> None:
        assert should_halt(ErrorCategory.PERMISSION) is True

    def test_should_halt_fatal(self) -> None:
        assert should_halt(ErrorCategory.FATAL) is True

    def test_should_not_halt_transient(self) -> None:
        assert should_halt(ErrorCategory.TRANSIENT) is False

    def test_should_not_halt_recoverable(self) -> None:
        assert should_halt(ErrorCategory.RECOVERABLE) is False

    def test_should_not_halt_verification(self) -> None:
        assert should_halt(ErrorCategory.VERIFICATION) is False


class TestRetryConfig:
    def test_max_retries_transient(self) -> None:
        assert max_retries_for(ErrorCategory.TRANSIENT) == 5

    def test_max_retries_recoverable(self) -> None:
        assert max_retries_for(ErrorCategory.RECOVERABLE) == 3

    def test_max_retries_verification(self) -> None:
        assert max_retries_for(ErrorCategory.VERIFICATION) == 3

    def test_max_retries_default(self) -> None:
        assert max_retries_for(ErrorCategory.FATAL, default=1) == 1

    def test_backoff_transient(self) -> None:
        assert backoff_for(ErrorCategory.TRANSIENT) == 1.0

    def test_backoff_recoverable(self) -> None:
        assert backoff_for(ErrorCategory.RECOVERABLE) == 2.0

    def test_backoff_verification(self) -> None:
        assert backoff_for(ErrorCategory.VERIFICATION) == 1.5

    def test_backoff_default(self) -> None:
        assert backoff_for(ErrorCategory.FATAL, default=0.5) == 0.5


class TestErrorSummary:
    def test_summary_structure(self) -> None:
        summary = error_summary(ValueError("bad input"))
        assert summary["type"] == "ValueError"
        assert summary["message"] == "bad input"
        assert summary["category"] == "configuration"
        assert summary["retryable"] is False
        assert summary["halt"] is True
        assert summary["next_action"] == "Fix local/provider configuration before retrying."
        assert summary["troubleshooting_doc"] == "docs/TROUBLESHOOTING.md"
        assert summary["troubleshooting_section"] == "Configuration Issues"

    def test_summary_for_transient(self) -> None:
        summary = error_summary(TimeoutError("slow"))
        assert summary["category"] == "transient"
        assert summary["retryable"] is True
        assert summary["halt"] is False
        assert summary["next_action"] == "Retry operation after backoff or switch provider if issue persists."
        assert summary["troubleshooting_section"] == "Provider rate limit or temporary outage"

    def test_summary_for_permission(self) -> None:
        summary = error_summary(ProviderError("Access denied"))
        assert summary["category"] == "permission"
        assert summary["retryable"] is False
        assert summary["halt"] is True
        assert summary["next_action"] == "Grant approval or update credentials/permissions before retrying."
        assert summary["troubleshooting_section"] == "Provider permission denied / forbidden"

    def test_summary_from_serialized_error(self) -> None:
        summary = error_summary_from_text("Authentication failed for provider", "ProviderError")
        assert summary["type"] == "ProviderError"
        assert summary["category"] == "configuration"
        assert summary["troubleshooting_section"] == "Provider authentication failed"
