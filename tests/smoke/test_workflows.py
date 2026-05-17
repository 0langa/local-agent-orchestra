from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.config import AgentModelConfig, ModelRole
from core.ledger import RunLedger
from core.model_registry import ModelDescriptor, ModelRegistry, ProviderDescriptor
from core.policy_engine import PolicyEngine
from core.tool_protocol import ToolRegistry


def _make_model_registry() -> ModelRegistry:
    """Build a ModelRegistry with default-capability models for all workflows."""
    providers = {
        "openai": ProviderDescriptor(id="openai", import_path="providers.openai_v1:OpenAIV1Provider"),
    }

    def _config(role: ModelRole, model: str = "test-model") -> AgentModelConfig:
        return AgentModelConfig(
            role=role,
            provider="openai",
            provider_type="openai_v1",
            endpoint="http://test",
            api_key="test-key",
            model=model,
        )

    models = {
        "planner": ModelDescriptor(id="planner", role="planner", capabilities=frozenset(["plan", "reasoning", "json"]), config=_config(ModelRole.PLANNER)),
        "executor": ModelDescriptor(id="executor", role="executor", capabilities=frozenset(["code_edit", "json"]), config=_config(ModelRole.EXECUTOR)),
        "verifier": ModelDescriptor(id="verifier", role="verifier", capabilities=frozenset(["verify", "json"]), config=_config(ModelRole.VERIFIER)),
        "gatherer": ModelDescriptor(id="gatherer", role="gatherer", capabilities=frozenset(["web_search", "fetch", "json"]), config=_config(ModelRole.GATHERER)),
        "summarizer": ModelDescriptor(id="summarizer", role="summarizer", capabilities=frozenset(["summarize", "compare", "json"]), config=_config(ModelRole.SUMMARIZER)),
        "reporter": ModelDescriptor(id="reporter", role="reporter", capabilities=frozenset(["report", "synthesize", "json"]), config=_config(ModelRole.REPORTER)),
        "indexer": ModelDescriptor(id="indexer", role="indexer", capabilities=frozenset(["file_read", "embedding_index", "json"]), config=_config(ModelRole.INDEXER)),
        "retriever": ModelDescriptor(id="retriever", role="retriever", capabilities=frozenset(["search", "summarize", "json"]), config=_config(ModelRole.RETRIEVER)),
        "answerer": ModelDescriptor(id="answerer", role="answerer", capabilities=frozenset(["synthesize", "cite", "json"]), config=_config(ModelRole.ANSWERER)),
    }
    return ModelRegistry(providers=providers, models=models)


class TestWorkflowImports:
    def test_coding_workflow_imports(self) -> None:
        from workflows.coding.workflows.coding import WORKFLOW_ID, CodingWorkflow
        assert WORKFLOW_ID == "coding"
        assert CodingWorkflow.workflow_id == "coding"
        assert len(CodingWorkflow.required_agents) > 0
        assert CodingWorkflow.dag is None or len(CodingWorkflow.dag.steps) > 0

    def test_documents_workflow_imports(self) -> None:
        from workflows.documents import DocumentsWorkflow
        assert DocumentsWorkflow.workflow_id == "documents"
        assert len(DocumentsWorkflow.required_agents) > 0

    def test_research_workflow_imports(self) -> None:
        from workflows.research import ResearchWorkflow
        assert ResearchWorkflow.workflow_id == "research"
        assert len(ResearchWorkflow.required_agents) > 0


class TestBuiltinWorkflowRegistry:
    def test_coding_is_registered(self) -> None:
        from workflows.registry import register_builtin_workflows
        from core.capability_registry import get_registry, list_workflows
        reg = get_registry()
        # Clear workflows registered by other tests
        for entry in list_workflows():
            reg._entries.pop(f"workflow:{entry.id}", None)
        register_builtin_workflows()
        all_ids = {w.id for w in list_workflows()}
        assert "coding" in all_ids, f"Expected 'coding' in registered workflows, got {all_ids}"

    def test_all_expected_workflows_registered(self) -> None:
        from workflows.registry import register_builtin_workflows
        from core.capability_registry import get_registry, list_workflows
        reg = get_registry()
        for entry in list_workflows():
            reg._entries.pop(f"workflow:{entry.id}", None)
        register_builtin_workflows()
        all_ids = {w.id for w in list_workflows()}
        expected = {"command_assistant", "coding", "context_maintainer", "docs_maintenance", "documents", "file_organization", "github_maintenance", "research"}
        missing = expected - all_ids
        assert not missing, f"Expected workflows: {missing}"

    def test_file_organization_workflow_imports(self) -> None:
        from workflows.file_organization import FileOrganizationWorkflow
        assert FileOrganizationWorkflow.workflow_id == "file_organization"
        assert len(FileOrganizationWorkflow.required_agents) > 0

    def test_docs_maintenance_workflow_imports(self) -> None:
        from workflows.docs_maintenance import DocsMaintenanceWorkflow
        assert DocsMaintenanceWorkflow.workflow_id == "docs_maintenance"
        assert len(DocsMaintenanceWorkflow.required_agents) > 0

    def test_github_maintenance_workflow_imports(self) -> None:
        from workflows.github_maintenance import GitHubMaintenanceWorkflow
        assert GitHubMaintenanceWorkflow.workflow_id == "github_maintenance"
        assert len(GitHubMaintenanceWorkflow.required_agents) > 0

    def test_command_assistant_workflow_imports(self) -> None:
        from workflows.command_assistant import CommandAssistantWorkflow
        assert CommandAssistantWorkflow.workflow_id == "command_assistant"
        assert len(CommandAssistantWorkflow.required_agents) > 0

    def test_context_maintainer_workflow_imports(self) -> None:
        from workflows.context_maintainer import ContextMaintainerWorkflow
        assert ContextMaintainerWorkflow.workflow_id == "context_maintainer"

    def test_workflow_support_state_in_registry(self) -> None:
        from workflows.registry import register_builtin_workflows
        from core.capability_registry import get_registry, list_workflows
        reg = get_registry()
        for entry in list_workflows():
            reg._entries.pop(f"workflow:{entry.id}", None)
        register_builtin_workflows()
        for wf in list_workflows():
            assert "support_state" in wf.metadata, f"Workflow {wf.id} missing support_state metadata"
            assert wf.metadata["support_state"] in {"stable_candidate", "beta", "experimental", "internal"}

    def test_stable_candidate_workflows(self) -> None:
        from workflows.coding.workflows.coding import CodingWorkflow
        from workflows.documents.workflows.documents import DocumentsWorkflow
        from workflows.command_assistant.workflows.command_assistant import CommandAssistantWorkflow
        from workflows.context_maintainer.workflow import ContextMaintainerWorkflow
        assert CodingWorkflow.support_state == "stable_candidate"
        assert DocumentsWorkflow.support_state == "stable_candidate"
        assert CommandAssistantWorkflow.support_state == "stable_candidate"
        assert ContextMaintainerWorkflow.support_state == "stable_candidate"

    def test_beta_workflows(self) -> None:
        from workflows.file_organization.workflows.file_organization import FileOrganizationWorkflow
        from workflows.docs_maintenance.workflows.docs_maintenance import DocsMaintenanceWorkflow
        from workflows.github_maintenance.workflows.github_maintenance import GitHubMaintenanceWorkflow
        from workflows.research.workflows.research import ResearchWorkflow
        assert FileOrganizationWorkflow.support_state == "beta"
        assert DocsMaintenanceWorkflow.support_state == "beta"
        assert GitHubMaintenanceWorkflow.support_state == "beta"
        assert ResearchWorkflow.support_state == "beta"


class TestWorkflowRuntimeImports:
    def test_coding_runtime_imports(self) -> None:
        from workflows.coding.runtime import plan_task, run_task
        assert callable(plan_task)
        assert callable(run_task)

    def test_documents_runtime_imports(self) -> None:
        from workflows.documents.runtime import plan_task, run_task
        assert callable(plan_task)
        assert callable(run_task)

    def test_documents_runtime_uses_shared_provider_map(self) -> None:
        from workflows.documents.provider_map import DEFAULT_PROVIDER_MAP
        assert "gemini" in DEFAULT_PROVIDER_MAP
        assert "azure_foundry" in DEFAULT_PROVIDER_MAP

    def test_research_runtime_imports(self) -> None:
        from workflows.research.runtime import plan_task, run_task
        assert callable(plan_task)
        assert callable(run_task)

    def test_file_organization_runtime_imports(self) -> None:
        from workflows.file_organization.runtime import plan_task, run_task
        assert callable(plan_task)
        assert callable(run_task)

    def test_docs_maintenance_runtime_imports(self) -> None:
        from workflows.docs_maintenance.runtime import plan_task, run_task
        assert callable(plan_task)
        assert callable(run_task)

    def test_github_maintenance_runtime_imports(self) -> None:
        from workflows.github_maintenance.runtime import plan_task, run_task
        assert callable(plan_task)
        assert callable(run_task)

    def test_command_assistant_runtime_imports(self) -> None:
        from workflows.command_assistant.runtime import plan_task, run_task
        assert callable(plan_task)
        assert callable(run_task)

    def test_context_maintainer_runtime_imports(self) -> None:
        from workflows.context_maintainer.runtime import run_context_maintainer
        assert callable(run_context_maintainer)



class TestWorkflowInstantiation:
    @pytest.fixture
    def mock_deps(self, tmp_path: Path):
        registry = _make_model_registry()
        tool_registry = ToolRegistry()
        policy_engine = PolicyEngine()
        ledger = RunLedger.create(tmp_path, "test")
        return registry, tool_registry, policy_engine, ledger

    def test_documents_workflow_instantiates(self, mock_deps) -> None:
        from workflows.documents import DocumentsWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = DocumentsWorkflow(registry, tools, policy, ledger)
        assert wf.workflow_id == "documents"
        assert wf.dag is not None

    def test_research_workflow_instantiates(self, mock_deps) -> None:
        from workflows.research import ResearchWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = ResearchWorkflow(registry, tools, policy, ledger)
        assert wf.workflow_id == "research"
        assert wf.dag is not None

    def test_file_organization_workflow_instantiates(self, mock_deps) -> None:
        from workflows.file_organization import FileOrganizationWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = FileOrganizationWorkflow(registry, tools, policy, ledger)
        assert wf.workflow_id == "file_organization"
        assert wf.dag is not None

    def test_docs_maintenance_workflow_instantiates(self, mock_deps) -> None:
        from workflows.docs_maintenance import DocsMaintenanceWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = DocsMaintenanceWorkflow(registry, tools, policy, ledger)
        assert wf.workflow_id == "docs_maintenance"
        assert wf.dag is not None

    def test_github_maintenance_workflow_instantiates(self, mock_deps) -> None:
        from workflows.github_maintenance import GitHubMaintenanceWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = GitHubMaintenanceWorkflow(registry, tools, policy, ledger)
        assert wf.workflow_id == "github_maintenance"
        assert wf.dag is not None

    def test_command_assistant_workflow_instantiates(self, mock_deps) -> None:
        from workflows.command_assistant import CommandAssistantWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = CommandAssistantWorkflow(registry, tools, policy, ledger)
        assert wf.workflow_id == "command_assistant"
        assert wf.dag is not None

    def test_context_maintainer_workflow_instantiates(self, mock_deps) -> None:
        from workflows.context_maintainer import ContextMaintainerWorkflow
        registry, tools, policy, ledger = mock_deps
        wf = ContextMaintainerWorkflow(registry, tools, policy, ledger)
        assert wf.workflow_id == "context_maintainer"
        assert wf.dag is not None

    def test_file_organization_no_crash_on_default_config(self, mock_deps) -> None:
        """Regression test: file_organization used to crash because gatherer/executor lacked requested capabilities."""
        from workflows.file_organization import FileOrganizationWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = FileOrganizationWorkflow(registry, tools, policy, ledger)
        # Verify the DAG steps exist
        assert "analyze" in wf.dag.steps
        assert "propose" in wf.dag.steps
        assert "preview" in wf.dag.steps
        assert "apply" in wf.dag.steps

    def test_dag_no_cycles(self, mock_deps) -> None:
        from workflows.research import ResearchWorkflow
        registry, tools, policy, ledger = mock_deps
        with patch.object(ModelRegistry, "create_provider", return_value=MagicMock()):
            wf = ResearchWorkflow(registry, tools, policy, ledger)
        order = wf.dag.topological_order()
        assert len(order) == 3
        ids = [s.id for s in order]
        assert ids.index("gather") < ids.index("summarize")
        assert ids.index("summarize") < ids.index("report")
