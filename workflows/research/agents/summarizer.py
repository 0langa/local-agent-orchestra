from __future__ import annotations

import json

from pydantic import BaseModel, Field
from pydantic import ValidationError

from core.json_repair import repair_json_text
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
        return self.run_structured(prompt, max_output_tokens=6000)

    def _parse(self, raw_output: str) -> SummaryResult:
        data = json.loads(repair_json_text(raw_output))

        # Normalize summaries array items (model returns title/summary/url variants)
        raw_summaries = data.get("summaries", [])
        normalized_summaries: list[dict] = []
        if isinstance(raw_summaries, list):
            for item in raw_summaries:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or item.get("link") or item.get("source") or "unknown")
                key_points = item.get("key_points") or item.get("summary") or item.get("findings") or item.get("description") or item.get("points") or []
                if isinstance(key_points, str):
                    key_points = [key_points]
                elif isinstance(key_points, list):
                    key_points = [str(kp) for kp in key_points]
                else:
                    key_points = [str(key_points)]
                credibility = str(item.get("credibility") or item.get("trustworthiness") or item.get("reliability") or "unknown")
                normalized_summaries.append({"url": url, "key_points": key_points, "credibility": credibility})
        data["summaries"] = normalized_summaries

        if "comparisons" not in data and isinstance(data.get("comparison"), dict):
            comparisons = []
            for key, value in data["comparison"].items():
                if isinstance(value, dict):
                    findings = [f"{subkey}: {subvalue}" for subkey, subvalue in value.items()]
                elif isinstance(value, list):
                    findings = [str(item) for item in value]
                else:
                    findings = [str(value)]
                comparisons.append({"dimension": str(key), "findings": findings})
            data["comparisons"] = comparisons

        # Normalize conflicts: dict items → string, dict-of-dicts → flattened strings
        raw_conflicts = data.get("conflicts", [])
        if isinstance(raw_conflicts, dict):
            data["conflicts"] = [
                f"{key}: " + "; ".join(f"{subkey}={subvalue}" for subkey, subvalue in value.items())
                if isinstance(value, dict)
                else f"{key}: {value}"
                for key, value in raw_conflicts.items()
            ]
        elif isinstance(raw_conflicts, list):
            normalized_conflicts = []
            for item in raw_conflicts:
                if isinstance(item, dict):
                    normalized_conflicts.append(
                        "; ".join(f"{k}={v}" for k, v in item.items())
                    )
                else:
                    normalized_conflicts.append(str(item))
            data["conflicts"] = normalized_conflicts

        # Normalize gaps: dict items → string, dict-of-dicts → flattened strings
        raw_gaps = data.get("gaps", [])
        if isinstance(raw_gaps, dict):
            data["gaps"] = [f"{key}: {value}" for key, value in raw_gaps.items()]
        elif isinstance(raw_gaps, list):
            normalized_gaps = []
            for item in raw_gaps:
                if isinstance(item, dict):
                    normalized_gaps.append(
                        "; ".join(f"{k}={v}" for k, v in item.items())
                    )
                else:
                    normalized_gaps.append(str(item))
            data["gaps"] = normalized_gaps

        try:
            return self.output_schema.model_validate(data)
        except (ValueError, ValidationError):
            raise
