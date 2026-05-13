from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingInfo:
    scan_duration_ms: float = 0.0
    plan_duration_ms: float = 0.0
    generation_duration_ms: float = 0.0
    total_duration_ms: float = 0.0


@dataclass
class EntropyInfo:
    redundancy_ratio: float = 0.0
    warning: str | None = None


@dataclass
class ContextRunReport:
    run_id: str
    scope: str
    write_mode: str
    files_scanned: int = 0
    files_selected: int = 0
    generated_files: list[str] = field(default_factory=list)
    timing: TimingInfo = field(default_factory=TimingInfo)
    entropy: EntropyInfo = field(default_factory=EntropyInfo)


def render_context_run_report_md(report: ContextRunReport) -> str:
    lines = [
        "# Context Run Report",
        "",
        f"- **Run ID**: {report.run_id}",
        f"- **Scope**: {report.scope}",
        f"- **Write Mode**: {report.write_mode}",
        "",
        "## Summary",
        f"- Files Scanned: {report.files_scanned}",
        f"- Files Selected: {report.files_selected}",
        f"- Generated Files: {len(report.generated_files)}",
        "",
        "## Timing",
        f"- Scan: {report.timing.scan_duration_ms:.2f} ms",
        f"- Plan: {report.timing.plan_duration_ms:.2f} ms",
        f"- Generation: {report.timing.generation_duration_ms:.2f} ms",
        f"- Total: {report.timing.total_duration_ms:.2f} ms",
        "",
        "## Entropy",
        f"- Redundancy Ratio: {report.entropy.redundancy_ratio:.4f}",
    ]
    if report.entropy.warning:
        lines.append(f"- Warning: {report.entropy.warning}")
    if report.generated_files:
        lines.extend(["", "## Generated Files"])
        for path in report.generated_files:
            lines.append(f"- {path}")
    return "\n".join(lines)
