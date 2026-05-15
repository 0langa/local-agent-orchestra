# Live AI Testing Matrix

Purpose: track live provider evidence separately from local regression evidence. This file must avoid mixing historical live runs with current drift-sweep checks.

Run live AI checks from repo root with the intended provider profile configured. Keep live retries bounded to 2 attempts with a 120 second timeout per attempt unless a task-specific note says otherwise.

---

## Fresh Live Evidence

### Azure Foundry Full Matrix — 2026-05-15

Profile `azure-real` (provider_type `azure_foundry`, model `gpt-5.4-mini`) via `scripts/live_validate.py --max-attempts 2`:

| Check | Result | Duration | Evidence |
|-------|--------|----------|----------|
| doctor | pass | 4.5s | All checks passed |
| ping-models | pass | 19.8s | All roles responded ok |
| provider-planner | pass | 3.6s | `"ok": true` |
| provider-executor | pass | 3.8s | `"ok": true` |
| provider-verifier | pass | 3.7s | `"ok": true` |
| command-assistant | pass | 6.7s | `status='done'`; run_id `20260515-183543-command-assistant-run` |
| local-document-chat | fail | 17.5s | `status='failed'`; empty answer against test repo (2 attempts) |
| codebase-assistant | fail | 18.0s | `status='failed'` against test repo (2 attempts) |
| context-maintainer | pass | 1.9s | `ContextRunReport` emitted successfully |
| file-organizer-dry-run | pass | 11.8s | `status='done'`; run_id `20260515-183705-file-organization-run` |
| docs-maintainer-plan | pass | 17.8s | `status='done'`; run_id `20260515-183716-docs-maintenance-run` |
| github-maintainer | pass | 8.4s | `status='done'`; run_id `20260515-183734-github-maintenance-run` |
| research-report | fail | 27.1s | exit code 1; known-failing tag (2 attempts) |
| report-command-assistant | pass | 0.9s | `"status": "completed"` in canonical run summary JSON |
| resume-command-assistant | pass | 5.3s | `"all_success": true` in resume result JSON |

**Interpretation:**

- OpenAI-compatible/Azure lane now has full 15-check structured live evidence.
- Provider smoke (doctor, ping-models, 3 role tests): all pass.
- Stable presets: 2/4 pass (`command-assistant`, `context-maintainer`). `local-document-chat` and `codebase-assistant` fail on `gpt-5.4-mini` — model capability limitation, not code bug.
- Beta presets: 3/4 pass (`file-organizer-dry-run`, `docs-maintainer-plan`, `github-maintainer`). `research-report` fails with exit code 1 (known-failing).
- Followup paths: `report-command-assistant` and `resume-command-assistant` both pass. Report/resume gap now closed for `command-assistant`.
- Lane gate partially satisfied. Missing: `local-document-chat`, `codebase-assistant`, `research-report` green runs; Web/Desktop interface smoke; vision.

### Safety-Negative Checks — 2026-05-15

Profile `azure-real` via `scripts/live_validate.py` with `expect_failure` flag:

| Check | Result | Duration | Evidence |
|-------|--------|----------|----------|
| invalid-role | pass | 1.1s | `provider test --role nonexistent-role` rejected with `nonexistent-role is not one of` |
| invalid-profile | pass | 1.4s | `provider test --profile nonexistent-profile` rejected with `Unknown profile` |
| copy-denied | pass | 1.4s | `copy /etc/passwd C:\temp\...` aborted with `Approval required` + `Aborted` |

**Interpretation:** Safety-negative CLI paths fail cleanly with actionable errors. Runner now supports `expect_failure` tests.

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

> **Archive note:** These are dated historical results. Some entries are **superseded** by current evidence above. Do not treat this table as current truth.

| Area | Historical status | Current status | Notes |
|------|-------------------|----------------|-------|
| Azure provider smoke | pass | ✅ Still valid | Fresh evidence 2026-05-15 confirms pass |
| Codebase assistant / coding run | pass with capable models | ⚠️ Superseded | Passes with `gpt-5.4` / `gpt-4.1`; fails with `gpt-5.4-mini` (2026-05-15) |
| Command assistant | pass | ✅ Still valid | Fresh pass 2026-05-15 on azure-real / gpt-5.4-mini |
| Docs maintainer | partial/pass | ⚠️ Superseded | Plan mode passes on azure-real; fails on Gemini due to rate limit (2026-05-15) |
| File organizer | pass | ⚠️ Superseded | Dry-run passes on azure-real and Gemini (2026-05-15); apply path not re-tested |
| Local document chat | pass | ❌ Contradicted | Historical pass with capable models; fails on azure-real / gpt-5.4-mini (2026-05-15) and Gemini |
| Context maintainer | pass for dry-run/patch planning | ✅ Still valid | Fresh pass 2026-05-15 on both azure-real and Gemini |
| GitHub maintainer | pass | ⚠️ Superseded | Fresh pass 2026-05-15 on azure-real; not tested on Gemini due to rate limit |
| Research report | mixed historical notes | ❌ Contradicted | Historical CLI pass; fails on azure-real / gpt-5.4-mini (exit 1, 2026-05-15) and Gemini |
| Resume/report | partial | ✅ Still valid | `command-assistant` report/resume pass 2026-05-15 on azure-real |
| API/Web UI | partial | ⚠️ Unchanged | TestClient paths pass; full provider-backed Web UI matrix not complete |
| Guided TUI | pass | ⚠️ Unchanged | Historical scripted stdin pass; not re-run in 2026-05-15 sweep |
| Desktop UI | not live tested | ⚠️ Unchanged | Still not live tested |

Historical model entries include `gpt-4.1`, `gpt-4.1-mini`, and `gpt-5.4`. Treat those as dated evidence, not current provider defaults.

---

## Google Lane Fresh Evidence

### Gemini API Key Path — 2026-05-14

Profile `gemini-live` with model `gemini-2.5-flash`:

| Check | Result | Evidence |
|-------|--------|----------|
| Gemini API key path | pass | `provider test --profile gemini-live --role planner` |
| Gemini text connectivity | pass | `ping-models` after `provider use gemini-live` |
| Gemini structured JSON-capable provider path | pass | `gemini-live` created with `text,json` capabilities; `provider test` passed |

### Gemini Full Matrix — 2026-05-15

Profile `gemini-lane2` (expanded 14-role profile) with model `gemini-2.5-flash` via `scripts/live_validate.py`:

| Check | Result | Duration | Evidence |
|-------|--------|----------|----------|
| doctor | pass | 2.5s | All checks passed |
| ping-models | fail | 45.2s | 429 Too Many Requests on multiple roles |
| provider-planner | fail | 5.3s | 429 Too Many Requests (2 attempts) |
| provider-executor | pass | 2.2s | `"ok": true` |
| provider-verifier | pass | 6.1s | `"ok": true` |
| command-assistant | fail | 5.5s | 429 rate limit |
| local-document-chat | fail | 2.3s | 429 rate limit |
| codebase-assistant | fail | 6.1s | 429 rate limit |
| context-maintainer | pass | 2.0s | `ContextRunReport` emitted |
| file-organizer-dry-run | pass | 5.8s | `status='done'` |
| docs-maintainer-plan | fail | 5.5s | 429 rate limit |
| github-maintainer | fail | 5.3s | 429 rate limit |
| research-report | fail | 5.6s | 429 rate limit |
| report-command-assistant | skipped | — | command-assistant failed, no run_id |
| resume-command-assistant | skipped | — | command-assistant failed, no run_id |
| invalid-role | pass | 1.0s | rejected cleanly |
| invalid-profile | pass | 1.5s | rejected cleanly |
| copy-denied | pass | 1.5s | `Approval required` + `Aborted` |

### Gemini Matrix with 45s Delay — 2026-05-15

Re-ran with `--delay-between-tests 45` to test rate-limit mitigation:

| Check | Result | Duration | Evidence |
|-------|--------|----------|----------|
| doctor | fail | 5.6s | 429 Too Many Requests (model connectivity check) |
| ping-models | fail | 61.2s | 429 on multiple roles |
| provider-planner | fail | 5.4s | 429 (2 attempts) |
| provider-executor | fail | 5.6s | 429 |
| provider-verifier | fail | 5.4s | 429 |
| command-assistant | fail | 5.7s | 429 |
| local-document-chat | fail | 2.0s | missing output (not rate limit) |
| codebase-assistant | fail | 6.4s | 429 |
| context-maintainer | pass | 1.6s | `ContextRunReport` emitted |
| file-organizer-dry-run | pass | 5.8s | `status='done'` |
| docs-maintainer-plan | fail | 5.6s | 429 |
| github-maintainer | fail | 5.4s | 429 |
| research-report | fail | 5.3s | missing output (not rate limit) |
| invalid-role | pass | 1.1s | rejected cleanly |
| invalid-profile | pass | 0.8s | rejected cleanly |
| copy-denied | pass | 0.9s | `Approval required` + `Aborted` |

**Interpretation:**

- Gemini provider adapter works: executor and verifier role tests pass when not rate-limited.
- **Aggressive rate limiting:** `gemini-2.5-flash` free tier returns 429 Too Many Requests after just a few sequential calls. **45-second inter-test delays are insufficient.** The rate limit appears to require minutes-level cooldown or a paid tier.
- `context-maintainer` and `file-organizer-dry-run` pass because they either don't hit the Gemini endpoint or use AICtx caching.
- Vertex ADC path: not tested. Vision path: not tested.
- Lane 2 gate partially satisfied. Need: minutes-level delays or paid-tier Gemini for reliable matrix testing; clean planner test; one preset end-to-end without 429.

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
| OpenAI-compatible lane | Provider smoke done. Need codebase-assistant, local-document-chat green runs. Web/Desktop smoke pending. |
| Google lane | Run Gemini API and Vertex AI smoke, structured JSON output, vision path, one preset end to end |
| Self-hosted lane | Run Ollama or LM Studio smoke, structured output failure handling, one local preset end to end |
| Research report | Clean CLI + API + Web live rerun with target repo/input honored |
| Resume/report | `command-assistant` report/resume pass 2026-05-15. Need same for `context-maintainer`, `local-document-chat`, `codebase-assistant`. |
| Web UI | Provider-backed preset run matrix, status polling, and artifact rendering |
| Desktop UI | Launch, route to local web UI, run one preset, close cleanly |
| Tools/adapters | Browser, HTTP, local DB, MCP, WebResearchAdapter, GitHubCliAdapter, MCPClientAdapter |
| Safety negatives | CLI input validation (invalid role/profile) and approval-required path proven 2026-05-15. Remaining: auth failure, rate limit, timeout, malformed JSON, unsafe patch, path escape. |
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
