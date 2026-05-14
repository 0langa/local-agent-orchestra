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
agentheim provider add openai --template openai_v1 --model gpt-4o-mini --role planner
agentheim provider assign executor --provider openai --model gpt-4o-mini
agentheim provider assign verifier --provider openai --model gpt-4o-mini
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

AI providers are configured through Agentheim provider profiles. Secrets are stored in the OS keychain by default, with encrypted local vault fallback. `.env` provider setup is migration-only and is not loaded at runtime.

### Provider Configuration

```bash
agentheim provider templates
agentheim provider add openai --template openai_v1 --model gpt-4o-mini --role planner
agentheim provider list
```

#### Supported Provider Types

| Type | Description | Example Endpoint |
|------|-------------|-----------------|
| `openai_compatible` | Any OpenAI-compatible API | `https://api.openai.com/v1` |
| `openai_v1` | OpenAI API | `https://api.openai.com/v1` |
| `azure_foundry` | Azure OpenAI Service | `https://your-resource.openai.azure.com/` |
| `aws_bedrock` | AWS Bedrock (uses boto3) | — |
| `oci_genai` | OCI GenAI (uses OCI SDK) | — |
| `anthropic` | Anthropic Messages API | `https://api.anthropic.com` |
| `gemini` | Google Gemini API key API | `https://generativelanguage.googleapis.com` |
| `vertex_ai` | Google Vertex AI with ADC | — |
| `cohere` | Cohere v2 API | `https://api.cohere.com` |
| `perplexity` | Perplexity API | `https://api.perplexity.ai` |
| `ollama_cloud` | Ollama cloud API | `https://ollama.com/api` |

#### Multiple Providers

```bash
agentheim provider add openai --template openai_v1 --model gpt-4o --role planner
agentheim provider add kimi --template kimi_moonshot --model kimi-k2 --role executor
agentheim provider add claude --template anthropic --model claude-sonnet-4-5 --role verifier
```

### Model Configuration

Bind each role to a provider/model pair:

```bash
agentheim provider assign planner --provider openai --model gpt-4o
agentheim provider assign executor --provider kimi --model kimi-k2
agentheim provider assign verifier --provider claude --model claude-sonnet-4-5
```

### Workflow Model Roles

| Workflow | Roles |
|----------|-------|
| Coding | `planner`, `executor`, `verifier` |
| Research | `gatherer`, `summarizer`, `reporter` |
| Documents | `indexer`, `retriever`, `answerer` |
| File Organization | `indexer`, `planner`, `executor` |
| Docs Maintenance | `planner`, `executor`, `verifier` |
| GitHub Maintenance | `planner`, `executor` |
| Command Assistant | `planner`, `executor` |
| Context Operations | `context` |

### Provider Profile Reference

| Setting | Default | Description |
|----------|---------|-------------|
| Profile name | `default` | Active provider profile |
| Secret backend | OS keychain | Falls back to encrypted local vault |
| Project pointer | `.ai-team/provider-profile.json` | Optional committed profile selector without secrets |
| Secret ref | `secret://provider/<id>/api_key` | Stored in profile, resolves through vault/keychain |
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
| `agentheim provider templates` | List supported provider setup templates |
| `agentheim provider add <id> --template <template> --model <model>` | Add provider and save secret securely |
| `agentheim provider assign <role> --provider <id> --model <model>` | Bind a team role to a model |
| `agentheim provider import-env` | One-time migration from old provider env vars |
| `agentheim inspect --repo <path>` | Inspect a repository for context |
| `agentheim plan <task> --repo <path>` | Plan a task without executing |
| `agentheim run <task> --repo <path>` | Execute a task with mode selection |
| `agentheim list-runs --repo <path>` | List all runs in a repository |
| `agentheim report --repo <path> --run-id <id>` | Show full report for a run |
| `agentheim resume --repo <path> --run-id <id>` | Resume a blocked or incomplete run |
| `agentheim presets` | List all available presets |
| `agentheim memory get --key <key>` | Read a value from global memory |
| `agentheim memory set --key <key> --value <value>` | Store a value in global memory |
| `agentheim mcp-list` | List tools provided by configured MCP servers |
| `agentheim mcp-call <tool> --arg key=value` | Call an MCP tool directly |
| `agentheim ctx init` | Initialize repo for context processing |
| `agentheim ctx scan` | Scan repository and print inventory summary |
| `agentheim ctx run` | Run full context generation pipeline |
| `agentheim ctx verify` | Verify context lock against repository state |
| `agentheim ctx status` | Show stale-context detection status |
| `agentheim ctx clean` | Remove generated run artifacts |
| `agentheim ctx public-docs impact` | Map source changes to impacted public docs |
| `agentheim ctx public-docs update` | Generate patches for impacted public docs |
| `agentheim ctx oci doctor` | Run OCI readiness checks |
| `agentheim ctx oci snapshot create` | Create deterministic repo snapshot |
| `agentheim ctx oci snapshot verify` | Verify snapshot integrity |
| `agentheim ctx oci bundle create` | Create result bundle for a run |
| `agentheim ctx oci bundle verify` | Verify result bundle integrity |

### What is MCP?

[MCP](https://modelcontextprotocol.io/) (Model Context Protocol) lets Agentheim connect to external tools — databases, browsers, file servers, and more — without writing custom code. If you have an MCP server running, Agentheim discovers its tools automatically and routes them through the same policy engine as native tools.

### Examples

```bash
# Run a preset with dirty-repo override
agentheim run "Review code" --repo . --allow-dirty

# Store a preference in global memory
agentheim memory set --key theme --value dark

# List available MCP tools
agentheim mcp-list

# Call an MCP tool (example: filesystem search)
agentheim mcp-call filesystem_search --arg query="*.py"
```

### Run Modes

| Mode | Behavior |
|------|----------|
| `apply` | Execute changes directly (requires approval for destructive ops) |
| `auto` | Auto-approve safe operations, ask for risky ones |
| `ci` | Non-interactive: skip operations requiring approval |

---

## Presets

Support states are tracked in [Support Matrix](SUPPORT_MATRIX.md). Stable candidates are the baseline paths being hardened first; beta presets are usable with documented limits until their current live and interface evidence is complete.

| Preset | What it does | CLI Shortcut |
|--------|-------------|-------------|
| **Codebase Assistant** | Inspects → plans → patches → tests → reports on your code | `agentheim start codebase-assistant` |
| **Research Report** | Gathers sources → summarizes → compares → writes a report | `agentheim start research-report` |
| **Local Document Chat** | Indexes documents → answers questions with citations | `agentheim start local-document-chat` |
| **File Organizer** | Analyzes → proposes → previews → applies file organization | `agentheim start file-organizer` |
| **Docs Maintainer** | Detects stale documentation → updates or aligns it | `agentheim start docs-maintainer` |
| **GitHub Maintainer** | Summarizes issues → drafts PR descriptions | `agentheim start github-maintainer` |
| **Command Assistant** | Parses natural language → generates safe shell commands | `agentheim start command-assistant` |
| **Context Maintainer** | Detects stale context → runs context pipeline | `agentheim start context-maintainer` |

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
