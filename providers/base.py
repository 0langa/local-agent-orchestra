from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from config.config import AgentModelConfig, ModelRole


# ------------------------------------------------------------------
# Token usage logging (dev-only, writes to .ai-team/tokens.jsonl)
# ------------------------------------------------------------------

def log_token_usage(
    provider: str,
    model: str,
    role: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append a token-usage record to ``.ai-team/tokens.jsonl``.

    Safe to call from any provider.  Silently skips if the directory
    does not exist (e.g. in unit tests).
    """
    log_path = Path(".ai-team") / "tokens.jsonl"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "role": role,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "duration_ms": duration_ms,
        "metadata": metadata or {},
    }
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError:
        pass


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
