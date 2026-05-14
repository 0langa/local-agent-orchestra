from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.public_api import (
    ApprovalRequest,
    ApprovalWorkflow,
    EventType,
    RunLedger,
    ToolContext,
    ToolInvocationResult,
    ToolInvoker,
)


@dataclass
class PendingToolApproval:
    request: ApprovalRequest
    tool_id: str
    params: dict[str, Any]
    context: ToolContext
    ledger: RunLedger
    workflow: ApprovalWorkflow


class InterfaceApprovalStore:
    """Keep pending interface approvals and continue them safely."""

    def __init__(self, repo_root: str | Path, purpose_prefix: str) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.purpose_prefix = purpose_prefix
        self._pending: dict[str, PendingToolApproval] = {}

    def create_ledger(self, tool_id: str, *, interface_name: str) -> RunLedger:
        slug = tool_id.replace(".", "-")
        ledger = RunLedger.create(self.repo_root, f"{self.purpose_prefix}-{slug}")
        ledger.write_json(
            "run.json",
            {
                "action": "tool_invoke",
                "interface": interface_name,
                "tool_id": tool_id,
            },
        )
        ledger.emit_event(
            EventType.RUN_INITIATED,
            payload={
                "workflow_id": "interface_tool_invoke",
                "repo_root": str(self.repo_root),
                "metadata": {
                    "interface": interface_name,
                    "tool_id": tool_id,
                },
            },
        )
        return ledger

    def add(
        self,
        *,
        tool_id: str,
        params: dict[str, Any],
        context: ToolContext,
        ledger: RunLedger,
        policy_decision,
    ) -> ApprovalRequest:
        workflow = ApprovalWorkflow(ledger=ledger)
        request = workflow.request(policy_decision, tool_id, params)
        self._pending[request.request_id] = PendingToolApproval(
            request=request,
            tool_id=tool_id,
            params=dict(params),
            context=context,
            ledger=ledger,
            workflow=workflow,
        )
        return request

    def grant(self, request_id: str, *, invoker: ToolInvoker) -> tuple[ApprovalRequest, ToolInvocationResult] | None:
        pending = self._pending.pop(request_id, None)
        if pending is None:
            return None
        granted = pending.workflow.grant(request_id)
        if granted is None:
            return None
        result = invoker.invoke(
            pending.tool_id,
            pending.params,
            pending.context,
            ledger=pending.ledger,
            granted_request=granted,
        )
        return granted, result

    def deny(self, request_id: str) -> ApprovalRequest | None:
        pending = self._pending.pop(request_id, None)
        if pending is None:
            return None
        return pending.workflow.deny(request_id)
