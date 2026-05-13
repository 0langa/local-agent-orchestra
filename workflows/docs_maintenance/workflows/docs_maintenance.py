from __future__ import annotations

from pathlib import Path

from workflows.base import Workflow, Step, StepContext, StepResult, ExecutionDAG, AgentRole
from workflows.docs_maintenance.agents.base import load_prompt
from workflows.docs_maintenance.agents.detector import DetectorAgent, DetectionResult
from workflows.docs_maintenance.agents.updater import UpdaterAgent, UpdateResult
from workflows.docs_maintenance.agents.aligner import AlignerAgent, AlignmentResult
from core.public_api import ModelRegistry

WORKFLOW_ID = "docs_maintenance"


def _prompt_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "prompts"


def create_detector_agent(registry: ModelRegistry) -> DetectorAgent:
    model = registry.resolve_model("planner", "plan")
    provider = registry.create_provider(model.config)
    return DetectorAgent(
        provider=provider,
        role_config=model.config,
        system_prompt=load_prompt(_prompt_dir() / "detector" / "system.md"),
        output_schema=DetectionResult,
    )


def create_updater_agent(registry: ModelRegistry) -> UpdaterAgent:
    model = registry.resolve_model("executor", "code_edit")
    provider = registry.create_provider(model.config)
    return UpdaterAgent(
        provider=provider,
        role_config=model.config,
        system_prompt=load_prompt(_prompt_dir() / "updater" / "system.md"),
        output_schema=UpdateResult,
    )


def create_aligner_agent(registry: ModelRegistry) -> AlignerAgent:
    model = registry.resolve_model("verifier", "verify")
    provider = registry.create_provider(model.config)
    return AlignerAgent(
        provider=provider,
        role_config=model.config,
        system_prompt=load_prompt(_prompt_dir() / "aligner" / "system.md"),
        output_schema=AlignmentResult,
    )


class DocsMaintenanceWorkflow(Workflow):
    workflow_id = WORKFLOW_ID
    required_agents = [
        AgentRole(id="detector", capabilities=["detect"]),
        AgentRole(id="updater", capabilities=["update"]),
        AgentRole(id="aligner", capabilities=["align"]),
    ]

    def __init__(self, model_registry, tool_registry, policy_engine, ledger):
        super().__init__(model_registry, tool_registry, policy_engine, ledger)
        self.detector = create_detector_agent(model_registry)
        self.updater = create_updater_agent(model_registry)
        self.aligner = create_aligner_agent(model_registry)
        self.dag = ExecutionDAG([
            Step(id="public_docs_impact", agent="public_docs_impact", type="public_docs_impact"),
            Step(id="detect", agent="detector", type="detect", depends_on=["public_docs_impact"]),
            Step(id="update", agent="updater", type="update", depends_on=["detect"]),
            Step(id="align", agent="aligner", type="align", depends_on=["update"]),
        ])

    def execute_step(self, step: Step, context: StepContext) -> StepResult:
        if step.agent == "detector":
            docs_context = context.metadata.get("docs_context", "")
            result = self.detector.run_detection(docs_context)
            return StepResult(step_id=step.id, success=result.success, output=result.raw_output)
        elif step.agent == "updater":
            stale_docs = context.prior_results.get("detect", StepResult(step_id="detect", success=True, output="")).output
            result = self.updater.run_update(stale_docs)
            return StepResult(step_id=step.id, success=result.success, output=result.raw_output)
        elif step.agent == "aligner":
            updated = context.prior_results.get("update", StepResult(step_id="update", success=True, output="")).output
            result = self.aligner.run_alignment(updated)
            return StepResult(step_id=step.id, success=result.success, output=result.raw_output)
        elif step.agent == "public_docs_impact":
            return StepResult(step_id=step.id, success=True, output="public docs impact checked")
        return StepResult(step_id=step.id, success=False, output="Unknown agent")
