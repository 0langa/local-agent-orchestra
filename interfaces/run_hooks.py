"""Default run hook adapter injected into RunExecutor from outside core."""

from __future__ import annotations

from core.public_api import RunExecutor


class _DefaultRunHook:
    """Adapts monitoring metrics and self-improving hooks to the RunHook protocol."""

    def __init__(self) -> None:
        from agents.self_improving.hooks import SelfImprovingHook
        from monitoring.metrics import MetricsCollector

        self.metrics = MetricsCollector()
        self.hook = SelfImprovingHook()

    def start_run(self, run_id: str) -> None:
        self.metrics.start_run(run_id)

    def end_run(self, run_id: str) -> None:
        self.metrics.end_run(run_id)

    def record_error(self, run_id: str) -> None:
        self.metrics.record_error(run_id)

    def on_run_complete(self, run_id: str, success: bool, error: str | None = None) -> None:
        self.hook.on_run_complete(run_id, success=success, error=error)


def register_default_run_hooks(executor: RunExecutor) -> None:
    """Register the default metrics and self-improving hooks if not already present."""
    executor.add_hook(_DefaultRunHook())
