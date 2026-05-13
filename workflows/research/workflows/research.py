from __future__ import annotations

from pathlib import Path
from typing import Any

from core.public_api import ModelRegistry, PolicyEngine, RunLedger, ToolRegistry
from workflows.base import AgentRole, ExecutionDAG, Step, StepContext, StepResult, Workflow
from workflows.research.agents.base import load_prompt
from workflows.research.agents.gatherer import GathererAgent, GatherResult
from workflows.research.agents.summarizer import SummarizerAgent, SummaryResult
from workflows.research.agents.reporter import ReporterAgent
from workflows.research.reports.final_report import ResearchReport


class ResearchWorkflow(Workflow):
    workflow_id = "research"
    required_agents = [
        AgentRole(id="gatherer", capabilities=["web_search", "fetch"]),
        AgentRole(id="summarizer", capabilities=["summarize", "compare"]),
        AgentRole(id="reporter", capabilities=["report", "synthesize"]),
    ]
    required_tools: list[str] = []

    def __init__(
        self,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
        policy_engine: PolicyEngine,
        ledger: RunLedger,
    ) -> None:
        super().__init__(model_registry, tool_registry, policy_engine, ledger)
        self.dag = ExecutionDAG(
            steps=[
                Step(id="gather", agent="gatherer", type="gather"),
                Step(id="summarize", agent="summarizer", type="summarize", depends_on=["gather"]),
                Step(id="report", agent="reporter", type="report", depends_on=["summarize"]),
            ]
        )
        self._gatherer = self._create_gatherer()
        self._summarizer = self._create_summarizer()
        self._reporter = self._create_reporter()

    def _prompt_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "prompts"

    def _create_gatherer(self) -> GathererAgent:
        model = self.model_registry.resolve_model("gatherer", "fetch")
        provider = self.model_registry.create_provider(model.config)
        prompt_path = self._prompt_dir() / "gatherer" / "system.md"
        return GathererAgent(
            provider=provider,
            role_config=model.config,
            system_prompt=load_prompt(prompt_path),
            output_schema=GatherResult,
        )

    def _create_summarizer(self) -> SummarizerAgent:
        model = self.model_registry.resolve_model("summarizer", "compare")
        provider = self.model_registry.create_provider(model.config)
        prompt_path = self._prompt_dir() / "summarizer" / "system.md"
        return SummarizerAgent(
            provider=provider,
            role_config=model.config,
            system_prompt=load_prompt(prompt_path),
            output_schema=SummaryResult,
        )

    def _create_reporter(self) -> ReporterAgent:
        model = self.model_registry.resolve_model("reporter", "synthesize")
        provider = self.model_registry.create_provider(model.config)
        prompt_path = self._prompt_dir() / "reporter" / "system.md"
        return ReporterAgent(
            provider=provider,
            role_config=model.config,
            system_prompt=load_prompt(prompt_path),
            output_schema=ResearchReport,
        )

    def execute_step(self, step: Step, context: StepContext) -> StepResult:
        topic = context.metadata.get("topic", "")
        shards = context.metadata.get("context_shards", {})
        if step.id == "gather":
            agent_result = self._gatherer.run_gather(topic, context_shards=shards)
            return StepResult(
                step_id=step.id,
                success=agent_result.success,
                output=agent_result.raw_output,
                metadata={"parsed": agent_result.parsed_output},
            )
        elif step.id == "summarize":
            gather_meta = context.prior_results.get("gather")
            gather_parsed = gather_meta.metadata.get("parsed", {}) if gather_meta else {}
            agent_result = self._summarizer.run_summarize(topic, gather_parsed, context_shards=shards)
            return StepResult(
                step_id=step.id,
                success=agent_result.success,
                output=agent_result.raw_output,
                metadata={"parsed": agent_result.parsed_output},
            )
        elif step.id == "report":
            summary_meta = context.prior_results.get("summarize")
            summary_parsed = summary_meta.metadata.get("parsed", {}) if summary_meta else {}
            agent_result = self._reporter.run_report(topic, summary_parsed, context_shards=shards)
            return StepResult(
                step_id=step.id,
                success=agent_result.success,
                output=agent_result.raw_output,
                metadata={"parsed": agent_result.parsed_output},
            )
        return StepResult(step_id=step.id, success=False, output=f"Unknown step: {step.id}")

    def generate_report(self, results: list[StepResult]) -> str:
        report_step = next((r for r in results if r.step_id == "report"), None)
        if report_step and report_step.success:
            parsed = report_step.metadata.get("parsed")
            if parsed:
                from workflows.research.reports.markdown import render_research_report_markdown
                report = ResearchReport.model_validate(parsed)
                return render_research_report_markdown(report)
        return super().generate_report(results)
