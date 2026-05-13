"""Helper for emitting context-operation events to a RunLedger."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.events import EventType
from core.ledger import RunLedger
from agentheim.context_ops import (
    ContextPlan,
    ContextStatus,
    PublicDocsImpactReport,
    RepositoryInventory,
    VerificationResult,
    WriteReport,
)


class ContextRunLedger:
    """Helper for emitting context-operation events to a RunLedger."""

    def __init__(self, ledger: RunLedger) -> None:
        self.ledger = ledger

    def emit_initialized(self, repo_root: Path) -> None:
        """Emit CONTEXT_INITIALIZED."""
        self.ledger.append_event(
            EventType.CONTEXT_INITIALIZED,
            payload={"repo_root": str(repo_root)},
        )

    def emit_scanned(self, inventory: RepositoryInventory) -> None:
        """Emit CONTEXT_SCANNED with file count."""
        file_count = len(inventory.raw.files) if inventory.raw else 0
        self.ledger.append_event(
            EventType.CONTEXT_SCANNED,
            payload={"file_count": file_count},
        )

    def emit_planned(self, plan: ContextPlan) -> None:
        """Emit CONTEXT_PLANNED with selected file count."""
        self.ledger.append_event(
            EventType.CONTEXT_PLANNED,
            payload={"selected_count": len(plan.selected_files)},
        )

    def emit_generated(self, repo_root: Path, fact_pack_count: int) -> None:
        """Emit CONTEXT_GENERATED with pack count."""
        self.ledger.append_event(
            EventType.CONTEXT_GENERATED,
            payload={"repo_root": str(repo_root), "fact_pack_count": fact_pack_count},
        )

    def emit_written(self, report: WriteReport) -> None:
        """Emit CONTEXT_WRITTEN with generated file count and patch size."""
        self.ledger.append_event(
            EventType.CONTEXT_WRITTEN,
            payload={
                "generated_count": len(report.generated_files),
                "patch_size": len(report.patch_text),
            },
        )

    def emit_verified(self, result: VerificationResult) -> None:
        """Emit CONTEXT_VERIFIED or CONTEXT_STALE_DETECTED."""
        event_type = EventType.CONTEXT_VERIFIED if result.is_pass else EventType.CONTEXT_STALE_DETECTED
        self.ledger.append_event(
            event_type,
            payload={"result": result.result, "is_pass": result.is_pass},
        )

    def emit_status(self, status: ContextStatus) -> None:
        """Emit CONTEXT_STALE_DETECTED if stale, else CONTEXT_VERIFIED."""
        event_type = EventType.CONTEXT_STALE_DETECTED if status.is_stale else EventType.CONTEXT_VERIFIED
        self.ledger.append_event(
            event_type,
            payload={"is_stale": status.is_stale},
        )

    def emit_public_docs_impact(self, report: PublicDocsImpactReport) -> None:
        """Emit PUBLIC_DOCS_IMPACT_MAPPED with entry count."""
        self.ledger.append_event(
            EventType.PUBLIC_DOCS_IMPACT_MAPPED,
            payload={"entry_count": len(report.entries)},
        )

    def emit_public_docs_updated(self, patch_path: Path | None) -> None:
        """Emit PUBLIC_DOCS_UPDATED with patch path."""
        self.ledger.append_event(
            EventType.PUBLIC_DOCS_UPDATED,
            payload={"patch_path": str(patch_path) if patch_path else None},
        )
