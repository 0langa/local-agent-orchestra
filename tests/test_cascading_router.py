"""Tests for core/cascading_router.py — cascading model router with fallbacks."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.cascading_router import CascadingRouter, ModelBinding
from core.events import EventType
from core.ledger import RunLedger
from core.model_registry import ModelDescriptor, ModelRegistry
from core.tool_protocol import RiskLevel


def _make_registry() -> ModelRegistry:
    """Build a registry with two coder models."""
    from config.config import AgentModelConfig, ModelRole

    providers = {}
    models = {
        "gpt-4": ModelDescriptor(
            id="gpt-4",
            role="planner",
            capabilities=frozenset({"code_generation", "refactoring"}),
            config=AgentModelConfig(
                role=ModelRole.PLANNER,
                provider="openai",
                provider_type="openai_v1",
                endpoint="https://api.openai.com",
                api_key="sk-test",
                model="gpt-4",
            ),
        ),
        "claude-3": ModelDescriptor(
            id="claude-3",
            role="planner",
            capabilities=frozenset({"code_generation", "analysis"}),
            config=AgentModelConfig(
                role=ModelRole.PLANNER,
                provider="anthropic",
                provider_type="anthropic_v1",
                endpoint="https://api.anthropic.com",
                api_key="sk-test",
                model="claude-3",
            ),
        ),
    }
    return ModelRegistry(providers=providers, models=models)


class TestModelBinding:
    def test_frozen(self) -> None:
        m = ModelDescriptor(id="x", role="r", capabilities=frozenset(), config=None)
        binding = ModelBinding(primary=m)
        with pytest.raises(Exception):
            binding.primary = m


class TestCascadingRouterResolve:
    def test_resolve_single_candidate(self) -> None:
        registry = _make_registry()
        router = CascadingRouter(registry)
        binding = router.resolve("planner", "code_generation")
        assert binding.primary.id in {"gpt-4", "claude-3"}
        # The other model should be a fallback if healthy
        fallback_ids = {f.id for f in binding.fallbacks}
        assert len(fallback_ids) == 1
        assert fallback_ids != {binding.primary.id}

    def test_resolve_no_match_raises(self) -> None:
        registry = _make_registry()
        router = CascadingRouter(registry)
        with pytest.raises(ValueError):
            router.resolve("coder", "image_generation")

    def test_resolve_emits_model_selected(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-router")
        registry = _make_registry()
        router = CascadingRouter(registry, ledger=ledger)
        router.resolve("planner", "code_generation")

        events = ledger.read_ledger()
        selected = [e for e in events if e.event_type == EventType.MODEL_SELECTED]
        assert len(selected) == 1
        assert selected[0].payload["role"] == "planner"
        assert selected[0].payload["capability"] == "code_generation"


class TestCascadingRouterHealth:
    def test_mark_unhealthy_excludes_from_fallbacks(self) -> None:
        registry = _make_registry()
        router = CascadingRouter(registry)
        binding = router.resolve("planner", "code_generation")
        # Mark primary unhealthy
        router.mark_unhealthy(binding.primary.id)
        binding2 = router.resolve("planner", "code_generation")
        # The previously-primary model should no longer appear in fallbacks
        if binding2.primary.id != binding.primary.id:
            assert binding.primary.id not in {f.id for f in binding2.fallbacks}

    def test_health_ttl_expires(self) -> None:
        registry = _make_registry()
        router = CascadingRouter(registry, health_ttl_seconds=0.0)
        binding = router.resolve("planner", "code_generation")
        router.mark_unhealthy(binding.primary.id)
        # With TTL=0, health should immediately expire
        assert router.is_healthy(binding.primary.id) is True


class TestCascadingRouterInvoke:
    def test_invoke_primary_succeeds(self) -> None:
        registry = _make_registry()
        router = CascadingRouter(registry)
        binding = router.resolve("planner", "code_generation")

        def fn(model: ModelDescriptor) -> str:
            return f"ok-{model.id}"

        result = router.invoke_with_fallback(binding, fn)
        assert result.startswith("ok-")

    def test_fallback_on_transient_error(self, tmp_path: Path) -> None:
        ledger = RunLedger.create(tmp_path, "test-fallback")
        registry = _make_registry()
        router = CascadingRouter(registry, ledger=ledger)
        binding = router.resolve("planner", "code_generation")

        call_count = 0

        def fn(model: ModelDescriptor) -> str:
            nonlocal call_count
            call_count += 1
            if model.id == binding.primary.id:
                raise ConnectionError("transient")
            return f"fallback-{model.id}"

        result = router.invoke_with_fallback(binding, fn)
        assert result.startswith("fallback-")
        assert call_count == 2

        events = ledger.read_ledger()
        fallback_events = [e for e in events if e.event_type == EventType.FALLBACK_USED]
        assert len(fallback_events) == 1
        assert fallback_events[0].payload["from_model"] == binding.primary.id

    def test_non_transient_error_raises_immediately(self) -> None:
        registry = _make_registry()
        router = CascadingRouter(registry)
        binding = router.resolve("planner", "code_generation")

        def fn(model: ModelDescriptor) -> str:
            raise ValueError("configuration error")

        with pytest.raises(ValueError):
            router.invoke_with_fallback(binding, fn)

    def test_all_models_failed_raises(self) -> None:
        registry = _make_registry()
        router = CascadingRouter(registry)
        binding = router.resolve("planner", "code_generation")

        def fn(model: ModelDescriptor) -> str:
            raise ConnectionError("transient")

        with pytest.raises(ConnectionError):
            router.invoke_with_fallback(binding, fn)
