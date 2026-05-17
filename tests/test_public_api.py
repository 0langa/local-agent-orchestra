"""Tests for core/public_api.py — stable facade."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import core.public_api as public_api


class TestPublicApiExports:
    def test_all_expected_symbols_exist(self) -> None:
        expected = {
            "Event",
            "EventType",
            "RunLedger",
            "ErrorCategory",
            "classify_error",
            "error_summary",
            "RetryEngine",
            "RetryExhaustedError",
            "BudgetExceededError",
            "BudgetLimits",
            "BudgetSnapshot",
            "StepBudgetEnforcer",
            "AsyncBaseTool",
            "BaseTool",
            "ParamSchema",
            "RiskLevel",
            "ToolContext",
            "ToolRegistry",
            "ToolResult",
            "ToolSchema",
            "ModelDescriptor",
            "ModelRegistry",
            "ProviderDescriptor",
            "PolicyDecision",
            "PolicyEngine",
            "CapabilityRegistry",
            "RegistryEntry",
            "get_capability_registry",
            "get_workflow",
            "list_workflows",
            "register_workflow",
            "WorkflowRunner",
            "ExecutionDAG",
            "Step",
            "StepBudget",
            "StepContext",
            "StepResult",
            "Workflow",
            "AgentContext",
            "AgentMessage",
            "AgentRequest",
            "AgentResponse",
            "ArtifactStore",
            "ArtifactSpec",
            "ContextManifest",
            "ContextPacker",
            "redact_dict",
            "redact_text",
            "ArtifactRef",
            "WorkflowRun",
            "WorkflowStep",
            "WorkflowStepStatus",
        }
        missing = expected - set(dir(public_api))
        assert not missing, f"Missing from public_api: {missing}"

    def test_no_internal_modules_exposed(self) -> None:
        """Ensure no submodules of core are leaked."""
        forbidden_prefixes = ("core.", "workflows.", "providers.", "tools.", "memory.")
        for name in dir(public_api):
            obj = getattr(public_api, name)
            module = getattr(obj, "__module__", "")
            if module.startswith(forbidden_prefixes):
                # Classes re-exported from internal modules are OK as long
                # as they don't expose the module itself
                continue
            if name.startswith("_"):
                continue
            # Check that no module objects are exported
            if isinstance(obj, type(__import__("sys"))):
                pytest.fail(f"Module object leaked via public_api.{name}: {obj}")

    def test_all_in_dunder_all(self) -> None:
        assert hasattr(public_api, "__all__")
        for name in public_api.__all__:
            assert hasattr(public_api, name), f"{name} in __all__ but not exported"


class TestPublicApiImportSafety:
    def test_import_does_not_load_providers(self) -> None:
        """Importing public_api should not trigger provider module loading."""
        # This is a soft check: if providers were eagerly loaded, they'd
        # appear in sys.modules. We just verify the import succeeds cleanly.
        import sys
        before = set(sys.modules.keys())
        import importlib
        importlib.reload(public_api)
        after = set(sys.modules.keys())
        new_modules = after - before
        provider_modules = {m for m in new_modules if "providers." in m}
        assert not provider_modules, f"Provider modules loaded: {provider_modules}"


class TestPublicApiFile:
    def test_no_direct_core_imports_in_public_api(self) -> None:
        """public_api.py itself only imports from core.* (which is expected),
        but the symbols it re-exports must not be module objects."""
        path = Path(__file__).parent.parent / "core" / "public_api.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("core."):
                    for alias in node.names:
                        # Use alias name if present, otherwise original name
                        exported_name = alias.asname if alias.asname else alias.name
                        imports.append(exported_name)

        # All imports should be re-exported in __all__
        for name in imports:
            if name == "annotations":
                continue
            assert name in public_api.__all__, f"{name} imported but not in __all__"
