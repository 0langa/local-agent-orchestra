from __future__ import annotations

from providers.base import ModelProvider, ModelRequest, ModelResponse


class OCIGenAIProvider(ModelProvider):
    def invoke(self, request: ModelRequest) -> ModelResponse:
        self.validate_request(request)
        from agentheim.vendor.aictx.llm.oci_genai import OCIGenAIProvider as _AictxOCI
        from agentheim.vendor.aictx.llm.base import ChatRequest

        aictx_provider = _AictxOCI(
            compartment_id=None,
            model_id=self.config.model,
            temperature=request.temperature,
        )

        chat_request = ChatRequest(
            system_prompt=request.system_prompt or "",
            messages=[{"role": "user", "content": request.user_prompt}],
            temperature=request.temperature,
            max_output_tokens=request.max_output_tokens or 4096,
        )

        chat_response = aictx_provider.chat(chat_request)

        return ModelResponse(
            role=request.role,
            model=self.config.model,
            provider="oci_genai",
            content=chat_response.content,
            raw={
                "input_tokens": chat_response.input_tokens,
                "output_tokens": chat_response.output_tokens,
                "finish_reason": chat_response.finish_reason,
            },
        )
