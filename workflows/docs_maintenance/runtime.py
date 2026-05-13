from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentheim.context_ops_impl import AictxContextOps
from agentheim.context_run_ledger import ContextRunLedger
from agentheim.vendor.aictx.config import AictxConfig
from config.config import load_team_config
from core.public_api import ArtifactStore, EventType, ModelRegistry, RunLedger, build_context_pack, inspect_repository
from workflows.coding.provider_map import DEFAULT_PROVIDER_MAP
from workflows.docs_maintenance.reports.final_report import DocUpdateRecord, FinalReport
from workflows.docs_maintenance.reports.markdown import render_final_report_markdown
from workflows.docs_maintenance.workflows.docs_maintenance import create_detector_agent, create_updater_agent, create_aligner_agent


def _build_context_pack(
    repo_root: Path,
    scan: Any,
    ledger: RunLedger | None,
) -> tuple[str, list[str]]:
    """Build context pack from AICtx shards, falling back to legacy scan on failure."""
    warnings: list[str] = []
    try:
        ops = AictxContextOps(config=AictxConfig())
        status = ops.status(repo_root)
        if ledger is not None:
            ContextRunLedger(ledger).emit_status(status)
        if status.is_stale:
            warnings.append("AICtx context is stale; regenerating via run_pipeline.")
            ops.run_pipeline(
                repo_root,
                run_id="docs-ctx",
                scope="changed",
                write_mode="apply",
            )

        context_dir = repo_root / ops.config.project.context_dir
        shards: list[str] = []
        if context_dir.exists():
            relevant: list[Path] = []
            other: list[Path] = []
            for md in sorted(context_dir.rglob("*.md")):
                stem = md.stem.lower()
                if "docs" in stem or "architecture" in stem:
                    relevant.append(md)
                else:
                    other.append(md)
            for p in relevant + other:
                shards.append(f"<!-- shard: {p.relative_to(repo_root).as_posix()} -->\n")
                shards.append(p.read_text(encoding="utf-8"))

        if shards:
            context_pack = "\n".join(shards)
        else:
            warnings.append("No AICtx shards found; falling back to legacy context pack.")
            context_pack = build_context_pack(scan)
    except Exception as exc:
        warnings.append(f"AICtx context build failed ({exc}); falling back to legacy context pack.")
        context_pack = build_context_pack(scan)
    return context_pack, warnings


def plan_task(repo_path: str | Path, write_ledger: bool = False) -> tuple[str, Any, Path | None, list[str]]:
    repo_root = Path(repo_path).resolve()
    scan = inspect_repository(repo_root)
    ledger: RunLedger | None = None
    ledger_dir: Path | None = None
    if write_ledger:
        ledger = RunLedger.create(repo_root, "docs_maintenance_plan")
        ledger_dir = ledger.run_dir

    context_pack, warnings = _build_context_pack(repo_root, scan, ledger)

    team_config = load_team_config()
    registry = ModelRegistry.from_team_config(team_config, provider_map=DEFAULT_PROVIDER_MAP)
    detector = create_detector_agent(registry)
    prompt = f"Repository docs context:\n{context_pack}\n\nIdentify stale docs."
    result = detector.run_detection(prompt)
    if write_ledger and ledger:
        ledger.write_json("run.json", {"action": "plan", "repo_name": scan.repo_name})
        ledger.write_text("context_pack.md", context_pack)
        ledger.write_text("raw_model_output.txt", result.raw_output)
        if result.parsed_output is not None:
            ledger.write_json("plan.json", result.parsed_output)
    return context_pack, result.parsed_output, ledger_dir, warnings


def check_public_docs_impact(
    repo_root: Path,
    ledger: RunLedger | None,
    artifact_store: ArtifactStore | None,
) -> tuple[bool, Any]:
    """Preflight step: map source changes to impacted public documentation.

    Returns:
        ``(has_impacts, report)`` tuple.  On failure we fall back to
        ``(False, None)`` so the legacy workflow path is preserved.
    """
    try:
        ops = AictxContextOps(config=AictxConfig())
        report = ops.public_docs_impact(repo_root, scope="changed")
    except Exception:
        return False, None

    if report.entries:
        if ledger is not None:
            ContextRunLedger(ledger).emit_public_docs_impact(report)
        if artifact_store is not None:
            artifact_store.produce_public_docs_impact(report)
        return True, report
    return False, report


def generate_public_docs_patch(
    repo_root: Path,
    ledger: RunLedger | None,
    artifact_store: ArtifactStore | None,
) -> Path | None:
    """Generate a patch for impacted public docs without applying it.

    Writes the patch to the artifact store as ``public_docs_patch.diff``
    and emits :data:`EventType.PUBLIC_DOCS_UPDATED`.

    Returns:
        Path to the generated patch, or ``None`` when no patch was
        produced or the operation failed.
    """
    try:
        ops = AictxContextOps(config=AictxConfig())
        patch_path = ops.public_docs_update(repo_root, scope="changed", write_mode="patch")
    except Exception:
        return None

    if patch_path is None or not patch_path.exists():
        return None

    if artifact_store is not None:
        diff_text = patch_path.read_text(encoding="utf-8")
        artifact_store.produce_patch(diff_text)
        public_patch = artifact_store.run_dir / "public_docs_patch.diff"
        public_patch.write_text(diff_text, encoding="utf-8")

    if ledger is not None:
        ContextRunLedger(ledger).emit_public_docs_updated(patch_path)

    return patch_path


def run_task(
    repo_path: str | Path,
    *,
    mode: str = "apply",
    write_ledger: bool = True,
) -> tuple[FinalReport, Path | None]:
    repo_root = Path(repo_path).resolve()
    ledger: RunLedger | None = None
    ledger_dir: Path | None = None
    if write_ledger:
        ledger = RunLedger.create(repo_root, "docs_maintenance_run")
        ledger_dir = ledger.run_dir

    context_pack, plan, _, warnings = plan_task(repo_root, write_ledger=write_ledger)

    artifact_store: ArtifactStore | None = None
    if ledger is not None:
        artifact_store = ArtifactStore(ledger.run_dir)

    # Track K: public-docs impact preflight
    has_impacts, impact_report = check_public_docs_impact(repo_root, ledger, artifact_store)
    public_doc_impacted_paths: set[str] = set()
    patch_path: Path | None = None

    if has_impacts and impact_report is not None:
        # Track L: review-first patch generation
        patch_path = generate_public_docs_patch(repo_root, ledger, artifact_store)
        public_doc_impacted_paths = {entry.get("path", "") for entry in impact_report.entries}

    team_config = load_team_config()
    registry = ModelRegistry.from_team_config(team_config, provider_map=DEFAULT_PROVIDER_MAP)
    detector = create_detector_agent(registry)
    updater = create_updater_agent(registry)
    aligner = create_aligner_agent(registry)

    detection = detector.run_detection(context_pack)
    if not detection.success or detection.parsed_output is None:
        report = FinalReport(
            task_summary="Detection failed",
            updated_docs=[],
            remaining_risks=[detection.error or "unknown"] + warnings,
            run_id=ledger.run_dir.name if ledger else "none",
            status="failed",
            public_docs_review_status="pending_review" if has_impacts else "no_impact",
            public_docs_patch_path=str(patch_path) if patch_path else None,
            public_docs_impacted_count=len(public_doc_impacted_paths),
        )
        if ledger:
            ledger.write_json("final_report.json", report.model_dump())
            ledger.write_text("final_report.md", render_final_report_markdown(report))
        return report, ledger_dir

    stale = detection.parsed_output.get("stale_docs", [])
    updates: list[DocUpdateRecord] = []
    for item in stale:
        doc_path = item.get("path", "")
        if doc_path in public_doc_impacted_paths:
            updates.append(
                DocUpdateRecord(
                    doc_path=doc_path,
                    status="skipped",
                    details="public doc impact — pending review",
                )
            )
            continue
        update_result = updater.run_update(json.dumps(item))
        if update_result.success and update_result.parsed_output:
            for u in update_result.parsed_output.get("updates", []):
                path = repo_root / u["path"]
                if mode == "apply":
                    if ledger:
                        ledger.append_jsonl(
                            "file_changes.jsonl",
                            {"operation": "write_text", "path": str(path.relative_to(repo_root)), "size": len(u["new_content"])},
                        )
                    path.write_text(u["new_content"], encoding="utf-8")
                updates.append(DocUpdateRecord(doc_path=u["path"], status="updated", details="content rewritten"))
        else:
            updates.append(DocUpdateRecord(doc_path=item["path"], status="failed", details=update_result.error or "update failed"))

    align_input = json.dumps([u.model_dump() for u in updates])
    alignment = aligner.run_alignment(align_input)
    remaining_risks: list[str] = []
    if alignment.success and alignment.parsed_output:
        if not alignment.parsed_output.get("aligned", True):
            remaining_risks = [i["issue"] for i in alignment.parsed_output.get("issues", [])]
    else:
        remaining_risks = [alignment.error or "alignment failed"]

    remaining_risks.extend(warnings)

    if has_impacts:
        public_docs_review_status = "pending_review"
        status = "pending_review"
    else:
        public_docs_review_status = "no_impact"
        status = "done"

    report = FinalReport(
        task_summary=f"Docs maintenance run. Stale docs detected: {len(stale)}",
        updated_docs=updates,
        remaining_risks=remaining_risks,
        run_id=ledger.run_dir.name if ledger else "none",
        status=status,
        public_docs_review_status=public_docs_review_status,
        public_docs_patch_path=str(patch_path) if patch_path else None,
        public_docs_impacted_count=len(public_doc_impacted_paths),
    )
    if ledger:
        ledger.write_json("final_report.json", report.model_dump())
        ledger.write_text("final_report.md", render_final_report_markdown(report))
    return report, ledger_dir
