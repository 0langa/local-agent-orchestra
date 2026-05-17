"""Tests for core/approval_workflow.py — 6-field disclosure and approval lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.approval_workflow import ApprovalRequest, ApprovalWorkflow
from core.events import EventType
from core.ledger import RunLedger
from core.policy_engine import PolicyDecision, PolicyEngine
from core.tool_protocol import RiskLevel


class TestApprovalRequest:
    def test_six_field_disclosure(self) -> None:
        """ApprovalRequest exposes exactly six disclosure fields."""
        decision = PolicyDecision(
            decision="ask",
            reason="MEDIUM risk requires approval.",
            policy_id="risk_level",
            risk_level=RiskLevel.MEDIUM,
            suggested_approval="Review before proceeding.",
            override_possible=True,
        )
        req = ApprovalRequest.from_decision(
            decision, "fs.write", {"path": "/tmp/test.txt", "operation": "write"}
        )
        assert req.tool_id == "fs.write"
        assert req.action == "write"
        assert req.target == "/tmp/test.txt"
        assert req.risk_level == RiskLevel.MEDIUM
        assert "MEDIUM risk requires approval" in req.justification
        assert "Review before proceeding" in req.justification
        assert req.params_redacted is not None
        assert req.request_id
        assert req.timestamp
        assert req.decision == "ask"
        assert req.policy_id == "risk_level"
        assert req.override_possible is True

    def test_params_are_redacted(self) -> None:
        decision = PolicyDecision(
            decision="ask",
            reason="reason",
            policy_id="p",
            risk_level=RiskLevel.LOW,
        )
        req = ApprovalRequest.from_decision(
            decision, "http.request", {"url": "https://example.com", "api_key": "api_key: secret12345678"}
        )
        assert req.params_redacted["url"] == "https://example.com"
        assert "[REDACTED" in req.params_redacted["api_key"]

    def test_to_dict_round_trip(self) -> None:
        decision = PolicyDecision(
            decision="deny",
            reason="denied",
            policy_id="p",
            risk_level=RiskLevel.HIGH,
        )
        req = ApprovalRequest.from_decision(decision, "tool", {})
        d = req.to_dict()
        assert d["tool_id"] == "tool"
        assert d["risk_level"] == "high"
        assert d["decision"] == "deny"


class TestApprovalWorkflow:
    def test_request_creates_pending(self) -> None:
        workflow = ApprovalWorkflow()
        decision = PolicyDecision(
            decision="ask",
            reason="ask reason",
            policy_id="risk",
            risk_level=RiskLevel.MEDIUM,
        )
        req = workflow.request(decision, "tool", {"path": "/tmp/x"})
        assert workflow.get_pending(req.request_id) == req
        assert workflow.list_pending() == [req]

    def test_grant_removes_pending(self) -> None:
        workflow = ApprovalWorkflow()
        decision = PolicyDecision(
            decision="ask",
            reason="ask",
            policy_id="p",
            risk_level=RiskLevel.MEDIUM,
        )
        req = workflow.request(decision, "tool", {})
        assert workflow.grant(req.request_id) == req
        assert workflow.get_pending(req.request_id) is None
        assert workflow.list_pending() == []

    def test_deny_removes_pending(self) -> None:
        workflow = ApprovalWorkflow()
        decision = PolicyDecision(
            decision="ask",
            reason="ask",
            policy_id="p",
            risk_level=RiskLevel.MEDIUM,
        )
        req = workflow.request(decision, "tool", {})
        assert workflow.deny(req.request_id) == req
        assert workflow.get_pending(req.request_id) is None

    def test_grant_unknown_returns_none(self) -> None:
        workflow = ApprovalWorkflow()
        assert workflow.grant("nonexistent") is None

    def test_deny_unknown_returns_none(self) -> None:
        workflow = ApprovalWorkflow()
        assert workflow.deny("nonexistent") is None


class TestApprovalWorkflowWithLedger:
    @pytest.fixture
    def ledger(self, tmp_path: Path) -> RunLedger:
        return RunLedger.create(tmp_path, "test-approval")

    def test_request_emits_approval_requested(self, ledger: RunLedger) -> None:
        workflow = ApprovalWorkflow(ledger=ledger)
        decision = PolicyDecision(
            decision="ask",
            reason="reason",
            policy_id="p",
            risk_level=RiskLevel.MEDIUM,
        )
        req = workflow.request(decision, "tool", {})

        events = ledger.read_ledger()
        approval_events = [e for e in events if e.event_type == EventType.APPROVAL_REQUESTED]
        assert len(approval_events) == 1
        assert approval_events[0].tool_id == "tool"
        assert approval_events[0].payload["request_id"] == req.request_id

    def test_grant_emits_approval_granted(self, ledger: RunLedger) -> None:
        workflow = ApprovalWorkflow(ledger=ledger)
        decision = PolicyDecision(
            decision="ask",
            reason="reason",
            policy_id="p",
            risk_level=RiskLevel.MEDIUM,
        )
        req = workflow.request(decision, "tool", {})
        workflow.grant(req.request_id)

        events = ledger.read_ledger()
        grant_events = [e for e in events if e.event_type == EventType.APPROVAL_GRANTED]
        assert len(grant_events) == 1
        assert grant_events[0].payload["request_id"] == req.request_id

    def test_deny_emits_approval_denied(self, ledger: RunLedger) -> None:
        workflow = ApprovalWorkflow(ledger=ledger)
        decision = PolicyDecision(
            decision="ask",
            reason="reason",
            policy_id="p",
            risk_level=RiskLevel.MEDIUM,
        )
        req = workflow.request(decision, "tool", {})
        workflow.deny(req.request_id)

        events = ledger.read_ledger()
        deny_events = [e for e in events if e.event_type == EventType.APPROVAL_DENIED]
        assert len(deny_events) == 1
        assert deny_events[0].payload["request_id"] == req.request_id
        assert deny_events[0].payload["reason"] == "User denied"

    def test_multiple_requests_tracked_independently(self, ledger: RunLedger) -> None:
        workflow = ApprovalWorkflow(ledger=ledger)
        decision = PolicyDecision(
            decision="ask",
            reason="reason",
            policy_id="p",
            risk_level=RiskLevel.MEDIUM,
        )
        req1 = workflow.request(decision, "tool1", {})
        req2 = workflow.request(decision, "tool2", {})

        assert len(workflow.list_pending()) == 2
        workflow.grant(req1.request_id)
        assert len(workflow.list_pending()) == 1
        assert workflow.get_pending(req2.request_id) == req2
