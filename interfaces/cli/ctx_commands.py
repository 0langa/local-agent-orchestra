"""CLI subcommands for the ``agentheim ctx`` namespace."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.table import Table
import typer

from agentheim.context_ops_impl import AictxContextOps
from agentheim.vendor.aictx.config import AictxConfig
from agentheim.vendor.aictx.errors import SafetyError, VerificationError

ctx_app = typer.Typer(help="AICtx context operations.")
public_docs_app = typer.Typer(help="Public docs impact and update commands.")
ctx_app.add_typer(
    public_docs_app,
    name="public-docs",
    help="Public docs commands: impact, update.",
)

from interfaces.cli.oci_commands import oci_app
ctx_app.add_typer(
    oci_app,
    name="oci",
    help="OCI commands: doctor, snapshot create/verify, bundle create/verify.",
)

console = Console()


def _get_ops() -> AictxContextOps:
    return AictxContextOps(config=AictxConfig())


def _handle_errors(fn: Callable[[], None]) -> None:
    try:
        fn()
    except SafetyError as exc:
        console.print(f"[red]Safety error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except VerificationError as exc:
        console.print(f"[red]Verification error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        console.print(f"[red]Value error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


@ctx_app.command("init")
def init_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
) -> None:
    """Initialize repo for context processing."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        ops.init(repo_root)
        console.print(f"[green]Initialized[/green] {repo_root}")
    _handle_errors(_body)


@ctx_app.command("scan")
def scan_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
) -> None:
    """Scan repository and print inventory summary."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        inventory = ops.scan(repo_root)
        file_count = len(inventory.raw.files) if inventory.raw and hasattr(inventory.raw, "files") else 0
        manifest_count = len(inventory.raw.manifests) if inventory.raw and hasattr(inventory.raw, "manifests") else 0
        console.print(f"[bold]Repo root:[/bold] {repo_root}")
        console.print(f"[bold]Files:[/bold] {file_count}")
        console.print(f"[bold]Manifests:[/bold] {manifest_count}")
    _handle_errors(_body)


@ctx_app.command("run")
def run_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    scope: str = typer.Option("full", "--scope", help="Run scope: full or changed."),
    write: str = typer.Option("patch", "--write", help="Write mode: patch or apply."),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Allow execution on dirty repo."),
) -> None:
    """Run full context generation pipeline."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        run_id = f"agentheim-ctx-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        report = ops.run_pipeline(
            repo_root=repo_root,
            run_id=run_id,
            scope=scope,
            write_mode=write,
            allow_dirty=allow_dirty,
        )
        console.print("[bold]Generated files:[/bold]")
        for path in report.generated_files:
            console.print(f"  - {path}")
        if report.timing:
            console.print(f"[bold]Timing:[/bold] {report.timing.total_duration_ms:.1f} ms total")
        patch_path = (
            report.run_report.patch_path
            if report.run_report and hasattr(report.run_report, "patch_path")
            else None
        )
        if patch_path:
            console.print(f"[bold]Patch:[/bold] {patch_path}")
        else:
            console.print("[bold]Patch:[/bold] none")
    _handle_errors(_body)


@ctx_app.command("verify")
def verify_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    strict: bool = typer.Option(False, "--strict", help="Strict verification."),
) -> None:
    """Verify context lock against repository state."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        result = ops.verify(repo_root, strict=strict)
        if result.is_pass:
            console.print(f"[green]PASS[/green] ({result.result})")
        else:
            console.print(f"[red]FAIL[/red] ({result.result})")
            raise typer.Exit(code=1)
    _handle_errors(_body)


@ctx_app.command("status")
def status_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    strict: bool = typer.Option(False, "--strict", help="Strict status check."),
) -> None:
    """Show stale-context detection status."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        status = ops.status(repo_root, strict=strict)
        table = Table(title="Context Status")
        table.add_column("Category", style="bold")
        table.add_column("Details")
        table.add_row("Stale sources", "\n".join(status.stale_sources) or "none")
        table.add_row("Missing sources", "\n".join(status.missing_sources) or "none")
        table.add_row("Missing generated", "\n".join(status.missing_generated) or "none")
        table.add_row("Generated mismatches", "\n".join(status.generated_mismatches) or "none")
        table.add_row("Next command", status.next_command or "none")
        console.print(table)
        if status.is_stale:
            console.print("[yellow]Status: stale[/yellow]")
        else:
            console.print("[green]Status: up to date[/green]")
    _handle_errors(_body)


@ctx_app.command("clean")
def clean_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    run_id: str | None = typer.Option(None, "--run-id", help="Specific run ID to remove."),
    keep_runs: int | None = typer.Option(None, "--keep-runs", help="Retain newest N runs."),
) -> None:
    """Remove generated run artifacts."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        result = ops.clean(repo_root, run_id=run_id, keep_runs=keep_runs)
        console.print(f"[bold]Removed:[/bold] {result.removed_count}")
        console.print(f"[bold]Kept:[/bold] {result.kept_count}")
        if result.removed_paths:
            console.print("[bold]Removed paths:[/bold]")
            for path in result.removed_paths:
                console.print(f"  - {path}")
    _handle_errors(_body)


@public_docs_app.command("impact")
def public_docs_impact_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    scope: str = typer.Option("full", "--scope", help="Impact scope: full or changed."),
) -> None:
    """Map source changes to impacted public documentation."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        report = ops.public_docs_impact(repo_root, scope=scope)
        table = Table(title="Public Docs Impact")
        table.add_column("Doc")
        table.add_column("Purpose")
        table.add_column("Sources")
        for entry in report.entries:
            doc = entry.get("path", "") if isinstance(entry, dict) else str(entry)
            purpose = entry.get("purpose", "") if isinstance(entry, dict) else ""
            sources = entry.get("source_paths", []) if isinstance(entry, dict) else []
            sources_str = ", ".join(sources) if isinstance(sources, list) else str(sources)
            table.add_row(doc, purpose, sources_str)
        if report.entries:
            console.print(table)
        else:
            console.print("No impacted docs.")
    _handle_errors(_body)


@public_docs_app.command("update")
def public_docs_update_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    scope: str = typer.Option("changed", "--scope", help="Update scope: full or changed."),
    write: str = typer.Option("patch", "--write", help="Write mode: patch or apply."),
) -> None:
    """Generate patches for impacted public docs."""
    def _body() -> None:
        repo_root = Path(project).resolve()
        ops = _get_ops()
        patch_path = ops.public_docs_update(repo_root, scope=scope, write_mode=write)
        if patch_path:
            console.print(f"[bold]Patch:[/bold] {patch_path}")
        else:
            console.print("No impacted docs.")
    _handle_errors(_body)
