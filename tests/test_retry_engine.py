"""Tests for core/retry_engine.py — bounded retry with backoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.error_classification import ErrorCategory
from core.events import EventType
from core.ledger import RunLedger
from core.retry_engine import RetryEngine, RetryExhaustedError


class TestRetryEngineExecute:
    def test_success_no_retry(self, tmp_path: Path) -> None:
        engine = RetryEngine()
        result = engine.execute(lambda: 42)
        assert result == 42

    def test_retry_then_success(self, tmp_path: Path) -> None:
        engine = RetryEngine()
        call_count = 0

        def flaky() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return 42

        result = engine.execute(flaky, max_retries=5, backoff=0.01)
        assert result == 42
        assert call_count == 3

    def test_retry_exhausted(self, tmp_path: Path) -> None:
        engine = RetryEngine()

        def always_fails() -> int:
            raise ConnectionError("transient")

        with pytest.raises(RetryExhaustedError) as exc_info:
            engine.execute(always_fails, max_retries=2, backoff=0.01)

        assert "Failed after 3 attempts" in str(exc_info.value)
        assert isinstance(exc_info.value.last_exception, ConnectionError)

    def test_no_retry_for_fatal(self, tmp_path: Path) -> None:
        engine = RetryEngine()

        def fatal() -> int:
            raise RuntimeError("fatal")

        with pytest.raises(RuntimeError):
            engine.execute(fatal, max_retries=3, backoff=0.01)

    def test_no_retry_for_configuration(self, tmp_path: Path) -> None:
        engine = RetryEngine()

        def bad_config() -> int:
            raise ValueError("config")

        with pytest.raises(ValueError):
            engine.execute(bad_config, max_retries=3, backoff=0.01)

    def test_explicit_error_category_override(self, tmp_path: Path) -> None:
        engine = RetryEngine()
        call_count = 0

        def flaky() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("treated as transient")
            return 42

        result = engine.execute(flaky, max_retries=3, backoff=0.01, error_category=ErrorCategory.TRANSIENT)
        assert result == 42
        assert call_count == 2


class TestRetryEngineWithLedger:
    def test_retry_attempts_emitted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "retry-test")
        engine = RetryEngine(ledger=ledger)
        call_count = 0

        def flaky() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("boom")
            return 42

        engine.execute(flaky, max_retries=5, backoff=0.01, step_id="s1")

        events = ledger.read_ledger()
        retry_events = [e for e in events if e.event_type == EventType.RETRY_ATTEMPTED]
        # 2 retry attempts + 1 success = 3 events
        assert len(retry_events) == 3
        assert retry_events[0].payload["outcome"] == "retry"
        assert retry_events[1].payload["outcome"] == "retry"
        assert retry_events[2].payload["outcome"] == "success"

    def test_retry_exhausted_emitted(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "retry-exhaust")
        engine = RetryEngine(ledger=ledger)

        def always_fails() -> int:
            raise ConnectionError("boom")

        with pytest.raises(RetryExhaustedError):
            engine.execute(always_fails, max_retries=1, backoff=0.01, step_id="s1")

        events = ledger.read_ledger()
        exhausted = [e for e in events if e.event_type == EventType.RETRY_EXHAUSTED]
        assert len(exhausted) == 1
        assert exhausted[0].payload["category"] == "transient"


class TestRetryEngineWithBudget:
    def test_budget_checker_blocks(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "retry-budget")
        engine = RetryEngine(ledger=ledger)
        call_count = 0
        budget_ok = True

        def flaky() -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("boom")
            return 42

        def checker() -> bool:
            return budget_ok

        # First attempt succeeds with budget
        result = engine.execute_with_budget(flaky, budget_checker=checker, max_retries=5, backoff=0.01)
        assert result == 42

    def test_budget_checker_halts(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "retry-budget-halt")
        engine = RetryEngine(ledger=ledger)
        budget_ok = False

        def never_runs() -> int:
            return 42

        def checker() -> bool:
            return budget_ok

        with pytest.raises(RuntimeError, match="Budget exceeded"):
            engine.execute_with_budget(never_runs, budget_checker=checker)
