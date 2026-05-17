"""Tests for policy audit trail — ledger events emitted by PolicyEngine."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.events import EventType
from core.ledger import RunLedger
from core.policy_engine import PolicyConfig, PolicyEngine
from core.tool_protocol import RiskLevel, ToolContext


class TestPolicyAuditTrail:
    @pytest.fixture
    def ledger(self, tmp_path: Path) -> RunLedger:
        return RunLedger.create(tmp_path, "test-policy-audit")

    @pytest.fixture
    def context(self) -> ToolContext:
        return ToolContext(workspace=Path("."))

    def test_allow_emits_policy_evaluated(self, ledger: RunLedger, context: ToolContext) -> None:
        engine = PolicyEngine()
        engine.evaluate(
            "fs.read",
            {"path": "readme.md"},
            context,
            RiskLevel.LOW,
            ledger=ledger,
            step_id="step-1",
            agent_id="agent-a",
        )
        events = ledger.read_ledger()
        eval_events = [e for e in events if e.event_type == EventType.POLICY_EVALUATED]
        assert len(eval_events) == 1
        assert eval_events[0].tool_id == "fs.read"
        assert eval_events[0].step_id == "step-1"
        assert eval_events[0].agent_id == "agent-a"
        assert eval_events[0].payload["decision"] == "allow"
        assert "params_redacted" in eval_events[0].payload

    def test_deny_emits_policy_evaluated(self, ledger: RunLedger, context: ToolContext) -> None:
        config = PolicyConfig(local_only=True)
        engine = PolicyEngine(config)
        engine.evaluate(
            "http.request",
            {"url": "https://example.com"},
            context,
            RiskLevel.HIGH,
            ledger=ledger,
        )
        events = ledger.read_ledger()
        eval_events = [e for e in events if e.event_type == EventType.POLICY_EVALUATED]
        assert len(eval_events) == 1
        assert eval_events[0].payload["decision"] == "deny"
        assert eval_events[0].payload["policy_id"] == "local_only"

    def test_ask_emits_policy_evaluated(self, ledger: RunLedger, context: ToolContext) -> None:
        config = PolicyConfig(
            risk_rules={
                RiskLevel.NONE: "allow",
                RiskLevel.LOW: "allow",
                RiskLevel.MEDIUM: "ask",
                RiskLevel.HIGH: "ask",
                RiskLevel.CRITICAL: "deny",
            }
        )
        engine = PolicyEngine(config)
        engine.evaluate(
            "fs.write",
            {"path": "/tmp/x"},
            context,
            RiskLevel.MEDIUM,
            ledger=ledger,
        )
        events = ledger.read_ledger()
        eval_events = [e for e in events if e.event_type == EventType.POLICY_EVALUATED]
        assert len(eval_events) == 1
        assert eval_events[0].payload["decision"] == "ask"

    def test_no_ledger_no_events(self, context: ToolContext) -> None:
        engine = PolicyEngine()
        engine.evaluate("fs.read", {"path": "readme.md"}, context, RiskLevel.LOW)
        # Should not crash and should not emit anything.

    def test_params_redacted_in_payload(self, ledger: RunLedger, context: ToolContext) -> None:
        engine = PolicyEngine()
        engine.evaluate(
            "http.request",
            {"url": "https://example.com", "api_key": "api_key: secret12345678"},
            context,
            RiskLevel.LOW,
            ledger=ledger,
        )
        events = ledger.read_ledger()
        payload = events[0].payload
        assert payload["params_redacted"]["url"] == "https://example.com"
        assert "[REDACTED" in payload["params_redacted"]["api_key"]

    def test_multiple_evaluations_in_order(self, ledger: RunLedger, context: ToolContext) -> None:
        engine = PolicyEngine()
        engine.evaluate("fs.read", {"path": "a"}, context, RiskLevel.LOW, ledger=ledger)
        engine.evaluate("fs.read", {"path": "b"}, context, RiskLevel.LOW, ledger=ledger)
        events = ledger.read_ledger()
        eval_events = [e for e in events if e.event_type == EventType.POLICY_EVALUATED]
        assert len(eval_events) == 2
        assert eval_events[0].payload["params_redacted"]["path"] == "a"
        assert eval_events[1].payload["params_redacted"]["path"] == "b"
        assert eval_events[1].sequence == eval_events[0].sequence + 1
