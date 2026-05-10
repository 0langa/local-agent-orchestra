from __future__ import annotations

import time

from openai import OpenAI

from core.errors import ProviderError
from providers.base import ModelProvider, ModelRequest, ModelResponse


class OpenAIV1Provider(ModelProvider):
    def __init__(self, config):
        super().__init__(config)
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.endpoint,
            timeout=float(config.timeout_seconds),
            default_headers=config.headers or None,
        )

    def invoke(self, request: ModelRequest) -> ModelResponse:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})

        create_kwargs = {
            "model": self.config.model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_output_tokens is not None:
            create_kwargs["max_completion_tokens"] = request.max_output_tokens

        last_error: Exception | None = None
        for delay in (0.0, 1.0, 2.0):
            if delay:
                time.sleep(delay)
            try:
                response = self._client.chat.completions.create(**create_kwargs)
                break
            except Exception as exc:  # pragma: no cover - network/provider dependent
                last_error = exc
        else:  # pragma: no cover - network/provider dependent
            raise ProviderError(f"Model invocation failed after retries: {last_error}") from last_error
        content = response.choices[0].message.content or ""
        return ModelResponse(
            role=request.role,
            model=self.config.model,
            provider=self.config.provider,
            content=content,
            raw=response.model_dump(),
        )
