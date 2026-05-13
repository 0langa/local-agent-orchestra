from __future__ import annotations

from pathlib import Path
from typing import Any

from agentheim.context_ops_impl import AictxContextOps
from agentheim.context_run_ledger import ContextRunLedger
from config.config import load_team_config
from core.public_api import (
    AIteamError,
    EventType,
    ModelRegistry,
    PolicyEngine,
    RunLedger,
    ToolRegistry,
    build_context_pack,
    inspect_repository,
)
from workflows.coding.provider_map import DEFAULT_PROVIDER_MAP
from workflows.research.reports.final_report import ResearchReport, Section
from workflows.research.reports.markdown import render_research_report_markdown
from workflows.research.workflows.research import ResearchWorkflow


class ResearchPlanningError(AIteamError):
    """Raised when research planning or execution fails."""


# Shard filenames considered relevant for research grounding.
_RELEVANT_SHARD_NAMES = [
    "ai-index.md",
    "project-state.md",
    "architecture.md",
    "public-docs-map.md",
    "workflows.md",
    "code-map.md",
]


def _load_context_shards(repo_root: Path) -> dict[str, str]:
    """Load relevant AICtx shards from docs/AIprojectcontext/."""
    context_dir = repo_root / "docs" / "AIprojectcontext"
    shards: dict[str, str] = {}
    if not context_dir.exists():
        return shards
    for name in _RELEVANT_SHARD_NAMES:
        path = context_dir / name
        if path.exists():
            shards[name] = path.read_text(encoding="utf-8")
    return shards


def _build_legacy_context(repo_root: Path) -> dict[str, str]:
    """Fallback legacy context using ad-hoc repo scanning."""
    scan = inspect_repository(repo_root)
    return {"legacy_context.md": build_context_pack(scan)}


def _preflight_context(
    repo_root: Path,
    ledger: RunLedger,
) -> tuple[dict[str, str], str | None]:
    """Ensure context is fresh and return relevant shards plus optional warning."""
    ops = AictxContextOps()
    ctx_ledger = ContextRunLedger(ledger)

    status = ops.status(repo_root, strict=False)
    ctx_ledger.emit_status(status)

    shards: dict[str, str] = {}
    warning: str | None = None

    if status.is_stale:
        warning = (
            "Project context was stale at the start of this research run. "
            "AICtx pipeline was triggered automatically."
        )
        try:
            ops.run_pipeline(
                repo_root,
                run_id="research-ctx",
                scope="changed",
                write_mode="apply",
            )
        except Exception as exc:
            warning = (
                f"Project context was stale and AICtx pipeline failed ({exc}). "
                "Falling back to legacy context scanning."
            )
            shards = _build_legacy_context(repo_root)
            ledger.append_event(
                EventType.CONTEXT_STALE_DETECTED,
                payload={"warning": warning, "fallback": "legacy"},
            )
            return shards, warning

    # Read shards regardless of whether we just generated them or they already existed.
    shards = _load_context_shards(repo_root)
    if not shards:
        warning = warning or "No AICtx shards found; using legacy context."
        shards = _build_legacy_context(repo_root)
        ledger.append_event(
            EventType.CONTEXT_STALE_DETECTED,
            payload={"warning": warning, "fallback": "legacy"},
        )

    return shards, warning


def plan_task(topic: str, write_ledger: bool = False) -> tuple[str, Path | None]:
    """Plan a research task. Returns the topic and optional ledger directory."""
    ledger_dir: Path | None = None
    if write_ledger:
        ledger = RunLedger.create(Path(".").resolve(), "research_plan")
        ledger.write_json("run.json", {"action": "plan", "topic": topic})
        ledger_dir = ledger.run_dir
    return topic, ledger_dir


def run_task(topic: str) -> tuple[ResearchReport, Path]:
    """Run the full research workflow and return the report and ledger path."""
    repo_root = Path(".").resolve()
    ledger = RunLedger.create(repo_root, "research")
    ledger.write_json("run.json", {"action": "run", "topic": topic})

    shards, warning = _preflight_context(repo_root, ledger)

    team_config = load_team_config()
    registry = ModelRegistry.from_team_config(team_config, provider_map=DEFAULT_PROVIDER_MAP)
    tool_registry = ToolRegistry()
    policy_engine = PolicyEngine()

    workflow = ResearchWorkflow(registry, tool_registry, policy_engine, ledger)
    results = workflow.run(repo_root, metadata={"topic": topic, "context_shards": shards})

    if not workflow.verify(results):
        failed = [r.step_id for r in results if not r.success]
        raise ResearchPlanningError(f"Research workflow failed at steps: {failed}")

    report_step = results[-1]
    if not report_step.success or report_step.metadata.get("parsed") is None:
        raise ResearchPlanningError("Report generation failed with invalid output.")

    report = ResearchReport.model_validate(report_step.metadata["parsed"])

    if warning:
        warning_section = Section(heading="Context Warning", content=warning)
        report = ResearchReport(
            topic=report.topic,
            executive_summary=report.executive_summary,
            sections=[warning_section, *report.sections],
            sources=report.sources,
            confidence=report.confidence,
            recommendations=report.recommendations,
        )

    ledger.write_json("final_report.json", report.model_dump())
    ledger.write_text("final_report.md", render_research_report_markdown(report))
    return report, ledger.run_dir
