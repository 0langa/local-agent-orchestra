from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
import typer

from ai_team.config import load_team_config
from ai_team.core.model_registry import ModelRegistry
from ai_team.errors import AIteamError, ConfigError, ProviderError
from ai_team.ledger import RunLedger
from ai_team.providers.base import ModelRequest
from ai_team.repo.context_pack import build_context_pack
from ai_team.repo.scanner import inspect_repository
from ai_team.resume import list_runs, load_final_report, load_run
from ai_team.runtime import plan_task, run_task

app = typer.Typer(help="Local-first three-agent runtime.")
console = Console()


@app.command("config-dump")
def config_dump(redacted: bool = typer.Option(True, "--redacted/--raw", help="Redact secrets in output.")) -> None:
    """Print loaded config."""
    config = load_team_config()
    console.print_json(json.dumps(config.dump(redacted=redacted)))


@app.command("ping-models")
def ping_models() -> None:
    """Ping configured models with tiny deterministic request."""
    config = load_team_config()
    registry = ModelRegistry.from_team_config(config)
    table = Table(title="Model Ping Results")
    table.add_column("role")
    table.add_column("provider")
    table.add_column("model")
    table.add_column("endpoint")
    table.add_column("status")

    for role, model_config in config.by_role().items():
        try:
            provider = registry.create_provider(model_config)
        except ValueError as exc:
            raise ProviderError(str(exc)) from exc
        request = ModelRequest(
            role=role,
            system_prompt="Reply with exactly: pong",
            user_prompt="ping",
            temperature=0.0,
        )
        try:
            response = provider.invoke(request)
            status = "ok" if response.content.strip() else "empty-response"
        except NotImplementedError as exc:
            status = f"not-implemented: {exc}"
        except Exception as exc:
            status = f"error: {exc}"
        table.add_row(
            role.value,
            model_config.provider,
            model_config.model,
            model_config.endpoint,
            status,
        )

    console.print(table)


@app.command("inspect")
def inspect(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
    write_ledger: bool = typer.Option(False, "--write-ledger", help="Write inspection ledger under target repo."),
) -> None:
    """Inspect repo and produce compact context summary."""
    repo_root = Path(repo).resolve()
    scan = inspect_repository(repo_root)
    context_pack = build_context_pack(scan)
    ledger_path: Path | None = None

    if write_ledger:
        ledger = RunLedger.create(repo_root, "inspect")
        ledger.write_json(
            "run.json",
            {"action": "inspect", "repo_name": scan.repo_name},
        )
        ledger.write_json("repo_snapshot.json", scan.model_dump())
        ledger.write_text("context_pack.md", context_pack)
        ledger.append_jsonl("tool_calls.jsonl", {"tool": "inspect_repository", "repo_name": scan.repo_name})
        ledger.append_jsonl("state_transitions.jsonl", {"state": "inspected", "repo_name": scan.repo_name})
        ledger_path = ledger.run_dir / "context_pack.md"

    if as_json:
        payload = scan.model_dump()
        if ledger_path is not None:
            payload["context_pack_file"] = ledger_path.name
        console.print_json(json.dumps(payload))
        return

    console.print(f"[bold]Repo:[/bold] {scan.repo_name}")
    console.print(f"[bold]Languages:[/bold] {', '.join(scan.languages) if scan.languages else 'none'}")
    console.print(f"[bold]Docs:[/bold] {len(scan.docs)}")
    console.print(f"[bold]Instruction files:[/bold] {len(scan.instruction_files)}")
    console.print(f"[bold]Git dirty:[/bold] {'yes' if scan.git.dirty else 'no'}")

    command_table = Table(title="Detected Commands")
    command_table.add_column("name")
    command_table.add_column("command")
    command_table.add_column("risk")
    command_table.add_column("reason")
    for command in scan.commands:
        command_table.add_row(command.name, " ".join(command.command), command.risk_level, command.reason)
    if scan.commands:
        console.print(command_table)
    else:
        console.print("No commands detected.")

    if scan.instruction_files:
        console.print("[bold]Instruction files:[/bold]")
        for path in scan.instruction_files:
            console.print(f"- {path}")

    if scan.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in scan.warnings:
            console.print(f"- {warning}")

    if ledger_path is not None:
        console.print(f"[bold]Context pack:[/bold] .ai-team/runs/{ledger_path.parent.name}/{ledger_path.name}")


@app.command("plan")
def plan(
    task_text: str,
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    write_ledger: bool = typer.Option(False, "--write-ledger", help="Write planning ledger under target repo."),
    out: str | None = typer.Option(None, "--out", help="Write parsed plan JSON to file."),
) -> None:
    """Build structured implementation plan without editing files."""
    scan, _context_pack, plan_result, ledger_dir = plan_task(task_text, repo, write_ledger=write_ledger)

    console.print(f"[bold]Plan summary:[/bold] {plan_result.summary}")
    console.print(f"[bold]Repo type:[/bold] {plan_result.detected_repo_type}")
    console.print(f"[bold]Likely files:[/bold] {', '.join(plan_result.files_likely_to_change) if plan_result.files_likely_to_change else 'none'}")

    table = Table(title="Planned Work Orders")
    table.add_column("id")
    table.add_column("type")
    table.add_column("title")
    table.add_column("max scope")
    for task in plan_result.task_graph.ordered_tasks:
        table.add_row(task.id, task.type.value, task.title, task.max_edit_scope)
    console.print(table)

    if plan_result.risks:
        console.print("[bold]Risks:[/bold]")
        for risk in plan_result.risks:
            console.print(f"- {risk.risk}: {risk.mitigation}")

    if ledger_dir is not None:
        console.print(f"[bold]Ledger:[/bold] {ledger_dir}")

    if out:
        out_path = Path(out)
        out_path.write_text(json.dumps(plan_result.model_dump(), indent=2), encoding="utf-8")
        console.print(f"[bold]Plan JSON:[/bold] {out_path}")


@app.command("run")
def run(
    task_text: str,
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    mode: str = typer.Option("apply", "--mode", help="Execution mode."),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Allow execution on dirty repo."),
    max_fix_attempts: int = typer.Option(0, "--max-fix-attempts", help="Additional coder retry attempts after first failure."),
    max_diff_lines: int = typer.Option(1200, "--max-diff-lines", help="Maximum allowed diff lines per patch."),
    command_timeout: int = typer.Option(120, "--command-timeout", help="Timeout for safe verification commands in seconds."),
    no_tests: bool = typer.Option(False, "--no-tests", help="Skip verification commands."),
) -> None:
    """Plan and apply bounded work orders without auto-commit."""
    if mode not in {"apply", "auto", "ci"}:
        raise typer.BadParameter("Mode must be one of: apply, auto, ci.")

    report, ledger_dir = run_task(
        task_text,
        repo,
        mode=mode,
        allow_dirty=allow_dirty,
        max_fix_attempts=max_fix_attempts,
        max_diff_lines=max_diff_lines,
        command_timeout=command_timeout,
        no_tests=no_tests,
    )

    console.print(f"[bold]Task summary:[/bold] {report.task_summary}")
    console.print(f"[bold]Changed files:[/bold] {', '.join(report.changed_files) if report.changed_files else 'none'}")
    console.print(f"[bold]Ledger:[/bold] {ledger_dir}")
    if report.commands_run:
        console.print("[bold]Commands run:[/bold]")
        for command in report.commands_run:
            console.print(f"- {' '.join(command)}")
    if report.tests:
        console.print("[bold]Verification:[/bold]")
        for item in report.tests:
            console.print(f"- {item.name}: {item.status}")


@app.command("list-runs")
def list_runs_cmd(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
) -> None:
    runs = list_runs(repo)
    if not runs:
        console.print("No runs found.")
        return
    for item in runs:
        console.print(f"- {item}")


@app.command("report")
def report(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    run_id: str = typer.Option(..., "--run-id", help="Run id under .ai-team/runs."),
) -> None:
    final_report = load_final_report(repo, run_id)
    console.print(f"[bold]Status:[/bold] {final_report.status}")
    console.print(f"[bold]Task summary:[/bold] {final_report.task_summary}")
    console.print(f"[bold]Changed files:[/bold] {', '.join(final_report.changed_files) if final_report.changed_files else 'none'}")
    console.print(f"[bold]Run id:[/bold] {final_report.run_id}")
    if final_report.next_command_suggestions:
        console.print("[bold]Next commands:[/bold]")
        for item in final_report.next_command_suggestions:
            console.print(f"- {item}")


@app.command("resume")
def resume(
    repo: str = typer.Option(..., "--repo", help="Target repository path."),
    run_id: str = typer.Option(..., "--run-id", help="Run id under .ai-team/runs."),
) -> None:
    run_data = load_run(repo, run_id)
    console.print_json(json.dumps(run_data))


def main() -> None:
    try:
        app()
    except (ConfigError, AIteamError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    main()
