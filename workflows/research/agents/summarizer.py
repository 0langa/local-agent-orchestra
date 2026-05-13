from __future__ import annotations

from pydantic import BaseModel, Field

from workflows.research.agents.base import BaseAgent


class SourceSummary(BaseModel):
    url: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)
    credibility: str = Field(default="unknown")


class Comparison(BaseModel):
    dimension: str = Field(min_length=1)
    findings: list[str] = Field(default_factory=list)


class SummaryResult(BaseModel):
    summaries: list[SourceSummary] = Field(default_factory=list)
    comparisons: list[Comparison] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class SummarizerAgent(BaseAgent[SummaryResult]):
    def build_prompt(self, topic: str, gather_result: dict, context_shards: dict[str, str] | None = None) -> str:
        sources = gather_result.get("sources", [])
        sources_text = "\n\n".join(
            f"Title: {s.get('title', '')}\nURL: {s.get('url', '')}\nSnippet: {s.get('snippet', '')}"
            for s in sources
        )
        queries = gather_result.get("search_queries", [])
        queries_text = "\n".join(f"- {q}" for q in queries) or "- none"
        findings = gather_result.get("raw_findings", "")
        shards_text = ""
        if context_shards:
            formatted = "\n\n".join(
                f"--- {name} ---\n{content}" for name, content in context_shards.items()
            )
            shards_text = f"\n\nProject context:\n{formatted}\n"
        return (
            f"Research topic: {topic}\n\n"
            f"{shards_text}"
            f"Search queries used:\n{queries_text}\n\n"
            f"Sources found:\n{sources_text}\n\n"
            f"Raw findings:\n{findings}\n\n"
            "Summarize each source, compare them across key dimensions, "
            "identify conflicts, and note any gaps in coverage. "
            "Return structured JSON matching the required schema."
        )

    def run_summarize(self, topic: str, gather_result: dict, context_shards: dict[str, str] | None = None):
        prompt = self.build_prompt(topic, gather_result, context_shards=context_shards)
        return self.run_structured(prompt, max_output_tokens=2500)
