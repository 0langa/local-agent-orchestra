"""Concrete ContextOps implementation delegating to AICtx internals.

M2 deliverable.
M2.5 additions: init, clean, run_pipeline, public_docs_update;
replace vendor imports with direct ``aictx`` package imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.path_security import safe_child_path, safe_project_path, safe_run_id
from agentheim.vendor.aictx.config import AictxConfig
from agentheim.vendor.aictx.context.fact_extractor import extract_facts
from agentheim.vendor.aictx.context.lockfile import build_lockfile_from_inventory, load_lockfile, write_lockfile
from agentheim.vendor.aictx.context.pipeline import run_local_context_pipeline
from agentheim.vendor.aictx.context.planner import plan_context
from agentheim.vendor.aictx.context.writer import build_context_lock, write_context_scaffold
from agentheim.vendor.aictx.public_docs.mapper import build_public_docs_map
from agentheim.vendor.aictx.public_docs.updater import update_public_docs
from agentheim.vendor.aictx.scan.scanner import scan_repository
from agentheim.vendor.aictx.verify.verifier import verify_detailed
from providers.base import ModelProvider as AgentheimModelProvider

def _rm_tree(root: Path) -> None:
    """Recursively delete a directory tree using pathlib only."""
    for child in root.iterdir():
        if child.is_dir():
            _rm_tree(child)
        else:
            child.unlink()
    root.rmdir()


from agentheim.context_ops import (
    CleanResult,
    ContextOps,
    ContextPlan,
    ContextStatus,
    GeneratedContext,
    PublicDocsImpactReport,
    RepositoryInventory,
    VerificationResult,
    WriteReport,
)


class AictxContextOps(ContextOps):
    """Delegate ContextOps methods to AICtx internals."""

    def __init__(self, config: AictxConfig | None = None) -> None:
        self.config = config or AictxConfig()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self, repo_root: Path) -> None:
        """Initialize *repo_root* for context processing."""
        repo_root = safe_project_path(repo_root)
        ignore_path = safe_child_path(repo_root, ".aictxignore")
        if not ignore_path.exists():
            ignore_path.write_text("# AICtx custom ignore patterns\n", encoding="utf-8")

        inventory = scan_repository(repo_root)
        context_dir = safe_child_path(repo_root, self.config.project.context_dir)
        context_dir.mkdir(parents=True, exist_ok=True)
        existing_lock = load_lockfile(context_dir)
        lock = build_lockfile_from_inventory(inventory)
        if existing_lock is not None and existing_lock.generated_files:
            lock = existing_lock.model_copy(
                update={
                    "tool_version": lock.tool_version,
                    "repo_head_commit": lock.repo_head_commit,
                    "generated_at": lock.generated_at,
                    "scanner_config_hash": lock.scanner_config_hash,
                    "source_files": lock.source_files,
                    "generated_files": existing_lock.generated_files,
                    "sections": existing_lock.sections,
                    "public_docs_map": existing_lock.public_docs_map,
                    "change_impact_map": existing_lock.change_impact_map,
                    "model_provider": existing_lock.model_provider,
                    "model_name": existing_lock.model_name,
                    "last_validation": existing_lock.last_validation,
                }
            )
        write_lockfile(context_dir, lock)

    def clean(
        self,
        repo_root: Path,
        *,
        run_id: str | None = None,
        keep_runs: int | None = None,
    ) -> CleanResult:
        """Remove generated run artifacts."""
        if run_id is None and keep_runs is None:
            raise ValueError("clean requires run_id or keep_runs")
        if keep_runs is not None and keep_runs < 0:
            raise ValueError("keep_runs must be >= 0")

        removed: list[str] = []
        repo_root = safe_project_path(repo_root)

        # Canonical store
        runs_dir = safe_child_path(repo_root, ".ai-team", "runs")
        if runs_dir.exists():
            all_runs = sorted([p for p in runs_dir.iterdir() if p.is_dir()])
            targets: list[Path] = []
            if run_id:
                target = safe_child_path(runs_dir, safe_run_id(run_id))
                if target.exists() and target.is_dir():
                    targets = [target]
            elif keep_runs is not None:
                targets = all_runs[: max(0, len(all_runs) - keep_runs)]
            for path in targets:
                _rm_tree(path)
                removed.append(path.name)
            kept = [p.name for p in all_runs if p.name not in removed]
        else:
            all_runs = []
            kept = []

        # Migration cleanup: also remove from legacy .aictx/runs/
        legacy_runs_dir = safe_child_path(repo_root, ".aictx", "runs")
        if legacy_runs_dir.exists():
            legacy_targets: list[Path] = []
            legacy_all = sorted([p for p in legacy_runs_dir.iterdir() if p.is_dir()])
            if run_id:
                lt = safe_child_path(legacy_runs_dir, safe_run_id(run_id))
                if lt.exists() and lt.is_dir():
                    legacy_targets = [lt]
            elif keep_runs is not None:
                legacy_targets = legacy_all[: max(0, len(legacy_all) - keep_runs)]
            for path in legacy_targets:
                _rm_tree(path)
                removed.append(path.name)
            if not kept:
                kept = [p.name for p in legacy_all if p.name not in removed]

        return CleanResult(
            removed_count=len(removed),
            kept_count=len(kept),
            removed_paths=removed,
        )

    # ------------------------------------------------------------------
    # Phase-1 context generation (granular)
    # ------------------------------------------------------------------

    def scan(self, repo_root: Path) -> RepositoryInventory:
        repo_root = safe_project_path(repo_root)
        raw = scan_repository(repo_root)
        return RepositoryInventory(raw=raw)

    def plan(
        self,
        inventory: RepositoryInventory,
        scope: str = "full",
        existing_lock: Any | None = None,
    ) -> ContextPlan:
        repo_root = safe_project_path(Path(inventory.repo_root) if inventory.repo_root else Path.cwd())
        context_dir = safe_child_path(repo_root, self.config.project.context_dir)
        agents_md = safe_child_path(repo_root, self.config.project.agents_file)
        plan_dict = plan_context(
            inventory=inventory.raw,
            existing_context_dir=context_dir if context_dir.exists() else None,
            existing_agents_md=agents_md if agents_md.exists() else None,
            scope=scope,
            config=self.config,
            existing_lock=existing_lock,
            changed_files=[],
        )
        return ContextPlan(raw=plan_dict)

    def generate(
        self,
        repo_root: Path,
        plan: ContextPlan,
        provider: Any | None = None,
    ) -> GeneratedContext:
        repo_root = safe_project_path(repo_root)
        if provider is None:
            from agentheim.vendor.aictx.llm.dry_run import DryRunProvider
            provider = DryRunProvider()
        elif hasattr(provider, "chat"):
            # Already an AICtx provider (e.g. DryRunProvider from tests)
            pass
        else:
            # Wrap Agentheim provider with Aictx adapter
            from agentheim.provider_adapter import AgentheimToAictxAdapter
            provider = AgentheimToAictxAdapter(provider)

        fact_packs = extract_facts(
            repo_root=repo_root,
            plan=plan.raw,
            provider=provider,
            run_id="agentheim-ctx",
        )
        return GeneratedContext(
            plan=plan,
            fact_packs=fact_packs,
            repo_root=repo_root,
        )

    def write(
        self,
        repo_root: Path,
        context: GeneratedContext,
        write_mode: str = "patch",
    ) -> WriteReport:
        from agentheim.vendor.aictx.context.pipeline import _build_patch
        from agentheim.vendor.aictx.io.files import safe_write

        repo_root = safe_project_path(repo_root)
        # Re-scan to get fresh inventory for lockfile
        inventory_raw = scan_repository(repo_root)
        out_dir = safe_child_path(repo_root, ".ai-team", "runs", "agentheim-ctx", "out")
        out_dir.mkdir(parents=True, exist_ok=True)

        generated_paths = write_context_scaffold(
            repo_root=repo_root,
            out_dir=out_dir,
            inventory=inventory_raw,
            plan=context.plan.raw,
            fact_packs=context.fact_packs,
        )

        lock = build_context_lock(
            repo_root=repo_root,
            out_dir=out_dir,
            inventory=inventory_raw,
            plan=context.plan.raw,
            fact_packs=context.fact_packs,
            generated_paths=generated_paths,
            model_provider=self.config.llm.provider,
            model_name=self.config.llm.model,
            existing_lock=None,
            changed_files=[],
            preserve_existing_sections=False,
        )

        staged_context_dir = out_dir / self.config.project.context_dir
        write_lockfile(staged_context_dir, lock)
        generated_paths.append(staged_context_dir / "context.lock.json")

        patch_text = _build_patch(repo_root=repo_root, out_dir=out_dir)
        patch_path = safe_child_path(repo_root, ".ai-team", "runs", "agentheim-ctx", "aictx.patch")
        safe_write(patch_path, patch_text)

        if write_mode == "apply":
            from agentheim.vendor.aictx.context.pipeline import _apply_out_dir

            _apply_out_dir(repo_root=repo_root, out_dir=out_dir)

        return WriteReport(
            generated_files=[p.relative_to(out_dir).as_posix() for p in generated_paths],
            lockfile_path=f"{self.config.project.context_dir}/context.lock.json",
            patch_text=patch_text,
        )

    # ------------------------------------------------------------------
    # End-to-end pipeline
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        repo_root: Path,
        run_id: str,
        scope: str = "full",
        write_mode: str = "patch",
        allow_ai: bool = False,
        allow_dirty: bool = False,
        provider: Any | None = None,
    ) -> WriteReport:
        """Run the full local Phase-1 pipeline and return enriched report."""
        repo_root = safe_project_path(repo_root)
        run_id = safe_run_id(run_id)
        if allow_ai:
            if provider is None:
                from config.config import ModelRole, load_team_config
                from core.model_registry import build_model_registry

                team_config = load_team_config()
                model_config = team_config.resolve_role(ModelRole.CONTEXT)
                provider = build_model_registry(team_config).create_provider(model_config)
            inventory = self.scan(repo_root)
            context_plan = self.plan(inventory, scope=scope)
            generated = self.generate(repo_root, context_plan, provider=provider)
            written = self.write(repo_root, generated, write_mode=write_mode)
            return WriteReport(
                generated_files=written.generated_files,
                lockfile_path=written.lockfile_path,
                patch_text=written.patch_text,
                run_report=written.run_report,
                timing=written.timing or {},
                entropy=written.entropy or {},
            )
        if provider is None:
            from agentheim.vendor.aictx.llm.dry_run import DryRunProvider

            provider = DryRunProvider()
        report = run_local_context_pipeline(
            repo_root=repo_root,
            run_id=run_id,
            config=self.config,
            scope=scope,  # type: ignore[arg-type]
            write_mode=write_mode,  # type: ignore[arg-type]
            provider=provider,
            allow_ai=allow_ai,
            allow_dirty=allow_dirty,
        )
        return WriteReport(
            generated_files=report.generated_files,
            lockfile_path=f"{self.config.project.context_dir}/context.lock.json",
            patch_text=safe_child_path(repo_root, Path(report.patch_path)).read_text(encoding="utf-8")
            if report.patch_path and safe_child_path(repo_root, Path(report.patch_path)).exists()
            else "",
            run_report=report,
            timing=report.timing,
            entropy=report.entropy,
        )

    # ------------------------------------------------------------------
    # Verification & status
    # ------------------------------------------------------------------

    def verify(self, repo_root: Path, strict: bool = False) -> VerificationResult:
        repo_root = safe_project_path(repo_root)
        report = verify_detailed(repo_root, strict=strict)
        return VerificationResult(
            result=report.result,
            is_pass=report.result == "PASS",
            raw=report,
        )

    def status(self, repo_root: Path, strict: bool = False) -> ContextStatus:
        repo_root = safe_project_path(repo_root)
        report = verify_detailed(repo_root, strict=strict)
        return ContextStatus(
            is_stale=report.result != "PASS",
            stale_sources=report.stale_sources,
            missing_sources=report.missing_sources,
            missing_generated=report.missing_generated,
            generated_mismatches=report.generated_mismatches,
            public_docs_impacts=report.public_docs_impacts,
            next_command=report.next_command,
        )

    # ------------------------------------------------------------------
    # Public docs
    # ------------------------------------------------------------------

    def public_docs_impact(
        self,
        repo_root: Path,
        scope: str = "full",
    ) -> PublicDocsImpactReport:
        repo_root = safe_project_path(repo_root)
        docs_map = build_public_docs_map(repo_root)
        return PublicDocsImpactReport(
            entries=[entry.model_dump(mode="json") for entry in docs_map.entries],
            raw=docs_map,
        )

    def public_docs_update(
        self,
        repo_root: Path,
        scope: str = "changed",
        write_mode: str = "patch",
    ) -> Path | None:
        """Generate patches for impacted public docs."""
        repo_root = safe_project_path(repo_root)
        return update_public_docs(
            repo_root=repo_root,
            scope=scope,  # type: ignore[arg-type]
            write_mode=write_mode,  # type: ignore[arg-type]
        )
