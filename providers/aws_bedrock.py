from __future__ import annotations

from providers.base import ModelProvider, ModelRequest, ModelResponse


class AWSBedrockProvider(ModelProvider):
    def invoke(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError("AWS Bedrock provider is not implemented yet.")
