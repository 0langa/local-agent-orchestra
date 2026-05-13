from __future__ import annotations

from pathlib import Path
from typing import Any

from agentheim.context_ops_impl import AictxContextOps
from agentheim.vendor.aictx.config import AictxConfig
from core.public_api import EventType, RunLedger, ArtifactStore

from workflows.context_maintainer.reports import (
    ContextRunReport,
    EntropyInfo,
    TimingInfo,
    render_context_run_report_md,
)


def run_context_maintainer(
    repo_root: str | Path,
    scope: str = "full",
    write_mode: str = "patch",
    ledger: RunLedger | None = None,
    artifact_store: ArtifactStore | None = None,
) -> ContextRunReport:
    """Run the deterministic context-maintainer pipeline.

    Creates an :class:`AictxContextOps`, invokes ``run_pipeline``, emits
    ledger events, builds a :class:`ContextRunReport`, writes the report
    and lockfile to the artifact store, and returns the report.
    """
    repo_root = Path(repo_root).resolve()
    ops = AictxContextOps(config=AictxConfig())
    run_id = ledger.run_dir.name if ledger is not None else "context-maintainer-run"

    if ledger is not None:
        ledger.emit_event(
            EventType.CONTEXT_SCANNED,
            payload={"scope": scope, "repo_root": str(repo_root)},
        )

    write_report = ops.run_pipeline(
        repo_root,
        run_id=run_id,
        scope=scope,
        write_mode=write_mode,
    )

    if ledger is not None:
        ledger.emit_event(
            EventType.CONTEXT_GENERATED,
            payload={"files_generated": len(write_report.generated_files)},
        )
        ledger.emit_event(
            EventType.CONTEXT_WRITTEN,
            payload={"write_mode": write_mode, "lockfile": write_report.lockfile_path},
        )
        ledger.emit_event(
            EventType.CONTEXT_VERIFIED,
            payload={"lockfile": write_report.lockfile_path},
        )

    run_report = write_report.run_report
    timing = write_report.timing
    entropy = write_report.entropy

    context_report = ContextRunReport(
        run_id=run_id,
        scope=scope,
        write_mode=write_mode,
        files_scanned=getattr(run_report, "files_scanned", 0) if run_report is not None else 0,
        files_selected=getattr(run_report, "files_selected", 0) if run_report is not None else 0,
        generated_files=write_report.generated_files,
        timing=TimingInfo(
            scan_duration_ms=getattr(timing, "scan_duration_ms", 0.0) if timing is not None else 0.0,
            plan_duration_ms=getattr(timing, "plan_duration_ms", 0.0) if timing is not None else 0.0,
            generation_duration_ms=getattr(timing, "generation_duration_ms", 0.0) if timing is not None else 0.0,
            total_duration_ms=getattr(timing, "total_duration_ms", 0.0) if timing is not None else 0.0,
        ),
        entropy=EntropyInfo(
            redundancy_ratio=getattr(entropy, "estimated_redundancy_ratio", 0.0) if entropy is not None else 0.0,
            warning=getattr(entropy, "warning", None) if entropy is not None else None,
        ),
    )

    if artifact_store is not None:
        report_path = artifact_store.run_dir / "context_run_report.md"
        report_path.write_text(render_context_run_report_md(context_report), encoding="utf-8")

        lockfile_src = repo_root / write_report.lockfile_path
        if lockfile_src.exists():
            lockfile_dest = artifact_store.run_dir / "context.lock.json"
            lockfile_dest.write_text(lockfile_src.read_text(encoding="utf-8"), encoding="utf-8")

    return context_report
