from __future__ import annotations

from pathlib import Path

from core.events import EventType
from core.ledger import RunLedger
from core.public_api import PolicyConfig, RiskLevel, ToolContext
from core.tool_invocation import ToolInvoker, interface_policy_config
from tools.registry import create_core_tool_registry


def test_filesystem_read_allowed_through_invoker(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("world", encoding="utf-8")
    registry = create_core_tool_registry(tmp_path)
    invoker = ToolInvoker(registry=registry)

    result = invoker.invoke(
        "filesystem",
        {"operation": "read", "path": "hello.txt"},
        ToolContext(workspace=tmp_path, allowed_paths=[str(tmp_path)]),
    )

    assert result.success is True
    assert result.data == "world"
    assert result.requires_approval is False
    assert result.policy is not None
    assert result.policy.decision == "allow"


def test_filesystem_write_requires_approval_and_does_not_write(tmp_path: Path) -> None:
    registry = create_core_tool_registry(tmp_path)
    invoker = ToolInvoker(registry=registry)

    result = invoker.invoke(
        "filesystem",
        {"operation": "write", "path": "created.txt", "content": "new"},
        ToolContext(workspace=tmp_path, allowed_paths=[str(tmp_path)]),
    )

    assert result.success is False
    assert result.requires_approval is True
    assert result.error == "approval_required"
    assert result.policy is not None
    assert result.policy.decision == "ask"
    assert not (tmp_path / "created.txt").exists()


def test_interface_policy_denies_high_risk_shell(tmp_path: Path) -> None:
    registry = create_core_tool_registry(tmp_path)
    invoker = ToolInvoker(registry=registry, policy_config=interface_policy_config())

    result = invoker.invoke(
        "shell.execute",
        {"command": ["echo", "hi"]},
        ToolContext(workspace=tmp_path, allowed_paths=[str(tmp_path)]),
    )

    assert result.success is False
    assert result.requires_approval is False
    assert result.policy is not None
    assert result.policy.decision == "deny"
    assert "risk level" in (result.error or "").lower()


def test_allowed_invocation_emits_policy_tool_and_result_events(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("world", encoding="utf-8")
    ledger = RunLedger.create(tmp_path, "tool-invocation-test")
    registry = create_core_tool_registry(tmp_path)
    invoker = ToolInvoker(
        registry=registry,
        policy_config=PolicyConfig(
            risk_rules={
                RiskLevel.NONE: "allow",
                RiskLevel.LOW: "allow",
                RiskLevel.MEDIUM: "allow",
                RiskLevel.HIGH: "deny",
                RiskLevel.CRITICAL: "deny",
            }
        ),
    )

    result = invoker.invoke(
        "filesystem",
        {"operation": "read", "path": "hello.txt"},
        ToolContext(workspace=tmp_path, allowed_paths=[str(tmp_path)], run_id=ledger.run_dir.name),
        ledger=ledger,
        step_id="step-1",
        agent_id="agent-1",
    )

    assert result.success is True
    events = ledger.read_ledger()
    event_types = [event.event_type for event in events]
    assert event_types == [
        EventType.POLICY_EVALUATED,
        EventType.TOOL_CALLED,
        EventType.TOOL_RESULT_RECEIVED,
    ]
    assert events[1].tool_id == "filesystem"
    assert events[2].payload["success"] is True


def test_granted_request_bypasses_policy_and_executes(tmp_path: Path) -> None:
    (tmp_path / "hello.txt").write_text("world", encoding="utf-8")
    registry = create_core_tool_registry(tmp_path)
    invoker = ToolInvoker(registry=registry)

    from core.public_api import ApprovalRequest, RiskLevel
    req = ApprovalRequest(
        request_id="req-1",
        tool_id="filesystem",
        action="copy",
        target="hello.txt",
        risk_level=RiskLevel.MEDIUM,
        justification="test",
        params_redacted={},
        timestamp="",
        decision="ask",
        policy_id="test",
        override_possible=True,
    )

    result = invoker.invoke(
        "filesystem",
        {"operation": "copy", "path": "hello.txt", "destination": "copied.txt"},
        ToolContext(workspace=tmp_path, allowed_paths=[str(tmp_path)]),
        granted_request=req,
    )

    assert result.success is True
    assert (tmp_path / "copied.txt").read_text(encoding="utf-8") == "world"
    assert result.policy is not None
    assert result.policy.decision == "allow"
    assert result.policy.policy_id == "approval_override"
