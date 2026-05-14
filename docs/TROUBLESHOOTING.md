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

No provider profile is configured.

1. Run `agentheim provider templates`
2. Add a provider, for example `agentheim provider add openai --template openai_v1 --model gpt-4o-mini --role planner`
3. Bind needed roles with `agentheim provider assign <role> --provider openai --model <model>`
4. Verify with `agentheim doctor`

### Provider not connecting

Check that:
- The endpoint URL is correct and reachable
- The provider profile has the right auth mode
- The provider secret was saved in keychain or encrypted vault
- For local providers (Ollama, LM Studio), ensure the service is running

### Provider authentication failed

Typical symptoms:
- `Authentication failed`
- `invalid api key`
- `unauthorized`
- `credentials`

Recovery:
1. Run `agentheim doctor` and confirm provider profile loads.
2. Re-enter or rotate the provider secret with `agentheim provider add` or `agentheim provider rotate-secret`.
3. Confirm endpoint + auth mode match provider docs.
4. Retry with `agentheim ping-models`.
5. If the CLI `doctor` table shows a failed or warning provider profile row, fix that first.

### Provider permission denied / forbidden

Typical symptoms:
- `Permission denied`
- `403 forbidden`
- `access denied`

Recovery:
1. Verify account/service principal has required role on target provider resource.
2. For Vertex AI, confirm ADC is set up and principal has model invoke permissions.
3. Retry with `agentheim ping-models` after role fix.
4. If tool operation requested approval, grant from CLI prompt or lower-risk path.

### Provider endpoint/model mismatch

Typical symptoms:
- `Model not found`
- `deployment not found`
- `unsupported model`
- `bad request`

Recovery:
1. Run `agentheim provider list` and confirm provider id, endpoint, and model/deployment name.
2. For Azure Foundry, confirm the endpoint resolves to your resource and deployment name matches the configured model field.
3. For OpenAI-compatible local servers, verify the model is actually loaded by the server.
4. Retry with `agentheim provider test --role planner`.

### Google ADC / project / location failure

Typical symptoms:
- `ADC not found`
- `requires ADC project`
- `permission denied` on Vertex AI

Recovery:
1. Run `gcloud auth application-default login`.
2. Ensure the provider metadata includes `project_id` and `location`.
3. Confirm the ADC principal can invoke Vertex AI models in that project and region.
4. Retry with `agentheim provider test --profile <profile> --role planner`.

### Local provider not running

Typical symptoms:
- `connection refused`
- `Network unreachable`
- localhost endpoint warnings in `agentheim doctor`

Recovery:
1. Start the local server first, for example Ollama, LM Studio, vLLM, TGI, llama.cpp, or the `.localtest/mock-ai-server/` shim.
2. Re-run `agentheim doctor --skip-connectivity` and confirm `Local endpoint reachability` passes or skips as expected.
3. Retry with `agentheim provider test --role planner`.

### Provider rate limit or temporary outage

Typical symptoms:
- `Rate limit exceeded`
- `quota exceeded`
- `service unavailable`
- `timed out`

Recovery:
1. Retry after short wait.
2. Reduce concurrency or switch to fallback model/provider.
3. Increase provider timeout if model is slow.
4. Re-run `agentheim ping-models` before full workflow.

### Multiple providers not loading

Run `agentheim provider list`. If a provider is missing, add it again with `agentheim provider add` or migrate once with `agentheim provider import-env`.

---

## Model / Provider Issues

### `ping-models` fails for one role

Check the model registry configuration:

```bash
agentheim config-dump --redacted
```

Ensure the model name is correct and the provider supports it. Try a simpler model first (e.g., `gpt-4o-mini` instead of `gpt-4o`).

### Model timeout errors

Increase `timeout_seconds` in the provider profile JSON or recreate the provider with a higher timeout once the CLI exposes timeout editing.

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
agentheim run "Review code" --repo . --allow-dirty
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

Use error category from run report/ledger summary as triage hint:
- `transient` → retry after backoff or switch provider
- `recoverable` → adjust input/prompt, rerun step
- `verification` → inspect verifier output, fix, rerun bounded loop
- `configuration` → fix local/provider config first
- `permission` → grant approval or fix IAM/credentials
- `fatal` → inspect diagnostics before rerun

### Tool call blocked

If a tool is blocked by the policy engine, try:

1. Adjust the approval level: use `--mode auto` for fewer prompts
2. Check privacy mode or policy config: `local_only` blocks network tools
3. For API calls, use LOW or MEDIUM risk tools only; HIGH and CRITICAL tools are rejected by the API route

### Approval required

Typical symptoms:
- `approval_required`
- CLI prompt asking whether to grant a copy/write action

Recovery:
1. Review the requested action and target path carefully.
2. Grant from the CLI prompt when the action is expected.
3. In API/Web flows, retry the same action through CLI if the route only returns the approval request payload.

### Privacy restriction

Typical symptoms:
- network tools blocked while repo is configured for local-only work

Recovery:
1. Confirm whether the current task should stay local-first.
2. Use local tools only, or re-run with a policy/profile that allows the specific networked action.
3. Retry after confirming privacy mode and provider/network policy settings.

### Path confinement

Typical symptoms:
- writes or copies rejected outside allowed workspace paths

Recovery:
1. Check the requested source and destination paths are under the intended repo root.
2. Re-run with paths relative to the target workspace.
3. If the path is intentionally outside the repo, do not bypass confinement silently; use a controlled manual path instead.

### Budget exceeded

Typical symptoms:
- run stops with budget or max-step guard errors

Recovery:
1. Reduce task scope.
2. Lower diff size or split the task into smaller batches.
3. Retry with a narrower prompt or smaller workflow slice.

### Malformed model output

Typical symptoms:
- structured agent returned invalid JSON
- verifier/coder/parser output failed schema parsing

Recovery:
1. Retry once in case it was transient.
2. Switch to a stronger model for the affected role.
3. Reduce prompt ambiguity and prefer a provider/model with proven JSON support.

### Stale context

Typical symptoms:
- context verification says stale
- generated context no longer matches repository state

Recovery:
1. Run `agentheim ctx status`.
2. If stale, run `agentheim ctx run --scope changed` or `agentheim ctx verify --strict`.
3. Re-run the workflow only after the context path is fresh again.

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

If resume/report says ledger metadata is missing or incompatible:
1. Inspect `.ai-team/runs/<run-id>/run.json` and `ledger.jsonl`
2. Re-run `agentheim report --repo . --run-id <id>` to confirm whether fallback metadata loads
3. If ledger is from older format, preserve artifacts and rerun workflow from clean state

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
