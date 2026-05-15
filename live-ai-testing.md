# Live AI Testing Matrix

Purpose: track live provider evidence separately from local regression evidence. This file must avoid mixing historical live runs with current drift-sweep checks.

Run live AI checks from repo root with the intended provider profile configured. Keep live retries bounded to 2 attempts with a 120 second timeout per attempt unless a task-specific note says otherwise.

---

## Fresh Live Evidence

### Azure Foundry Lane — 2026-05-15

Profile `azure-real` (provider_type `azure_foundry`, model `gpt-5.4-mini`) via `scripts/live_validate.py`:

| Check | Result | Duration | Evidence |
|-------|--------|----------|----------|
| doctor | pass | 4.3s | All checks passed |
| ping-models | pass | 18.9s | All roles responded ok |
| provider-planner | pass | 3.7s | `"ok": true` |
| provider-executor | pass | 4.0s | `"ok": true` |
| provider-verifier | pass | 3.6s | `"ok": true` |
| command-assistant | pass | 7.0s | `status='done'`; run_id `20260515-181130-command-assistant-run` |

**Interpretation:** OpenAI-compatible/Azure lane now has current structured live evidence for provider smoke, role connectivity, and one stable preset end-to-end. Lane gate partially satisfied; additional stable preset runs (local-document-chat, codebase-assistant, context-maintainer) would strengthen the claim before `stable` promotion.

## Current Drift Sweep

**Sweep date:** 2026-05-15

This sweep verified docs, governance, CLI smoke, test collection, and the live validation runner mechanics. The Azure live gate was rerun above.

| Check | Result | Evidence |
|-------|--------|----------|
| Agent instruction drift | pass | `python scripts/check-agent-instructions.py` |
| Directive devtest | pass | `powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt` |
| Baseline smoke gate | pass after Phase 4 slice | `powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt` |
| CLI help smoke | pass | included in directive devtest |
| Doctor smoke | pass | `doctor --skip-connectivity`, included in directive devtest |
| Test collection | pass | `pytest --collect-only -q` collected 1230 total tests; default lane selected 1195 and deselected 35 |
| Markdown local links | pass after docs sync | repo-wide `*.md` link scan |

---

## Historical Live Evidence

Last recorded live provider runs were on 2026-05-14 against Azure Foundry profile `azure-real`.

| Area | Historical status | Notes |
|------|-------------------|-------|
| Azure provider smoke | pass | `doctor`, `ping-models`, and role provider tests were previously recorded as passing |
| Codebase assistant / coding run | pass with capable models | Historical runs passed with `gpt-5.4` and `gpt-4.1`; `gpt-4.1-mini` was insufficient for the division-by-zero coding task |
| Command assistant | pass | Historical live command path generated Windows-compatible shell output |
| Docs maintainer | partial/pass | Plan mode passed; apply mode still needs explicit live validation |
| File organizer | pass | Historical live dry-run and apply paths moved files as expected |
| Local document chat | pass | Historical live run answered with citation from local docs |
| Context maintainer | pass for dry-run/patch planning | Fresh runs emitted reports and initiation events |
| GitHub maintainer | pass | Historical live run summarized issues and drafted PR text |
| Research report | mixed historical notes | Unit/deep path and at least one live CLI path were recorded as passing, but API/Web live paths still need a clean rerun before stable claim |
| Resume/report | partial | Fresh command-assistant/context-maintainer ledgers were fixed; old ledgers without `RUN_INITIATED` may remain non-resumable |
| API/Web UI | partial | TestClient and selected live server paths passed historically; full provider-backed Web UI matrix not complete |
| Guided TUI | pass | Scripted stdin route to local-document-chat passed historically |
| Desktop UI | not live tested | Import/availability is not the same as full desktop validation |

Historical model entries include `gpt-4.1`, `gpt-4.1-mini`, and `gpt-5.4`. Treat those as dated evidence, not current provider defaults.

---

## Google Lane Fresh Evidence

Recorded on 2026-05-14 using profile `gemini-live` with model `gemini-2.5-flash`.

| Check | Result | Evidence |
|-------|--------|----------|
| Gemini API key path | pass | `python -m interfaces.cli.cli provider test --profile gemini-live --role planner` |
| Gemini text connectivity | pass | `python -m interfaces.cli.cli ping-models` after `python -m interfaces.cli.cli provider use gemini-live` |
| Gemini structured JSON-capable provider path | pass | `gemini-live` was created with `text,json` capabilities and `provider test` passed against the live endpoint |
| Gemini stable preset end-to-end | partial / blocked | after temporarily assigning planner capability `plan`, `python -m interfaces.cli.cli start command-assistant --input "command_description=print a tiny json object with keys status and source"` progressed into workflow execution but failed with `ValueError: No model for role='executor' with capability='code_edit'`; default profile was then restored with `python -m interfaces.cli.cli provider use azure-real` |
| Vertex ADC path | not tested | no fresh ADC-backed run in this sweep |
| Google vision path | not tested | no fresh multimodal run in this sweep |

Interpretation:

- Fresh live evidence now proves the Gemini API-key path and tiny live request path.
- This is enough to count `Gemini API key path`, `text`, and a minimal `structured JSON` provider path as freshly proven.
- This is not yet enough to claim the full Google lane gate, because Vertex ADC, vision, and one stable preset end to end remain unproven.

---

## Provider Lanes

### Harden First

| Lane | Goal | Required evidence |
|------|------|-------------------|
| OpenAI-compatible providers | Covers OpenAI, Azure OpenAI/Foundry OpenAI-compatible endpoint, local gateways, and many hosted vendors | provider smoke, structured output, streaming/tool-call compatibility where supported, CLI/API/Web preset run |
| Google AI services | Covers Gemini API, Vertex AI, and Google Cloud use cases | provider smoke, structured output, vision-capable path, CLI/API/Web preset run |
| Self-hosted models | Covers Ollama, LM Studio, localhost gateways, and cloud VM-hosted OSS models | no-secret local setup path, capability detection, degraded quality handling, CLI preset run |

### Functional But Lower Polish Bar

Other integrated providers should remain loadable and theoretically functional, but they do not block the baseline unless they break provider registry integrity, lazy loading, config parsing, or documented capability semantics.

### Self-Hosted Localhost Compatibility Shim Evidence

Recorded on 2026-05-14 using the gitignored local helper under `.localtest/mock-ai-server/`.

| Check | Result | Evidence |
|-------|--------|----------|
| Localhost Azure/OpenAI-compatible proxy startup | pass | `powershell -ExecutionPolicy Bypass -File .\.localtest\mock-ai-server\start-gpt54-mini-azure.ps1 -Fake` |
| Generated local profile set | pass | `.localtest/mock-ai-server/make_agentheim_profiles.py` emitted 18 local mock profiles |
| Localhost provider smoke through Agentheim provider configs | pass | `python .\.localtest\mock-ai-server\smoke_agentheim_http_providers.py` |

Interpretation:

- This is valid evidence that self-hosted-shaped localhost configuration paths work through Agentheim.
- This proves endpoint wiring, profile generation, role binding, and request/response handling against a localhost endpoint.
- This does **not** prove real OSS model quality or actual local-server quirks for Ollama, LM Studio, vLLM, TGI, or llama.cpp.
- Keep the self-hosted lane as partial until at least one real local endpoint is rerun end-to-end.

---

## Current Live Gaps

These need fresh evidence before claiming a polished baseline:

| Gap | Needed proof |
|-----|--------------|
| OpenAI-compatible lane | Run provider smoke and at least command-assistant, codebase-assistant, local-document-chat, report/resume paths |
| Google lane | Run Gemini API and Vertex AI smoke, structured JSON output, vision path, one preset end to end |
| Self-hosted lane | Run Ollama or LM Studio smoke, structured output failure handling, one local preset end to end |
| Research report | Clean CLI + API + Web live rerun with target repo/input honored |
| Resume/report | Fresh ledgers for every stable preset resume/report cleanly or fail with explicit unsupported reason |
| Web UI | Provider-backed preset run matrix, status polling, and artifact rendering |
| Desktop UI | Launch, route to local web UI, run one preset, close cleanly |
| Tools/adapters | Browser, HTTP, local DB, MCP, WebResearchAdapter, GitHubCliAdapter, MCPClientAdapter |
| Safety negatives | Missing secret, invalid model, auth failure, rate limit, timeout, malformed JSON, unsafe patch, path escape |
| Vision | Vision-capable provider path and non-vision rejection path |

---

## Baseline Readiness Gate

Do not claim live baseline readiness until:

- docs/instruction drift checks pass
- default test lane and full collection are understood and recorded
- top 3 provider lanes have current evidence
- stable presets pass CLI and at least one non-CLI surface
- report/resume behavior is deterministic for stable presets
- safety-negative cases fail cleanly with actionable errors
- live evidence includes date, provider profile, model/deployment, command, and outcome

---

## Live Validation Runner

Use `scripts/live_validate.py` (or `devtest/live_validate.ps1` on Windows) for repeatable, bounded live evidence collection.

```powershell
# List available checks
python scripts/live_validate.py --list

# Run default matrix against current provider profile
python scripts/live_validate.py --repo-root . --test-repo ../agentheim-testing-enviroment

# Run only stable presets with max 2 attempts
python scripts/live_validate.py --include-tags stable --max-attempts 2

# Run with explicit profile override for evidence logging
python scripts/live_validate.py --profile azure-real --only doctor,ping-models
```

The runner produces:
- `evidence.jsonl` — one line per test with command, provider/profile, model, repo path, run ID, result, artifact path, timestamp, failure category
- `summary.json` — structured pass/fail/skip counts and per-test metadata
- `summary.md` — human-readable Markdown table
- Per-test `.stdout.log` and `.stderr.log` files

Failure categories:
- `timeout` — exceeded per-test timeout (default 120s)
- `provider_auth` — authentication or configuration failure
- `provider_rate_limit` — rate limit or quota exhaustion
- `provider_error` — other provider-side error
- `policy_denial` — tool invocation denied by policy engine
- `approval_required` — approval required but not granted
- `model_misformat` — model output did not match expected schema
- `missing_output` — expected pattern not found in output
- `exit_failure` — non-zero exit code without specific provider error
- `skipped` — dependency missing (e.g., prior test run_id unavailable)
- `unexpected_error` — catch-all for uncategorized failures

---

## Useful Commands

```powershell
python scripts/check-agent-instructions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt
pytest --collect-only -q
python -m interfaces.cli.cli --help
python -m interfaces.cli.cli doctor --skip-connectivity
python -m interfaces.cli.cli provider test --role planner
python -m interfaces.cli.cli ping-models
```
