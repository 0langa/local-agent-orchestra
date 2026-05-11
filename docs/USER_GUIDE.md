# User Guide

> Everything you need to install, configure, and run Agentheim.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Presets](#presets)
- [Run Modes](#run-modes)
- [Privacy & Safety](#privacy--safety)

---

## Requirements

- **Python 3.12 or higher**
- **Git** (for repository-aware workflows)
- **(Optional) Playwright** — only needed for browser automation: `playwright install chromium`

---

## Installation

```bash
# Clone the repository
git clone https://github.com/0langa/agentheim.git
cd agentheim

# Install in editable mode
pip install -e .
```

### Verify

```bash
# Check CLI is available
agentheim --help

# Run system diagnostics
agentheim doctor
```

---

## Quick Start

### 1. Configure a Provider

```bash
cp Agent-Team/.env.example .env
```

Edit `.env` with your provider details:

```env
AI_TEAM_PROVIDER_IDS=default
AI_TEAM_PROVIDER_DEFAULT_TYPE=openai_compatible
AI_TEAM_PROVIDER_DEFAULT_ENDPOINT=https://api.openai.com/v1
AI_TEAM_PROVIDER_DEFAULT_API_KEY_ENV=OPENAI_API_KEY
OPENAI_API_KEY=sk-your-key-here
```

### 2. Verify Connectivity

```bash
agentheim ping-models
```

### 3. Run a Preset

```bash
# Interactive guided mode — pick a preset
agentheim guided

# Or run directly
agentheim start codebase-assistant --input repo=./my-project --input task="Review code"
```

---

## Configuration

Agentheim is configured entirely through environment variables. You can use a `.env` file for convenience.

### Provider Configuration

```env
# Which providers to load (comma-separated)
AI_TEAM_PROVIDER_IDS=default

# For each provider, set these variables:
AI_TEAM_PROVIDER_DEFAULT_TYPE=openai_compatible
AI_TEAM_PROVIDER_DEFAULT_ENDPOINT=https://api.openai.com/v1
AI_TEAM_PROVIDER_DEFAULT_API_KEY_ENV=OPENAI_API_KEY
AI_TEAM_PROVIDER_DEFAULT_TIMEOUT_SECONDS=60
```

#### Supported Provider Types

| Type | Description | Example Endpoint |
|------|-------------|-----------------|
| `openai_compatible` | Any OpenAI-compatible API | `https://api.openai.com/v1` |
| `azure_foundry` | Azure OpenAI Service | `https://your-resource.openai.azure.com/` |
| `aws_bedrock` | AWS Bedrock (uses boto3) | — |
| `oci_genai` | OCI GenAI (uses OCI SDK) | — |

#### Multiple Providers

```env
AI_TEAM_PROVIDER_IDS=openai,ollama

AI_TEAM_PROVIDER_OPENAI_TYPE=openai_compatible
AI_TEAM_PROVIDER_OPENAI_ENDPOINT=https://api.openai.com/v1
AI_TEAM_PROVIDER_OPENAI_API_KEY_ENV=OPENAI_API_KEY

AI_TEAM_PROVIDER_OLLAMA_TYPE=openai_compatible
AI_TEAM_PROVIDER_OLLAMA_ENDPOINT=http://localhost:11434/v1
AI_TEAM_PROVIDER_OLLAMA_API_KEY_ENV=OLLAMA_API_KEY
```

### Model Configuration

#### Option A: Explicit model registry (recommended)

```env
AI_TEAM_MODELS_JSON=[
  {"id":"planner","role":"planner","provider":"default","model_name":"gpt-4o","capabilities":["plan","reasoning","json"]},
  {"id":"executor","role":"executor","provider":"default","model_name":"gpt-4o-mini","capabilities":["code_edit","json"]},
  {"id":"verifier","role":"verifier","provider":"default","model_name":"gpt-4o","capabilities":["verify","json"]}
]
```

#### Option B: Per-role environment variables

```env
AI_TEAM_MODEL_PLANNER_PROVIDER=default
AI_TEAM_MODEL_PLANNER_NAME=gpt-4o
AI_TEAM_MODEL_EXECUTOR_PROVIDER=default
AI_TEAM_MODEL_EXECUTOR_NAME=gpt-4o-mini
AI_TEAM_MODEL_VERIFIER_PROVIDER=default
AI_TEAM_MODEL_VERIFIER_NAME=gpt-4o
```

### Workflow Model Roles

| Workflow | Roles |
|----------|-------|
| Coding | `planner`, `executor`, `verifier` |
| Research | `gatherer`, `summarizer`, `reporter` |
| Documents | `indexer`, `retriever`, `answerer` |
| File Organization | `analyzer`, `proposer`, `applier` |
| Docs Maintenance | `detector`, `updater`, `aligner` |
| GitHub Maintenance | `summarizer`, `drafter` |
| Command Assistant | `parser`, `generator` |

### Full Environment Reference

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

### MCP Integration

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

---

## CLI Reference

### Global Flags

```bash
agentheim --help              # Show help
agentheim presets             # List available presets
```

### Commands

| Command | Description |
|---------|-------------|
| `agentheim guided` | Interactive preset picker (recommended for beginners) |
| `agentheim start <preset>` | Run a specific preset with inputs |
| `agentheim doctor` | Run system diagnostics |
| `agentheim ping-models` | Test provider connectivity for all configured models |
| `agentheim config-dump --redacted` | Show resolved configuration (secrets redacted) |
| `agentheim inspect --repo <path>` | Inspect a repository for context |
| `agentheim plan <task> --repo <path>` | Plan a task without executing |
| `agentheim run <task> --repo <path>` | Execute a task with mode selection |
| `agentheim list-runs --repo <path>` | List all runs in a repository |
| `agentheim report --repo <path> --run-id <id>` | Show full report for a run |
| `agentheim resume --repo <path> --run-id <id>` | Resume a blocked or incomplete run |
| `agentheim presets` | List all available presets |

### Run Modes

| Mode | Behavior |
|------|----------|
| `apply` | Execute changes directly (requires approval for destructive ops) |
| `auto` | Auto-approve safe operations, ask for risky ones |
| `ci` | Non-interactive: skip operations requiring approval |

---

## Presets

| Preset | What it does | CLI Shortcut |
|--------|-------------|-------------|
| **Codebase Assistant** | Inspects → plans → patches → tests → reports on your code | `agentheim start codebase-assistant` |
| **Research Report** | Gathers sources → summarizes → compares → writes a report | `agentheim start research-report` |
| **Local Document Chat** | Indexes documents → answers questions with citations | `agentheim start local-document-chat` |
| **File Organizer** | Analyzes → proposes → previews → applies file organization | `agentheim start file-organizer` |
| **Docs Maintainer** | Detects stale documentation → updates or aligns it | `agentheim start docs-maintainer` |
| **GitHub Maintainer** | Summarizes issues → drafts PR descriptions | `agentheim start github-maintainer` |
| **Command Assistant** | Parses natural language → generates safe shell commands | `agentheim start command-assistant` |

---

## Architecture at a Glance

Agentheim serves three user layers from the same runtime:

```
Beginner (Presets)        →  Pick intent, system handles the rest
    ↓
Power-User (CLI/Config)   →  Override models, privacy modes, approval rules
    ↓
Developer (Extensible)    →  Add workflow packs, providers, tools — no core changes
    ↓
Core Runtime (Generic)    →  DAG execution, policy engine, ledger, model registry
```

**Key design principles:**
- **Core ignorance** — `core/` knows no provider, model, or workflow names
- **Local-first** — zero external services required; privacy modes enforced in code
- **Safety by default** — destructive ops require approval; policies are code, not prompts
- **Fully auditable** — every run produces an append-only event ledger
- **Provider-agnostic** — swap Grok, OpenAI, Azure, Ollama, LM Studio without code changes

---

## Privacy & Safety

See the [Safety & Security](SAFETY.md) document for complete details.

### Quick Reference

| Privacy Mode | Behavior |
|-------------|----------|
| `standard` | Baseline mode with no extra privacy restrictions |
| `local_only` | Blocks network-oriented tools |
| `strict_private` | Blocks sensitive-path access under stricter privacy rules |
| `encrypted` | Redacts audited params and applies the strictest privacy handling |

These mode names come from `core/privacy_enforcer.py`. The current CLI surface does not yet expose a dedicated privacy-mode flag.

### Approval Levels

| Level | Behavior |
|-------|----------|
| `auto-approve` | Read-only ops run automatically |
| `always-ask` | Every non-read operation pauses for approval |
| `risk-based` (default) | LOW auto-runs, MEDIUM asks, HIGH blocks |

---

## Ledger & Artifacts

Every run produces artifacts under `.ai-team/runs/<run-id>/` inside the target repository:

| Artifact | Description |
|----------|-------------|
| `run.json` | Run metadata |
| `ledger.jsonl` | Append-only event log |
| `ledger.hash` | SHA-256 hash chain for tamper detection |
| `config.redacted.json` | Configuration (secrets redacted) |
| `context_bundle.md` | Human-readable context snapshot |
| `plan.md` | Execution plan |
| `tool_calls.jsonl` | All tool invocations |
| `policy_decisions.jsonl` | Policy evaluation results |
| `patch.diff` | File changes (if applicable) |
| `verification.json` | Verification results |
| `final_report.md` | Human-readable final report |

---

## See Also

- [Architecture Overview](ARCHITECTURE.md) — deep dive into system design
- [API Reference](API_REFERENCE.md) — REST API and programmatic usage
- [Troubleshooting](TROUBLESHOOTING.md) — common issues and fixes
- [Development & Testing](DEV_TESTING.md) — running tests and contributing
