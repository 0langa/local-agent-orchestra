"""FastAPI API server with OpenAPI spec, auth, rate limiting, and execution."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from config.config import (
    ConfigError,
    ModelBinding,
    ModelRole,
    ProfilesDocument,
    TeamProfile,
    get_secret_store,
    list_provider_templates,
    load_profiles_document,
    make_secret_ref,
    provider_account_from_template,
    save_profiles_document,
)
from core.public_api import (
    CanonicalRunSummary,
    DEFAULT_PROVIDER_MAP,
    RunExecutor,
    RunRecord,
    RunStatus,
    ToolContext,
    ToolInvoker,
    build_live_run_summary,
    build_run_summary,
    build_model_registry,
    interface_policy_config,
    list_workflows as cap_list_workflows,
)
from memory.bus import MemoryBus
from tools.registry import ToolRegistry, create_core_tool_registry

from interfaces.api_server.auth import verify_api_key
from interfaces.api_server.rate_limit import RateLimiter
from interfaces.tool_approval import InterfaceApprovalStore
from presets.base import PresetInputError
from presets.catalog import CATALOG, QuestionSchema

from agentheim.context_ops_impl import AictxContextOps
from agentheim.vendor.aictx.config import AictxConfig
from agentheim.vendor.aictx.errors import SafetyError

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Pydantic models (module-level for FastAPI compatibility)
# ------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    components: dict[str, str] = Field(default_factory=dict)


class ToolSchemaItem(BaseModel):
    tool_id: str
    risk_level: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class ToolInvokeResponse(BaseModel):
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    policy: dict[str, Any] | None = None
    approval_request: dict[str, Any] | None = None


class ApprovalDecisionResponse(BaseModel):
    success: bool
    status: str
    request_id: str
    tool_id: str | None = None
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] | None = None


class WorkflowListItem(BaseModel):
    workflow_id: str
    name: str
    description: str


class WorkflowDetail(BaseModel):
    workflow_id: str
    name: str
    description: str
    required_agents: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)


class WorkflowExecuteRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class PresetListItem(BaseModel):
    preset_id: str
    workflow_id: str
    name: str
    description: str
    support_state: str = "unknown"
    product_tier: str = "advanced"
    recommended_for: list[str] = Field(default_factory=list)
    requires_integrations: list[str] = Field(default_factory=list)
    estimated_time: str = ""
    output_kind: str = ""
    example_inputs: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[str] = Field(default_factory=list)
    questions: list[QuestionSchema] = Field(default_factory=list)
    default_config: dict[str, Any] = Field(default_factory=dict)


class PresetRunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class ExecuteResponse(BaseModel):
    run_id: str
    status: str


class MemoryReadResponse(BaseModel):
    scope: str
    key: str
    value: Any = None
    found: bool = False


class MemoryWriteRequest(BaseModel):
    value: dict[str, Any]


class MemoryWriteResponse(BaseModel):
    scope: str
    key: str
    status: str = "written"


class ModelListItem(BaseModel):
    model_id: str
    provider: str
    capabilities: list[str] = Field(default_factory=list)


class ProviderListItem(BaseModel):
    provider_id: str
    available: bool = False  # Adapter can be imported
    healthy: bool = False    # Implemented and not known-broken
    configured: bool = False  # Has live config/env (best-effort)
    error: str | None = None


class ProviderTemplateItem(BaseModel):
    kind: str
    display_name: str
    endpoint: str
    auth_mode: str
    provider_type: str
    capabilities: list[str] = Field(default_factory=list)
    docs_url: str
    support_state: str = "unknown"


class ProviderAddRequest(BaseModel):
    provider_id: str
    template: str
    model: str
    role: ModelRole = ModelRole.PLANNER
    profile: str = "default"
    endpoint: str | None = None
    api_key: str | None = None
    capabilities: list[str] = Field(default_factory=lambda: ["text", "json"])


class ProviderAssignRequest(BaseModel):
    profile: str = "default"
    role: ModelRole
    provider_id: str
    model: str
    capabilities: list[str] = Field(default_factory=lambda: ["text", "json"])


class ProviderMutationResponse(BaseModel):
    status: str
    profile: str


class CtxInitRequest(BaseModel):
    project: str = "."


class CtxScanRequest(BaseModel):
    project: str = "."


class CtxScanResponse(BaseModel):
    repo_root: str
    head_commit: str
    branch: str
    dirty_state: bool
    file_count: int
    manifest_count: int


class CtxRunRequest(BaseModel):
    project: str = "."
    scope: str = "full"
    write_mode: str = "patch"
    allow_dirty: bool = False


class CtxVerifyRequest(BaseModel):
    project: str = "."
    strict: bool = False


class CtxStatusRequest(BaseModel):
    project: str = "."
    strict: bool = False


class CtxCleanRequest(BaseModel):
    project: str = "."
    run_id: str | None = None
    keep_runs: int | None = None


class CtxPublicDocsImpactRequest(BaseModel):
    project: str = "."
    scope: str = "full"


class CtxPublicDocsUpdateRequest(BaseModel):
    project: str = "."
    scope: str = "changed"
    write_mode: str = "patch"


class CtxRunResponse(BaseModel):
    run_id: str
    generated_files: list[str]
    patch_text: str
    timing: dict
    entropy: dict


class CtxVerifyResponse(BaseModel):
    result: str
    is_pass: bool


class CtxStatusResponse(BaseModel):
    is_stale: bool
    stale_sources: list[str]
    missing_sources: list[str]
    next_command: str | None


class CtxCleanResponse(BaseModel):
    removed_count: int
    kept_count: int
    removed_paths: list[str]


class CtxPublicDocsImpactResponse(BaseModel):
    entries: list[dict]


class CtxPublicDocsUpdateResponse(BaseModel):
    patch_path: str | None


# ------------------------------------------------------------------
# App factory
# ------------------------------------------------------------------

def create_api_app(repo_root: str | Path = ".") -> FastAPI:
    repo_root = Path(repo_root).resolve()
    app = FastAPI(
        title="Agentheim API",
        description="Production API for agent orchestration, tool invocation, and workflow management.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS — default localhost-only; override via AGENTHEIM_CORS_ORIGINS env.
    _cors_origins = os.getenv("AGENTHEIM_CORS_ORIGINS", "")
    if _cors_origins:
        allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
    else:
        allow_origins = ["http://localhost", "http://127.0.0.1"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type", "Authorization"],
    )

    tool_registry = ToolRegistry(repo_root)
    core_tool_registry = create_core_tool_registry(repo_root)
    tool_invoker = ToolInvoker(registry=core_tool_registry, policy_config=interface_policy_config())
    approval_store = InterfaceApprovalStore(repo_root, "api-tool-approval")
    memory_bus = MemoryBus(repo_root)
    rate_limiter = RateLimiter(max_requests=60, window_seconds=60.0)
    run_executor = RunExecutor()
    from interfaces.run_hooks import register_default_run_hooks

    register_default_run_hooks(run_executor)

    # ------------------------------------------------------------------
    # Request logging middleware
    # ------------------------------------------------------------------

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "%s %s %d %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            duration,
        )
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_tool(tool_id: str):
        for candidate in tool_registry.tool_objects():
            if getattr(candidate, "tool_id", None) == tool_id:
                return candidate
        return None

    def _policy_to_dict(policy) -> dict[str, Any] | None:
        if policy is None:
            return None
        return {
            "decision": policy.decision,
            "reason": policy.reason,
            "policy_id": policy.policy_id,
            "risk_level": policy.risk_level.value,
            "suggested_approval": policy.suggested_approval,
            "override_possible": policy.override_possible,
            "metadata": policy.metadata,
        }

    def _run_status_payload(run_id: str, record: RunRecord | None = None) -> CanonicalRunSummary:
        if record is not None:
            return build_live_run_summary(repo_root, run_id, record)
        return build_run_summary(repo_root, run_id)

    def _import_workflows() -> None:
        try:
            from workflows.registry import register_builtin_workflows

            register_builtin_workflows()
        except Exception:
            pass

    def _tool_schema_to_dict(tool) -> dict[str, Any]:
        params = {}
        for name, ps in tool.schema.parameters.items():
            params[name] = {
                "type": ps.type,
                "description": ps.description,
                "required": ps.required,
                "default": ps.default,
            }
            if ps.enum:
                params[name]["enum"] = ps.enum
        return params

    def _check_provider_health(provider_id: str) -> tuple[bool, bool, bool, str | None]:
        """Return (available, healthy, configured, error) for a provider.

        *available* = adapter module/class can be imported.
        *healthy*   = provider is implemented (not NotImplementedError).
        *configured* = live env/config present (best-effort, may be False
                       even for working setups).
        """
        descriptor = DEFAULT_PROVIDER_MAP.get(provider_id)
        if descriptor is None:
            return False, False, False, "Unknown provider"
        try:
            import importlib
            module_path, class_name = descriptor.import_path.split(":", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
        except Exception as exc:
            return False, False, False, str(exc)

        try:
            from config.config import AgentModelConfig, ModelRole

            cls(AgentModelConfig(role=ModelRole.PLANNER, provider=provider_id, provider_type=provider_id, endpoint="http://localhost", api_key="-", model="test"))
        except NotImplementedError as exc:
            return True, False, False, f"not implemented: {exc}"
        except Exception as exc:
            return True, False, False, f"adapter error: {exc}"

        # Best-effort configured check
        configured = False
        try:
            from config.config import load_team_config
            team = load_team_config()
            configured = any(provider.provider_type == provider_id for provider in team.providers.values())
        except Exception:
            pass

        return True, True, configured, None

    def _get_ops(config=None):
        cfg = config if config is not None else AictxConfig()
        return AictxContextOps(cfg)

    def _ctx_exc(exc: Exception) -> None:
        from core.public_api import catalog_entry_for, format_api_response

        entry = catalog_entry_for(exc)
        raise HTTPException(
            status_code=entry.http_status,
            detail=format_api_response(entry, exc),
        ) from exc

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/api/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            components={
                "tools": "ok",
                "memory": "ok",
                "workflows": "ok",
            }
        )

    @app.get("/api/health/oci", tags=["system"])
    def health_oci() -> dict[str, Any]:
        try:
            from agentheim.vendor.aictx.oci.doctor import run_oci_doctor

            report = run_oci_doctor()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OCI support not installed",
            )
        if not report.sdk_available:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OCI support not installed",
            )
        return report.model_dump()

    @app.get("/api/tools", response_model=list[ToolSchemaItem], tags=["tools"])
    def list_tools() -> list[ToolSchemaItem]:
        """List all available tools with their schemas."""
        items = []
        for tool in tool_registry.tool_objects():
            if hasattr(tool, "tool_id") and hasattr(tool, "schema"):
                items.append(
                    ToolSchemaItem(
                        tool_id=tool.tool_id,
                        risk_level=tool.risk_level.value,
                        description=tool.schema.description,
                        parameters=_tool_schema_to_dict(tool),
                    )
                )
        return sorted(items, key=lambda x: x.tool_id)

    @app.post(
        "/api/tools/{tool_id}/invoke",
        response_model=ToolInvokeResponse,
        tags=["tools"],
        dependencies=[Depends(rate_limiter.check)],
    )
    def invoke_tool(
        tool_id: str,
        request: ToolInvokeRequest,
        api_key: str = Depends(verify_api_key),
    ) -> ToolInvokeResponse:
        """Invoke a tool with the given parameters. MEDIUM+ risk tools require confirmation."""
        tool = _find_tool(tool_id)
        if tool is None:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")

        ctx = ToolContext(network_allowed=False, workspace=repo_root, allowed_paths=[str(repo_root)])
        ledger = approval_store.create_ledger(tool_id, interface_name="api")
        result = tool_invoker.invoke(tool_id, request.params, ctx, ledger=ledger)
        if result.requires_approval:
            approval_request = approval_store.add(
                tool_id=tool_id,
                params=request.params,
                context=ctx,
                ledger=ledger,
                policy_decision=result.policy,
            )
            return JSONResponse(
                status_code=409,
                content=ToolInvokeResponse(
                    success=False,
                    error=result.error,
                    metadata=result.metadata or {},
                    requires_approval=True,
                    policy=_policy_to_dict(result.policy),
                    approval_request=approval_request.to_dict(),
                ).model_dump(),
            )
        if result.policy and result.policy.decision == "deny":
            raise HTTPException(
                status_code=403,
                detail=f"Tool '{tool_id}' blocked by policy. Use CLI for high-risk operations. {result.error}",
            )

        return ToolInvokeResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata or {},
            requires_approval=result.requires_approval,
            policy=_policy_to_dict(result.policy),
        )

    @app.post(
        "/api/tools/approvals/{request_id}/grant",
        response_model=ApprovalDecisionResponse,
        tags=["tools"],
        dependencies=[Depends(rate_limiter.check)],
    )
    def grant_tool_approval(
        request_id: str,
        api_key: str = Depends(verify_api_key),
    ) -> ApprovalDecisionResponse:
        granted = approval_store.grant(request_id, invoker=tool_invoker)
        if granted is None:
            raise HTTPException(status_code=404, detail=f"Approval request '{request_id}' not found")
        approval_request, result = granted
        return ApprovalDecisionResponse(
            success=result.success,
            status="granted",
            request_id=request_id,
            tool_id=approval_request.tool_id,
            data=result.data,
            error=result.error,
            metadata=result.metadata or {},
            policy=_policy_to_dict(result.policy),
        )

    @app.post(
        "/api/tools/approvals/{request_id}/deny",
        response_model=ApprovalDecisionResponse,
        tags=["tools"],
        dependencies=[Depends(rate_limiter.check)],
    )
    def deny_tool_approval(
        request_id: str,
        api_key: str = Depends(verify_api_key),
    ) -> ApprovalDecisionResponse:
        denied = approval_store.deny(request_id)
        if denied is None:
            raise HTTPException(status_code=404, detail=f"Approval request '{request_id}' not found")
        return ApprovalDecisionResponse(
            success=False,
            status="denied",
            request_id=request_id,
            tool_id=denied.tool_id,
            error="approval_denied",
            metadata={"target": denied.target, "risk_level": denied.risk_level.value},
        )

    @app.get("/api/workflows", response_model=list[WorkflowListItem], tags=["workflows"])
    def list_workflows() -> list[WorkflowListItem]:
        """List registered workflows."""
        _import_workflows()
        return [
            WorkflowListItem(
                workflow_id=w.id,
                name=w.id.replace("_", " ").title(),
                description=w.metadata.get("description", "") or "",
            )
            for w in cap_list_workflows()
        ]

    @app.get("/api/workflows/{workflow_id}", response_model=WorkflowDetail, tags=["workflows"])
    def get_workflow(workflow_id: str) -> WorkflowDetail:
        """Get detailed information about a workflow."""
        _import_workflows()
        for w in cap_list_workflows():
            if w.id == workflow_id:
                return WorkflowDetail(
                    workflow_id=w.id,
                    name=w.id.replace("_", " ").title(),
                    description=w.metadata.get("description", "") or "",
                    required_agents=[agent.id for agent in getattr(w.factory, "required_agents", [])],
                    required_tools=getattr(w.factory, "required_tools", []),
                )
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    @app.post(
        "/api/workflows/{workflow_id}/execute",
        response_model=ExecuteResponse,
        tags=["workflows"],
        dependencies=[Depends(rate_limiter.check)],
    )
    def execute_workflow(
        workflow_id: str,
        request: WorkflowExecuteRequest,
        api_key: str = Depends(verify_api_key),
    ) -> ExecuteResponse:
        """Execute a workflow asynchronously. Returns a run ID for polling."""
        _import_workflows()
        workflow_cls = None
        for w in cap_list_workflows():
            if w.id == workflow_id:
                workflow_cls = w.factory
                break
        if workflow_cls is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        def _run():
            from core.public_api import RunLedger, PolicyEngine
            ledger = RunLedger.create(repo_root, f"api-{workflow_id}")
            registry = build_model_registry()
            policy = PolicyEngine()
            wf = workflow_cls(registry, tool_registry, policy, ledger)
            return wf.run(repo_root, metadata=request.params)

        run_id = run_executor.submit(_run)
        return ExecuteResponse(run_id=run_id, status="pending")

    @app.get("/api/presets", response_model=list[PresetListItem], tags=["presets"])
    def list_presets() -> list[PresetListItem]:
        """List available presets."""
        return CATALOG.list()

    @app.post(
        "/api/presets/{preset_id}/run",
        response_model=ExecuteResponse,
        tags=["presets"],
        dependencies=[Depends(rate_limiter.check)],
    )
    def run_preset(
        preset_id: str,
        request: PresetRunRequest,
        api_key: str = Depends(verify_api_key),
    ) -> ExecuteResponse:
        """Run a preset asynchronously. Returns a run ID for polling."""
        from presets import PRESET_REGISTRY

        try:
            preset = PRESET_REGISTRY.get(preset_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")

        try:
            inputs = preset.validate_inputs(request.inputs)
        except PresetInputError as exc:
            raise HTTPException(status_code=400, detail=exc.to_dict()) from exc

        run_id = run_executor.submit(preset.run, inputs)
        return ExecuteResponse(run_id=run_id, status="pending")

    @app.get("/api/memory/{scope}/{key}", response_model=MemoryReadResponse, tags=["memory"])
    def read_memory(scope: str, key: str) -> MemoryReadResponse:
        """Read a value from the memory bus."""
        value = memory_bus.read(scope, key)
        return MemoryReadResponse(
            scope=scope,
            key=key,
            value=value,
            found=value is not None,
        )

    @app.post("/api/memory/{scope}/{key}", response_model=MemoryWriteResponse, tags=["memory"])
    def write_memory(
        scope: str,
        key: str,
        request: MemoryWriteRequest,
        api_key: str = Depends(verify_api_key),
    ) -> MemoryWriteResponse:
        """Write a value to the memory bus."""
        memory_bus.write(scope, key, request.value)
        return MemoryWriteResponse(scope=scope, key=key)

    @app.get("/api/models", response_model=list[ModelListItem], tags=["models"])
    def list_models() -> list[ModelListItem]:
        """List configured models and their capabilities."""
        try:
            registry = build_model_registry()
            return [
                ModelListItem(
                    model_id=model.id,
                    provider=model.config.provider,
                    capabilities=sorted(model.capabilities),
                )
                for model in registry.list_models()
            ]
        except (ConfigError, ValueError):
            return []
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to list models: {exc}") from exc

    @app.get("/api/providers", response_model=list[ProviderListItem], tags=["providers"])
    def list_providers() -> list[ProviderListItem]:
        """List providers and their health status."""
        providers = [ProviderListItem(provider_id=provider_id) for provider_id in sorted(DEFAULT_PROVIDER_MAP)]
        for p in providers:
            available, healthy, configured, error = _check_provider_health(p.provider_id)
            p.available = available
            p.healthy = healthy
            p.configured = configured
            p.error = error
        return providers

    @app.get("/api/providers/templates", response_model=list[ProviderTemplateItem], tags=["providers"])
    def provider_templates() -> list[ProviderTemplateItem]:
        return [ProviderTemplateItem(**item) for item in list_provider_templates(include_experimental=False)]

    @app.post("/api/providers", response_model=ProviderMutationResponse, tags=["providers"], dependencies=[Depends(rate_limiter.check)])
    def add_provider(request: ProviderAddRequest, api_key: str = Depends(verify_api_key)) -> ProviderMutationResponse:
        try:
            document = load_profiles_document()
        except ConfigError:
            document = ProfilesDocument(profiles={request.profile: TeamProfile(name=request.profile)})
        profile = document.profiles.setdefault(request.profile, TeamProfile(name=request.profile))
        secret_ref = make_secret_ref(request.provider_id)
        provider = provider_account_from_template(request.provider_id, request.template, endpoint=request.endpoint, secret_ref=secret_ref)
        if provider.auth_mode in {"api_key", "bearer", "x_api_key", "bedrock_api_key"}:
            if not request.api_key:
                raise HTTPException(status_code=400, detail="api_key required for this provider auth mode")
            get_secret_store().set(secret_ref, request.api_key)
        else:
            provider = provider.model_copy(update={"secret_ref": None})
        profile.providers[request.provider_id] = provider
        profile.models[request.role.value] = ModelBinding(
            id=request.role.value,
            role=request.role,
            provider=request.provider_id,
            model=request.model,
            capabilities=request.capabilities,
        )
        document.default_profile = request.profile
        save_profiles_document(document)
        return ProviderMutationResponse(status="written", profile=request.profile)

    @app.post("/api/providers/assign", response_model=ProviderMutationResponse, tags=["providers"], dependencies=[Depends(rate_limiter.check)])
    def assign_provider(request: ProviderAssignRequest, api_key: str = Depends(verify_api_key)) -> ProviderMutationResponse:
        document = load_profiles_document()
        profile = document.profiles.get(request.profile)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Profile '{request.profile}' not found")
        if request.provider_id not in profile.providers:
            raise HTTPException(status_code=404, detail=f"Provider '{request.provider_id}' not found")
        profile.models[request.role.value] = ModelBinding(
            id=request.role.value,
            role=request.role,
            provider=request.provider_id,
            model=request.model,
            capabilities=request.capabilities,
        )
        save_profiles_document(document)
        return ProviderMutationResponse(status="written", profile=request.profile)

    @app.get("/api/runs/{run_id}", response_model=CanonicalRunSummary, tags=["runs"])
    def get_run_status(run_id: str) -> CanonicalRunSummary:
        """Get the status of a run."""
        # First check in-memory executor
        record = run_executor.get(run_id)
        if record is not None:
            return _run_status_payload(run_id, record)

        # Fallback to disk
        run_dir = repo_root / ".ai-team" / "runs" / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        return _run_status_payload(run_id)

    @app.get("/api/runs/{run_id}/stream", tags=["runs"])
    def stream_run_status(run_id: str):
        """Stream run status updates via Server-Sent Events."""
        import asyncio

        record = run_executor.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        async def _event_generator():
            import json
            last_status = None
            # Yield initial status immediately
            yield f"data: {json.dumps(_run_status_payload(run_id, record).model_dump(mode='json'))}\n\n"
            for _ in range(3600):  # Max ~1 hour of streaming
                await asyncio.sleep(1)
                current = run_executor.get(run_id)
                if current is None:
                    break
                if current.status.value != last_status:
                    last_status = current.status.value
                    payload = _run_status_payload(run_id, current).model_dump(mode="json")
                    yield f"data: {json.dumps(payload)}\n\n"
                if current.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                    break
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _event_generator(),
            media_type="text/event-stream",
        )

    @app.get("/api/metrics", response_class=PlainTextResponse, tags=["system"])
    def metrics() -> str:
        """Prometheus-compatible metrics endpoint."""
        from monitoring.metrics import MetricsCollector
        collector = MetricsCollector()
        return collector.get_prometheus_metrics()

    @app.post("/api/ctx/init", tags=["ctx"])
    def ctx_init(request: CtxInitRequest):
        ops = _get_ops()
        try:
            ops.init(Path(request.project).resolve())
        except Exception as exc:
            _ctx_exc(exc)
        return {"status": "ok"}

    @app.post("/api/ctx/scan", response_model=CtxScanResponse, tags=["ctx"])
    def ctx_scan(request: CtxScanRequest):
        ops = _get_ops()
        try:
            inventory = ops.scan(Path(request.project).resolve())
        except Exception as exc:
            _ctx_exc(exc)
        raw = inventory.raw
        file_count = len(raw.files) if raw and hasattr(raw, "files") else 0
        manifest_count = len(raw.manifests) if raw and hasattr(raw, "manifests") else 0
        return CtxScanResponse(
            repo_root=inventory.repo_root,
            head_commit=inventory.head_commit,
            branch=getattr(raw, "branch", "") if raw else "",
            dirty_state=getattr(raw, "dirty_state", False) if raw else False,
            file_count=file_count,
            manifest_count=manifest_count,
        )

    @app.post("/api/ctx/run", response_model=CtxRunResponse, tags=["ctx"])
    def ctx_run(request: CtxRunRequest):
        import uuid
        ops = _get_ops()
        run_id = f"api-ctx-{uuid.uuid4().hex[:8]}"
        try:
            report = ops.run_pipeline(
                repo_root=Path(request.project).resolve(),
                run_id=run_id,
                scope=request.scope,
                write_mode=request.write_mode,
                allow_dirty=request.allow_dirty,
            )
        except Exception as exc:
            _ctx_exc(exc)
        return CtxRunResponse(
            run_id=run_id,
            generated_files=report.generated_files or [],
            patch_text=report.patch_text or "",
            timing=report.timing or {},
            entropy=report.entropy or {},
        )

    @app.post("/api/ctx/verify", response_model=CtxVerifyResponse, tags=["ctx"])
    def ctx_verify(request: CtxVerifyRequest):
        ops = _get_ops()
        try:
            result = ops.verify(Path(request.project).resolve(), strict=request.strict)
        except Exception as exc:
            _ctx_exc(exc)
        return CtxVerifyResponse(result=result.result, is_pass=result.is_pass)

    @app.post("/api/ctx/status", response_model=CtxStatusResponse, tags=["ctx"])
    def ctx_status(request: CtxStatusRequest):
        ops = _get_ops()
        try:
            result = ops.status(Path(request.project).resolve(), strict=request.strict)
        except Exception as exc:
            _ctx_exc(exc)
        return CtxStatusResponse(
            is_stale=result.is_stale,
            stale_sources=result.stale_sources or [],
            missing_sources=result.missing_sources or [],
            next_command=result.next_command,
        )

    @app.post("/api/ctx/clean", response_model=CtxCleanResponse, tags=["ctx"])
    def ctx_clean(request: CtxCleanRequest):
        ops = _get_ops()
        try:
            result = ops.clean(
                Path(request.project).resolve(),
                run_id=request.run_id,
                keep_runs=request.keep_runs,
            )
        except Exception as exc:
            _ctx_exc(exc)
        return CtxCleanResponse(
            removed_count=result.removed_count,
            kept_count=result.kept_count,
            removed_paths=result.removed_paths or [],
        )

    @app.post("/api/ctx/public-docs/impact", response_model=CtxPublicDocsImpactResponse, tags=["ctx"])
    def ctx_public_docs_impact(request: CtxPublicDocsImpactRequest):
        ops = _get_ops()
        try:
            result = ops.public_docs_impact(Path(request.project).resolve(), scope=request.scope)
        except Exception as exc:
            _ctx_exc(exc)
        return CtxPublicDocsImpactResponse(entries=result.entries or [])

    @app.post("/api/ctx/public-docs/update", response_model=CtxPublicDocsUpdateResponse, tags=["ctx"])
    def ctx_public_docs_update(request: CtxPublicDocsUpdateRequest):
        ops = _get_ops()
        try:
            path = ops.public_docs_update(
                Path(request.project).resolve(),
                scope=request.scope,
                write_mode=request.write_mode,
            )
        except Exception as exc:
            _ctx_exc(exc)
        return CtxPublicDocsUpdateResponse(patch_path=str(path) if path else None)

    @app.websocket("/api/runs/{run_id}/ws")
    async def websocket_run_status(websocket: WebSocket, run_id: str):
        """Stream run status updates via WebSocket."""
        import asyncio
        import json

        await websocket.accept()
        record = run_executor.get(run_id)
        if record is None:
            await websocket.close(code=1008, reason="Run not found")
            return

        queue: asyncio.Queue[RunRecord] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def on_update(r: RunRecord):
            try:
                asyncio.run_coroutine_threadsafe(queue.put(r), loop)
            except Exception:
                pass

        run_executor.subscribe(run_id, on_update)
        try:
            await websocket.send_json(_run_status_payload(run_id, record).model_dump(mode="json"))
            if record.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                await websocket.close()
                return
            while True:
                record = await queue.get()
                payload = _run_status_payload(run_id, record).model_dump(mode="json")
                await websocket.send_json(payload)
                if record.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                    await websocket.close()
                    break
        except WebSocketDisconnect:
            pass
        finally:
            run_executor.unsubscribe(run_id, on_update)

    return app
