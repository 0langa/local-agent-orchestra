from __future__ import annotations

import time
from typing import Any

import requests

from core.errors import ProviderError
from providers.base import ModelProvider, ModelRequest, ModelResponse


class GeminiProvider(ModelProvider):
    def invoke(self, request: ModelRequest) -> ModelResponse:
        self.validate_request(request)
        parts: list[dict[str, Any]] = [{"text": request.user_prompt}]
        for part in request.content:
            if part.type == "text" and part.text:
                parts.append({"text": part.text})
            elif part.type == "image_url" and part.image_url:
                parts.append({"file_data": {"file_uri": part.image_url}})

        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": request.temperature},
        }
        if request.max_output_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = request.max_output_tokens
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}

        url = f"{self.config.endpoint.rstrip('/')}/v1beta/models/{self.config.model}:generateContent"
        headers = {"x-goog-api-key": self.config.api_key, **self.config.headers}
        last_error: Exception | None = None
        for delay in (0.0, 1.0, 2.0):
            if delay:
                time.sleep(delay)
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout_seconds)
                response.raise_for_status()
                raw = response.json()
                break
            except Exception as exc:  # pragma: no cover - network/provider dependent
                last_error = exc
        else:  # pragma: no cover - network/provider dependent
            raise ProviderError(f"Gemini invocation failed after retries: {last_error}") from last_error

        content = ""
        for candidate in raw.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                content += part.get("text", "")
        return ModelResponse(role=request.role, model=self.config.model, provider=self.config.provider, content=content, raw=raw)


class VertexAIProvider(ModelProvider):
    def invoke(self, request: ModelRequest) -> ModelResponse:
        self.validate_request(request)
        try:
            import google.auth
            from google.auth.transport.requests import Request
        except ImportError as exc:
            raise ImportError("Vertex AI provider requires google-auth. Install google-auth and configure ADC.") from exc

        credentials, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(Request())
        location = self.config.metadata.get("location", "us-central1")
        project_id = self.config.metadata.get("project_id") or project
        if not project_id:
            raise ProviderError("Vertex AI provider requires ADC project or metadata.project_id.")
        endpoint = self.config.endpoint
        if endpoint == "-":
            endpoint = f"https://{location}-aiplatform.googleapis.com"
        parts: list[dict[str, Any]] = [{"text": request.user_prompt}]
        for part in request.content:
            if part.type == "text" and part.text:
                parts.append({"text": part.text})
            elif part.type == "image_url" and part.image_url:
                parts.append({"file_data": {"file_uri": part.image_url}})
        payload: dict[str, Any] = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"temperature": request.temperature}}
        if request.max_output_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = request.max_output_tokens
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        url = f"{endpoint.rstrip('/')}/v1/projects/{project_id}/locations/{location}/publishers/google/models/{self.config.model}:generateContent"
        headers = {"Authorization": f"Bearer {credentials.token}", **self.config.headers}
        response = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        raw = response.json()
        content = ""
        for candidate in raw.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                content += part.get("text", "")
        return ModelResponse(role=request.role, model=self.config.model, provider=self.config.provider, content=content, raw=raw)
