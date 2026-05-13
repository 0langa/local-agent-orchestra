from __future__ import annotations

from workflows.research.agents.base import BaseAgent
from workflows.research.reports.final_report import ResearchReport


class ReporterAgent(BaseAgent[ResearchReport]):
    def build_prompt(self, topic: str, summary_result: dict, context_shards: dict[str, str] | None = None) -> str:
        summaries = summary_result.get("summaries", [])
        summaries_text = "\n\n".join(
            f"URL: {s.get('url', '')}\nKey points: {', '.join(s.get('key_points', []))}\nCredibility: {s.get('credibility', 'unknown')}"
            for s in summaries
        )
        comparisons = summary_result.get("comparisons", [])
        comparisons_text = "\n\n".join(
            f"Dimension: {c.get('dimension', '')}\nFindings: {', '.join(c.get('findings', []))}"
            for c in comparisons
        )
        conflicts = summary_result.get("conflicts", [])
        gaps = summary_result.get("gaps", [])
        shards_text = ""
        if context_shards:
            formatted = "\n\n".join(
                f"--- {name} ---\n{content}" for name, content in context_shards.items()
            )
            shards_text = f"\n\nProject context:\n{formatted}\n"
        return (
            f"Research topic: {topic}\n\n"
            f"{shards_text}"
            f"Source summaries:\n{summaries_text}\n\n"
            f"Comparisons:\n{comparisons_text}\n\n"
            f"Conflicts: {conflicts or 'none'}\n"
            f"Gaps: {gaps or 'none'}\n\n"
            "Generate a final research report with an executive summary, "
            "detailed sections, source list, confidence assessment, and recommendations. "
            "Return structured JSON matching the required schema."
        )

    def run_report(self, topic: str, summary_result: dict, context_shards: dict[str, str] | None = None):
        prompt = self.build_prompt(topic, summary_result, context_shards=context_shards)
        return self.run_structured(prompt, max_output_tokens=3000)
