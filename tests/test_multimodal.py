from __future__ import annotations

from multimodal import ImageTool
from multimodal.protocol import MultimodalProcessor


class FakeMultimodalProcessor:
    def test_describe_image(self) -> None:
        p = FakeMultimodalProcessor()
        result = p.describe_image("fakeb64")
        assert result["description"] == "fake description"
        assert result["confidence"] == 1.0

    def test_extract_text(self) -> None:
        p = FakeMultimodalProcessor()
        text = p.extract_text_from_image("fakeb64")
        assert text == "fake text"

    def describe_image(self, image_b64: str, prompt: str | None = None) -> dict:
        return {"description": "fake description", "confidence": 1.0}

    def extract_text_from_image(self, image_b64: str) -> str:
        return "fake text"


class TestImageTool:
    def test_tool_id(self) -> None:
        tool = ImageTool()
        assert tool.tool_id == "multimodal.image"

    def test_describe_operation(self) -> None:
        from core.tool_protocol import ToolContext

        tool = ImageTool()
        tool._processor = FakeMultimodalProcessor()
        result = tool.invoke({"operation": "describe", "image_b64": "abc"}, ToolContext())
        assert result.success is True
        assert result.data["description"] == "fake description"

    def test_ocr_operation(self) -> None:
        from core.tool_protocol import ToolContext

        tool = ImageTool()
        tool._processor = FakeMultimodalProcessor()
        result = tool.invoke({"operation": "ocr", "image_b64": "abc"}, ToolContext())
        assert result.success is True
        assert result.data["text"] == "fake text"

    def test_invalid_operation(self) -> None:
        from core.tool_protocol import ToolContext

        tool = ImageTool()
        result = tool.invoke({"operation": "invalid", "image_b64": "abc"}, ToolContext())
        assert result.success is False
        assert "Unknown operation" in result.error

    def test_unconfigured_vision_returns_failure(self, monkeypatch) -> None:
        from core.tool_protocol import ToolContext

        monkeypatch.setenv("AGENTHEIM_VISION_PROVIDER", "unknown")
        tool = ImageTool()
        result = tool.invoke({"operation": "describe", "image_b64": "abc"}, ToolContext())
        assert result.success is False
        assert "Vision is not configured" in result.error
