from __future__ import annotations

from pathlib import Path

from workflows.coding.agents.base import BaseAgent
from core.schemas_runtime import PatchPlan, WorkOrder


class CoderAgent(BaseAgent[PatchPlan]):
    def build_prompt(self, work_order: WorkOrder, repo_root: str | Path) -> str:
        repo_name = Path(repo_root).name
        acceptance = "\n".join(f"- {item.description}" for item in work_order.acceptance_criteria) or "- none"
        relevant = "\n".join(f"- {item}" for item in work_order.relevant_files) or "- none"
        excerpts = "\n---\n".join(work_order.required_context_excerpts) or "none"
        constraints = "\n".join(f"- {item}" for item in work_order.constraints) or "- none"
        forbidden = "\n".join(f"- {item}" for item in work_order.forbidden_changes) or "- none"
        return (
            f"Repository: {repo_name}\n"
            f"Work order id: {work_order.id}\n"
            f"Title: {work_order.title}\n"
            f"Objective: {work_order.objective}\n\n"
            f"Allowed files:\n{relevant}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"Forbidden changes:\n{forbidden}\n\n"
            f"Acceptance criteria:\n{acceptance}\n\n"
            f"Relevant context:\n{excerpts}\n\n"
            "Return only valid JSON matching PatchPlan. "
            "Use full file contents in patch for each changed file. "
            "Do not include any files outside allowed files."
        )

    def run_work_order(self, work_order: WorkOrder, repo_root: str | Path):
        prompt = self.build_prompt(work_order, repo_root)
        return self.run_structured(prompt, max_output_tokens=2500)