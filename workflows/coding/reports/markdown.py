from __future__ import annotations

from workflows.coding.reports.final_report import FinalReport


def render_final_report_markdown(report: FinalReport) -> str:
    commands = "\n".join(f"- {' '.join(item)}" for item in report.commands_run) or "- none"
    changed_files = "\n".join(f"- {item}" for item in report.changed_files) or "- none"
    risks = "\n".join(f"- {item}" for item in report.remaining_risks) or "- none"
    next_commands = "\n".join(f"- {item}" for item in report.next_command_suggestions) or "- none"
    verification = "\n".join(
        f"- {item.name}: {item.status}" + (f" ({item.details})" if item.details else "")
        for item in report.tests
    ) or "- none"
    return (
        f"# Final Report\n\n"
        f"## Task summary\n{report.task_summary}\n\n"
        f"## Changed files\n{changed_files}\n\n"
        f"## Commands run\n{commands}\n\n"
        f"## Verification\n{verification}\n\n"
        f"## Remaining risks\n{risks}\n\n"
        f"## Run id\n`{report.run_id}`\n\n"
        f"## Next command suggestions\n{next_commands}\n"
    )