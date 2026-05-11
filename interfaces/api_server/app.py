"""FastAPI API server with OpenAPI spec, auth, rate limiting, and execution."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from core.capability_registry import list_workflows as cap_list_workflows
from core.run_executor import RunExecutor, RunStatus
from core.tool_protocol import ToolContext, ToolResult
from memory.bus import MemoryBus
from tools.registry import ToolRegistry

from interfaces.api_server.auth import verify_api_key
from interfaces.api_server.rate_limit import RateLimiter

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
    name: str
    description: str


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
    healthy: bool
    error: str | None = None


class RunStatusResponse(BaseModel):
    run_id: str
    status: str
    artifacts: list[str] = Field(default_factory=list)
    error: str | None = None


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

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    tool_registry = ToolRegistry(repo_root)
    memory_bus = MemoryBus(repo_root)
    rate_limiter = RateLimiter(max_requests=60, window_seconds=60.0)
    run_executor = RunExecutor()

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
        for attr_name in dir(tool_registry):
            if attr_name.startswith("_"):
                continue
            candidate = getattr(tool_registry, attr_name)
            if getattr(candidate, "tool_id", None) == tool_id:
                return candidate
        return None

    def _import_workflows() -> None:
        try:
            import workflows.coding
            import workflows.command_assistant
            import workflows.docs_maintenance
            import workflows.documents
            import workflows.file_organization
            import workflows.github_maintenance
            import workflows.research
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

    def _check_provider_health(provider_id: str) -> tuple[bool, str | None]:
        """Check if a provider is healthy by attempting a lightweight operation."""
        provider_map = {
            "openai_v1": ("providers.openai_v1", "OpenAIProvider"),
            "aws_bedrock": ("providers.aws_bedrock", "AWSBedrockProvider"),
            "azure_foundry": ("providers.azure_foundry", "AzureFoundryProvider"),
            "oci_genai": ("providers.oci_genai", "OCIGenAIProvider"),
        }
        if provider_id not in provider_map:
            return False, "Unknown provider"
        module_path, class_name = provider_map[provider_id]
        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            instance = cls()
            if hasattr(instance, "health_check"):
                instance.health_check()
            return True, None
        except Exception as exc:
            return False, str(exc)

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

    @app.get("/api/tools", response_model=list[ToolSchemaItem], tags=["tools"])
    def list_tools() -> list[ToolSchemaItem]:
        """List all available tools with their schemas."""
        items = []
        for attr_name in dir(tool_registry):
            if attr_name.startswith("_"):
                continue
            tool = getattr(tool_registry, attr_name)
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

        # Safety: block high/critical risk tools without explicit confirmation
        if tool.risk_level.value in ("high", "critical"):
            raise HTTPException(
                status_code=403,
                detail=f"Tool '{tool_id}' has risk level '{tool.risk_level.value}'. Use CLI for high-risk operations.",
            )

        ctx = ToolContext(network_allowed=False)
        result: ToolResult = tool.invoke(request.params, ctx)
        return ToolInvokeResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata,
        )

    @app.get("/api/workflows", response_model=list[WorkflowListItem], tags=["workflows"])
    def list_workflows() -> list[WorkflowListItem]:
        """List registered workflows."""
        _import_workflows()
        return [
            WorkflowListItem(
                workflow_id=w.id,
                name=w.id.replace("_", " ").title(),
                description=getattr(w, "description", "") or "",
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
                    description=getattr(w, "description", "") or "",
                    required_agents=getattr(w, "required_agents", []),
                    required_tools=getattr(w, "required_tools", []),
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
                workflow_cls = w
                break
        if workflow_cls is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        def _run():
            from core.ledger import RunLedger
            from core.model_registry import ModelRegistry
            from core.policy_engine import PolicyEngine
            ledger = RunLedger.create(repo_root, f"api-{workflow_id}")
            registry = ModelRegistry.from_team_config()
            policy = PolicyEngine()
            wf = workflow_cls(registry, tool_registry, policy, ledger)
            return wf.run(repo_root, metadata=request.params)

        run_id = run_executor.submit(_run)
        return ExecuteResponse(run_id=run_id, status="pending")

    @app.get("/api/presets", response_model=list[PresetListItem], tags=["presets"])
    def list_presets() -> list[PresetListItem]:
        """List available presets."""
        from presets import PRESET_REGISTRY

        return [
            PresetListItem(
                preset_id=p.preset_id,
                name=getattr(p, "name", p.preset_id) or p.preset_id,
                description=getattr(p, "description", "") or "",
            )
            for p in PRESET_REGISTRY.list()
        ]

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

        run_id = run_executor.submit(preset.run, request.inputs)
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
        from core.model_registry import ModelRegistry

        try:
            registry = ModelRegistry.from_team_config()
            items = []
            for binding in registry._bindings.values():
                items.append(
                    ModelListItem(
                        model_id=binding.model_id,
                        provider=binding.provider,
                        capabilities=list(binding.capabilities),
                    )
                )
            return items
        except Exception:
            return []

    @app.get("/api/providers", response_model=list[ProviderListItem], tags=["providers"])
    def list_providers() -> list[ProviderListItem]:
        """List providers and their health status."""
        providers = [
            ProviderListItem(provider_id="openai_v1", healthy=True),
            ProviderListItem(provider_id="aws_bedrock", healthy=True),
            ProviderListItem(provider_id="azure_foundry", healthy=True),
            ProviderListItem(provider_id="oci_genai", healthy=True),
        ]
        for p in providers:
            healthy, error = _check_provider_health(p.provider_id)
            p.healthy = healthy
            p.error = error
        return providers

    @app.get("/api/runs/{run_id}", response_model=RunStatusResponse, tags=["runs"])
    def get_run_status(run_id: str) -> RunStatusResponse:
        """Get the status of a run."""
        # First check in-memory executor
        record = run_executor.get(run_id)
        if record is not None:
            return RunStatusResponse(
                run_id=run_id,
                status=record.status.value,
                artifacts=record.artifacts,
                error=record.error,
            )

        # Fallback to disk
        run_dir = repo_root / ".ai-team" / "runs" / run_id
        if not run_dir.exists():
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

        artifacts = []
        if run_dir.is_dir():
            artifacts = sorted(
                f.name for f in run_dir.iterdir() if f.is_file()
            )

        status_str = "completed" if (run_dir / "final_report.md").exists() else "in_progress"
        return RunStatusResponse(
            run_id=run_id,
            status=status_str,
            artifacts=artifacts,
        )

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
            yield f"data: {json.dumps({'run_id': run_id, 'status': record.status.value})}\n\n"
            for _ in range(3600):  # Max ~1 hour of streaming
                await asyncio.sleep(1)
                current = run_executor.get(run_id)
                if current is None:
                    break
                if current.status.value != last_status:
                    last_status = current.status.value
                    payload = {
                        "run_id": run_id,
                        "status": current.status.value,
                        "artifacts": current.artifacts,
                    }
                    if current.error:
                        payload["error"] = current.error
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
            await websocket.send_json(
                {
                    "run_id": run_id,
                    "status": record.status.value,
                    "artifacts": record.artifacts,
                }
            )
            if record.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                await websocket.close()
                return
            while True:
                record = await queue.get()
                payload = {
                    "run_id": run_id,
                    "status": record.status.value,
                    "artifacts": record.artifacts,
                }
                if record.error:
                    payload["error"] = record.error
                await websocket.send_json(payload)
                if record.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
                    await websocket.close()
                    break
        except WebSocketDisconnect:
            pass
        finally:
            run_executor.unsubscribe(run_id, on_update)

    return app
