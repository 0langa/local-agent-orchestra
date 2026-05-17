"""Web UI for Agentheim local dashboard and API.

FastAPI-based product surface for readiness, tasks, runs, tools, workflows, presets, and memory.
"""

from __future__ import annotations

from interfaces.web_ui.app import create_app

__all__ = ["create_app"]
