from __future__ import annotations

from pathlib import Path

from workflows.coding.agents.base import BaseAgent
from core.schemas_runtime import ImplementationPlan, VerificationReport, WorkOrder


class VerifierAgent(BaseAgent[VerificationReport]):
    def build_prompt(
        self,
        original_task: str,
        plan: ImplementationPlan,
        work_order: WorkOrder,
        git_diff: str,
        command_outputs: list[str],
        relevant_file_excerpts: list[str],
    ) -> str:
        commands = "\n".join(command_outputs) or "none"
        excerpts = "\n---\n".join(relevant_file_excerpts) or "none"
        acceptance = "\n".join(f"- {item.description}" for item in work_order.acceptance_criteria) or "- none"
        return (
            f"Original user task: {original_task}\n"
            f"Plan summary: {plan.summary}\n"
            f"Work order id: {work_order.id}\n"
            f"Work order title: {work_order.title}\n\n"
            f"Acceptance criteria:\n{acceptance}\n\n"
            f"Git diff:\n{git_diff[:6000]}\n\n"
            f"Command outputs:\n{commands}\n\n"
            f"Relevant file excerpts:\n{excerpts}\n\n"
            "The git diff is cumulative for the whole run. For fix or test-only work orders, "
            "do not fail the current work order only because the cumulative diff still contains "
            "production-code changes that an earlier verifier step already accepted. Judge whether "
            "the current work order's requested outcome is satisfied by the current repo state and "
            "command evidence.\n\n"
            "Return only valid JSON matching VerificationReport. Provide evidence for any failure."
        )

    def run_verification(
        self,
        original_task: str,
        plan: ImplementationPlan,
        work_order: WorkOrder,
        git_diff: str,
        command_outputs: list[str],
        relevant_file_excerpts: list[str],
    ):
        prompt = self.build_prompt(original_task, plan, work_order, git_diff, command_outputs, relevant_file_excerpts)
        return self.run_structured(prompt, max_output_tokens=2200)
