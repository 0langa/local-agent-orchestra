from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from config.config import AgentModelConfig
from core.json_repair import repair_json_text
from providers.base import ModelProvider, ModelRequest
from core.schemas_runtime import AgentResult

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class BaseAgent(Generic[SchemaT]):
    def __init__(
        self,
        provider: ModelProvider,
        role_config: AgentModelConfig,
        system_prompt: str,
        output_schema: type[SchemaT],
    ) -> None:
        self.provider = provider
        self.role_config = role_config
        self.system_prompt = system_prompt
        self.output_schema = output_schema

    def run_structured(self, user_prompt: str, max_output_tokens: int | None = None) -> AgentResult:
        raw_output = self._invoke(user_prompt, max_output_tokens=max_output_tokens)
        try:
            parsed = self._parse(raw_output)
            return AgentResult(role=self.role_config.role, success=True, raw_output=raw_output, parsed_output=parsed.model_dump())
        except (ValueError, ValidationError) as first_error:
            repair_prompt = (
                "Your previous output was invalid. Return only valid JSON matching the required schema. "
                f"Previous output:\n{raw_output}"
            )
            repaired_output = self._invoke(repair_prompt, max_output_tokens=max_output_tokens)
            try:
                parsed = self._parse(repaired_output)
                return AgentResult(role=self.role_config.role, success=True, raw_output=repaired_output, parsed_output=parsed.model_dump())
            except (ValueError, ValidationError) as second_error:
                return AgentResult(
                    role=self.role_config.role,
                    success=False,
                    raw_output=repaired_output,
                    error=f"Structured output validation failed after repair attempt: {second_error}; first error: {first_error}",
                )

    def _invoke(self, user_prompt: str, max_output_tokens: int | None = None) -> str:
        request = ModelRequest(
            role=self.role_config.role,
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_output_tokens=max_output_tokens,
        )
        response = self.provider.invoke(request)
        return response.content

    def _parse(self, raw_output: str) -> SchemaT:
        json_text = repair_json_text(raw_output)
        data = json.loads(json_text)
        return self.output_schema.model_validate(data)


def load_prompt(prompt_path: str | Path) -> str:
    return Path(prompt_path).read_text(encoding="utf-8")