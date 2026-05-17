from __future__ import annotations

import time

from monitoring import HealthReporter, MetricsCollector


class TestMetricsCollector:
    def test_start_and_end_run(self) -> None:
        m = MetricsCollector()
        m.start_run("r1")
        time.sleep(0.01)
        m.end_run("r1")
        data = m.get_run_metrics("r1")
        assert data is not None
        assert data["run_id"] == "r1"
        assert data["duration_seconds"] > 0

    def test_record_tool_call(self) -> None:
        m = MetricsCollector()
        m.start_run("r1")
        m.record_tool_call("r1")
        m.record_tool_call("r1")
        data = m.get_run_metrics("r1")
        assert data["tool_calls"] == 2

    def test_record_error(self) -> None:
        m = MetricsCollector()
        m.start_run("r1")
        m.record_error("r1")
        data = m.get_run_metrics("r1")
        assert data["errors"] == 1

    def test_record_tokens(self) -> None:
        m = MetricsCollector()
        m.start_run("r1")
        m.record_tokens("r1", 150)
        data = m.get_run_metrics("r1")
        assert data["token_usage"] == 150

    def test_prometheus_export(self) -> None:
        m = MetricsCollector()
        m.start_run("r1")
        m.record_tool_call("r1")
        m.record_error("r1")
        prom = m.get_prometheus_metrics()
        assert "agent_runs_total" in prom
        assert "agent_tool_calls_total" in prom
        assert "agent_errors_total" in prom

    def test_missing_run_returns_none(self) -> None:
        m = MetricsCollector()
        assert m.get_run_metrics("nonexistent") is None


class TestHealthReporter:
    def test_disk_space(self, tmp_path: Path) -> None:
        h = HealthReporter(repo_root=tmp_path)
        status = h.check_disk_space(min_gb=0.001)
        assert status.component == "disk"
        assert status.healthy is True
        assert "GB free" in status.message

    def test_memory(self, tmp_path: Path) -> None:
        h = HealthReporter(repo_root=tmp_path)
        status = h.check_memory()
        assert status.component == "memory"
        # May be True or False depending on psutil and actual memory
        assert "MB available" in status.message or "psutil not installed" in status.message

    def test_providers(self, tmp_path: Path) -> None:
        h = HealthReporter(repo_root=tmp_path)
        statuses = h.check_providers()
        assert len(statuses) >= 4
        provider_ids = {s.component for s in statuses}
        assert "provider:openai_v1" in provider_ids
        assert "provider:gemini" in provider_ids

    def test_full_report(self, tmp_path: Path) -> None:
        h = HealthReporter(repo_root=tmp_path)
        report = h.full_report()
        assert "disk" in report
        assert "memory" in report
        assert "providers" in report
        assert "overall_healthy" in report
