"""Tests for the background run executor."""

from __future__ import annotations

import time

from core.run_executor import RunExecutor, RunStatus


class TestRunExecutor:
    def test_submit_returns_run_id(self) -> None:
        RunExecutor.reset_instance()
        executor = RunExecutor()
        run_id = executor.submit(lambda: "result")
        assert isinstance(run_id, str)
        assert len(run_id) > 0
        RunExecutor.reset_instance()

    def test_get_returns_record(self) -> None:
        RunExecutor.reset_instance()
        executor = RunExecutor()
        run_id = executor.submit(lambda: "result")
        record = executor.get(run_id)
        assert record is not None
        assert record.run_id == run_id
        RunExecutor.reset_instance()

    def test_run_completes(self) -> None:
        RunExecutor.reset_instance()
        executor = RunExecutor()
        run_id = executor.submit(lambda: "done")
        # Wait for completion
        for _ in range(50):
            record = executor.get(run_id)
            if record and record.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                break
            time.sleep(0.1)
        record = executor.get(run_id)
        assert record is not None
        assert record.status == RunStatus.COMPLETED
        assert record.result == "done"
        RunExecutor.reset_instance()

    def test_run_failure(self) -> None:
        RunExecutor.reset_instance()
        executor = RunExecutor()

        def _fail():
            raise ValueError("boom")

        run_id = executor.submit(_fail)
        for _ in range(50):
            record = executor.get(run_id)
            if record and record.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                break
            time.sleep(0.1)
        record = executor.get(run_id)
        assert record is not None
        assert record.status == RunStatus.FAILED
        assert "boom" in record.error
        RunExecutor.reset_instance()

    def test_hooks_called(self) -> None:
        RunExecutor.reset_instance()
        executor = RunExecutor()

        calls: list[str] = []

        class DummyHook:
            def start_run(self, run_id: str) -> None:
                calls.append("start")

            def end_run(self, run_id: str) -> None:
                calls.append("end")

            def record_error(self, run_id: str) -> None:
                calls.append("error")

            def on_run_complete(self, run_id: str, success: bool, error: str | None = None) -> None:
                calls.append(f"complete:{success}")

        hook = DummyHook()
        executor.add_hook(hook)
        # Idempotent: adding same hook twice should not duplicate
        executor.add_hook(hook)

        run_id = executor.submit(lambda: "ok")
        for _ in range(50):
            record = executor.get(run_id)
            if record and record.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                break
            time.sleep(0.1)

        assert calls == ["start", "end", "complete:True"]
        RunExecutor.reset_instance()

    def test_hook_failure_does_not_break_run(self) -> None:
        RunExecutor.reset_instance()
        executor = RunExecutor()

        class BrokenHook:
            def start_run(self, run_id: str) -> None:
                raise RuntimeError("broken")

            def end_run(self, run_id: str) -> None:
                pass

            def record_error(self, run_id: str) -> None:
                pass

            def on_run_complete(self, run_id: str, success: bool, error: str | None = None) -> None:
                pass

        executor.add_hook(BrokenHook())
        run_id = executor.submit(lambda: "ok")
        for _ in range(50):
            record = executor.get(run_id)
            if record and record.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                break
            time.sleep(0.1)
        record = executor.get(run_id)
        assert record is not None
        assert record.status == RunStatus.COMPLETED
        RunExecutor.reset_instance()
