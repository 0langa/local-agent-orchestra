"""Tests for core/policy_engine.py — comprehensive policy evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.policy_engine import PolicyConfig, PolicyDecision, PolicyEngine
from core.tool_protocol import RiskLevel, ToolContext


class TestPolicyEngineDefaults:
    def test_default_config_allows_none(self) -> None:
        engine = PolicyEngine()
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.read", {"path": "x"}, ctx, RiskLevel.NONE)
        assert decision.decision == "allow"

    def test_default_config_allows_low(self) -> None:
        engine = PolicyEngine()
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.read", {"path": "x"}, ctx, RiskLevel.LOW)
        assert decision.decision == "allow"

    def test_default_config_asks_medium(self) -> None:
        engine = PolicyEngine()
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.write", {"path": "x"}, ctx, RiskLevel.MEDIUM)
        assert decision.decision == "ask"

    def test_default_config_asks_high(self) -> None:
        engine = PolicyEngine()
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.delete", {"path": "x"}, ctx, RiskLevel.HIGH)
        assert decision.decision == "ask"

    def test_default_config_denies_critical(self) -> None:
        engine = PolicyEngine()
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("system.exec", {"command": ["rm", "-rf", "/"]}, ctx, RiskLevel.CRITICAL)
        assert decision.decision == "deny"


class TestLocalOnlyMode:
    def test_blocks_http_request(self) -> None:
        config = PolicyConfig(local_only=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("http.request", {"url": "https://x.com"}, ctx, RiskLevel.HIGH)
        assert decision.decision == "deny"
        assert "local_only" in decision.reason

    def test_blocks_git_push(self) -> None:
        config = PolicyConfig(local_only=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("git.push", {}, ctx, RiskLevel.HIGH)
        assert decision.decision == "deny"

    def test_allows_local_tool(self) -> None:
        config = PolicyConfig(local_only=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.read", {"path": "readme.md"}, ctx, RiskLevel.LOW)
        assert decision.decision == "allow"


class TestStrictPrivateMode:
    def test_blocks_env_file(self) -> None:
        config = PolicyConfig(strict_private=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.read", {"path": ".env"}, ctx, RiskLevel.LOW)
        assert decision.decision == "deny"
        assert "strict_private" in decision.reason

    def test_blocks_pem_file(self) -> None:
        config = PolicyConfig(strict_private=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.read", {"path": "key.pem"}, ctx, RiskLevel.LOW)
        assert decision.decision == "deny"

    def test_allows_regular_file(self) -> None:
        config = PolicyConfig(strict_private=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.read", {"path": "readme.md"}, ctx, RiskLevel.LOW)
        assert decision.decision == "allow"


class TestPathBoundaries:
    def test_denies_outside_allowed_paths(self) -> None:
        config = PolicyConfig(path_boundaries_allowed=["/tmp"])
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("/tmp"), allowed_paths=["/tmp"])
        decision = engine.evaluate("fs.read", {"path": "/etc/passwd"}, ctx, RiskLevel.LOW)
        assert decision.decision == "deny"
        assert "path_boundary" in decision.policy_id

    def test_allows_inside_allowed_paths(self) -> None:
        config = PolicyConfig(path_boundaries_allowed=["/tmp"])
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("/tmp"), allowed_paths=["/tmp"])
        decision = engine.evaluate("fs.read", {"path": "/tmp/file.txt"}, ctx, RiskLevel.LOW)
        assert decision.decision == "allow"


class TestCommandAllowlistDenylist:
    def test_denylist_blocks_denied_command(self) -> None:
        config = PolicyConfig(command_denylist=["rm"])
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("shell.exec", {"command": ["rm", "-rf", "/tmp"]}, ctx, RiskLevel.HIGH)
        assert decision.decision == "deny"
        assert "command_denylist" in decision.policy_id

    def test_allowlist_blocks_unlisted_command(self) -> None:
        config = PolicyConfig(command_allowlist=["ls", "cat"])
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("shell.exec", {"command": ["rm", "/tmp"]}, ctx, RiskLevel.HIGH)
        assert decision.decision == "deny"
        assert "command_allowlist" in decision.policy_id

    def test_allowlist_allows_listed_command(self) -> None:
        config = PolicyConfig(command_allowlist=["ls", "cat"])
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("shell.exec", {"command": ["ls", "/tmp"]}, ctx, RiskLevel.LOW)
        assert decision.decision == "allow"


class TestNetworkRestriction:
    def test_blocks_http_when_network_not_allowed(self) -> None:
        config = PolicyConfig(network_allowed=False)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("http.request", {"url": "https://x.com"}, ctx, RiskLevel.HIGH)
        assert decision.decision == "deny"
        assert "network_restriction" in decision.policy_id

    def test_allows_http_when_network_allowed(self) -> None:
        config = PolicyConfig(network_allowed=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("http.request", {"url": "https://x.com"}, ctx, RiskLevel.LOW)
        assert decision.decision == "allow"


class TestDeleteRestriction:
    def test_asks_when_delete_require_reason(self) -> None:
        config = PolicyConfig(delete_allowed=False, delete_require_reason=True)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.delete", {"path": "/tmp/x"}, ctx, RiskLevel.HIGH)
        assert decision.decision == "ask"
        assert "delete_restriction" in decision.policy_id

    def test_denies_when_delete_no_reason(self) -> None:
        config = PolicyConfig(delete_allowed=False, delete_require_reason=False)
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))
        decision = engine.evaluate("fs.delete", {"path": "/tmp/x"}, ctx, RiskLevel.HIGH)
        assert decision.decision == "deny"


class TestBudgetLimit:
    def test_denies_when_budget_exceeded(self) -> None:
        from core.tool_protocol import ToolBudget

        config = PolicyConfig()
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."), budget=ToolBudget(max_calls=5, calls_used=5))
        decision = engine.evaluate("fs.read", {"path": "x"}, ctx, RiskLevel.LOW)
        assert decision.decision == "deny"
        assert "budget_limit" in decision.policy_id

    def test_allows_when_budget_available(self) -> None:
        from core.tool_protocol import ToolBudget

        config = PolicyConfig()
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."), budget=ToolBudget(max_calls=5, calls_used=2))
        decision = engine.evaluate("fs.read", {"path": "x"}, ctx, RiskLevel.LOW)
        assert decision.decision == "allow"


class TestPolicyDecisionImmutability:
    def test_frozen_dataclass(self) -> None:
        decision = PolicyDecision(
            decision="allow",
            reason="ok",
            policy_id="p",
            risk_level=RiskLevel.LOW,
        )
        with pytest.raises(Exception):
            decision.decision = "deny"


class TestRiskRules:
    def test_custom_risk_rules(self) -> None:
        config = PolicyConfig(
            risk_rules={
                RiskLevel.NONE: "allow",
                RiskLevel.LOW: "ask",
                RiskLevel.MEDIUM: "deny",
                RiskLevel.HIGH: "deny",
                RiskLevel.CRITICAL: "deny",
            }
        )
        engine = PolicyEngine(config)
        ctx = ToolContext(workspace=Path("."))

        assert engine.evaluate("t", {}, ctx, RiskLevel.NONE).decision == "allow"
        assert engine.evaluate("t", {}, ctx, RiskLevel.LOW).decision == "ask"
        assert engine.evaluate("t", {}, ctx, RiskLevel.MEDIUM).decision == "deny"
