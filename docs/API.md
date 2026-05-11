# API Reference

Agentheim exposes a FastAPI-based REST API for external integrations.

## Starting the API Server

```python
from interfaces.api_server import create_api_app
import uvicorn

app = create_api_app(".")
uvicorn.run(app, host="127.0.0.1", port=8000)
```

Or programmatically:

```bash
python -c "from interfaces.api_server import create_api_app; import uvicorn; uvicorn.run(create_api_app('.'), host='0.0.0.0', port=8000)"
```

## Authentication

All endpoints (except `/api/health`) require an API key header:

```
X-API-Key: dev-key
```

In production, configure valid keys in `app.state.api_keys`.

## Rate Limiting

- 60 requests per minute per IP
- Returns `429 Too Many Requests` when exceeded

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

**Safety:** MEDIUM+ tools require `confirm_risk=true` query parameter. HIGH/CRITICAL tools are blocked.

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

### Presets

#### List Presets
```
GET /api/presets
```

Returns all available presets with descriptions.

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

Returns configured providers (API keys redacted).

### Runs

#### Get Run
```
GET /api/runs/{run_id}
```

Returns run metadata from ledger if found.

### OpenAPI / Docs

```
GET /openapi.json
GET /docs
```

Interactive Swagger UI at `/docs`.

## Error Codes

| Status | Meaning |
|--------|---------|
| `200` | Success |
| `401` | Missing or invalid API key |
| `429` | Rate limit exceeded |
| `403` | Risk confirmation required or tool blocked |
| `404` | Tool/workflow/run not found |
| `422` | Invalid parameters |

## Web UI

Agentheim also includes a prototype web dashboard:

```python
from interfaces.web_ui import create_app
```

Provides HTML pages for browsing tools, workflows, and presets in a browser.

## Desktop UI

A PyQt6 desktop wrapper is available:

```python
from interfaces.desktop_ui import run_desktop_app
run_desktop_app()
```

Falls back to tkinter if PyQt6 is not installed.
