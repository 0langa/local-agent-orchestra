from __future__ import annotations

from multimodal import ImageTool
from multimodal.image import StubMultimodalProcessor
from multimodal.protocol import MultimodalProcessor


class TestStubMultimodalProcessor:
    def test_describe_image(self) -> None:
        p = StubMultimodalProcessor()
        result = p.describe_image("fakeb64")
        assert "not configured" in result["description"]
        assert result["confidence"] == 0.0

    def test_extract_text(self) -> None:
        p = StubMultimodalProcessor()
        text = p.extract_text_from_image("fakeb64")
        assert "not configured" in text


class TestImageTool:
    def test_tool_id(self) -> None:
        tool = ImageTool()
        assert tool.tool_id == "multimodal.image"

    def test_describe_operation(self) -> None:
        from core.tool_protocol import ToolContext

        tool = ImageTool()
        tool._processor = StubMultimodalProcessor()
        result = tool.invoke({"operation": "describe", "image_b64": "abc"}, ToolContext())
        assert result.success is True
        assert "not configured" in result.data["description"]

    def test_ocr_operation(self) -> None:
        from core.tool_protocol import ToolContext

        tool = ImageTool()
        tool._processor = StubMultimodalProcessor()
        result = tool.invoke({"operation": "ocr", "image_b64": "abc"}, ToolContext())
        assert result.success is True
        assert "not configured" in result.data["text"]

    def test_invalid_operation(self) -> None:
        from core.tool_protocol import ToolContext

        tool = ImageTool()
        result = tool.invoke({"operation": "invalid", "image_b64": "abc"}, ToolContext())
        assert result.success is False
        assert "Unknown operation" in result.error
