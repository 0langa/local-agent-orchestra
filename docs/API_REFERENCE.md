# API Reference

> Agentheim exposes a FastAPI-based REST API with WebSocket streaming for external integrations.

---

## Table of Contents

- [Starting the API Server](#starting-the-api-server)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
- [WebSocket Streaming](#websocket-streaming)
- [OpenAPI / Interactive Docs](#openapi--interactive-docs)
- [Error Codes](#error-codes)
- [Web UI](#web-ui)
- [Desktop UI](#desktop-ui)
- [Programmatic Usage](#programmatic-usage)

---

## Starting the API Server

```python
from interfaces.api_server import create_api_app
import uvicorn

app = create_api_app(".")
uvicorn.run(app, host="127.0.0.1", port=8000)
```

Or from the command line:

```bash
python -c "from interfaces.api_server import create_api_app; import uvicorn; uvicorn.run(create_api_app('.'), host='0.0.0.0', port=8000)"
```

---

## Authentication

Execution and write endpoints require an API key header:

```
X-API-Key: <your-api-key>
```

In the current implementation, read-oriented endpoints such as `/api/health`, `/api/tools`, `/api/workflows`, `/api/presets`, `/api/models`, and `/api/providers` are accessible without the header.

Configured keys are loaded from the `AI_TEAM_API_KEYS` environment variable.

---

## Rate Limiting

- 60 requests per minute per IP
- Returns `429 Too Many Requests` when exceeded

---

## Endpoints

### Health

```
GET /api/health
```

No auth required. Returns `{"status": "ok"}`.

### Tools

#### List Tools
```
GET /api/tools
```

Returns all registered tools with schemas and risk levels.

#### Invoke Tool
```
POST /api/tools/{tool_id}/invoke
```

Body: tool parameters as JSON.

**Safety:** the current API route invokes LOW and MEDIUM tools directly. HIGH and CRITICAL tools are rejected with `403` and must be run through a local interface such as the CLI.

### Workflows

#### List Workflows
```
GET /api/workflows
```

Returns all registered workflow packs.

#### Get Workflow Detail
```
GET /api/workflows/{workflow_id}
```

Returns workflow metadata including required agents and tools.

#### Execute Workflow
```
POST /api/workflows/{workflow_id}/execute
```

Execute a workflow pack with the given input parameters.

### Presets

#### List Presets
```
GET /api/presets
```

Returns all available presets with descriptions.

#### Run Preset
```
POST /api/presets/{preset_id}/run
```

Run a preset with the provided inputs.

### Memory

#### Read Memory
```
GET /api/memory/{scope}/{key}
```

Scopes: `run`, `repository`, `global`

#### Write Memory
```
POST /api/memory/{scope}/{key}
```

Body: `{"value": <any JSON-serializable value>}`

### Models & Providers

#### List Models
```
GET /api/models
```

Returns resolved model bindings per role.

#### List Providers
```
GET /api/providers
```

Returns provider health entries for the built-in provider adapters.

### Runs

#### Get Run
```
GET /api/runs/{run_id}
```

Returns run metadata from ledger if found.

#### Stream Run Events (SSE)
```
GET /api/runs/{run_id}/stream
```

Server-Sent Events stream of run progress.

#### WebSocket Run Events
```
WS /api/runs/{run_id}/ws
```

Bidirectional WebSocket for real-time run events.

### Metrics

```
GET /api/metrics
```

Prometheus-format metrics (if monitoring is enabled).

---

## WebSocket Streaming

Agentheim supports WebSocket connections for real-time run event streaming:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/runs/{run_id}/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Run event:', data);
};
```

The WebSocket bridge syncs `RunExecutor` notifications to async handlers via `asyncio.Queue`. Connections close cleanly for already-completed runs.

---

## OpenAPI / Interactive Docs

```
GET /openapi.json    # Raw OpenAPI spec
GET /docs            # Swagger UI
```

Interactive API documentation is available at `/docs` when the server is running.

---

## Error Codes

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `401` | Missing API key header |
| `403` | Invalid API key or blocked operation |
| `429` | Rate limit exceeded |
| `404` | Tool/workflow/run not found |
| `422` | Invalid parameters |

---

## Web UI

Agentheim also includes a prototype web dashboard:

```python
from interfaces.web_ui import create_app
import uvicorn

app = create_app(".")
uvicorn.run(app, host="127.0.0.1", port=8080)
```

Provides HTML pages for browsing tools, workflows, and presets in a browser.

---

## Desktop UI

A PyQt6 desktop wrapper is available:

```python
from interfaces.desktop_ui import run_desktop_app
run_desktop_app()
```

Falls back to tkinter if PyQt6 is not installed, then to opening a browser window.

---

## Programmatic Usage

### Python SDK (Core Public API)

All public API symbols are exported through `core.public_api`:

```python
from core.public_api import (
    WorkflowRunner,
    RunLedger,
    PolicyEngine,
    ToolRegistry,
    ModelRegistry,
    CapabilityRegistry,
    Event,
    AgentRequest,
    AgentResponse,
    AgentContext,
    ContextPacker,
    ArtifactStore,
    ErrorCategory,
    RetryEngine,
    StepBudgetEnforcer,
    ToolContext,
    ToolResult,
    ToolSchema,
    BaseTool,
    AsyncBaseTool,
)
```

### Creating a Custom Preset

```python
from presets.base import Preset

class MyPreset(Preset):
    def __init__(self) -> None:
        super().__init__(
            preset_id="my-preset",
            workflow_id="command_assistant",
            name="My Custom Preset",
            description="Does something useful",
        )

    def run(self, inputs: dict) -> dict:
        return {"task": inputs["task"]}
```

### Running a Workflow Programmatically

```python
from core.public_api import WorkflowRunner
from pathlib import Path

runner = WorkflowRunner()

results = runner.run(
    workflow=my_workflow,
    repo_root=Path("."),
    metadata={"task": "Review code"}
)
```

---

## See Also

- [User Guide](USER_GUIDE.md) — CLI commands and preset usage
- [Architecture](ARCHITECTURE.md) — core runtime and subsystem details
- [Development & Testing](DEV_TESTING.md) — running tests
