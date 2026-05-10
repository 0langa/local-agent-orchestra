"""Shim: model_registry.resolve(role, required_capability)

Delegates to core.model_registry.ModelRegistry until core/ exposes a
standalone `resolve()` function.
"""

from __future__ import annotations

from core.model_registry import ModelDescriptor, ModelRegistry
from config.config import TeamConfig


def resolve(registry: ModelRegistry, role: str, required_capability: str) -> ModelDescriptor:
    """Resolve a role + capability to a model descriptor."""
    return registry.resolve_model(role, required_capability)
