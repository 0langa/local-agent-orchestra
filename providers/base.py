from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from config.config import AgentModelConfig, ModelRole


class ModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: ModelRole
    system_prompt: str | None = None
    user_prompt: str = Field(min_length=1)
    temperature: float = 0.0
    max_output_tokens: int | None = None


class ModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: ModelRole
    model: str
    provider: str
    content: str
    raw: dict[str, Any] | None = None


class ModelProvider(ABC):
    def __init__(self, config: AgentModelConfig) -> None:
        self.config = config

    @abstractmethod
    def invoke(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError
