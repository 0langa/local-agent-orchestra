# Troubleshooting

> Common issues, diagnostics, and recovery procedures for Agentheim.

---

## Table of Contents

- [Diagnostics](#diagnostics)
- [Installation Issues](#installation-issues)
- [Configuration Issues](#configuration-issues)
- [Model / Provider Issues](#model--provider-issues)
- [Run Issues](#run-issues)
- [Ledger & Recovery](#ledger--recovery)
- [Integration Issues](#integration-issues)
- [Environment Notes](#environment-notes)

---

## Diagnostics

Run these commands first when something isn't working:

```bash
# Overall system health
agentheim doctor

# Test model connectivity
agentheim ping-models

# View resolved configuration (secrets redacted)
agentheim config-dump --redacted
```

---

## Installation Issues

### `ModuleNotFoundError` on import

Make sure you installed in editable mode from the repo root:

```bash
pip install -e .
```

### `agentheim` command not found

Ensure the Python Scripts directory is on your PATH, or use:

```bash
python -m interfaces.cli.cli --help
```

### Tests fail with `ImportError`

Set `PYTHONPATH` to include the repo root:

```bash
# Windows — pytest auto-detects with pythonpath in pyproject.toml
pytest tests\ -q

# Linux/Mac
PYTHONPATH="." pytest tests/ -q
```

---

## Configuration Issues

### `doctor` reports missing provider

Your `.env` file is either missing or the API key environment variable is not set.

1. Copy the example: `cp Agent-Team/.env.example .env`
2. Fill in your API key
3. Verify: `agentheim doctor`

### Provider not connecting

Check that:
- The endpoint URL is correct and reachable
- The API key environment variable name matches `AI_TEAM_PROVIDER_*_API_KEY_ENV`
- The API key is actually set in your environment
- For local providers (Ollama, LM Studio), ensure the service is running

### Multiple providers not loading

Ensure provider IDs are comma-separated with **no spaces**:

```env
# ✅ Correct
AI_TEAM_PROVIDER_IDS=openai,ollama

# ❌ Wrong
AI_TEAM_PROVIDER_IDS=openai, ollama
```

---

## Model / Provider Issues

### `ping-models` fails for one role

Check the model registry configuration:

```bash
agentheim config-dump --redacted
```

Ensure the model name is correct and the provider supports it. Try a simpler model first (e.g., `gpt-4o-mini` instead of `gpt-4o`).

### Model timeout errors

Increase the timeout in your provider configuration:

```env
AI_TEAM_PROVIDER_DEFAULT_TIMEOUT_SECONDS=120
```

### Provider not found

Ensure you're using the correct provider type:

- OpenAI-compatible APIs → `openai_compatible`
- Azure OpenAI → `azure_foundry`
- AWS Bedrock → `aws_bedrock`
- OCI GenAI → `oci_genai`

---

## Run Issues

### Dirty repo blocked

By default, Agentheim refuses to run on repositories with uncommitted changes:

```bash
# Use --allow-dirty if you're sure
agentheim start codebase-assistant --input repo=. --input task="Review code" --input allow-dirty=true
```

### Run fails mid-execution

Inspect and resume the run:

```bash
# List recent runs
agentheim list-runs --repo .

# View run report
agentheim report --repo . --run-id <id>

# Resume from last checkpoint
agentheim resume --repo . --run-id <id>
```

### Tool call blocked

If a tool is blocked by the policy engine, try:

1. Adjust the approval level: use `--mode auto` for fewer prompts
2. Check privacy mode or policy config: `local_only` blocks network tools
3. For API calls, use LOW or MEDIUM risk tools only; HIGH and CRITICAL tools are rejected by the API route

---

## Ledger & Recovery

### Viewing run artifacts

Run artifacts are stored under `.ai-team/runs/<run-id>/` in the target repository:

```
.ai-team/runs/<run-id>/
├── run.json                  # Run metadata
├── ledger.jsonl              # Event log
├── ledger.hash               # Hash chain (tamper verification)
├── config.redacted.json      # Configuration snapshot
├── context_bundle.md         # Context snapshot
├── plan.md                   # Execution plan
├── tool_calls.jsonl          # All tool invocations
├── policy_decisions.jsonl    # Policy decisions
├── patch.diff                # Changes made
├── verification.json         # Verification results
└── final_report.md           # Final output
```

### Verifying ledger integrity

You can programmatically verify the ledger hash chain:

```python
from core.ledger import RunLedger
from pathlib import Path

ledger = RunLedger(repo_root=Path("."), run_dir=Path(".ai-team/runs/<run-id>"))
valid, broken_links = ledger.verify_chain()
print(f"Ledger valid: {valid}")
```

### Recovering from a failed run

```bash
agentheim resume --repo . --run-id <id>
```

This replays the event log and resumes from the last checkpoint. Works for most failure modes including network errors, provider timeouts, and approval timeouts.

---

## Integration Issues

### Optional integrations unavailable

Local workflows continue even when external integrations are unavailable:

| Integration | Effect When Unavailable |
|-------------|------------------------|
| GitHub (`gh` CLI) | GitHub workflow pack disabled |
| MCP servers | MCP tools not registered |
| Web research | HTTP tool falls back to requests only |
| Playwright | Browser tool falls back to HTTP-only mode |

### MCP tools not showing up

1. Check that `.ai-team/mcp.json` exists and is valid JSON
2. Ensure `AI_TEAM_ENABLE_MCP=true` is set
3. Check that MCP server binaries are installed and on PATH

### WebSocket not connecting

- Ensure the API server is running (`uvicorn`)
- Check that the run ID is correct
- The WebSocket closes cleanly for completed runs

---

## Environment Notes

### Windows: `pytest` temp cleanup warnings

These are harmless Windows-specific warnings from pytest's temp directory cleanup. They do not affect test results.

### Windows: Desktop UI fallback

If PyQt6 is not installed, the desktop UI falls back to tkinter, then to opening a browser window.

### Pydantic `ArbitraryTypeWarning`

A warning may appear around lock validation in tests. This is non-blocking and does not affect functionality.

---

## See Also

- [User Guide](USER_GUIDE.md) — installation and configuration
- [Development & Testing](DEV_TESTING.md) — running the test suite
- [Safety & Security](SAFETY.md) — privacy modes and approval gates
