from __future__ import annotations

from pathlib import Path
from typing import Any

from workflows.base import ExecutionDAG, Step, StepContext, StepResult, Workflow


class ContextMaintainerWorkflow(Workflow):
    workflow_id = "context_maintainer"
    required_agents = []
    required_tools: list[str] = []

    def __init__(
        self,
        model_registry: Any,
        tool_registry: Any,
        policy_engine: Any,
        ledger: Any,
    ) -> None:
        super().__init__(model_registry, tool_registry, policy_engine, ledger)
        self.dag = ExecutionDAG(
            steps=[
                Step(id="scan", agent="context_ops", type="scan"),
                Step(id="plan", agent="context_ops", type="plan", depends_on=["scan"]),
                Step(id="generate", agent="context_ops", type="generate", depends_on=["plan"]),
                Step(id="write", agent="context_ops", type="write", depends_on=["generate"]),
                Step(
                    id="verify",
                    agent="context_ops",
                    type="verify",
                    depends_on=["write"],
                    parallel_safe=True,
                ),
                Step(
                    id="public_docs_impact",
                    agent="context_ops",
                    type="public_docs_impact",
                    depends_on=["write"],
                    parallel_safe=True,
                ),
                Step(
                    id="produce_report",
                    agent="context_ops",
                    type="produce_report",
                    depends_on=["verify"],
                ),
            ]
        )

    def execute_step(self, step: Step, context: StepContext) -> StepResult:
        return StepResult(
            step_id=step.id,
            success=True,
            output=f"Step '{step.id}' handled by context-maintainer runtime.",
            metadata={"routed": True},
        )

    def run(self, repo_root: Path, metadata: dict[str, Any] | None = None) -> list[StepResult]:
        from workflows.context_maintainer.runtime import run_context_maintainer

        repo_root = Path(repo_root).resolve()
        meta = metadata or {}
        scope = meta.get("scope", "full")
        write_mode = meta.get("write_mode", "patch")

        run_context_maintainer(
            repo_root=repo_root,
            scope=scope,
            write_mode=write_mode,
            ledger=self.ledger,
            artifact_store=meta.get("artifact_store"),
        )

        return [
            StepResult(step_id="scan", success=True, output="Scanned via context-maintainer runtime."),
            StepResult(step_id="plan", success=True, output="Planned via context-maintainer runtime."),
            StepResult(step_id="generate", success=True, output="Generated via context-maintainer runtime."),
            StepResult(step_id="write", success=True, output="Written via context-maintainer runtime."),
            StepResult(step_id="verify", success=True, output="Verified via context-maintainer runtime."),
            StepResult(step_id="public_docs_impact", success=True, output="Public docs impact checked via context-maintainer runtime."),
            StepResult(step_id="produce_report", success=True, output="Report produced via context-maintainer runtime."),
        ]
