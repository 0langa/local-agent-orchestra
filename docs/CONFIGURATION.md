# Configuration Guide

Agentheim is configured entirely through environment variables. No config files are required — though you can use a `.env` file for convenience.

## Quick Config

Create a `.env` file in the project root:

```bash
cp Agent-Team/.env.example .env
```

## Provider Configuration

### 1. Define your provider(s)

```env
# Which providers to load (comma-separated)
AI_TEAM_PROVIDER_IDS=default

# For each provider ID, set these variables:
AI_TEAM_PROVIDER_DEFAULT_TYPE=openai_compatible
AI_TEAM_PROVIDER_DEFAULT_ENDPOINT=https://api.openai.com/v1
AI_TEAM_PROVIDER_DEFAULT_API_KEY_ENV=OPENAI_API_KEY
AI_TEAM_PROVIDER_DEFAULT_TIMEOUT_SECONDS=60
```

### Provider Types

| Type | Description |
|------|-------------|
| `openai_compatible` | Any OpenAI-compatible API (OpenAI, Grok, Ollama, LM Studio, etc.) |
| `azure_foundry` | Azure OpenAI Service |
| `aws_bedrock` | AWS Bedrock |
| `oci_genai` | Oracle Cloud Infrastructure GenAI |

### Multiple Providers

```env
AI_TEAM_PROVIDER_IDS=openai,ollama

AI_TEAM_PROVIDER_OPENAI_TYPE=openai_compatible
AI_TEAM_PROVIDER_OPENAI_ENDPOINT=https://api.openai.com/v1
AI_TEAM_PROVIDER_OPENAI_API_KEY_ENV=OPENAI_API_KEY

AI_TEAM_PROVIDER_OLLAMA_TYPE=openai_compatible
AI_TEAM_PROVIDER_OLLAMA_ENDPOINT=http://localhost:11434/v1
AI_TEAM_PROVIDER_OLLAMA_API_KEY_ENV=OLLAMA_API_KEY
```

## Model Configuration

### Option A: Explicit model registry (recommended)

```env
AI_TEAM_MODELS_JSON=[
  {"id":"planner","role":"planner","provider":"default","model_name":"gpt-4o","capabilities":["plan","reasoning","json"]},
  {"id":"executor","role":"executor","provider":"default","model_name":"gpt-4o-mini","capabilities":["code_edit","json"]},
  {"id":"verifier","role":"verifier","provider":"default","model_name":"gpt-4o","capabilities":["verify","json"]}
]
```

### Option B: Per-role environment variables

```env
AI_TEAM_MODEL_PLANNER_PROVIDER=default
AI_TEAM_MODEL_PLANNER_NAME=gpt-4o

AI_TEAM_MODEL_EXECUTOR_PROVIDER=default
AI_TEAM_MODEL_EXECUTOR_NAME=gpt-4o-mini

AI_TEAM_MODEL_VERIFIER_PROVIDER=default
AI_TEAM_MODEL_VERIFIER_NAME=gpt-4o
```

### Workflow-Specific Roles

Different workflows need different agent roles:

| Workflow | Roles |
|----------|-------|
| Coding | `planner`, `executor`, `verifier` |
| Research | `gatherer`, `summarizer`, `reporter` |
| Documents | `indexer`, `retriever`, `answerer` |

## Privacy Modes

Agentheim enforces privacy at the policy engine level:

| Mode | Behavior |
|------|----------|
| `remote-allowed` | Can call remote APIs freely |
| `local-preferred` | Prefers local models; asks before remote |
| `local-only` | Blocks all remote network access |
| `strict-private` | Blocks network + restricts file access |

Set via the CLI:

```bash
python -m ai_team run --preset coding --privacy local-only
```

## Approval Behavior

| Level | Behavior |
|-------|----------|
| `auto-approve` | Read-only ops run automatically |
| `always-ask` | Every non-read operation pauses for approval |
| `risk-based` | Default — LOW auto-runs, MEDIUM asks, HIGH blocks |

```bash
python -m ai_team run --preset coding --approval risk-based
```

## MCP Integration

Enable MCP servers by creating `.ai-team/mcp.json`:

```json
[
  {
    "name": "filesystem",
    "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."],
    "enabled": true
  }
]
```

MCP tools are discovered at runtime and go through the same policy engine as native tools.

## Memory Configuration

Memory is scoped per repository. By default, Agentheim stores:
- **Working memory** — in-memory, flushed to ledger at run end
- **Episodic memory** — `.ai-team/memory/episodes/`
- **Semantic memory** — `.ai-team/memory/semantic/`
- **Global preferences** — cross-project SQLite in platformdirs path

No configuration needed — memory initializes automatically on first use.

## Full Environment Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_TEAM_PROVIDER_IDS` | `default` | Comma-separated provider IDs |
| `AI_TEAM_PROVIDER_*_TYPE` | `openai_compatible` | Provider adapter type |
| `AI_TEAM_PROVIDER_*_ENDPOINT` | (required) | API base URL |
| `AI_TEAM_PROVIDER_*_API_KEY_ENV` | (required) | Env var containing API key |
| `AI_TEAM_PROVIDER_*_TIMEOUT_SECONDS` | `60` | Request timeout |
| `AI_TEAM_MODELS_JSON` | (built-in defaults) | Full model registry JSON |
| `AI_TEAM_MODEL_*_PROVIDER` | `default` | Provider for role |
| `AI_TEAM_MODEL_*_NAME` | (placeholder) | Model name for role |
| `AI_TEAM_ENABLE_GITHUB` | `false` | Enable GitHub integration |
| `AI_TEAM_ENABLE_MCP` | `false` | Enable MCP discovery |
| `AI_TEAM_ENABLE_WEB` | `false` | Enable web research tool |

## Legacy Config

If you have old `GROK_*` environment variables, they still work but are deprecated. Migrate to `AI_TEAM_PROVIDER_*` at your convenience.
