from __future__ import annotations

from typing import Any

from presets.base import PRESET_REGISTRY, Preset, Question


class ContextMaintainerPreset(Preset):
    def __init__(self) -> None:
        super().__init__(
            preset_id="context-maintainer",
            workflow_id="context_maintainer",
            name="Context Maintainer",
            description="Maintain deterministic AI context for a repository.",
            guided_questions=[
                Question(
                    key="scope",
                    type="choice",
                    text="Run scope?",
                    options=["full", "changed"],
                    default="full",
                ),
                Question(
                    key="write_mode",
                    type="choice",
                    text="Write mode?",
                    options=["patch", "apply"],
                    default="patch",
                ),
                Question(
                    key="project_path",
                    type="text",
                    text="Target repository path?",
                    default=".",
                ),
            ],
            default_config={"scope": "full", "write_mode": "patch", "project_path": "."},
            required_capabilities=[],
        )

    def run(self, inputs: dict[str, Any]) -> Any:
        from pathlib import Path

        from core.artifact_store import ArtifactStore
        from core.ledger import RunLedger
        from workflows.context_maintainer.runtime import run_context_maintainer

        repo_path = inputs.get("project_path", ".")
        scope = inputs.get("scope", "full")
        write_mode = inputs.get("write_mode", "patch")
        repo_root = Path(repo_path).resolve()

        ledger = RunLedger.create(repo_root, "context_maintainer")
        artifact_store = ArtifactStore.create_run(
            ledger.run_dir,
            workflow_id=self.workflow_id,
            preset_id=self.preset_id,
            config={"scope": scope, "write_mode": write_mode},
        )

        return run_context_maintainer(
            repo_root=repo_root,
            scope=scope,
            write_mode=write_mode,
            ledger=ledger,
            artifact_store=artifact_store,
        )


PRESET_REGISTRY.register(ContextMaintainerPreset())
