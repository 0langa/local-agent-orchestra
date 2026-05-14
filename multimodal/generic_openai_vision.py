"""Generic OpenAI-compatible vision processor (works with Azure, Groq, etc.)."""

from __future__ import annotations

from typing import Any

from multimodal.protocol import MultimodalProcessor


class GenericOpenAIVisionProcessor(MultimodalProcessor):
    """Vision processor using any OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.headers = headers or {}

    def _client(self) -> Any:
        from openai import OpenAI

        return OpenAI(
            api_key=self.api_key,
            base_url=self.endpoint,
            default_headers=self.headers or None,
        )

    def _build_messages(self, prompt: str, image_b64: str) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ]

    def _chat(self, messages: list[dict[str, Any]], max_tokens: int) -> str:
        client = self._client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def describe_image(self, image_b64: str) -> dict[str, Any]:
        messages = self._build_messages("Describe this image in detail.", image_b64)
        description = self._chat(messages, max_tokens=1000)
        return {
            "description": description,
            "model": self.model,
            "provider": self.endpoint,
        }

    def extract_text_from_image(self, image_b64: str) -> str:
        messages = self._build_messages(
            "Extract all text from this image. Return only the text.", image_b64
        )
        return self._chat(messages, max_tokens=2000)
