from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestStateMachineNegative:
    def test_invalid_transition_raises(self) -> None:
        from core.state_machine import RuntimeState, RuntimeStateMachine

        sm = RuntimeStateMachine()
        with pytest.raises(Exception) as exc_info:
            sm.transition(RuntimeState.DONE)
        assert "Invalid state transition" in str(exc_info.value)

    def test_valid_transition_succeeds(self) -> None:
        from core.state_machine import RuntimeState, RuntimeStateMachine

        sm = RuntimeStateMachine()
        sm.transition(RuntimeState.LOAD_CONFIG)
        assert sm.current == RuntimeState.LOAD_CONFIG
        assert RuntimeState.INIT in sm.history
        assert RuntimeState.LOAD_CONFIG in sm.history

    def test_transition_emits_state_transition_event(self, tmp_path: Path) -> None:
        from core.state_machine import RuntimeState, RuntimeStateMachine
        from core.ledger import RunLedger
        from core.events import EventType

        ledger = RunLedger.create(tmp_path, "sm-test")
        sm = RuntimeStateMachine(ledger=ledger)
        sm.transition(RuntimeState.LOAD_CONFIG, {"reason": "test"})

        events = ledger.read_ledger()
        state_events = [e for e in events if e.event_type == EventType.STATE_TRANSITION]
        assert len(state_events) == 2  # INIT + LOAD_CONFIG
        assert state_events[1].payload["state"] == "LOAD_CONFIG"
        assert state_events[1].payload["reason"] == "test"

    def test_legacy_state_transitions_jsonl_still_written(self, tmp_path: Path) -> None:
        from core.state_machine import RuntimeState, RuntimeStateMachine
        from core.ledger import RunLedger

        ledger = RunLedger.create(tmp_path, "sm-legacy-test")
        sm = RuntimeStateMachine(ledger=ledger)
        sm.transition(RuntimeState.LOAD_CONFIG)

        legacy_path = ledger.run_dir / "state_transitions.jsonl"
        assert legacy_path.exists()
        lines = [line.strip() for line in legacy_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2
        import json
        assert json.loads(lines[1])["state"] == "LOAD_CONFIG"


class TestCodingRuntimeNegative:
    def test_plan_task_raises_on_invalid_output(self, tmp_path: Path) -> None:
        from workflows.coding.runtime import plan_task, PlanningError

        with (
            patch(
                "workflows.coding.runtime.create_orchestrator_agent"
            ) as mock_create,
            patch(
                "workflows.coding.runtime._resolve_context_pack",
                return_value=("ctx", False),
            ),
        ):
            mock_agent = MagicMock()
            mock_agent.run_structured.return_value = MagicMock(
                success=False, parsed_output=None, error="Model refused"
            )
            mock_create.return_value = mock_agent
            with pytest.raises(PlanningError) as exc_info:
                plan_task("test", tmp_path)
            assert "Model refused" in str(exc_info.value)

    def test_run_task_raises_on_dirty_repo(self, tmp_path: Path) -> None:
        from workflows.coding.runtime import run_task, ExecutionError
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )
        (tmp_path / "dirty.txt").write_text("x")
        subprocess.run(["git", "add", "dirty.txt"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
        (tmp_path / "dirty.txt").write_text("dirty")

        with pytest.raises(ExecutionError) as exc_info:
            run_task("test", tmp_path)
        assert "uncommitted changes" in str(exc_info.value).lower()

    def test_run_task_allow_dirty_bypasses_block(self, tmp_path: Path) -> None:
        from workflows.coding.runtime import run_task, ExecutionError
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, capture_output=True)
        (tmp_path / "dirty.txt").write_text("x")

        with patch("workflows.coding.runtime.create_orchestrator_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.run_structured.return_value = MagicMock(
                success=False, parsed_output=None, error="Planning failed", raw_output=""
            )
            mock_create.return_value = mock_agent
            with pytest.raises(ExecutionError, match="Planning failed"):
                run_task("test", tmp_path, allow_dirty=True)

    def test_run_task_raises_on_planning_failure(self, tmp_path: Path) -> None:
        from workflows.coding.runtime import run_task, ExecutionError
        import subprocess

        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, capture_output=True)

        with patch(
            "workflows.coding.runtime.create_orchestrator_agent"
        ) as mock_create:
            mock_agent = MagicMock()
            mock_agent.run_structured.return_value = MagicMock(
                success=False, parsed_output=None, error="Planning failed", raw_output=""
            )
            mock_create.return_value = mock_agent
            with pytest.raises(ExecutionError) as exc_info:
                run_task("test", tmp_path, allow_dirty=True)
            assert "Planning failed" in str(exc_info.value)


class TestFilesystemToolNegative:
    def test_copy_overwrite_blocked(self, tmp_path: Path) -> None:
        from tools.filesystem import FilesystemTool
        from core.tool_protocol import ToolContext

        tool = FilesystemTool(repo_root=tmp_path)
        ctx = ToolContext()
        (tmp_path / "src.txt").write_text("src")
        (tmp_path / "dst.txt").write_text("dst")
        result = tool.invoke(
            {"operation": "copy", "path": "src.txt", "destination": "dst.txt"},
            ctx,
        )
        assert result.success is False
        assert "already exists" in result.error.lower()

    def test_copy_path_escape_blocked(self, tmp_path: Path) -> None:
        from tools.filesystem import FilesystemTool
        from core.tool_protocol import ToolContext

        tool = FilesystemTool(repo_root=tmp_path)
        ctx = ToolContext()
        result = tool.invoke(
            {"operation": "copy", "path": "../escape.txt", "destination": "dst.txt"},
            ctx,
        )
        assert result.success is False
        assert "escapes" in result.error.lower()


class TestModelRegistryNegative:
    def test_resolve_model_not_found(self) -> None:
        from core.model_registry import ModelRegistry, ProviderDescriptor
        from config.config import ModelRole

        registry = ModelRegistry(
            providers={"p": ProviderDescriptor(id="p", import_path="x")},
            models={},
        )
        with pytest.raises(Exception) as exc_info:
            registry.resolve_model(ModelRole.PLANNER, required_capability="plan")
        assert "no model" in str(exc_info.value).lower()
