from __future__ import annotations

import pytest

from core.errors import (
    AIteamError,
    ConfigError,
    ExecutionError,
    PatchApplicationError,
    PlanningError,
    ProviderError,
    RepoInspectionError,
    ResumeError,
    ToolSafetyError,
    VerificationError,
)


class TestErrorHierarchy:
    def test_base_is_exception(self) -> None:
        with pytest.raises(AIteamError):
            raise AIteamError("base")

    def test_config_error_is_base(self) -> None:
        try:
            raise ConfigError("bad config")
        except AIteamError as exc:
            assert "bad config" in str(exc)

    def test_provider_error_is_base(self) -> None:
        try:
            raise ProviderError("provider down")
        except AIteamError:
            pass

    def test_execution_error_is_base(self) -> None:
        try:
            raise ExecutionError("execution failed")
        except AIteamError:
            pass

    def test_planning_error_is_base(self) -> None:
        try:
            raise PlanningError("plan failed")
        except AIteamError:
            pass

    def test_patch_application_error_is_base(self) -> None:
        try:
            raise PatchApplicationError("patch rejected")
        except AIteamError:
            pass

    def test_verification_error_is_base(self) -> None:
        try:
            raise VerificationError("verify failed")
        except AIteamError:
            pass

    def test_tool_safety_error_is_base(self) -> None:
        try:
            raise ToolSafetyError("unsafe")
        except AIteamError:
            pass

    def test_repo_inspection_error_is_base(self) -> None:
        try:
            raise RepoInspectionError("scan failed")
        except AIteamError:
            pass

    def test_resume_error_is_base(self) -> None:
        try:
            raise ResumeError("resume failed")
        except AIteamError:
            pass

    def test_error_chaining(self) -> None:
        original = ValueError("original")
        try:
            raise ConfigError("wrapped") from original
        except ConfigError as wrapped:
            assert wrapped.__cause__ is original
