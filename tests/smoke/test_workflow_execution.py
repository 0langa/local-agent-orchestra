from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core.ledger import RunLedger
from core.model_registry import ModelDescriptor, ModelRegistry, ProviderDescriptor
from core.policy_engine import PolicyEngine
from core.tool_protocol import ToolRegistry


def _make_model_registry() -> ModelRegistry:
    from config.config import AgentModelConfig, ModelRole

    providers = {
        "openai_v1": ProviderDescriptor(id="openai_v1", import_path="providers.openai_v1:OpenAIV1Provider"),
    }

    def _config(role: ModelRole, caps: list[str]) -> AgentModelConfig:
        return AgentModelConfig(
            role=role,
            provider="openai",
            provider_type="openai_v1",
            endpoint="http://test",
            api_key="test-key",
            model="test-model",
        )

    models = {
        "planner": ModelDescriptor(id="planner", role="planner", capabilities=frozenset(["plan", "json"]), config=_config(ModelRole.PLANNER, ["plan"])),
        "executor": ModelDescriptor(id="executor", role="executor", capabilities=frozenset(["code_edit", "json"]), config=_config(ModelRole.EXECUTOR, ["code_edit"])),
        "gatherer": ModelDescriptor(id="gatherer", role="gatherer", capabilities=frozenset(["web_search", "fetch", "json"]), config=_config(ModelRole.GATHERER, ["fetch"])),
        "summarizer": ModelDescriptor(id="summarizer", role="summarizer", capabilities=frozenset(["summarize", "compare", "json"]), config=_config(ModelRole.SUMMARIZER, ["summarize"])),
        "reporter": ModelDescriptor(id="reporter", role="reporter", capabilities=frozenset(["report", "synthesize", "json"]), config=_config(ModelRole.REPORTER, ["report"])),
        "indexer": ModelDescriptor(id="indexer", role="indexer", capabilities=frozenset(["file_read", "json"]), config=_config(ModelRole.INDEXER, ["file_read"])),
        "retriever": ModelDescriptor(id="retriever", role="retriever", capabilities=frozenset(["search", "json"]), config=_config(ModelRole.RETRIEVER, ["search"])),
        "answerer": ModelDescriptor(id="answerer", role="answerer", capabilities=frozenset(["synthesize", "json"]), config=_config(ModelRole.ANSWERER, ["synthesize"])),
        "parser": ModelDescriptor(id="parser", role="planner", capabilities=frozenset(["plan", "json"]), config=_config(ModelRole.PLANNER, ["plan"])),
        "generator": ModelDescriptor(id="generator", role="executor", capabilities=frozenset(["code_edit", "json"]), config=_config(ModelRole.EXECUTOR, ["code_edit"])),
        "validator": ModelDescriptor(id="validator", role="verifier", capabilities=frozenset(["verify", "json"]), config=_config(ModelRole.VERIFIER, ["verify"])),
        "analyzer": ModelDescriptor(id="analyzer", role="indexer", capabilities=frozenset(["file_read", "json"]), config=_config(ModelRole.INDEXER, ["file_read"])),
        "proposer": ModelDescriptor(id="proposer", role="planner", capabilities=frozenset(["plan", "json"]), config=_config(ModelRole.PLANNER, ["plan"])),
        "applier": ModelDescriptor(id="applier", role="executor", capabilities=frozenset(["code_edit", "json"]), config=_config(ModelRole.EXECUTOR, ["code_edit"])),
        "detector": ModelDescriptor(id="detector", role="planner", capabilities=frozenset(["plan", "json"]), config=_config(ModelRole.PLANNER, ["plan"])),
        "updater": ModelDescriptor(id="updater", role="executor", capabilities=frozenset(["code_edit", "json"]), config=_config(ModelRole.EXECUTOR, ["code_edit"])),
        "aligner": ModelDescriptor(id="aligner", role="verifier", capabilities=frozenset(["verify", "json"]), config=_config(ModelRole.VERIFIER, ["verify"])),
    }
    return ModelRegistry(providers=providers, models=models)


def _fake_invoke(self: Any, user_prompt: str, max_output_tokens: int | None = None) -> str:
    """Patch for BaseAgent._invoke that returns schema-valid JSON based on output_schema."""
    schema_name = self.output_schema.__name__
    responses: dict[str, str] = {
        "GatherResult": json.dumps({
            "sources": [{"url": "https://example.com/1", "title": "Example", "snippet": "info", "relevance_score": 8}],
            "search_queries": ["test query"],
            "raw_findings": "Some findings",
        }),
        "SummaryResult": json.dumps({
            "summaries": [{"url": "https://example.com/1", "key_points": ["point 1"], "credibility": "high"}],
            "comparisons": [],
            "conflicts": [],
            "gaps": [],
        }),
        "ResearchReport": json.dumps({
            "topic": "Test Topic",
            "executive_summary": "Summary",
            "sections": [{"heading": "Intro", "content": "Content"}],
            "sources": ["https://example.com/1"],
            "confidence": "high",
            "recommendations": ["Do something"],
        }),
        "ParsedIntent": json.dumps({"action": "search", "target": "files", "parameters": {}}),
        "GeneratedCommand": json.dumps({"commands": [{"command": ["echo", "hello"], "description": "Say hello", "safety": "safe"}]}),
        "ValidationResult": json.dumps({"valid": True, "issues": [], "safe_commands": [{"command": ["echo", "hello"], "safe": True}]}),
        "AnalyzerResult": json.dumps({
            "files": [{"path": "README.md", "category": "document", "confidence": 0.9}],
            "summary": "A readme file",
        }),
        "ProposerResult": json.dumps({"actions": [{"source": "old.txt", "target": "new.txt", "reason": "organize"}]}),
        "ApplierResult": json.dumps({"moves": [{"source": "old.txt", "target": "new.txt", "success": True, "error": ""}], "summary": "done"}),
        "DetectionResult": json.dumps({"stale_docs": [{"path": "README.md", "reason": "outdated"}]}),
        "UpdateResult": json.dumps({"updates": [{"path": "README.md", "new_content": "# Updated"}]}),
        "AlignmentResult": json.dumps({"aligned": True, "issues": []}),
        "IndexerOutput": json.dumps({"chunks": [{"id": "c1", "text": "hello", "metadata": {}}]}),
        "RetrieverOutput": json.dumps({"results": [{"chunk_id": "c1", "score": 0.9, "text": "hello"}]}),
        "AnswererOutput": json.dumps({"answer": "It works", "citations": ["c1"], "confidence": "high"}),
        "ImplementationPlan": json.dumps({"summary": "plan", "assumptions": [], "non_goals": [], "detected_repo_type": "python", "risks": [], "task_graph": {"ordered_tasks": []}}),
        "PatchPlan": json.dumps({"patches": []}),
        "VerificationReport": json.dumps({"passed": True, "results": []}),
    }
    return responses.get(schema_name, json.dumps({"result": "ok"}))


@pytest.fixture
def mock_deps(tmp_path: Path):
    registry = _make_model_registry()
    tool_registry = ToolRegistry()
    policy_engine = PolicyEngine()
    ledger = RunLedger.create(tmp_path, "test")
    return registry, tool_registry, policy_engine, ledger


class TestResearchWorkflowExecution:
    def test_research_workflow_runs_end_to_end(self, mock_deps, tmp_path: Path) -> None:
        from workflows.research import ResearchWorkflow
        from workflows.research.agents.base import BaseAgent
        registry, tools, policy, ledger = mock_deps
        with patch.object(BaseAgent, "_invoke", _fake_invoke):
            wf = ResearchWorkflow(registry, tools, policy, ledger)
            results = wf.run(tmp_path, metadata={"topic": "AI testing"})

        assert len(results) == 3
        assert all(r.success for r in results)
        # Verify ledger has final report
        assert (ledger.run_dir / "final_report.json").exists() or any(
            r.metadata.get("parsed") for r in results
        )


class TestCommandAssistantWorkflowExecution:
    def test_command_assistant_runs_end_to_end(self, mock_deps, tmp_path: Path) -> None:
        from workflows.command_assistant import CommandAssistantWorkflow
        from workflows.command_assistant.agents.base import BaseAgent
        registry, tools, policy, ledger = mock_deps
        with patch.object(BaseAgent, "_invoke", _fake_invoke):
            wf = CommandAssistantWorkflow(registry, tools, policy, ledger)
            results = wf.run(tmp_path, metadata={"user_input": "list files"})

        assert len(results) == 2
        assert results[-1].success

    def test_command_assistant_run_task_unsafe_command(self, tmp_path: Path) -> None:
        from workflows.command_assistant.runtime import run_task
        from workflows.command_assistant.agents.parser import ParserAgent
        from workflows.command_assistant.agents.generator import GeneratorAgent

        unsafe_generate = {"command": ["rm", "-rf", "/"], "explanation": "dangerous", "safe": False}
        with (
            patch.object(ParserAgent, "run_parse", return_value=MagicMock(success=True, parsed_output={"action": "run"})),
            patch.object(GeneratorAgent, "run_generate", return_value=MagicMock(success=True, parsed_output=unsafe_generate, raw_output=json.dumps(unsafe_generate))),
            patch("workflows.command_assistant.runtime.RunLedger.create", return_value=MagicMock(run_dir=tmp_path, write_json=MagicMock(), write_text=MagicMock(), emit_event=MagicMock())),
        ):
            report, _ = run_task("delete everything", write_ledger=True)

        assert len(report.commands) == 1
        assert report.commands[0].safe is False
        assert report.status == "done"

    def test_command_assistant_run_task_parse_failure(self, tmp_path: Path) -> None:
        from workflows.command_assistant.runtime import run_task
        from workflows.command_assistant.agents.parser import ParserAgent

        with (
            patch.object(ParserAgent, "run_parse", return_value=MagicMock(success=False, parsed_output=None, error="parse error")),
            patch("workflows.command_assistant.runtime.RunLedger.create", return_value=MagicMock(run_dir=tmp_path, write_json=MagicMock(), write_text=MagicMock(), emit_event=MagicMock())),
        ):
            report, _ = run_task("bad input", write_ledger=True)

        assert report.status == "failed"
        assert report.commands == []


class TestFileOrganizationWorkflowExecution:
    def test_file_organization_runs_end_to_end(self, mock_deps, tmp_path: Path) -> None:
        from workflows.file_organization import FileOrganizationWorkflow
        from workflows.file_organization.agents.base import BaseAgent
        registry, tools, policy, ledger = mock_deps
        # Create a dummy file to organize
        (tmp_path / "old.txt").write_text("content", encoding="utf-8")
        with patch.object(BaseAgent, "_invoke", _fake_invoke):
            wf = FileOrganizationWorkflow(registry, tools, policy, ledger)
            results = wf.run(tmp_path, metadata={"dry_run": True})

        assert len(results) == 4
        assert all(r.success for r in results)
        # Verify ledger has working_memory or file_changes
        assert (ledger.run_dir / "working_memory.json").exists()


class TestDocumentsWorkflowExecution:
    def test_documents_workflow_runs_end_to_end(self, mock_deps, tmp_path: Path) -> None:
        from workflows.documents import DocumentsWorkflow
        from workflows.documents.agents.base import BaseAgent
        registry, tools, policy, ledger = mock_deps
        (tmp_path / "README.md").write_text("# Hello\nThis is a test.", encoding="utf-8")
        with patch.object(BaseAgent, "_invoke", _fake_invoke):
            wf = DocumentsWorkflow(registry, tools, policy, ledger)
            results = wf.run(tmp_path, metadata={"query": "hello"})

        assert len(results) == 3
        assert all(r.success for r in results)
        # Verify answer step has parsed answer
        answer_result = results[-1]
        assert "parsed" in answer_result.metadata

    def test_documents_workflow_empty_repo_fallback(self, mock_deps, tmp_path: Path) -> None:
        from workflows.documents import DocumentsWorkflow
        from workflows.documents.agents.base import BaseAgent
        registry, tools, policy, ledger = mock_deps
        # Empty repo — no files
        with patch.object(BaseAgent, "_invoke", _fake_invoke):
            wf = DocumentsWorkflow(registry, tools, policy, ledger)
            results = wf.run(tmp_path, metadata={"query": "hello"})

        assert len(results) == 3
        # Index succeeds even with no files
        assert results[0].success
        # Retrieve succeeds
        assert results[1].success
        # Answer succeeds (may use fallback)
        assert results[2].success
        # Workflow should produce some answer metadata
        assert "parsed" in results[2].metadata


class TestDocumentsCollectTextFiles:
    def test_excludes_binary_suffixes(self, tmp_path: Path) -> None:
        from workflows.documents.workflows.documents import _collect_text_files
        (tmp_path / "readme.md").write_text("text", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "app.exe").write_bytes(b"MZ")
        files = _collect_text_files(tmp_path)
        names = {p.name for p in files}
        assert "readme.md" in names
        assert "image.png" not in names
        assert "app.exe" not in names

    def test_excludes_directories(self, tmp_path: Path) -> None:
        from workflows.documents.workflows.documents import _collect_text_files
        (tmp_path / "src").mkdir(exist_ok=True)
        (tmp_path / "src" / "main.py").write_text("print(1)", encoding="utf-8")
        (tmp_path / ".git").mkdir(exist_ok=True)
        (tmp_path / ".git" / "config").write_text("[core]", encoding="utf-8")
        (tmp_path / "node_modules" / "pkg").mkdir(parents=True, exist_ok=True)
        (tmp_path / "node_modules" / "pkg" / "index.js").write_text("module.exports = {};", encoding="utf-8")
        files = _collect_text_files(tmp_path)
        names = {p.name for p in files}
        assert "main.py" in names
        assert "config" not in names
        assert "index.js" not in names

    def test_empty_repo_returns_empty(self, tmp_path: Path) -> None:
        from workflows.documents.workflows.documents import _collect_text_files
        files = _collect_text_files(tmp_path)
        assert files == []
