"""Provider map for the coding workflow.

This module lives in workflows/ (not core/) because it encodes
workflow-specific knowledge about which provider backends to use.
"""

from __future__ import annotations

from core.model_registry import ProviderDescriptor


DEFAULT_PROVIDER_MAP: dict[str, ProviderDescriptor] = {
    "openai_compatible": ProviderDescriptor(id="openai_compatible", import_path="providers.openai_v1:OpenAIV1Provider"),
    "openai_v1": ProviderDescriptor(id="openai_v1", import_path="providers.openai_v1:OpenAIV1Provider"),
    "azure_foundry": ProviderDescriptor(id="azure_foundry", import_path="providers.azure_foundry:AzureFoundryProvider"),
    "oci_genai": ProviderDescriptor(id="oci_genai", import_path="providers.oci_genai:OCIGenAIProvider"),
    "aws_bedrock": ProviderDescriptor(id="aws_bedrock", import_path="providers.aws_bedrock:AWSBedrockProvider"),
}
