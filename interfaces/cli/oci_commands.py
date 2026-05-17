"""OCI CLI subcommands for ``agentheim ctx oci``."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table
import typer

oci_app = typer.Typer(help="OCI remote execution commands.")
console = Console()

_OCI_MISSING_MSG = "OCI support requires `pip install agentheim[oci]`"


def _import_oci_doctor() -> object:
    from agentheim.vendor.aictx.oci.doctor import run_oci_doctor
    return run_oci_doctor


def _import_snapshot_create() -> object:
    from agentheim.vendor.aictx.oci.snapshot import create_snapshot
    return create_snapshot


def _import_snapshot_verify() -> object:
    from agentheim.vendor.aictx.oci.snapshot import verify_snapshot
    return verify_snapshot


def _import_bundle_create() -> object:
    from agentheim.vendor.aictx.oci.bundle import create_result_bundle
    return create_result_bundle


def _import_bundle_verify() -> object:
    from agentheim.vendor.aictx.oci.bundle import verify_bundle
    return verify_bundle


@oci_app.command("doctor")
def oci_doctor_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
) -> None:
    """Run OCI readiness checks."""
    try:
        run_oci_doctor = _import_oci_doctor()
    except ImportError:
        console.print(_OCI_MISSING_MSG)
        raise typer.Exit(code=1)

    try:
        report = run_oci_doctor()
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="OCI Readiness Report")
    table.add_column("Check", style="bold")
    table.add_column("Status")

    checks = [
        ("SDK available", report.sdk_available),
        ("Config file exists", report.config_file_exists),
        ("Profile exists", report.profile_exists),
        ("Compartment ID present", report.compartment_id_present),
        ("Model ID present", report.model_id_present),
        ("Auth OK", report.auth_ok),
        ("Bucket access", report.bucket_access),
        ("Region matches", report.region_matches),
    ]

    for check, ok in checks:
        status = "[green]PASS[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(check, status)

    console.print(table)

    if report.missing:
        console.print("[red]Missing:[/red] " + ", ".join(report.missing))

    if report.ready:
        console.print("[green]OCI is ready.[/green]")
    else:
        console.print("[red]OCI is not ready.[/red]")
        raise typer.Exit(code=1)


snapshot_app = typer.Typer(help="Snapshot commands.")
oci_app.add_typer(snapshot_app, name="snapshot", help="Snapshot commands: create, verify.")


@snapshot_app.command("create")
def snapshot_create_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    run_id: str = typer.Option("", "--run-id", help="Optional run ID to register as artifact."),
) -> None:
    """Create a deterministic snapshot of the repository."""
    try:
        create_snapshot = _import_snapshot_create()
    except ImportError:
        console.print(_OCI_MISSING_MSG)
        raise typer.Exit(code=1)

    repo_root = Path(project).resolve()
    output_dir = repo_root / ".ai-team" / "runs"

    try:
        snapshot_path = create_snapshot(repo_root=repo_root, output_dir=output_dir)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if run_id:
        from core.public_api import ArtifactStore

        run_dir = repo_root / ".ai-team" / "runs" / run_id
        store = ArtifactStore(run_dir)
        store.produce_snapshot_zip(snapshot_path)
        console.print(f"[green]Snapshot created and registered to run {run_id}:[/green] {snapshot_path}")
    else:
        console.print(f"[green]Snapshot created:[/green] {snapshot_path}")


@snapshot_app.command("verify")
def snapshot_verify_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
) -> None:
    """Verify snapshot integrity."""
    try:
        verify_snapshot = _import_snapshot_verify()
    except ImportError:
        console.print(_OCI_MISSING_MSG)
        raise typer.Exit(code=1)

    repo_root = Path(project).resolve()
    snapshot_path = repo_root / ".ai-team" / "runs" / "aictx-snapshot.zip"

    try:
        result = verify_snapshot(snapshot_path)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    valid = result.get("valid", False)
    if valid:
        console.print(f"[green]Snapshot is valid[/green] ({result.get('file_count', 0)} files)")
    else:
        errors = result.get("errors", [])
        error_msg = result.get("error", "unknown error")
        console.print(f"[red]Snapshot is invalid:[/red] {error_msg}")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(code=1)


bundle_app = typer.Typer(help="Bundle commands.")
oci_app.add_typer(bundle_app, name="bundle", help="Bundle commands: create, verify.")


@bundle_app.command("create")
def bundle_create_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    run_id: str = typer.Option(..., "--run-id", help="Run ID for the bundle."),
) -> None:
    """Create a result bundle for a run."""
    try:
        create_result_bundle = _import_bundle_create()
    except ImportError:
        console.print(_OCI_MISSING_MSG)
        raise typer.Exit(code=1)

    repo_root = Path(project).resolve()
    output_dir = repo_root / ".ai-team" / "runs" / run_id

    try:
        bundle_path = create_result_bundle(output_dir=output_dir)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    from core.public_api import ArtifactStore

    run_dir = repo_root / ".ai-team" / "runs" / run_id
    store = ArtifactStore(run_dir)
    store.produce_bundle_zip(bundle_path)
    console.print(f"[green]Bundle created and registered:[/green] {bundle_path}")


@bundle_app.command("verify")
def bundle_verify_cmd(
    project: str = typer.Option(".", "--project", help="Target repository path."),
    run_id: str = typer.Option(..., "--run-id", help="Run ID for the bundle."),
) -> None:
    """Verify result bundle integrity."""
    try:
        verify_bundle = _import_bundle_verify()
    except ImportError:
        console.print(_OCI_MISSING_MSG)
        raise typer.Exit(code=1)

    repo_root = Path(project).resolve()
    bundle_path = repo_root / ".ai-team" / "runs" / run_id / "aictx-result.zip"

    try:
        result = verify_bundle(bundle_path)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    valid = result.get("valid", False)
    if valid:
        console.print(f"[green]Bundle is valid[/green] ({result.get('file_count', 0)} files)")
    else:
        errors = result.get("errors", [])
        error_msg = result.get("error", "unknown error")
        console.print(f"[red]Bundle is invalid:[/red] {error_msg}")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(code=1)
