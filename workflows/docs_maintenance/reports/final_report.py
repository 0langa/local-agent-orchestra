from __future__ import annotations

from pydantic import BaseModel, Field


class DocUpdateRecord(BaseModel):
    doc_path: str
    status: str
    details: str = ""


class FinalReport(BaseModel):
    task_summary: str
    updated_docs: list[DocUpdateRecord] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    run_id: str
    status: str = "done"
    public_docs_review_status: str = "no_impact"
    public_docs_patch_path: str | None = None
    public_docs_impacted_count: int = 0
