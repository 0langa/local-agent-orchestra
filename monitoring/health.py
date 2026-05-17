"""Health checks for system components."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from providers import list_providers


@dataclass
class HealthStatus:
    component: str
    healthy: bool
    message: str


class HealthReporter:
    """Reports health status of system components."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()

    def check_disk_space(self, min_gb: float = 1.0) -> HealthStatus:
        usage = shutil.disk_usage(self.repo_root)
        free_gb = usage.free / (1024 ** 3)
        healthy = free_gb >= min_gb
        return HealthStatus(
            component="disk",
            healthy=healthy,
            message=f"{free_gb:.1f} GB free" if healthy else f"Only {free_gb:.1f} GB free (need {min_gb} GB)",
        )

    def check_memory(self) -> HealthStatus:
        try:
            import psutil

            mem = psutil.virtual_memory()
            healthy = mem.available > 512 * 1024 * 1024  # 512 MB
            return HealthStatus(
                component="memory",
                healthy=healthy,
                message=f"{mem.available // (1024 ** 2)} MB available",
            )
        except ImportError:
            return HealthStatus(component="memory", healthy=False, message="psutil not installed; install with: pip install psutil")

    def check_providers(self) -> list[HealthStatus]:
        """Basic provider health (imports successfully)."""
        statuses = []
        for name in list_providers():
            try:
                module_name = f"providers.{name}"
                __import__(module_name)
                statuses.append(HealthStatus(component=f"provider:{name}", healthy=True, message="import ok"))
            except Exception as exc:
                statuses.append(HealthStatus(component=f"provider:{name}", healthy=False, message=str(exc)))
        return statuses

    def full_report(self) -> dict[str, Any]:
        report = {
            "disk": self.check_disk_space(),
            "memory": self.check_memory(),
            "providers": self.check_providers(),
        }
        all_healthy = report["disk"].healthy and report["memory"].healthy
        report["overall_healthy"] = all_healthy
        return report
