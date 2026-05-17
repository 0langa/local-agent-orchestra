"""Image processing tool with configurable vision backends."""

from __future__ import annotations

import logging
import os
from typing import Any

from core.tool_protocol import BaseTool, ParamSchema, ReturnSchema, RiskLevel, ToolContext, ToolResult, ToolSchema
from multimodal.protocol import MultimodalProcessor

logger = logging.getLogger(__name__)


def _resolve_processor() -> MultimodalProcessor:
    """Resolve the best available vision processor from environment."""
    provider = os.getenv("AGENTHEIM_VISION_PROVIDER", "auto").lower()

    if provider == "openai" or (provider == "auto" and os.getenv("OPENAI_API_KEY")):
        try:
            from multimodal.openai_vision import OpenAIVisionProcessor
            model = os.getenv("AGENTHEIM_VISION_MODEL", "gpt-4o")
            return OpenAIVisionProcessor(model=model)
        except Exception as exc:
            logger.warning("OpenAI vision processor unavailable: %s", exc)

    if provider == "claude" or (provider == "auto" and os.getenv("ANTHROPIC_API_KEY")):
        try:
            from multimodal.claude_vision import ClaudeVisionProcessor
            model = os.getenv("AGENTHEIM_VISION_MODEL", "claude-3-sonnet-20240229")
            return ClaudeVisionProcessor(model=model)
        except Exception as exc:
            logger.warning("Claude vision processor unavailable: %s", exc)

    if provider == "auto":
        try:
            from config.config import load_team_config, ModelCapability
            team = load_team_config()
            for role, cfg in team.by_role().items():
                caps = [c.lower() for c in (cfg.metadata.get("capabilities") or [])]
                if ModelCapability.VISION.value in caps:
                    from multimodal.generic_openai_vision import GenericOpenAIVisionProcessor
                    return GenericOpenAIVisionProcessor(
                        endpoint=cfg.endpoint,
                        api_key=cfg.api_key,
                        model=cfg.model,
                        headers=cfg.headers,
                    )
        except Exception as exc:
            logger.debug("Auto-resolution via team config failed: %s", exc)

    if provider != "auto":
        logger.warning("Unknown vision provider '%s'", provider)

    raise RuntimeError(
        "Vision is not configured. Set AGENTHEIM_VISION_PROVIDER=openai or claude, "
        "set OPENAI_API_KEY or ANTHROPIC_API_KEY, or configure a provider with vision capability."
    )


class ImageTool(BaseTool):
    """Image analysis tool with configurable vision backend."""

    def __init__(self) -> None:
        schema = ToolSchema(
            description="Analyze images using vision models (OpenAI GPT-4o or Claude 3).",
            parameters={
                "operation": ParamSchema(
                    type="string",
                    description="Operation: describe, ocr",
                    enum=["describe", "ocr"],
                    required=True,
                ),
                "image_b64": ParamSchema(type="string", description="Base64-encoded image", required=True),
            },
            returns=ReturnSchema(type="object", description="Analysis result"),
        )
        super().__init__("multimodal.image", schema, RiskLevel.LOW)
        self._processor: MultimodalProcessor | None = None

    def _get_processor(self) -> MultimodalProcessor:
        if self._processor is None:
            self._processor = _resolve_processor()
        return self._processor

    def invoke(self, params: dict[str, Any], context: ToolContext) -> ToolResult:
        valid, err = self.validate_params(params)
        if not valid:
            return ToolResult(success=False, error=err)

        operation = params.get("operation")
        image_b64 = params.get("image_b64", "")

        try:
            processor = self._get_processor()
            if operation == "describe":
                result = processor.describe_image(image_b64)
                return ToolResult(success=True, data=result)
            if operation == "ocr":
                text = processor.extract_text_from_image(image_b64)
                return ToolResult(success=True, data={"text": text})
        except Exception as exc:
            logger.warning("Image analysis failed: %s", exc)
            return ToolResult(success=False, error=str(exc))

        return ToolResult(success=False, error=f"Unknown operation: {operation}")
