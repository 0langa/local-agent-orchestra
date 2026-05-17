"""Tests for core/privacy_enforcer.py — structured privacy modes."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.privacy_enforcer import PrivacyEnforcer, PrivacyMode
from core.tool_protocol import ToolContext


class TestPrivacyMode:
    def test_standard_is_standard(self) -> None:
        assert PrivacyMode.STANDARD.value == "standard"

    def test_local_only_is_local_only(self) -> None:
        assert PrivacyMode.LOCAL_ONLY.value == "local_only"

    def test_strict_private_is_strict_private(self) -> None:
        assert PrivacyMode.STRICT_PRIVATE.value == "strict_private"

    def test_encrypted_is_encrypted(self) -> None:
        assert PrivacyMode.ENCRYPTED.value == "encrypted"


class TestPrivacyEnforcerStandard:
    def test_standard_allows_network_tool(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.STANDARD)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("http.request", {"url": "https://example.com"}, ctx)
        assert report["allowed"] is True
        assert report["violations"] == []

    def test_standard_allows_any_path(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.STANDARD)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": "secret.key"}, ctx)
        assert report["allowed"] is True

    def test_standard_no_redaction(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.STANDARD)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": "readme.md"}, ctx)
        assert report["redacted"] is False


class TestPrivacyEnforcerLocalOnly:
    def test_blocks_http_tool(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.LOCAL_ONLY)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("http.request", {"url": "https://example.com"}, ctx)
        assert report["allowed"] is False
        assert any("http.request" in v for v in report["violations"])

    def test_blocks_git_push(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.LOCAL_ONLY)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("git.push", {}, ctx)
        assert report["allowed"] is False

    def test_allows_local_tool(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.LOCAL_ONLY)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": "readme.md"}, ctx)
        assert report["allowed"] is True


class TestPrivacyEnforcerStrictPrivate:
    def test_blocks_sensitive_path(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.STRICT_PRIVATE)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": ".env"}, ctx)
        assert report["allowed"] is False
        assert any(".env" in v for v in report["violations"])

    def test_blocks_key_file(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.STRICT_PRIVATE)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": "id_rsa.pem"}, ctx)
        assert report["allowed"] is False

    def test_allows_non_sensitive_path(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.STRICT_PRIVATE)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": "readme.md"}, ctx)
        assert report["allowed"] is True


class TestPrivacyEnforcerEncrypted:
    def test_blocks_sensitive_path(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.ENCRYPTED)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": ".env"}, ctx)
        assert report["allowed"] is False

    def test_marks_redacted(self) -> None:
        enforcer = PrivacyEnforcer(mode=PrivacyMode.ENCRYPTED)
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": "readme.md"}, ctx)
        assert report["allowed"] is True
        assert report["redacted"] is True


class TestPrivacyEnforcerRedactParams:
    def test_redacts_secrets(self) -> None:
        enforcer = PrivacyEnforcer()
        params = {"api_key": "api_key: sk-12345abcdef", "name": "hello"}
        redacted = enforcer.redact_params(params)
        assert redacted["name"] == "hello"
        assert "[REDACTED" in redacted["api_key"]


class TestPrivacyEnforcerCustomPatterns:
    def test_custom_pattern_blocks(self) -> None:
        enforcer = PrivacyEnforcer(
            mode=PrivacyMode.STRICT_PRIVATE,
            sensitive_patterns=["*.custom"],
        )
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": "data.custom"}, ctx)
        assert report["allowed"] is False

    def test_custom_pattern_allows_others(self) -> None:
        enforcer = PrivacyEnforcer(
            mode=PrivacyMode.STRICT_PRIVATE,
            sensitive_patterns=["*.custom"],
        )
        ctx = ToolContext(workspace=Path("."))
        report = enforcer.evaluate("fs.read", {"path": ".env"}, ctx)
        # .env is NOT in custom patterns, so it passes
        assert report["allowed"] is True
