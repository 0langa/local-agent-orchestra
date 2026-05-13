"""Stable public API facade for agentheim.

This is the ONLY module that interfaces (CLI, API, Web UI, Desktop UI, TUI)
may import from `core/`. All internal modules are hidden behind this facade.

Importing directly from `core.*` internals is an architectural breach.
"""

from __future__ import annotations

# ─── Events ─────────────────────────────────────────────────────────
from core.events import Event as Event
from core.events import EventType as EventType

# ─── Ledger ─────────────────────────────────────────────────────────
from core.ledger import RunLedger as RunLedger

# ─── Run executor ───────────────────────────────────────────────────
from core.run_executor import RunExecutor as RunExecutor
from core.run_executor import RunRecord as RunRecord
from core.run_executor import RunStatus as RunStatus

# ─── Errors ─────────────────────────────────────────────────────────
from core.errors import AIteamError as AIteamError
from core.errors import ConfigError as ConfigError
from core.errors import ExecutionError as ExecutionError
from core.errors import IntegrationError as IntegrationError
from core.errors import PatchApplicationError as PatchApplicationError
from core.errors import PlanningError as PlanningError
from core.errors import ProviderError as ProviderError
from core.errors import RepoInspectionError as RepoInspectionError
from core.errors import ResumeError as ResumeError
from core.errors import ToolSafetyError as ToolSafetyError
from core.errors import VerificationError as VerificationError

# ─── Repo helpers ───────────────────────────────────────────────────
from core.repo.context_pack import build_context_pack as build_context_pack
from core.repo.scanner import inspect_repository as inspect_repository

# ─── Resume ─────────────────────────────────────────────────────────
from core.replay_engine import ReplayEngine as ReplayEngine
from core.replay_engine import RunState as RunState
from core.resume import ResumeOrchestrator as ResumeOrchestrator
from core.resume import list_runs as list_resume_runs
from core.resume import load_final_report as load_final_report
from core.resume import load_run as load_run

# ─── Error classification & retry ───────────────────────────────────
from core.error_classification import ErrorCategory as ErrorCategory
from core.error_classification import classify_error as classify_error
from core.error_classification import error_summary as error_summary
from core.retry_engine import RetryEngine as RetryEngine
from core.retry_engine import RetryExhaustedError as RetryExhaustedError

# ─── Budget ─────────────────────────────────────────────────────────
from core.step_budget import BudgetExceededError as BudgetExceededError
from core.step_budget import BudgetLimits as BudgetLimits
from core.step_budget import BudgetSnapshot as BudgetSnapshot
from core.step_budget import StepBudgetEnforcer as StepBudgetEnforcer

# ─── Tool protocol ──────────────────────────────────────────────────
from core.tool_protocol import AsyncBaseTool as AsyncBaseTool
from core.tool_protocol import BaseTool as BaseTool
from core.tool_protocol import ParamSchema as ParamSchema
from core.tool_protocol import RiskLevel as RiskLevel
from core.tool_protocol import ToolContext as ToolContext
from core.tool_protocol import ToolRegistry as ToolRegistry
from core.tool_protocol import ToolResult as ToolResult
from core.tool_protocol import ToolSchema as ToolSchema

# ─── Model registry ─────────────────────────────────────────────────
from core.cascading_router import CascadingRouter as CascadingRouter
from core.cascading_router import ModelBinding as ModelBinding
from core.model_registry import ModelDescriptor as ModelDescriptor
from core.model_registry import DEFAULT_PROVIDER_MAP as DEFAULT_PROVIDER_MAP
from core.model_registry import build_model_registry as build_model_registry
from core.model_registry import ModelRegistry as ModelRegistry
from core.model_registry import ProviderDescriptor as ProviderDescriptor

# ─── Policy engine ──────────────────────────────────────────────────
from core.approval_workflow import ApprovalRequest as ApprovalRequest
from core.approval_workflow import ApprovalWorkflow as ApprovalWorkflow
from core.policy_engine import PolicyDecision as PolicyDecision
from core.policy_engine import PolicyConfig as PolicyConfig
from core.policy_engine import PolicyEngine as PolicyEngine
from core.privacy_enforcer import PrivacyEnforcer as PrivacyEnforcer
from core.privacy_enforcer import PrivacyMode as PrivacyMode

# ─── Capability registry ────────────────────────────────────────────
from core.capability_registry import CapabilityRegistry as CapabilityRegistry
from core.capability_registry import RegistryEntry as RegistryEntry
from core.capability_registry import get_registry as get_capability_registry
from core.capability_registry import get_workflow as get_workflow
from core.capability_registry import list_workflows as list_workflows
from core.capability_registry import register_workflow as register_workflow

# ─── Workflow runtime ───────────────────────────────────────────────
from core.workflow_runner import WorkflowRunner as WorkflowRunner
from workflows.base import ExecutionDAG as ExecutionDAG
from workflows.base import Step as Step
from workflows.base import StepBudget as StepBudget
from workflows.base import StepContext as StepContext
from workflows.base import StepResult as StepResult
from workflows.base import Workflow as Workflow

# ─── Agent protocol ─────────────────────────────────────────────────
from core.agent_protocol import AgentContext as AgentContext
from core.agent_protocol import AgentMessage as AgentMessage
from core.agent_protocol import AgentRequest as AgentRequest
from core.agent_protocol import AgentResponse as AgentResponse

# ─── Context & artifacts ────────────────────────────────────────────
from core.artifact_store import ArtifactStore as ArtifactStore
from core.artifact_store import ArtifactSpec as ArtifactSpec
from core.context_packer import ContextManifest as ContextManifest
from core.context_packer import ContextPacker as ContextPacker


# Lazy imports for ContextOps to avoid circular dependencies at module load.
# Dataclasses import directly (no vendor deps); ABC + impl are deferred.
from agentheim.context_ops import (
    CleanResult as CleanResult,
    ContextPlan as ContextPlan,
    ContextStatus as ContextStatus,
    GeneratedContext as GeneratedContext,
    PublicDocsImpactReport as PublicDocsImpactReport,
    RepositoryInventory as RepositoryInventory,
    VerificationResult as VerificationResult,
    WriteReport as WriteReport,
)


def __getattr__(name: str):
    if name == "ContextOps":
        from agentheim.context_ops import ContextOps
        return ContextOps
    if name == "AictxContextOps":
        from agentheim.context_ops_impl import AictxContextOps
        return AictxContextOps
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# ─── Redaction ──────────────────────────────────────────────────────
from core.redaction import redact_dict as redact_dict
from core.redaction import redact_text as redact_text
from core.json_repair import repair_json_text as repair_json_text

# ─── Runtime internals used by workflow-facing code ────────────────
from core.patching import PatchApplier as PatchApplier
from core.repo.scanner import RepoScanResult as RepoScanResult
from core.schemas_runtime import AgentResult as AgentResult
from core.schemas_runtime import ImplementationPlan as ImplementationPlan
from core.schemas_runtime import PatchPlan as PatchPlan
from core.schemas_runtime import UserTask as UserTask
from core.schemas_runtime import VerificationReport as VerificationReport
from core.schemas_runtime import WorkOrder as WorkOrder
from core.state_machine import RuntimeState as RuntimeState
from core.state_machine import RuntimeStateMachine as RuntimeStateMachine
from core.policies import CommandPolicy as CommandPolicy
from core.policies import classify_command as classify_command

# ─── Schemas ────────────────────────────────────────────────────────
from core.schemas import ArtifactRef as ArtifactRef
from core.schemas import AgentMessage as WorkflowAgentMessage
from core.schemas import WorkflowRun as WorkflowRun
from core.schemas import WorkflowStep as WorkflowStep
from core.schemas import WorkflowStepStatus as WorkflowStepStatus
from core.schemas_runtime import AgentMessage as RuntimeAgentMessage

__all__ = [
    # Events
    "Event",
    "EventType",
    # Ledger
    "RunLedger",
    # Run executor
    "RunExecutor",
    "RunRecord",
    "RunStatus",
    # Errors
    "AIteamError",
    "ConfigError",
    "ExecutionError",
    "IntegrationError",
    "PatchApplicationError",
    "PlanningError",
    "ProviderError",
    "RepoInspectionError",
    "ResumeError",
    "ToolSafetyError",
    "VerificationError",
    # Repo helpers
    "build_context_pack",
    "inspect_repository",
    # Resume
    "ReplayEngine",
    "ResumeOrchestrator",
    "RunState",
    "list_resume_runs",
    "load_final_report",
    "load_run",
    # Error / retry
    "ErrorCategory",
    "classify_error",
    "error_summary",
    "RetryEngine",
    "RetryExhaustedError",
    # Budget
    "BudgetExceededError",
    "BudgetLimits",
    "BudgetSnapshot",
    "StepBudgetEnforcer",
    # Tools
    "AsyncBaseTool",
    "BaseTool",
    "ParamSchema",
    "RiskLevel",
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "ToolSchema",
    # Models
    "CascadingRouter",
    "ModelBinding",
    "ModelDescriptor",
    "DEFAULT_PROVIDER_MAP",
    "ModelRegistry",
    "ProviderDescriptor",
    "build_model_registry",
    # Policy
    "ApprovalRequest",
    "ApprovalWorkflow",
    "PolicyDecision",
    "PolicyConfig",
    "PolicyEngine",
    "PrivacyEnforcer",
    "PrivacyMode",
    # Capabilities
    "CapabilityRegistry",
    "RegistryEntry",
    "get_capability_registry",
    "get_workflow",
    "list_workflows",
    "register_workflow",
    # Workflow runtime
    "WorkflowRunner",
    "ExecutionDAG",
    "Step",
    "StepBudget",
    "StepContext",
    "StepResult",
    "Workflow",
    # Agent protocol
    "AgentContext",
    "AgentMessage",
    "AgentRequest",
    "AgentResponse",
    # Context & artifacts
    "ArtifactStore",
    "ArtifactSpec",
    "ContextManifest",
    "ContextPacker",
    # Redaction
    "redact_dict",
    "redact_text",
    "repair_json_text",
    # Workflow-facing runtime internals
    "PatchApplier",
    "RepoScanResult",
    "AgentResult",
    "ImplementationPlan",
    "PatchPlan",
    "UserTask",
    "VerificationReport",
    "WorkOrder",
    "RuntimeState",
    "RuntimeStateMachine",
    "CommandPolicy",
    "classify_command",
    # Schemas
    "ArtifactRef",
    "WorkflowAgentMessage",
    "WorkflowRun",
    "WorkflowStep",
    "WorkflowStepStatus",
    "RuntimeAgentMessage",
    # ContextOps (lazy)
    "ContextOps",
    "AictxContextOps",
    "RepositoryInventory",
    "ContextPlan",
    "GeneratedContext",
    "WriteReport",
    "VerificationResult",
    "ContextStatus",
    "PublicDocsImpactReport",
    "CleanResult",
]
