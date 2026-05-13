"""AWS Bedrock native provider using the Converse API.

Requires ``boto3``. Install via ``pip install agentheim[aws]``.

The provider reads AWS credentials and region from standard boto3
sources: env vars (``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``,
``AWS_REGION`` / ``AWS_DEFAULT_REGION``), ``~/.aws/credentials``, or
IAM role.  The Bedrock model ID is taken from ``self.config.model``.
"""

from __future__ import annotations

from typing import Any

from providers.base import ModelProvider, ModelRequest, ModelResponse, log_token_usage


class AWSBedrockProvider(ModelProvider):
    """Native AWS Bedrock provider via boto3 Converse API."""

    def invoke(self, request: ModelRequest) -> ModelResponse:
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:
            raise ImportError(
                "AWS Bedrock provider requires boto3. "
                "Install: pip install agentheim[aws]"
            ) from exc

        region = self._resolve_region()
        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=BotoConfig(connect_timeout=10, read_timeout=self.config.timeout_seconds),
        )

        # Bedrock Converse API: system prompt goes in separate 'system' param,
        # messages array only contains 'user' and 'assistant' roles.
        system_prompts: list[dict[str, Any]] | None = None
        if request.system_prompt:
            system_prompts = [{"text": request.system_prompt}]

        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": request.user_prompt}]},
        ]

        inference_config: dict[str, Any] = {}
        if request.temperature is not None:
            inference_config["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            inference_config["maxTokens"] = request.max_output_tokens

        try:
            kwargs: dict[str, Any] = {
                "modelId": self.config.model,
                "messages": messages,
            }
            if system_prompts:
                kwargs["system"] = system_prompts
            if inference_config:
                kwargs["inferenceConfig"] = inference_config
            response = client.converse(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"Bedrock Converse API error: {exc}") from exc

        content = ""
        if "output" in response and "message" in response["output"]:
            msg = response["output"]["message"]
            for block in msg.get("content", []):
                content += block.get("text", "")

        usage = response.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        raw = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": usage.get("totalTokens", 0),
            "region": region,
            "model_id": self.config.model,
        }

        log_token_usage(
            provider="aws_bedrock",
            model=self.config.model,
            role=request.role.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            metadata={"region": region},
        )

        return ModelResponse(
            role=request.role,
            model=self.config.model,
            provider="aws_bedrock",
            content=content,
            raw=raw,
        )

    def _resolve_region(self) -> str:
        """Return AWS region from config headers, env, or fallback."""
        import os

        # Config-level override via headers_json
        region = self.config.headers.get("aws-region", "")
        if region:
            return region

        # Standard env vars
        for env_name in ("AWS_REGION", "AWS_DEFAULT_REGION"):
            val = os.getenv(env_name, "").strip()
            if val:
                return val

        # Fallback — Bedrock is not available in all regions;
        # eu-central-1 is a common default for European users.
        return "eu-central-1"
