"""Background run executor for workflow and preset execution via API.

Runs long-lived tasks in background threads and exposes status polling
and SSE streaming.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunRecord:
    run_id: str
    status: RunStatus
    started_at: float
    finished_at: float | None = None
    result: Any = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


class RunExecutor:
    """Singleton executor that manages background runs."""

    _instance: "RunExecutor | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "RunExecutor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._runs: dict[str, RunRecord] = {}
                cls._instance._run_lock = threading.Lock()
                cls._instance._subscribers: dict[str, list[Callable[[RunRecord], None]]] = {}
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (mainly for tests)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance = None

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Submit *fn* for background execution and return a run ID."""
        run_id = str(uuid.uuid4())
        record = RunRecord(
            run_id=run_id,
            status=RunStatus.PENDING,
            started_at=time.time(),
        )
        with self._run_lock:
            self._runs[run_id] = record
            self._subscribers[run_id] = []

        def _run() -> None:
            from agents.self_improving.hooks import SelfImprovingHook
            from monitoring.metrics import MetricsCollector

            metrics = MetricsCollector()
            metrics.start_run(run_id)
            hook = SelfImprovingHook()

            with self._run_lock:
                record.status = RunStatus.RUNNING
            self._notify(run_id)
            try:
                result = fn(*args, **kwargs)
                with self._run_lock:
                    record.status = RunStatus.COMPLETED
                    record.result = result
                    record.finished_at = time.time()
                    if isinstance(result, tuple) and len(result) == 2:
                        # Coding runtime returns (report, ledger_dir)
                        report, ledger_dir = result
                        if hasattr(report, "run_id"):
                            record.artifacts = [report.run_id]
                        if isinstance(ledger_dir, Path):
                            record.artifacts.append(str(ledger_dir.name))
                metrics.end_run(run_id)
                hook.on_run_complete(run_id, success=True)
            except Exception as exc:
                logger.exception("Run %s failed", run_id)
                with self._run_lock:
                    record.status = RunStatus.FAILED
                    record.error = str(exc)
                    record.finished_at = time.time()
                metrics.record_error(run_id)
                hook.on_run_complete(run_id, success=False, error=str(exc))
            self._notify(run_id)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return run_id

    def get(self, run_id: str) -> RunRecord | None:
        with self._run_lock:
            return self._runs.get(run_id)

    def list_runs(self) -> list[RunRecord]:
        with self._run_lock:
            return list(self._runs.values())

    def subscribe(self, run_id: str, callback: Callable[[RunRecord], None]) -> None:
        with self._run_lock:
            if run_id in self._subscribers:
                self._subscribers[run_id].append(callback)

    def unsubscribe(self, run_id: str, callback: Callable[[RunRecord], None]) -> None:
        with self._run_lock:
            if run_id in self._subscribers:
                try:
                    self._subscribers[run_id].remove(callback)
                except ValueError:
                    pass

    def _notify(self, run_id: str) -> None:
        with self._run_lock:
            record = self._runs.get(run_id)
            callbacks = list(self._subscribers.get(run_id, []))
        if record is None:
            return
        for cb in callbacks:
            try:
                cb(record)
            except Exception:
                pass

    def log(self, run_id: str, message: str) -> None:
        with self._run_lock:
            record = self._runs.get(run_id)
            if record is not None:
                record.logs.append(message)
        self._notify(run_id)
