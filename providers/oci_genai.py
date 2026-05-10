from __future__ import annotations

from providers.base import ModelProvider, ModelRequest, ModelResponse


class OCIGenAIProvider(ModelProvider):
    def invoke(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError("OCI GenAI provider is not implemented yet.")
