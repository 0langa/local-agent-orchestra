"""FastAPI web UI for Agentheim local dashboard and API."""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config.config import list_provider_templates, load_profiles_document
from core.public_api import (
    CanonicalRunSummary,
    RunExecutor,
    RunRecord,
    RunStatus,
    ToolContext,
    ToolInvoker,
    build_model_registry,
    error_summary,
    interface_policy_config,
    list_run_views,
    list_workflows as cap_list_workflows,
)
from interfaces.common.run_views import run_status_payload
from memory.bus import MemoryBus
from tools.registry import ToolRegistry, create_core_tool_registry

from agentheim.context_ops_impl import AictxContextOps
from agentheim.vendor.aictx.config import AictxConfig
from agentheim.vendor.aictx.errors import SafetyError
from interfaces.readiness import ReadinessState, build_readiness_state
from interfaces.tool_approval import InterfaceApprovalStore
from presets.base import PresetInputError
from presets.catalog import CATALOG, QuestionSchema

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Pydantic models (module-level for FastAPI compatibility)
# ------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class ToolListItem(BaseModel):
    tool_id: str
    risk_level: str
    description: str


class ToolInvokeRequest(BaseModel):
    tool_id: str
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
    support_state: str = "unknown"


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


class HomeTaskGroup(BaseModel):
    title: str
    tasks: list[PresetListItem] = Field(default_factory=list)


class HomeResponse(BaseModel):
    readiness: ReadinessState
    provider_cta: str
    recommended_tasks: list[PresetListItem] = Field(default_factory=list)
    advanced_tasks: list[PresetListItem] = Field(default_factory=list)
    recent_runs: list[dict[str, Any]] = Field(default_factory=list)
    optional_integrations: list[dict[str, Any]] = Field(default_factory=list)
    version: str = "0.1.0"


class ExecuteRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)


class ExecuteResponse(BaseModel):
    run_id: str
    status: str


class ProviderTemplateItem(BaseModel):
    kind: str
    display_name: str
    endpoint: str
    auth_mode: str
    provider_type: str
    capabilities: list[str] = Field(default_factory=list)
    docs_url: str
    support_state: str = "unknown"


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


class CtxInitRequest(BaseModel):
    project_path: str = "."


class CtxScanRequest(BaseModel):
    project_path: str = "."


class CtxRunRequest(BaseModel):
    project_path: str = "."
    scope: str = "full"
    write_mode: str = "patch"
    allow_dirty: bool = False


class CtxVerifyRequest(BaseModel):
    project_path: str = "."
    strict: bool = False


class CtxStatusRequest(BaseModel):
    project_path: str = "."
    strict: bool = False


class CtxCleanRequest(BaseModel):
    project_path: str = "."
    run_id: str | None = None
    keep_runs: int | None = None


class CtxPublicDocsImpactRequest(BaseModel):
    project_path: str = "."
    scope: str = "full"


class CtxPublicDocsUpdateRequest(BaseModel):
    project_path: str = "."
    scope: str = "changed"
    write_mode: str = "patch"


# ------------------------------------------------------------------
# App factory
# ------------------------------------------------------------------

def create_app(repo_root: str | Path = ".") -> FastAPI:
    """Create and configure the FastAPI application."""
    repo_root = Path(repo_root).resolve()
    try:
        app_version = package_version("agentheim")
    except PackageNotFoundError:
        app_version = "0.1.0"

    app = FastAPI(
        title="Agentheim",
        description="Local Agentheim dashboard and API",
        version=app_version,
    )

    @app.middleware("http")
    async def _structured_error_middleware(request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            from core.public_api import catalog_entry_for, format_api_response

            entry = catalog_entry_for(exc)
            return JSONResponse(
                status_code=entry.http_status,
                content=format_api_response(entry, exc),
            )

    tool_registry = ToolRegistry(repo_root)
    core_tool_registry = create_core_tool_registry(repo_root)
    tool_invoker = ToolInvoker(registry=core_tool_registry, policy_config=interface_policy_config())
    approval_store = InterfaceApprovalStore(repo_root, "web-tool-approval")
    memory_bus = MemoryBus(repo_root)
    run_executor = RunExecutor()
    from interfaces.run_hooks import register_default_run_hooks

    register_default_run_hooks(run_executor)
    aictx_config = AictxConfig()

    # Serve static files if the directory exists
    static_dir = Path(__file__).parent / "static"
    if static_dir.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

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

    def _preset_item(preset_id: str) -> PresetListItem:
        return PresetListItem(**CATALOG.get(preset_id).model_dump())

    def _home_payload() -> HomeResponse:
        readiness = build_readiness_state(skip_connectivity=True, check_optional_integrations=True)
        recommended = [_preset_item(item.preset_id) for item in CATALOG.recommended()]
        advanced = [_preset_item(item.preset_id) for item in CATALOG.advanced()]
        recent_runs = [view.model_dump(mode="json") for view in list_run_views(repo_root)[:5]]
        provider_cta = (
            "Connect a provider in the CLI with `agentheim setup` to unlock guided tasks."
            if readiness.status != "ready"
            else "Provider is ready. Pick a recommended task to get started."
        )
        return HomeResponse(
            readiness=readiness,
            provider_cta=provider_cta,
            recommended_tasks=recommended,
            advanced_tasks=advanced,
            recent_runs=recent_runs,
            optional_integrations=[item.model_dump(mode="json") for item in readiness.optional_integrations],
            version=app_version,
        )

    @app.get("/", response_class=HTMLResponse)
    def root() -> str:
        """Serve the Agentheim dashboard."""
        return _dashboard_html(app_version)

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=app_version)

    @app.get("/api/status", response_model=HomeResponse)
    def status() -> HomeResponse:
        """Return product home screen data for the dashboard."""
        return _home_payload()

    @app.get("/api/tasks", response_model=list[PresetListItem])
    def tasks() -> list[PresetListItem]:
        """Return product-facing tasks for the home screen."""
        return [_preset_item(item.preset_id) for item in CATALOG.list() if item.product_tier in {"recommended", "advanced"}]

    @app.get("/api/tools", response_model=list[ToolListItem])
    def list_tools() -> list[ToolListItem]:
        """List all available tools with their risk levels."""
        items = []
        for tool in tool_registry.tool_objects():
            if hasattr(tool, "tool_id") and hasattr(tool, "schema"):
                items.append(
                    ToolListItem(
                        tool_id=tool.tool_id,
                        risk_level=tool.risk_level.value,
                        description=tool.schema.description,
                    )
                )
        return sorted(items, key=lambda x: x.tool_id)

    @app.post("/api/tools/invoke", response_model=ToolInvokeResponse)
    def invoke_tool(body: ToolInvokeRequest) -> ToolInvokeResponse:
        """Invoke a tool with the given parameters."""
        tool = None
        for candidate in tool_registry.tool_objects():
            if getattr(candidate, "tool_id", None) == body.tool_id:
                tool = candidate
                break

        if tool is None:
            raise HTTPException(status_code=404, detail=f"Tool '{body.tool_id}' not found")

        ctx = ToolContext(network_allowed=False, workspace=repo_root, allowed_paths=[str(repo_root)])
        ledger = approval_store.create_ledger(body.tool_id, interface_name="web")
        result = tool_invoker.invoke(body.tool_id, body.params, ctx, ledger=ledger)
        if result.requires_approval:
            approval_request = approval_store.add(
                tool_id=body.tool_id,
                params=body.params,
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
                detail=f"Tool '{body.tool_id}' blocked by policy: {result.error}",
            )

        return ToolInvokeResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata or {},
            requires_approval=result.requires_approval,
            policy=_policy_to_dict(result.policy),
        )

    @app.post("/api/tools/approvals/{request_id}/grant", response_model=ApprovalDecisionResponse)
    def grant_tool_approval(request_id: str) -> ApprovalDecisionResponse:
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

    @app.post("/api/tools/approvals/{request_id}/deny", response_model=ApprovalDecisionResponse)
    def deny_tool_approval(request_id: str) -> ApprovalDecisionResponse:
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

    @app.get("/api/workflows", response_model=list[WorkflowListItem])
    def list_workflows() -> list[WorkflowListItem]:
        """List registered workflows."""
        _import_workflows()

        return [
            WorkflowListItem(
                workflow_id=w.id,
                name=w.id.replace("_", " ").title(),
                description=w.metadata.get("description", "") or "",
                support_state=w.metadata.get("support_state", "unknown"),
            )
            for w in cap_list_workflows()
        ]

    @app.post("/api/workflows/{workflow_id}/execute", response_model=ExecuteResponse)
    def execute_workflow(workflow_id: str, body: ExecuteRequest) -> ExecuteResponse:
        """Execute a workflow asynchronously."""
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
            ledger = RunLedger.create(repo_root, f"webui-{workflow_id}")
            registry = build_model_registry()
            policy = PolicyEngine()
            wf = workflow_cls(registry, tool_registry, policy, ledger)
            return wf.run(repo_root, metadata=body.inputs)

        run_id = run_executor.submit(_run)
        return ExecuteResponse(run_id=run_id, status="pending")

    @app.get("/api/presets", response_model=list[PresetListItem])
    def list_presets() -> list[PresetListItem]:
        """List available presets."""
        return CATALOG.list()

    @app.get("/api/providers/templates", response_model=list[ProviderTemplateItem])
    def provider_templates() -> list[ProviderTemplateItem]:
        return [ProviderTemplateItem(**item) for item in list_provider_templates(include_experimental=False)]

    @app.get("/api/providers/profiles")
    def provider_profiles() -> dict[str, Any]:
        try:
            document = load_profiles_document()
        except Exception as exc:
            return {"configured": False, "error": str(exc), "profiles": []}
        return {
            "configured": True,
            "default_profile": document.default_profile,
            "profiles": [
                {
                    "name": profile.name,
                    "providers": [
                        {
                            "id": provider.id,
                            "kind": provider.kind,
                            "auth_mode": provider.auth_mode,
                            "endpoint": provider.endpoint,
                            "has_secret": bool(provider.secret_ref),
                        }
                        for provider in profile.providers.values()
                    ],
                    "models": [binding.model_dump() for binding in profile.models.values()],
                }
                for profile in document.profiles.values()
            ],
        }

    @app.post("/api/presets/{preset_id}/run", response_model=ExecuteResponse)
    def run_preset(preset_id: str, body: ExecuteRequest) -> ExecuteResponse:
        """Run a preset asynchronously."""
        from presets import PRESET_REGISTRY

        try:
            preset = PRESET_REGISTRY.get(preset_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")

        try:
            inputs = preset.validate_inputs(body.inputs)
        except PresetInputError as exc:
            return JSONResponse(status_code=400, content=exc.to_dict())

        run_id = run_executor.submit(preset.run, inputs)
        return ExecuteResponse(run_id=run_id, status="pending")

    @app.get("/api/runs/{run_id}", response_model=CanonicalRunSummary)
    def get_run_status(run_id: str) -> CanonicalRunSummary:
        """Get the status of a run."""
        record = run_executor.get(run_id)
        if record is not None:
            return run_status_payload(repo_root, run_id, record)

        run_dir = repo_root / ".ai-team" / "runs" / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        return run_status_payload(repo_root, run_id)

    @app.get("/api/runs/{run_id}/stream")
    def stream_run_status(run_id: str):
        """Stream run status updates via Server-Sent Events."""
        import asyncio
        import json

        record = run_executor.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        async def _event_generator():
            last_status = None
            yield f"data: {json.dumps(run_status_payload(repo_root, run_id, record).model_dump(mode='json'))}\n\n"
            for _ in range(3600):
                await asyncio.sleep(1)
                current = run_executor.get(run_id)
                if current is None:
                    break
                if current.status.value != last_status:
                    last_status = current.status.value
                    payload = run_status_payload(repo_root, run_id, current).model_dump(mode="json")
                    yield f"data: {json.dumps(payload)}\n\n"
                if current.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                    break
            yield "data: [DONE]\n\n"

        return StreamingResponse(_event_generator(), media_type="text/event-stream")

    @app.get("/api/memory/{scope}/{key}", response_model=MemoryReadResponse)
    def read_memory(scope: str, key: str) -> MemoryReadResponse:
        """Read a value from the memory bus."""
        value = memory_bus.read(scope, key)
        return MemoryReadResponse(
            scope=scope,
            key=key,
            value=value,
            found=value is not None,
        )

    @app.post("/api/memory/{scope}/{key}", response_model=MemoryWriteResponse)
    def write_memory(scope: str, key: str, body: MemoryWriteRequest) -> MemoryWriteResponse:
        """Write a value to the memory bus."""
        memory_bus.write(scope, key, body.value)
        return MemoryWriteResponse(scope=scope, key=key)

    def _ctx_exc(exc: Exception):
        summary = error_summary(exc)
        status_code = 500
        if isinstance(exc, ValueError):
            status_code = 400
        if isinstance(exc, SafetyError):
            status_code = 409
        return JSONResponse(status_code=status_code, content=summary)

    @app.post("/api/ctx/init")
    def ctx_init(body: CtxInitRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            ops.init(Path(body.project_path))
            return {"ok": True}
        except Exception as exc:
            return _ctx_exc(exc)

    @app.post("/api/ctx/scan")
    def ctx_scan(body: CtxScanRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            inventory = ops.scan(Path(body.project_path))
            return {"repo_root": inventory.repo_root, "head_commit": inventory.head_commit}
        except Exception as exc:
            return _ctx_exc(exc)

    @app.post("/api/ctx/run")
    def ctx_run(body: CtxRunRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            report = ops.run_pipeline(
                repo_root=Path(body.project_path),
                run_id="webui-ctx",
                scope=body.scope,
                write_mode=body.write_mode,
                allow_dirty=body.allow_dirty,
            )
            return {
                "generated_files": report.generated_files,
                "lockfile_path": report.lockfile_path,
                "patch_text": report.patch_text,
            }
        except Exception as exc:
            return _ctx_exc(exc)

    @app.post("/api/ctx/verify")
    def ctx_verify(body: CtxVerifyRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            result = ops.verify(Path(body.project_path), strict=body.strict)
            return {"result": result.result, "is_pass": result.is_pass}
        except Exception as exc:
            return _ctx_exc(exc)

    @app.post("/api/ctx/status")
    def ctx_status(body: CtxStatusRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            st = ops.status(Path(body.project_path), strict=body.strict)
            return {
                "is_stale": st.is_stale,
                "stale_sources": st.stale_sources,
                "missing_sources": st.missing_sources,
                "missing_generated": st.missing_generated,
                "generated_mismatches": st.generated_mismatches,
                "public_docs_impacts": st.public_docs_impacts,
                "next_command": st.next_command,
            }
        except Exception as exc:
            return _ctx_exc(exc)

    @app.post("/api/ctx/clean")
    def ctx_clean(body: CtxCleanRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            result = ops.clean(Path(body.project_path), run_id=body.run_id, keep_runs=body.keep_runs)
            return {
                "removed_count": result.removed_count,
                "kept_count": result.kept_count,
                "removed_paths": result.removed_paths,
            }
        except Exception as exc:
            return _ctx_exc(exc)

    @app.post("/api/ctx/public-docs/impact")
    def ctx_public_docs_impact(body: CtxPublicDocsImpactRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            report = ops.public_docs_impact(Path(body.project_path), scope=body.scope)
            return {"entries": report.entries}
        except Exception as exc:
            return _ctx_exc(exc)

    @app.post("/api/ctx/public-docs/update")
    def ctx_public_docs_update(body: CtxPublicDocsUpdateRequest) -> dict[str, Any]:
        try:
            ops = AictxContextOps(aictx_config)
            patch_path = ops.public_docs_update(
                Path(body.project_path),
                scope=body.scope,
                write_mode=body.write_mode,
            )
            return {"patch_path": str(patch_path) if patch_path else None}
        except Exception as exc:
            return _ctx_exc(exc)

    @app.websocket("/api/runs/{run_id}/ws")
    async def websocket_run_status(websocket: WebSocket, run_id: str):
        """Stream run status updates via WebSocket."""
        import asyncio

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
            await websocket.send_json(run_status_payload(repo_root, run_id, record).model_dump(mode="json"))
            if record.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                await websocket.close()
                return
            while True:
                record = await queue.get()
                payload = run_status_payload(repo_root, run_id, record).model_dump(mode="json")
                await websocket.send_json(payload)
                if record.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                    await websocket.close()
                    break
        except WebSocketDisconnect:
            pass
        finally:
            run_executor.unsubscribe(run_id, on_update)

    return app


def _import_workflows() -> None:
    """Register all workflow packs explicitly."""
    try:
        from workflows.registry import register_builtin_workflows

        register_builtin_workflows()
    except Exception as exc:
        logger.warning("Failed to register builtin workflows: %s", exc)


def _dashboard_html(app_version: str) -> str:
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agentheim</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }
  h1 { font-size: 1.75rem; margin-bottom: 0.5rem; }
  .subtitle { color: #94a3b8; margin-bottom: 2rem; }
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}
  .card { background: #1e293b; border-radius: 0.5rem; padding: 1.25rem; border: 1px solid #334155; }
  .card h2 { font-size: 1.1rem; margin-bottom: 0.75rem; color: #60a5fa; }
  .card ul { list-style: none; }
  .card li { padding: 0.35rem 0; border-bottom: 1px solid #334155; font-size: 0.9rem; }
  .card li:last-child { border-bottom: none; }
  .risk-high { color: #f87171; }
  .risk-medium { color: #fbbf24; }
  .risk-low { color: #34d399; }
  .risk-none { color: #94a3b8; }
  .badge { font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 0.25rem; background: #334155; margin-left: 0.5rem; }
  .state-stable { background: #064e3b; color: #34d399; }
  .state-stable_candidate { background: #064e3b; color: #34d399; }
  .state-beta { background: #713f12; color: #fbbf24; }
  .state-experimental { background: #4c0519; color: #f87171; }
  .state-unknown { background: #334155; color: #94a3b8; }
  .legend { margin-top: 1.5rem; font-size: 0.8rem; color: #94a3b8; }
  .legend .badge { margin-right: 0.5rem; margin-left: 0; }
  #status { margin-bottom: 1.5rem; font-size: 0.85rem; color: #34d399; }
  .loading { color: #94a3b8; }
  .error { color: #f87171; }
  .ctx-section { margin-top: 2rem; }
  .ctx-section h2 { font-size: 1.1rem; margin-bottom: 0.75rem; color: #60a5fa; }
  .ctx-form { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem; }
  .ctx-form label { font-size: 0.85rem; color: #94a3b8; }
  .ctx-form input, .ctx-form select { background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 0.35rem 0.5rem; border-radius: 0.25rem; font-size: 0.85rem; }
  .ctx-form button { background: #2563eb; border: none; color: #fff; padding: 0.4rem 0.75rem; border-radius: 0.25rem; cursor: pointer; font-size: 0.85rem; }
  .ctx-form button:hover { background: #1d4ed8; }
  .ctx-results { background: #0f172a; border: 1px solid #334155; border-radius: 0.5rem; padding: 1rem; margin-top: 1rem; min-height: 120px; font-family: ui-monospace, monospace; font-size: 0.8rem; white-space: pre-wrap; overflow-x: auto; color: #e2e8f0; }
  .run-btn { background: #2563eb; border: none; color: #fff; padding: 0.2rem 0.5rem; border-radius: 0.25rem; cursor: pointer; font-size: 0.75rem; margin-left: 0.5rem; }
  .run-btn:hover { background: #1d4ed8; }
  .run-status { font-size: 0.75rem; color: #94a3b8; margin-left: 0.5rem; }
  .run-completed { color: #34d399; }
  .run-failed { color: #f87171; }
  .run-artifacts { margin-top: 0.35rem; font-size: 0.75rem; }
  .run-error { margin-top: 0.35rem; font-size: 0.75rem; color: #f87171; }
    .task-group { margin-top: 1rem; }
    .task-group h3 { font-size: 0.95rem; margin-bottom: 0.5rem; color: #cbd5e1; }
    .preset-question { display: block; margin-top: 0.4rem; font-size: 0.8rem; }
    .preset-question input, .preset-question select { margin-top: 0.2rem; width: 100%; background: #0f172a; border: 1px solid #334155; color: #e2e8f0; padding: 0.35rem 0.45rem; border-radius: 0.25rem; }
    .task-meta { font-size: 0.78rem; color: #94a3b8; margin-top: 0.3rem; }
    .run-btn[disabled] { opacity: 0.5; cursor: not-allowed; }
</style>
</head>
<body>
<h1>Agentheim</h1>
<p class="subtitle">Local agent workflow dashboard</p>
<div id="status">Loading...</div>
<div class="grid">
  <div class="card">
        <h2>Readiness</h2>
        <ul id="readiness-list"><li class="loading">Loading...</li></ul>
  </div>
  <div class="card">
        <h2>Connect Provider</h2>
        <p id="provider-cta" class="loading">Loading...</p>
        <ul id="providers-list"><li class="loading">Loading...</li></ul>
  </div>
  <div class="card">
        <h2>Recommended Tasks</h2>
        <div id="recommended-tasks"><p class="loading">Loading...</p></div>
  </div>
  <div class="card">
        <h2>Advanced Tasks</h2>
        <div id="advanced-tasks"><p class="loading">Loading...</p></div>
  </div>
  <div class="card">
        <h2>Recent Runs</h2>
        <ul id="runs-list"><li class="loading">Loading...</li></ul>
    </div>
    <div class="card">
        <h2>Optional Integrations</h2>
        <ul id="integrations-list"><li class="loading">Loading...</li></ul>
  </div>
</div>
<div class="legend">
  <span class="badge state-stable">stable</span> default path
  <span class="badge state-beta">beta</span> real use, known limits
  <span class="badge state-experimental">experimental</span> not baseline-critical
</div>
<div class="ctx-section">
  <h2>Context Operations</h2>
  <div class="ctx-form">
    <label>Project path</label>
    <input type="text" id="ctx-project-path" value="." style="width: 200px;">
  </div>
  <div class="ctx-form">
    <button onclick="ctxAction('init')">Init</button>
    <button onclick="ctxAction('scan')">Scan</button>
    <button onclick="ctxAction('verify')">Verify</button>
    <button onclick="ctxAction('status')">Status</button>
  </div>
  <div class="ctx-form">
    <label>Scope</label>
    <select id="ctx-run-scope">
      <option value="full">full</option>
      <option value="changed">changed</option>
    </select>
    <label>Write mode</label>
    <select id="ctx-run-mode">
      <option value="patch">patch</option>
      <option value="apply">apply</option>
    </select>
    <label><input type="checkbox" id="ctx-run-dirty"> Allow dirty</label>
    <button onclick="ctxRun()">Run</button>
  </div>
  <div class="ctx-form">
    <label>Scope</label>
    <select id="ctx-docs-scope">
      <option value="full">full</option>
      <option value="changed">changed</option>
    </select>
    <button onclick="ctxDocs('impact')">Impact</button>
    <button onclick="ctxDocs('update')">Update</button>
  </div>
  <div id="ctx-results" class="ctx-results">Results will appear here...</div>
</div>
<script>
async function fetchJSON(url, options) {
  try {
    const r = await fetch(url, options);
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    return await r.json();
  } catch (e) {
    return { error: e.message };
  }
}
function clearElement(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
}
function textNode(tag, text, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = text;
    return el;
}
function badge(text, className) {
    const span = document.createElement('span');
    span.className = className ? 'badge ' + className : 'badge';
    span.textContent = text;
    return span;
}
function listMessage(listEl, message, className) {
    clearElement(listEl);
    const li = document.createElement('li');
    if (className) li.className = className;
    li.textContent = message;
    listEl.appendChild(li);
}
function isQuestionFilled(question, value) {
    if (question.type === 'confirm') return true;
    return String(value || '').trim().length > 0;
}
function requiredQuestions(preset) {
    return (preset.questions || []).filter(q => q.default === null || q.default === undefined || q.default === '');
}
function inputsReady(preset) {
    const inputs = collectPresetInputs(preset.preset_id);
    return requiredQuestions(preset).every(q => isQuestionFilled(q, inputs[q.key]));
}
function updateRunButtons() {
    document.querySelectorAll('.run-btn[data-preset-id]').forEach(btn => {
        const presetId = btn.getAttribute('data-preset-id');
        const preset = window.agentheimTasksById[presetId];
        if (!preset) return;
        btn.disabled = !inputsReady(preset);
    });
}
function renderReadiness(readiness) {
    const list = document.getElementById('readiness-list');
    clearElement(list);
    const statusItem = document.createElement('li');
    statusItem.textContent = 'Status: ' + readiness.status;
    statusItem.appendChild(badge(readiness.profile_name || 'default', ''));
    list.appendChild(statusItem);
    const detailItem = document.createElement('li');
    detailItem.textContent = readiness.detail || 'Ready to start.';
    list.appendChild(detailItem);
    if (readiness.missing_roles && readiness.missing_roles.length) {
        const roles = document.createElement('li');
        roles.textContent = 'Missing roles: ' + readiness.missing_roles.join(', ');
        list.appendChild(roles);
    }
    (readiness.next_actions || []).forEach(action => {
        const li = document.createElement('li');
        li.textContent = action;
        list.appendChild(li);
    });
}
function renderProviders(providers, ctaText) {
    const cta = document.getElementById('provider-cta');
    cta.textContent = ctaText;
    cta.className = '';
    const list = document.getElementById('providers-list');
    if (providers.error) {
        listMessage(list, providers.error, 'error');
        return;
    }
    clearElement(list);
    if (!providers.configured || !providers.profiles.length) {
        listMessage(list, 'No providers configured yet.', 'loading');
        return;
    }
    providers.profiles.forEach(profile => {
        profile.providers.forEach(provider => {
            const li = document.createElement('li');
            li.appendChild(textNode('span', profile.name + ' / ' + provider.id));
            li.appendChild(badge(provider.kind));
            list.appendChild(li);
        });
    });
}
function createQuestionInput(preset, question) {
    const label = document.createElement('label');
    label.className = 'preset-question';
    label.textContent = question.text;
    let input;
    const value = question.default === null || question.default === undefined ? '' : question.default;
    if (question.options && question.options.length) {
        input = document.createElement('select');
        question.options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt;
            option.textContent = opt;
            if (String(opt) === String(value)) option.selected = true;
            input.appendChild(option);
        });
    } else if (question.type === 'confirm') {
        input = document.createElement('input');
        input.type = 'checkbox';
        input.checked = value === true;
    } else {
        input = document.createElement('input');
        input.type = 'text';
        input.value = String(value);
        input.placeholder = question.key;
    }
    input.setAttribute('data-preset-id', preset.preset_id);
    input.setAttribute('data-input-key', question.key);
    input.addEventListener('input', updateRunButtons);
    input.addEventListener('change', updateRunButtons);
    label.appendChild(input);
    return label;
}
function createTaskItem(preset) {
    const wrapper = document.createElement('div');
    wrapper.className = 'task-group';
    const title = document.createElement('h3');
    title.textContent = preset.name;
    wrapper.appendChild(title);
    wrapper.appendChild(textNode('p', preset.description));
    const meta = document.createElement('p');
    meta.className = 'task-meta';
    meta.textContent = 'Task ID: ' + preset.preset_id;
    wrapper.appendChild(meta);
    (preset.questions || []).forEach(question => wrapper.appendChild(createQuestionInput(preset, question)));
    const button = document.createElement('button');
    button.className = 'run-btn';
    button.textContent = 'Run';
    button.setAttribute('data-preset-id', preset.preset_id);
    button.addEventListener('click', () => runPreset(preset.preset_id));
    wrapper.appendChild(button);
    return wrapper;
}
function renderTaskSection(containerId, tasks, emptyText) {
    const container = document.getElementById(containerId);
    clearElement(container);
    if (!tasks.length) {
        container.appendChild(textNode('p', emptyText, 'loading'));
        return;
    }
    tasks.forEach(task => container.appendChild(createTaskItem(task)));
}
function renderIntegrations(items) {
    const list = document.getElementById('integrations-list');
    clearElement(list);
    if (!items.length) {
        listMessage(list, 'No optional integrations detected.', 'loading');
        return;
    }
    items.forEach(item => {
        const li = document.createElement('li');
        li.appendChild(textNode('span', item.integration_id));
        li.appendChild(badge(item.available ? 'available' : 'unavailable', item.available ? 'state-stable' : 'state-beta'));
        const detail = document.createElement('div');
        detail.className = item.available ? '' : 'error';
        detail.textContent = item.detail || item.next_action || '';
        li.appendChild(detail);
        list.appendChild(li);
    });
}
function renderRecentRuns(runs) {
    const runsList = document.getElementById('runs-list');
    clearElement(runsList);
    if (!runs.length) {
        listMessage(runsList, 'No recent runs yet.', 'loading');
        return;
    }
    runs.forEach(info => {
        const li = document.createElement('li');
        li.appendChild(textNode('span', (info.preset_id || info.workflow_id || 'run') + ' '));
        li.appendChild(badge(info.status || 'unknown'));
        li.appendChild(textNode('code', info.run_id));
        if (info.summary) li.appendChild(textNode('div', info.summary, 'task-meta'));
        runsList.appendChild(li);
    });
}
function riskClass(level) {
  const map = { high: 'risk-high', medium: 'risk-medium', low: 'risk-low', none: 'risk-none' };
  return map[level] || 'risk-none';
}
async function loadAll() {
  const status = document.getElementById('status');
    const [health, home, providers] = await Promise.all([
    fetchJSON('/api/health'),
        fetchJSON('/api/status'),
    fetchJSON('/api/providers/profiles')
  ]);

  if (health.error) {
    status.textContent = 'Error: ' + health.error;
    status.className = 'error';
    return;
  }
    status.textContent = 'API connected — v' + health.version;
    window.agentheimTasksById = Object.create(null);
    if (home.error) {
        status.textContent = 'Error: ' + home.error;
        status.className = 'error';
        return;
  }
    [...home.recommended_tasks, ...home.advanced_tasks].forEach(task => {{
        window.agentheimTasksById[task.preset_id] = task;
    }});
    renderReadiness(home.readiness);
    renderProviders(providers, home.provider_cta);
    renderTaskSection('recommended-tasks', home.recommended_tasks || [], 'No recommended tasks available.');
    renderTaskSection('advanced-tasks', home.advanced_tasks || [], 'No advanced tasks available.');
    renderIntegrations(home.optional_integrations || []);
    renderRecentRuns(home.recent_runs || []);
    updateRunButtons();
}
function collectPresetInputs(preset_id) {
  const inputs = {};
  document.querySelectorAll('[data-preset-id="' + preset_id + '"][data-input-key]').forEach(el => {
    const key = el.getAttribute('data-input-key');
    if (el.type === 'checkbox') inputs[key] = el.checked;
    else inputs[key] = el.value;
  });
  return inputs;
}
async function ctxAction(action) {
  const path = document.getElementById('ctx-project-path').value || '.';
  const results = document.getElementById('ctx-results');
  results.textContent = 'Loading...';
  const payload = { project_path: path };
  if (action === 'verify' || action === 'status') {
    payload.strict = false;
  }
  const data = await fetchJSON('/api/ctx/' + action, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  results.textContent = data.error ? 'Error: ' + data.error : JSON.stringify(data, null, 2);
}
async function ctxRun() {
  const path = document.getElementById('ctx-project-path').value || '.';
  const scope = document.getElementById('ctx-run-scope').value;
  const mode = document.getElementById('ctx-run-mode').value;
  const dirty = document.getElementById('ctx-run-dirty').checked;
  const results = document.getElementById('ctx-results');
  results.textContent = 'Loading...';
  const data = await fetchJSON('/api/ctx/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_path: path, scope: scope, write_mode: mode, allow_dirty: dirty })
  });
  results.textContent = data.error ? 'Error: ' + data.error : JSON.stringify(data, null, 2);
}
async function ctxDocs(action) {
  const path = document.getElementById('ctx-project-path').value || '.';
  const scope = document.getElementById('ctx-docs-scope').value;
  const results = document.getElementById('ctx-results');
  results.textContent = 'Loading...';
  const body = { project_path: path, scope: scope };
  if (action === 'update') {
    body.write_mode = 'patch';
  }
  const data = await fetchJSON('/api/ctx/public-docs/' + action, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  results.textContent = data.error ? 'Error: ' + data.error : JSON.stringify(data, null, 2);
}
const activeRuns = new Map();
async function runPreset(preset_id) {
    const runsList = document.getElementById('runs-list');
    listMessage(runsList, 'Starting ' + preset_id + '...', 'loading');
  const data = await fetchJSON('/api/presets/' + preset_id + '/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inputs: collectPresetInputs(preset_id) })
  });
  if (data.error) {
        listMessage(runsList, 'Failed to start ' + preset_id + ': ' + data.error, 'error');
    return;
  }
  const run_id = data.run_id;
  activeRuns.set(run_id, { preset_id, status: 'pending' });
  renderRuns();
  pollRun(run_id);
}
function renderRuns() {
  const runsList = document.getElementById('runs-list');
    clearElement(runsList);
    if (activeRuns.size === 0) { listMessage(runsList, 'No recent runs yet.', 'loading'); return; }
    Array.from(activeRuns.entries()).forEach(([run_id, info]) => {
        let statusClass = 'run-status';
        if (info.status === 'completed') statusClass += ' run-completed';
        if (info.status === 'failed') statusClass += ' run-failed';
        const li = document.createElement('li');
        li.appendChild(textNode('span', info.preset_id + ' '));
        li.appendChild(textNode('span', info.status, statusClass));
        li.appendChild(textNode('code', run_id));
        if (info.artifacts && info.artifacts.length) {
            const artifacts = document.createElement('div');
            artifacts.className = 'run-artifacts';
            artifacts.appendChild(textNode('span', 'Artifacts: '));
            info.artifacts.forEach(a => artifacts.appendChild(badge(a)));
            li.appendChild(artifacts);
        }
        if (info.error) {
            li.appendChild(textNode('div', info.error, 'run-error'));
        }
        runsList.appendChild(li);
    });
}
async function pollRun(run_id) {
  for (let i = 0; i < 120; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const data = await fetchJSON('/api/runs/' + run_id);
    if (data.error) { activeRuns.set(run_id, { ...activeRuns.get(run_id), status: 'error: ' + data.error }); renderRuns(); break; }
    activeRuns.set(run_id, { ...activeRuns.get(run_id), status: data.status, artifacts: data.artifacts || [], error: data.error_summary || data.error || null });
    renderRuns();
    if (['completed', 'failed', 'cancelled'].includes(data.status)) { break; }
  }
}
loadAll();
</script>
</body>
</html>
"""
    return html.replace("__AGENTHEIM_VERSION__", app_version)
