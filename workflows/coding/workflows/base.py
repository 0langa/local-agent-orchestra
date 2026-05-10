from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from workflows.coding.agents.base import BaseAgent, load_prompt
from core.model_registry import ModelRegistry

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class AgentSpec:
    role: str
    capability: str
    prompt_path: Path


def build_agent(
    registry: ModelRegistry,
    spec: AgentSpec,
    output_schema: type[SchemaT],
) -> BaseAgent[SchemaT]:
    model = registry.resolve_model(spec.role, spec.capability)
    provider = registry.create_provider(model.config)
    return BaseAgent(
        provider=provider,
        role_config=model.config,
        system_prompt=load_prompt(spec.prompt_path),
        output_schema=output_schema,
    )
