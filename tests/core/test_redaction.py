from __future__ import annotations

import pytest

from core.redaction import redact_dict, redact_text


class TestRedactText:
    def test_api_key_redaction(self) -> None:
        text = "api_key: sk-1234567890abcdef"
        result = redact_text(text)
        assert "REDACTED" in result
        assert "sk-1234567890abcdef" not in result

    def test_token_redaction(self) -> None:
        text = "token: abcdef1234567890"
        result = redact_text(text)
        assert "REDACTED" in result

    def test_password_redaction(self) -> None:
        text = "password: secret123"
        result = redact_text(text)
        assert "REDACTED" in result

    def test_bearer_token_redaction(self) -> None:
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = redact_text(text)
        assert "REDACTED" in result

    def test_no_secrets_unchanged(self) -> None:
        text = "hello world, no secrets here"
        result = redact_text(text)
        assert result == text

    def test_aws_key_redaction(self) -> None:
        text = "AKIAIOSFODNN7EXAMPLE"
        result = redact_text(text)
        assert "REDACTED" in result


class TestRedactDict:
    def test_dict_with_secret(self) -> None:
        data = {"name": "app", "key": "api_key: secret12345"}
        result = redact_dict(data)
        assert "REDACTED" in result["key"]
        assert result["name"] == "app"

    def test_nested_dict(self) -> None:
        data = {"config": {"pass": "password: hunter12345"}}
        result = redact_dict(data)
        assert "REDACTED" in result["config"]["pass"]

    def test_list_with_secrets(self) -> None:
        data = ["api_key: abc123456789", "normal text"]
        result = redact_dict(data)
        assert "REDACTED" in result[0]
        assert result[1] == "normal text"

    def test_no_secrets_preserved(self) -> None:
        data = {"name": "app", "count": 42}
        result = redact_dict(data)
        assert result == data
