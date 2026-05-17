# User Guide

> Everything you need to install, configure, and run Agentheim.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Beginner Path](#beginner-path)
- [Recipes](#recipes)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Presets](#presets)
- [Privacy & Safety](#privacy--safety)
- [Ledger & Artifacts](#ledger--artifacts)

---

## Requirements

- **Python 3.12 or higher**
- **Git** (for repository-aware workflows)
- **(Optional) Playwright** — only needed for browser automation: `playwright install chromium`

---

## Installation

**With pipx (recommended for end users):**

```bash
pipx install agentheim
```

**With pip (editable for developers):**

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

## Beginner Path

This is the fastest path from install to a working preset run.

### 1. Run Setup

```bash
agentheim setup
```

This interactively prompts for:
- Provider (OpenAI, Google, Anthropic, local, etc.)
- Model
- API key (stored in the OS keychain, never in repo files)
- Privacy mode (`standard`, `local_only`, `strict_private`)

It then creates a profile, binds core roles (`planner`, `executor`, `verifier`, `context`), and runs readiness checks.

Non-interactive equivalent:

```bash
agentheim setup --provider openai --template openai_v1 --model gpt-4o-mini --api-key $env:OPENAI_API_KEY --yes
```

### 2. Check Status

```bash
agentheim status
```

Shows:
- Provider readiness
- Missing role bindings
- Optional integrations (MCP, browser, GitHub, context ops)
- Recent runs
- Suggested next actions

JSON output for scripting:

```bash
agentheim status --json
```

Generate a redacted debug bundle:

```bash
agentheim status --debug-bundle
```

### 3. Run a Task

The quickest way is `use`, which maps a plain-language goal to the right preset:

```bash
# Review code
agentheim use code --input repo=. --input task="Review the auth module"

# Chat with your documents
agentheim use docs-chat --input repo=. --input query="How does routing work?"

# Generate a shell command
agentheim use command --input command_description="List all Python files modified in the last week"
```

Or use the interactive picker:

```bash
agentheim guided
```

Or run a preset directly:

```bash
agentheim start codebase-assistant --input repo=. --input task="Review code"
```

### 4. Inspect Runs

```bash
agentheim runs                    # list all runs
agentheim runs show <run-id>      # detailed view
agentheim runs report <run-id>    # print the report
agentheim runs resume <run-id>    # resume a blocked run
agentheim runs open-folder <run-id>  # open artifact folder
```

### 5. Open the UI

```bash
agentheim open
```

Launches the local web UI on `http://localhost:8765` and opens your browser.

---

## Recipes

### Connect an OpenAI-compatible provider

Any provider with an OpenAI-compatible HTTP API:

```bash
agentheim provider add myprovider --template openai_compatible \
  --model my-model --role planner \
  --endpoint https://api.example.com/v1 --api-key $env:MY_API_KEY
agentheim provider assign executor --provider myprovider --model my-model
agentheim provider assign verifier --provider myprovider --model my-model
agentheim ping-models
```

### Connect local Ollama

1. Start Ollama and pull a model:

```bash
ollama run llama3.1
```

2. Add the provider:

```bash
agentheim provider add local --template ollama --model llama3.1 --role planner
agentheim provider assign executor --provider local --model llama3.1
agentheim provider assign verifier --provider local --model llama3.1
agentheim doctor --skip-connectivity
agentheim provider test --role planner
```

3. Quality notes:
- Smaller OSS models may pass `command-assistant` but struggle with coding or verifier-heavy flows.
- Use stronger instruction-following models for `codebase-assistant`.
- Vision claims only matter when the local server and chosen model both support vision inputs.

### Connect LM Studio

1. In LM Studio, start the local server (default port 1234).
2. Add the provider:

```bash
agentheim provider add local --template lm_studio --model my-model --role planner
agentheim provider assign executor --provider local --model my-model
agentheim provider assign verifier --provider local --model my-model
agentheim ping-models
```

### Run Codebase Assistant

```bash
agentheim use code --input repo=./my-project --input task="Refactor the auth module"
```

Or run directly:

```bash
agentheim start codebase-assistant --input repo=./my-project --input task="Add input validation to the API"
```

The preset inspects the repo, plans the work, applies patches, runs tests, and produces a report.

### Ask questions over your documents

```bash
agentheim use docs-chat --input repo=./my-docs --input query="What is the refund policy?"
```

Or run directly:

```bash
agentheim start local-document-chat --input repo=./my-docs --input query="Summarize the onboarding guide"
```

Documents are indexed locally. Nothing is sent to the provider except your question and the retrieved context chunks.

### Inspect prior runs

```bash
# List recent runs
agentheim runs --repo .

# Show a specific run
agentheim runs show 2026-05-17-a1b2c3d4 --repo .

# Watch a run in progress
agentheim runs show 2026-05-17-a1b2c3d4 --watch

# Print the report
agentheim runs report 2026-05-17-a1b2c3d4 --repo .
```

### Recover from provider failure

1. Run diagnostics:

```bash
agentheim doctor
agentheim ping-models
```

2. If a provider is unreachable, check your endpoint and API key:

```bash
agentheim provider test --role planner
agentheim provider list
```

3. Rotate a secret if needed:

```bash
agentheim provider rotate-secret openai
```

4. Switch to a backup provider:

```bash
agentheim provider add backup --template openai_v1 --model gpt-4o-mini --role planner --api-key $env:BACKUP_KEY
agentheim provider assign-all --provider backup --model gpt-4o-mini
```

5. If the issue is rate-limiting, reduce concurrent load or switch to a local provider for non-critical tasks.

---

## Configuration

AI providers are configured through Agentheim provider profiles. Secrets are stored in the OS keychain by default, with encrypted local vault fallback. `.env` provider setup is migration-only and is not loaded at runtime.

### Provider Configuration

```bash
agentheim provider templates
agentheim provider add openai --template openai_v1 --model gpt-4o-mini --role planner
agentheim provider list
```

`agentheim doctor` also checks provider profile presence, planner/executor/verifier role coverage, first-class lane readiness, localhost endpoint reachability when local providers are configured, and ContextOps availability.

#### Google AI Services Setup

Gemini API and Vertex AI are supported as native Google lanes.

**Gemini API key path**

```bash
agentheim provider add gemini --template gemini --model gemini-2.5-flash --role planner
agentheim provider assign executor --provider gemini --model gemini-2.5-flash
agentheim provider assign verifier --provider gemini --model gemini-2.5-flash
agentheim ping-models
```

**Vertex AI ADC path**

1. Authenticate ADC:

```bash
gcloud auth application-default login
```

2. Add the provider with explicit project and location metadata:

```bash
agentheim provider add vertex --template vertex_ai --model gemini-2.5-pro --role planner
agentheim provider assign executor --provider vertex --model gemini-2.5-pro
agentheim provider assign verifier --provider vertex --model gemini-2.5-pro
```

3. Edit the provider profile if needed so the provider metadata includes:

- `project_id`: your Google Cloud project id
- `location`: the Vertex region, for example `us-central1`

4. Re-run diagnostics:

```bash
agentheim doctor --skip-connectivity
agentheim ping-models
```

If Vertex fails with permission errors, verify the ADC principal can invoke models in the configured project and location.

#### Self-Hosted OpenAI-Compatible Setup

Agentheim treats localhost and VM-hosted OpenAI-compatible endpoints as the main self-hosted lane.

Common templates:
- `ollama` → `http://localhost:11434/v1`
- `lm_studio` → `http://localhost:1234/v1`
- `vllm` → `http://localhost:8000/v1`
- `tgi` → `http://localhost:8080/v1`
- `llama_cpp` → `http://localhost:8080/v1`

Typical local setup flow:

```bash
agentheim provider add local --template ollama --model llama3.1 --role planner
agentheim provider assign executor --provider local --model llama3.1
agentheim provider assign verifier --provider local --model llama3.1
agentheim doctor --skip-connectivity
agentheim provider test --role planner
```

Quality guidance:
- smaller OSS models may pass `command-assistant` but still fail coding or verifier-heavy flows
- use stronger instruction-following models for `codebase-assistant`
- vision claims only matter when the local server and chosen model both support vision inputs

#### Supported Provider Types

| Type | Description | Example Endpoint |
|------|-------------|-----------------|
| `openai_compatible` | Any OpenAI-compatible API | `https://example.com/v1` |
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
| `agentheim setup` | Interactive setup wizard (recommended for beginners) |
| `agentheim status` | Show readiness, integrations, runs, and next actions |
| `agentheim use <task>` | Launch a task by plain-language goal |
| `agentheim runs` | List, show, report, resume, and open run artifacts |
| `agentheim open` | Open the local web UI |
| `agentheim guided` | Interactive preset picker |
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
| `agentheim report --repo <path> --run-id <id>` | Emit the canonical run summary JSON for a run |
| `agentheim resume --repo <path> --run-id <id>` | Resume a blocked or incomplete run |
| `agentheim presets` | List all available presets |
| `agentheim memory get --key <key>` | Read a value from global memory |
| `agentheim memory set --key <key> --value <value>` | Store a value in global memory |
| `agentheim memory history` | Show approval history stored in global memory |
| `agentheim memory profile --model-id <id>` | Show model profile metadata from global memory |
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

# Generate a debug bundle
agentheim status --debug-bundle
```

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
| **Codebase Assistant** | Inspects → plans → patches → tests → reports on your code | `agentheim use code` |
| **Research Report** | Gathers sources → summarizes → compares → writes a report | `agentheim start research-report` |
| **Local Document Chat** | Indexes documents → answers questions with citations | `agentheim use docs-chat` |
| **File Organizer** | Analyzes → proposes → previews → applies file organization | `agentheim start file-organizer` |
| **Docs Maintainer** | Detects stale documentation → updates or aligns it | `agentheim start docs-maintainer` |
| **GitHub Maintainer** | Summarizes issues → drafts PR descriptions | `agentheim start github-maintainer` |
| **Command Assistant** | Parses natural language → generates safe shell commands | `agentheim use command` |
| **Context Maintainer** | Detects stale context → runs context pipeline | `agentheim start context-maintainer` |

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

Set during setup:

```bash
agentheim setup --privacy-mode local_only
```

Or check the current mode:

```bash
agentheim status
```

### Approval Levels

| Level | Behavior |
|-------|----------|
| `auto-approve` | Read-only ops run automatically |
| `always-ask` | Every non-read operation pauses for approval |
| `risk-based` (default) | LOW auto-runs, MEDIUM asks, HIGH blocks |

---

## Ledger & Artifacts

Runs write artifacts under `.ai-team/runs/<run-id>/` inside the target repository. Common files in the current tree include:

| Artifact | Description |
|----------|-------------|
| `run.json` | Run metadata |
| `ledger.jsonl` | Append-only event log |
| `ledger.hash` | SHA-256 hash chain for tamper detection |
| `tool_calls.jsonl` | All tool invocations |
| `final_report.md` | Human-readable final report |
| `final_report.json` | Workflow-specific structured final report |

The exact artifact set depends on the workflow/runtime. Do not assume every run produces `context_bundle.md`, `plan.md`, `policy_decisions.jsonl`, `patch.diff`, or `verification.json`.

---

## See Also

- [Architecture Overview](ARCHITECTURE.md) — deep dive into system design
- [API Reference](API_REFERENCE.md) — REST API and programmatic usage
- [Troubleshooting](TROUBLESHOOTING.md) — common issues and fixes
- [Safety & Security](SAFETY.md) — privacy modes and approval gates
