from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class VerificationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    status: str
    details: str = ""
    command: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_summary: str
    changed_files: list[str] = Field(default_factory=list)
    commands_run: list[list[str]] = Field(default_factory=list)
    tests: list[VerificationRecord] = Field(default_factory=list)
    remaining_risks: list[str] = Field(default_factory=list)
    run_id: str
    next_command_suggestions: list[str] = Field(default_factory=list)
    status: str = "done"