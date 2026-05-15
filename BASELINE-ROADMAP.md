# Agentheim Baseline Roadmap

This roadmap turns the old catch-up list into the blueprint for reaching a polished Agentheim baseline: a local-first AI automation platform with a reliable core runtime, safe tool execution, clear support tiers, proven provider lanes, consistent interfaces, and live validation evidence.

The roadmap is based on the current repository state, especially:

- Binding rules in [`AGENTS.md`](AGENTS.md) and [`.github/instructions/`](.github/instructions/)
- Current architecture in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Safety model in [`docs/SAFETY.md`](docs/SAFETY.md)
- API surface in [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)
- CLI surface in [`interfaces/cli/cli.py`](interfaces/cli/cli.py)
- Provider profiles and templates in [`config/config.py`](config/config.py)
- Provider registry in [`core/model_registry.py`](core/model_registry.py)
- Workflow and preset registries in [`workflows/registry.py`](workflows/registry.py) and [`presets/__init__.py`](presets/__init__.py)
- Live validation record in [`live-ai-testing.md`](live-ai-testing.md)

## Status Legend

- 🟢 done / strong evidence
- 🟡 partial / needs more work or fresher proof
- 🔴 not touched yet
- ⚪ missing / not yet proven

## Baseline Goal

Agentheim baseline is done when a new user can install the project, configure one first-class provider lane, run core presets from CLI and API, inspect/resume/report runs, and trust that every side effect is policy-gated, auditable, documented, and validated.

The baseline is not "every experimental subsystem polished." The baseline is a stable spine that future work can build on without guessing.

## Non-Negotiable Product Decisions

### Provider Focus

All currently integrated providers remain supported as functional-in-theory adapters where possible. Hardening priority is:

1. **OpenAI-compatible lane**: OpenAI-compatible APIs are the main provider contract because they cover OpenAI, Azure OpenAI / Azure Foundry, Groq, OpenRouter, Ollama, LM Studio, vLLM, TGI, llama.cpp servers, and many cloud endpoints.
2. **Google lane**: Gemini API and Vertex AI are first-class because Gemini has broad free access and Vertex/Gemini API are realistic test targets.
3. **Self-hosted OSS lane**: localhost or cloud-VM OpenAI-compatible endpoints are first-class because they are free, common, and important for local-first users.

Other integrated providers stay available but are labeled advanced until they have equivalent docs, tests, and live evidence.

### Support States

Every exposed subsystem, provider lane, workflow, preset, and interface must carry one state:

| State | Meaning | Promotion Gate |
| --- | --- | --- |
| Stable | Reliable default path; safe for first-run docs | Unit tests, smoke tests, docs, live evidence, troubleshooting entries |
| Beta | Intended for real use, known limits documented | Unit tests, smoke tests, docs, at least one live path |
| Experimental | Useful but not baseline-critical | Import/unit tests, explicit limits, hidden from first-run path |
| Internal | Implementation detail; not a user promise | Covered by owner subsystem tests |

No unlabeled surface should appear in README, CLI help, API docs, or Web UI.

### Tier-1 User Journeys

Baseline work serves these journeys only:

1. Install and run `doctor`
2. Add provider and ping models
3. Inspect and plan against a repository
4. Run stable presets
5. Report and resume a run
6. Inspect run artifacts and diagnostics
7. Use API/Web/Desktop only as thin layers over the same contracts

Everything outside this set is beta or experimental until promoted.

## Current Maturity Snapshot

### Strong Foundations

- Core runtime primitives exist: DAG execution, ledger hash chain, artifact store, policy engine, state machine, retry, budget, privacy, approval, and redaction.
- Built-in workflows exist for coding, research, documents, file organization, docs maintenance, GitHub maintenance, command assistant, and context maintenance.
- Provider profiles replaced legacy `.env` loading, with vault/keychain-backed secret refs.
- AICtx integration is routed through ContextOps and `.ai-team/runs/` as the canonical runtime artifact store.
- Tests are broad, with subsystem suites for core, memory, tools, providers, workflows, interfaces, and smoke paths.

### Main Risks

1. **Tool policy path is not unified across interfaces.** API/Web UI directly invoke tools after coarse risk checks instead of always using the policy engine and ledger path.
2. **Support promise exceeds evidence.** README/docs expose many presets, workflows, providers, interfaces, marketplace, federation, distributed, multimodal, and remote/OCI areas without a consistent support state.
3. **Provider capability claims are too optimistic.** Templates list streaming, tool calling, JSON, and vision capabilities that are not equally implemented or live-tested across adapters.
4. **Live validation is inconsistent.** `live-ai-testing.md` contains contradictions around `research-report`, `resume`, `copy`, API/Web coverage, model names, and test counts.
5. **Interface parity is weak.** CLI, API, Web UI, Desktop, and Guided TUI expose overlapping but not identical behavior and status shapes.
6. **Docs and instruction drift exist.** Some active docs and checks do not reflect all binding instruction files or current AICtx integration shape.

## Roadmap Phases

Phases are ordered by dependency. Do not expand product surface until earlier gates pass.

---

## 🟢 Phase 0 - Roadmap Governance And Evidence Cleanup

**Status:** Complete as of 2026-05-14. Evidence is now captured in `docs/SUPPORT_MATRIX.md`, `docs/TIER1_CONTRACTS.md`, `live-ai-testing.md`, `docs/DEV_TESTING.md`, and the `baseline` devtest mode.

**Goal:** Make active docs and validation evidence trustworthy before claiming product readiness.

**Why first:** Current docs contain contradictions. A roadmap based on stale evidence will make later hardening unreliable.

### Work

1. Replace `live-ai-testing.md` with a single non-contradictory matrix:
   - one current provider/profile row per live run
   - one status per command/workflow/tool/interface
   - one result source per claim
   - explicit `not tested` instead of mixed pass/fail text
2. Add a support-state matrix in docs:
   - stable/beta/experimental/internal
   - owner subsystem
   - entrypoints
   - docs status
   - unit/smoke/live evidence
   - known limits
3. Add a contract matrix for Tier-1 journeys:
   - CLI command
   - API route
   - Web UI/Desktop availability
   - auth requirement
   - output schema
   - docs
   - tests
4. Fix instruction drift:
   - ensure `.github/instructions/07-chat-output.md` is included in instruction checks
   - remove or update stale references to deleted AICtx planning docs
5. Update test-count docs from actual local commands, not memory or older notes.

### Files

- `live-ai-testing.md`
- `docs/README.md`
- `docs/DEV_TESTING.md`
- `docs/AGENT_OPERATIONS.md`
- `docs/API_REFERENCE.md`
- `docs/USER_GUIDE.md`
- `docs/TROUBLESHOOTING.md`
- `scripts/check-agent-instructions.py`
- `.github/agents/agentheim-autonomous-engineer.agent.md`

### Done When

- No active doc gives conflicting pass/fail status for the same surface.
- Every exposed subsystem has a support state.
- Every Tier-1 journey has a mapped CLI/API/docs/tests row.
- `python scripts/check-agent-instructions.py` passes.
- Local Markdown links pass.

### Verification Gate

```powershell
python scripts/check-agent-instructions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
python -m interfaces.cli.cli --help
python -m interfaces.cli.cli doctor --skip-connectivity
```

---

## 🟢 Phase 1 - Safety And Runtime Spine

**Status:** Complete as of 2026-05-14. All user-facing interface tool invocations (API, Web UI, CLI copy) route through `ToolInvoker`. Operation-level filesystem risk resolves read/list/stat to none and write/copy to medium. CLI grants/denies interactively. API and Web UI now expose explicit approval grant/deny continuation routes for medium-risk operations, and those flows are covered by tests with ledger proof. Core no longer imports product-specific implementations (`agents.self_improving`, `monitoring`). State transitions emit canonical `STATE_TRANSITION` events. Safety docs describe actual behavior.

**Goal:** Ensure every side effect flows through one policy-gated, ledger-audited path.

**Why:** Safety by default is an immutable law. API/Web tool invocation currently risks bypassing the full policy path.

### Work

1. Create one tool invocation service:
   - tool lookup
   - operation-level risk resolution
   - privacy enforcement
   - `PolicyEngine.evaluate()`
   - approval request or denial handling
   - tool execution only after allow
   - ledger events for policy/tool request/result/error
2. Replace direct interface tool calls:
   - API `/api/tools/{tool_id}/invoke`
   - Web UI tool invoke path
   - CLI copy/tool helper paths where applicable
   - workflow shim registries where direct invocation exists
3. Add operation-level risk:
   - filesystem read/list/stat -> low or none
   - filesystem write/copy -> medium
   - delete/destructive operations -> high or critical
   - shell and network retain strict sandbox/policy enforcement
4. Wire approval UX minimally:
   - CLI can grant/deny when policy returns `ask`
   - API/Web return an approval request payload and expose explicit grant/deny continuation routes
   - ledger records request and decision
5. Move core side dependencies outward:
   - remove `agents.self_improving` and monitoring-specific imports from core runtime paths
   - use injected hooks or subscribers outside `core/`
6. Make state transitions part of event truth:
   - emit structured ledger events for runtime state transitions
   - keep legacy JSONL mirrors only for compatibility

### Files

- `core/tool_protocol.py`
- `core/policy_engine.py`
- `core/approval_workflow.py`
- `core/ledger.py`
- `core/run_executor.py`
- `core/state_machine.py`
- `tools/filesystem/__init__.py`
- `tools/registry.py`
- `interfaces/api_server/app.py`
- `interfaces/web_ui/app.py`
- `interfaces/cli/cli.py`
- `tests/test_tool_protocol.py`
- `tests/test_policy_engine.py`
- `tests/test_policy_audit.py`
- `tests/test_api_server.py`
- `tests/test_web_ui.py`
- `tests/test_filesystem_tool.py`

### Done When

- No user-facing interface invokes a side-effecting tool outside the maintained policy path.
- Medium-risk filesystem write/copy produces `ask` or policy denial as configured.
- Tool decisions and results are visible in the run ledger.
- Core runtime no longer imports product-specific or monitoring-specific implementations.
- Safety docs describe actual behavior.

### Verification Gate

```powershell
pytest -q tests/test_tool_protocol.py tests/test_policy_engine.py tests/test_policy_audit.py tests/test_filesystem_tool.py
pytest -q tests/test_api_server.py tests/test_web_ui.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -NoPrompt
```

---

## 🟡 Phase 2 - Provider Lanes

**Status:** Partial as of 2026-05-15. Lane 1 (OpenAI-compatible/Azure) now has full 18-check structured live evidence via `scripts/live_validate.py` against `azure-real` profile: provider smoke (5/5 pass), stable presets (2/4 pass), beta presets (3/4 pass), report/resume followups (2/2 pass), safety negatives (3/3 pass). Lane 2 (Google) has fresh Gemini API-key path evidence from 2026-05-14 and full matrix attempted 2026-05-15 against `gemini-lane2` — executor/verifier pass, but aggressive 429 rate limits from `gemini-2.5-flash` block reliable full-matrix validation. Lane 3 (self-hosted) remains partially proven via localhost compatibility shim only.

**Goal:** Make the top 3 provider lanes polished, documented, and empirically proven.

**Why:** Provider setup is the first real product hurdle. Broad adapter lists are less valuable than three excellent paths.

### 🟢 Lane 1: OpenAI-Compatible, Including Azure

**Decision:** This is the default first-class provider lane. Keep Chat Completions as the compatibility baseline. Add newer APIs or Azure variants behind capability switches instead of forcing every endpoint into one behavior.

#### Work

1. 🟢 Harden `OpenAIV1Provider`:
   - 🟢 omit auth header/client key behavior for `auth_mode="none"` where possible
   - 🟢 support compatible max-token field variants where required
   - 🟢 normalize empty content as a provider failure when structured output is required
   - 🟢 expose clear retry/auth/rate-limit/timeout errors
2. 🟢 Harden `AzureFoundryProvider`:
   - 🟢 keep `/openai/v1` normalized path as primary
   - 🟢 document deployment/model naming expectations
   - ⚪ add bearer/Entra path only if implemented and tested
   - 🟢 add clear errors for wrong endpoint, wrong deployment, auth failure, and unsupported model capability
3. 🟢 Add local/self-hosted templates under the OpenAI-compatible lane:
   - 🟢 Ollama local
   - 🟢 LM Studio
   - 🟢 vLLM
   - 🟢 TGI
   - 🟢 llama.cpp server
   - 🟢 generic cloud VM endpoint with bearer auth
4. Keep advanced OpenAI-compatible providers listed as advanced:
   - Groq
   - OpenRouter
   - Together
   - Mistral
   - DeepSeek
   - Kimi/Moonshot
   - xAI/Grok
5. Add live setup scorecards:
   - install requirement
   - endpoint format
   - auth mode
   - `provider add` command
   - role assignment command
   - `doctor` output
   - `ping-models` output
   - common failures

#### Gates

- OpenAI-compatible remote endpoint passes `provider test`, `ping-models`, and `ai_test.ps1`.
- Azure Foundry passes `provider test`, `ping-models`, and at least coding or command-assistant live path.
- Ollama or LM Studio passes local planner/executor/verifier smoke where model capability is sufficient.

### 🟡 Lane 2: Google AI Services

**Decision:** Gemini API and Vertex AI stay as native Google adapters, not OpenAI-compatible shims.

#### Work

1. 🟢 Share request mapping logic between Gemini API and Vertex AI where possible.
2. 🟢 Support text and JSON output reliably before claiming tools/streaming.
3. 🟢 Fix vision input mapping:
   - 🟢 support data URL/base64 inline image paths where Google API allows it
   - 🟢 support file URI only where explicitly documented
4. 🟢 Add Vertex setup UX:
   - 🟢 ADC requirement
   - 🟢 project ID
   - 🟢 location
   - 🟢 model name
   - 🟢 permissions failure guidance
5. 🟢 Add retry/error wrapping parity with other providers.
6. 🟡 Add Google live validation:
   - 🟢 Gemini API key path
   - ⚪ Vertex ADC path
   - 🟢 text
   - 🟢 structured JSON
   - ⚪ vision when configured

**Status note (2026-05-14):** Fresh Gemini API live evidence now proves the API-key path, provider smoke, and tiny text/JSON connectivity with `gemini-live` against `gemini-2.5-flash` via `provider test` and `ping-models`. Vertex ADC and Google vision remain unproven in the current sweep. A stable-preset end-to-end Gemini run was attempted and advanced farther after temporarily adding planner `plan`, but it still stops before success because the temporary `gemini-live` profile does not provide an executor binding with `code_edit`. Default profile was restored to `azure-real` immediately after the attempt.

#### Gates

- Gemini API passes provider test, JSON structured output smoke, and one stable preset.
- Vertex AI passes provider test with ADC and one stable preset.
- Gemini or Vertex vision path passes `multimodal.image` describe and OCR if the chosen model declares vision.

### 🟡 Lane 3: Self-Hosted Open Source Models

**Decision:** Self-hosted support is first-class through OpenAI-compatible endpoints first. Do not build a separate local-model provider zoo until this path is reliable.

**Status note (2026-05-14):** Localhost compatibility path is now partially proven via `.localtest/mock-ai-server/`, including a localhost Azure/OpenAI-compatible proxy shim and generated local profiles. This validates localhost endpoint wiring, profile/role binding, and request/response flow through self-hosted-shaped configurations, but it does **not** yet replace fresh evidence from a real Ollama, LM Studio, vLLM, TGI, or llama.cpp server.

#### Work

1. 🟢 Add templates and docs for:
   - 🟢 Ollama local
   - 🟢 LM Studio
   - 🟢 vLLM
   - 🟢 TGI
   - 🟢 llama.cpp server
   - 🟢 remote VM endpoint with bearer auth
2. 🟢 Add model quality guidance:
   - 🟢 small models may pass command-assistant but fail coding
   - 🟢 coding preset requires stronger instruction-following and patch quality
   - 🟢 vision requires explicit vision capability
3. ⚪ Add model discovery where low-risk:
   - `/v1/models` for compatible endpoints
   - clear fallback when not supported
4. 🟡 Add local lane live matrix:
   - 🟢 service running
   - 🟢 endpoint reachable
   - 🟢 planner/executor/verifier roles bound
   - ⚪ stable preset outcome

#### Gates

- At least two local/self-hosted endpoints pass `provider test`.
- At least one local/self-hosted endpoint passes a stable non-coding preset.
- Docs clearly explain expected limitations for smaller OSS models.

### 🟢 Cross-Provider Work

1. 🟢 Align `providers/__init__.py` lazy metadata with `DEFAULT_PROVIDER_MAP` or make one source authoritative.
2. 🟢 Make provider template capabilities conservative:
   - 🟢 do not claim streaming/tools/vision unless implemented and tested
   - 🟢 separate declared potential from proven support
3. 🟢 Add provider capability tests:
   - 🟢 text
   - 🟢 JSON
   - 🟢 vision
   - 🟢 auth failure
   - 🟢 timeout/retry
   - 🟢 rate-limit/quota
   - 🟢 empty content
   - 🟢 non-JSON content for structured agents
4. 🟢 Update provider docs and troubleshooting catalog.

---

## 🟡 Phase 3 - Run Diagnostics And Observability

**Status:** Partial as of 2026-05-15. Canonical run summary is now implemented across CLI `report`, `GET /api/runs/{run_id}`, and API/Web SSE/WebSocket final status payloads. Failed-run diagnostics bundle (`run_summary.json`, `diagnostics.md`) is now written automatically by `WorkflowRunner` on step failure and exception paths. Desktop UI shell parity is implemented by architecture inheritance (pywebview wrapper around Web UI routes).

**Goal:** Make every run explainable from one canonical summary.

**Why:** Users should not debug by reading raw artifacts first. CLI/API/UI should show the same run truth.

### Work

1. Define canonical run summary schema:
   - `run_id`
   - workflow and preset
   - status
   - duration
   - repo path redacted
   - provider/model by role
   - state transitions
   - tool counts
   - policy decisions
   - approval requests/decisions
   - verification result
   - artifacts
   - error category
   - next recommended action
2. Build summary from ledger and artifacts, not side-channel state.
   - Implemented for persisted runs in `core/run_summary.py`
3. Use the same summary in:
   - `agentheim report` 🟢
   - `GET /api/runs/{run_id}` 🟢
   - SSE/WebSocket final events 🟢
   - Web UI run detail 🟢
   - Desktop UI shell 🟢 (inherits Web UI parity via pywebview wrapper; no separate native shell logic needed)
4. Add failed-run diagnostics bundle:
   - Status: 🟢 implemented
   - `run_summary.json` written to run dir on failure
   - `diagnostics.md` written to run dir on failure
   - redacted provider error, policy/tool timeline, verification tail, troubleshooting links included in markdown output
5. Improve error classification:
   - 🟢 provider auth/config
   - 🟢 provider rate limit/quota
   - 🟢 network timeout
   - 🟢 invalid model
   - 🟢 policy denial
   - 🟢 privacy restriction
   - 🟢 budget exceeded
   - 🟢 path confinement
   - 🟢 patch failure
   - 🟢 malformed model output

### Files

- `core/ledger.py`
- `core/replay_engine.py`
- `core/resume.py`
- `core/error_classification.py`
- `core/artifact_store.py`
- `interfaces/cli/cli.py`
- `interfaces/api_server/app.py`
- `interfaces/web_ui/app.py`
- `interfaces/desktop_ui/app.py`
- `docs/TROUBLESHOOTING.md`
- `docs/API_REFERENCE.md`
- `tests/test_resume.py`
- `tests/test_replay_engine.py`
- `tests/test_api_server.py`
- `tests/test_web_ui.py`

### Done When

- CLI/API/Web UI report the same canonical summary for the same run.
- Failed runs include actionable error category and next-step guidance.
- Resume/report work for all stable workflows and presets.
- Historical ledgers either load or fail with a clear compatibility message.

### Verification Gate

```powershell
pytest -q tests/test_resume.py tests/test_replay_engine.py tests/test_api_server.py tests/test_web_ui.py
python -m interfaces.cli.cli list-runs --repo .
```

---

## 🟡 Phase 4 - Stable Workflow And Preset Set

**Status:** Partial as of 2026-05-15. Preset and workflow support-state metadata is now embedded in the `Preset` dataclass, `Workflow` base class, and capability registry. All 8 presets and 8 workflows carry `stable_candidate` or `beta` labels matching `SUPPORT_MATRIX.md`. `context-maintainer` is now included in preset smoke expectations. Readiness checklists for all 8 workflows added to `SUPPORT_MATRIX.md`. Fresh live evidence collected via `scripts/live_validate.py`: `command-assistant` and `context-maintainer` passed against `azure-real`; `local-document-chat` and `codebase-assistant` returned `status='failed'` against test repo and remain blocked for stable promotion.

**Goal:** Promote a small, proven set of workflows/presets to stable and label the rest honestly.

**Why:** Baseline quality requires fewer promises with stronger evidence.

### Stable Candidate Set

Promote these first if gates pass:

1. `command-assistant`
2. `local-document-chat`
3. `codebase-assistant`
4. `context-maintainer`

### Beta Candidate Set

Promote these after focused gaps close:

1. `file-organizer`
2. `docs-maintainer`
3. `research-report`
4. `github-maintainer`

### Work

1. 🟢 Add support state to preset/workflow metadata.
2. Add readiness checklist per workflow:
   - structured input/output
   - artifacts
   - final report
   - failure modes
   - negative tests
   - CLI path
   - API path
   - docs
   - live evidence
3. Bring non-coding workflows to a minimum bar:
   - structured input/output schemas
   - documented artifacts
   - documented failures
   - golden-path test
   - negative-path test
   - live happy path where stable/beta
4. Close known gaps:
   - 🟢 coding dirty-repo block live evidence (allow-dirty bypass tested 2026-05-15)
   - 🟢 coding patch rollback and verifier fix loop (rollback assertion + repeated-failure guard + fix-loop rollback tested 2026-05-15)
   - 🟢 coding max-total-tasks and max-diff guards (max-diff-lines enforcement + existing max-tasks tests 2026-05-15)
   - 🟢 `run --no-tests` evidence (no_tests=True skips commands and records skipped status 2026-05-15)
   - 🟢 documents binary/excluded-dir and empty-repo behavior (smoke tests added 2026-05-15)
   - 🟢 file organization missing/unsafe move reporting (explicit overwrite guard + negative tests added 2026-05-15)
   - 🟢 command assistant unsafe command returns `safe=false` (negative tests added 2026-05-15)
   - 🟢 docs maintenance align/apply path (detect/update failure halt + empty stale-docs graceful propagation covered by smoke tests 2026-05-15)
   - 🟢 research API execution path (gather failure halt + empty sources graceful propagation covered by smoke tests 2026-05-15)
   - 🟢 GitHub API execution path (summarize-failure halt + empty-issues graceful propagation covered by smoke tests 2026-05-15)
5. 🟢 Add context-maintainer to preset smoke expectations (already in `tests/smoke/test_presets.py`; golden-path e2e tests added for context-maintainer and docs-maintenance 2026-05-15)

### Files

- `presets/base.py`
- `presets/*.py`
- `workflows/*/runtime.py`
- `workflows/*/reports/*.py`
- `workflows/*/agents/*.py`
- `workflows/registry.py`
- `tests/smoke/test_presets.py`
- `tests/smoke/test_workflows.py`
- `tests/smoke/test_workflow_execution.py`
- `tests/workflow_agents/`
- `tests/test_live_regressions.py`
- `docs/USER_GUIDE.md`
- `docs/TROUBLESHOOTING.md`

### Done When

- Every preset and workflow has a support state.
- Stable presets pass CLI, API, report, resume, and live provider paths.
- Beta presets have documented limitations and at least one live path.
- Experimental presets are hidden from beginner docs unless explicitly requested.

### Verification Gate

```powershell
pytest -q tests/smoke/test_presets.py tests/smoke/test_workflows.py tests/smoke/test_workflow_execution.py
pytest -q tests/workflow_agents tests/test_live_regressions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -NoPrompt
```

---

## 🟡 Phase 5 - Interface Contract Freeze

**Goal:** Make CLI, API, Web UI, Desktop, and Guided TUI consistent for Tier-1 journeys.

**Why:** The same product action should behave the same way regardless of interface.

### Work

1. Freeze stable CLI commands 🟢:
   - `doctor`
   - `provider templates/add/list/assign/test/use`
   - `ping-models`
   - `inspect`
   - `plan`
   - `run`
   - `presets`
   - `start`
   - `list-runs`
   - `report`
   - `resume`
   - `guided`
   - `ctx init/scan/run/verify/status/clean`
2. Freeze stable API routes 🟢:
   - `GET /api/health`
   - `GET /api/tools`
   - `GET /api/workflows`
   - `GET /api/presets`
   - `GET /api/models`
   - `GET /api/providers`
   - `GET /api/providers/templates`
   - `POST /api/providers`
   - `POST /api/providers/assign`
   - `POST /api/presets/{preset_id}/run`
   - `GET /api/runs/{run_id}`
   - `GET /api/runs/{run_id}/stream`
   - `WS /api/runs/{run_id}/ws`
   - core `POST /api/ctx/*` routes
   - `POST /api/ctx/scan` 🟢 (parity with CLI `ctx scan` + Web UI)
3. Simplify CLI help 🟢:
   - top-level help shows Tier-1 path first via rich_help_panel groups
   - advanced/experimental commands grouped under Advanced panel
   - Getting Started, Repository Work, Presets, Context, Advanced panels
5. Add parity tests 🟢:
   - preset registry vs API preset list 🟢
   - workflow registry vs API workflow list 🟢
   - CLI command list vs docs 🟢
   - API OpenAPI paths vs docs 🟢
   - same run summary across CLI/API/Web 🟢
6. Promote Web UI/Desktop only after browser smoke:
   - root loads
   - provider health visible
   - preset run starts
   - polling shows completed/failed
   - artifacts/errors visible
   - Desktop launches Web UI and routes correctly

### Files

- `interfaces/cli/cli.py`
- `interfaces/cli/ctx_commands.py`
- `interfaces/cli/provider_commands.py`
- `interfaces/api_server/app.py`
- `interfaces/web_ui/app.py`
- `interfaces/desktop_ui/app.py`
- `interfaces/guided_tui/app.py`
- `tests/smoke/test_cli.py`
- `tests/test_api_server.py`
- `tests/api_server/test_ctx_routes.py`
- `tests/test_web_ui.py`
- `tests/test_desktop_ui.py`
- `tests/guided_tui/test_guided_tui.py`
- `docs/CLI-COMMANDS.md`
- `docs/API_REFERENCE.md`
- `docs/USER_GUIDE.md`

### Done When

- Tier-1 journeys behave consistently across CLI and API.
- Web UI/Desktop are thin clients over stable routes, with no UI-only product logic.
- API docs match OpenAPI route inventory.
- CLI docs match actual Typer commands.

### Verification Gate

```powershell
pytest -q tests/smoke/test_cli.py tests/test_api_server.py tests/api_server/test_ctx_routes.py
pytest -q tests/test_web_ui.py tests/test_desktop_ui.py tests/guided_tui/test_guided_tui.py
python -m interfaces.cli.cli --help
python -m interfaces.cli.cli presets
python -m interfaces.cli.cli copy --help
```

---

## 🟡 Phase 6 - Live Validation Program

**Status:** Partial as of 2026-05-15. Foundation slice complete: `scripts/live_validate.py` provides a repeatable, bounded live validation runner with built-in matrix, structured evidence output (JSONL + summary JSON/Markdown), provider/profile/model detection, failure category classification, configurable max attempts (default 2) with 120-second timeout per attempt, `expect_failure` support for safety-negative tests, and `--delay-between-tests` / `--delay-between-attempts` for rate-limit mitigation. Full matrix run completed against Lane 1 (azure-real): 18 checks, 14 pass, 4 fail. Safety-negative checks added. Lane 2 (Google) matrix attempted against `gemini-lane2` — aggressive 429 rate limits from `gemini-2.5-flash` free tier block reliable testing even with 45s inter-test delays. Remaining work: Lane 2 with minutes-level delays or paid tier, Lane 3 (self-hosted), vision checks, archive contradictory historical results.

**Goal:** Make live evidence repeatable, bounded, and safe.

**Why:** Unit tests prove mapping and failure handling. Live tests prove the integrated product works.

### Work

1. 🟢 Create a live validation runner or documented script that records:
   - command
   - provider/profile
   - model
   - repo path
   - run ID
   - result
   - artifact path
   - timestamp
   - failure category
2. Use the external test repo for adversarial end-to-end checks.
3. Keep live AI attempts bounded:
   - `devtest/ai_test.ps1` max two consecutive attempts
   - 120-second hard timeout per attempt
4. Define live gates:
   - provider lane gates
   - stable preset gates
   - tool gates
   - safety negative gates
   - interface gates
   - vision gates
5. Move contradictory or historical live results into an archive section or changelog note.

### Required Live Matrices

#### Provider

- OpenAI-compatible remote
- Azure Foundry/OpenAI
- Gemini API
- Vertex AI
- Ollama or LM Studio
- one self-hosted cloud VM OpenAI-compatible endpoint when available

#### Stable Presets

- `command-assistant`
- `local-document-chat`
- `codebase-assistant`
- `context-maintainer`

#### Tools

- filesystem read/write/copy/list
- git status/diff
- HTTP GET/POST
- browser fetch/screenshot
- local DB configured SQLite operation
- MCP mock server list/call
- memory read/write
- network diagnostics

#### Safety Negative Cases

- missing provider secret
- invalid model ID
- auth failure
- rate limit/quota
- network timeout
- provider empty content
- provider non-JSON for structured output
- policy denial
- privacy restriction
- patch outside allowed files
- dirty repo without allow flag

#### Interfaces

- CLI stable journey
- API stable journey
- Web UI preset run and polling
- Desktop launch and routing
- Guided TUI selected preset run

#### Vision

- OpenAI-compatible/Azure vision describe
- Google vision describe if configured
- OCR on text image
- non-vision model rejection
- API tool invocation for `multimodal.image`

### Done When

- `live-ai-testing.md` contains only current, non-contradictory live evidence.
- Each stable support claim has a live evidence row.
- Failed live checks include a linked issue or roadmap task.
- No live validation command can retry indefinitely.

### Verification Gate

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1
```

---

## 🟡 Phase 7 - Troubleshooting And Operator Experience

**Status:** Mostly complete as of 2026-05-15. CLI/operator guidance, troubleshooting coverage, doctor checks, and structured API/Web error responses now cover the main baseline failure lanes. Web UI returns structured diagnostics via `_structured_error_middleware` + `_ctx_exc()` on all ctx routes. Desktop inherits the same surface via pywebview wrapper.

**Goal:** Make common failures self-service.

**Why:** A reliable baseline is not only passing tests. It must fail clearly.

### Work

1. Expand troubleshooting catalog:
   - 🟢 provider auth/config
   - 🟢 provider endpoint/model mismatch
   - 🟢 Google ADC/project/location failure
   - 🟢 local provider not running
   - 🟢 policy denial
   - 🟢 approval required
   - 🟢 privacy restriction
   - 🟢 path confinement
   - 🟢 budget exceeded
   - 🟢 timeout/retry exhausted
   - 🟢 malformed model output
   - 🟢 stale context
   - 🟢 resume/report compatibility
2. 🟢 Link runtime errors to troubleshooting entries.
3. 🟢 Add exact recovery commands.
4. 🟢 Add `doctor` checks for:
   - 🟢 provider profile presence
   - 🟢 role coverage
   - 🟢 first-class lane readiness
   - 🟢 local endpoint reachability where relevant
   - 🟢 optional dependencies
   - 🟢 AICtx/ContextOps availability
5. 🟢 Make Web/Desktop show diagnostics, not raw stack traces. (Web UI done via `_structured_error_middleware` + `_ctx_exc()` on all ctx routes; Desktop inherits via pywebview wrapper.)

### Files

- `docs/TROUBLESHOOTING.md`
- `docs/USER_GUIDE.md`
- `interfaces/cli/cli.py`
- `interfaces/api_server/app.py`
- `interfaces/web_ui/app.py`
- `monitoring/health.py`
- `core/error_classification.py`
- `tests/test_monitoring.py`
- `tests/test_error_classification.py`
- `tests/smoke/test_cli.py`

### Done When

- Top recurring failures have an exact remediation path.
- CLI/API/UI expose actionable messages for the same failure categories.
- `doctor` is useful before and after provider setup.

### Verification Gate

```powershell
pytest -q tests/test_error_classification.py tests/test_monitoring.py tests/smoke/test_cli.py
python -m interfaces.cli.cli doctor --skip-connectivity
```

---

## 🟡 Phase 8 - Advanced Subsystem Decisions

**Status:** Partial as of 2026-05-15. Initial regression-guard slice complete: `tests/smoke/test_experimental_surfaces.py` verifies no experimental presets/workflows leak into registry, CLI commands don't expose experimental subsystem tokens, and API routes don't contain experimental subsystem paths. Remaining work: support labels in UI, removal from first-run path, promotion criteria per subsystem.

**Goal:** Stop ambiguous semi-support for expensive subsystems.

**Why:** Marketplace, federation, distributed execution, OCI/remote paths, and advanced multimodal support are valuable, but they must not dilute baseline stability.

### Decisions

1. **Marketplace:** Experimental until plugin install/load/signature UX has stable docs, threat model, and live smoke.
2. **Federation:** Experimental/internal until cross-machine auth, transport security, failure recovery, and operator docs exist.
3. **Distributed workflows:** Experimental/internal until scheduler/worker lifecycle and resume semantics are proven.
4. **OCI/remote context:** Advanced/beta only for users who opt in and install extras.
5. **Multimodal:** Beta only for first-class provider lanes with live vision evidence; experimental otherwise.
6. **Self-improving agents:** Internal until governance, rollback, and audit model are explicit.

### Work

1. Add support labels in docs and UI.
2. Remove experimental subsystems from first-run path.
3. Add promotion criteria per subsystem:
   - owner
   - entrypoints
   - security model
   - docs
   - tests
   - live evidence
   - known limits
4. Add regression tests ensuring experimental surfaces are not shown as stable.

### Files

- `marketplace/`
- `federation/`
- `workflows/distributed/`
- `agents/self_improving/`
- `multimodal/`
- `interfaces/cli/cli.py`
- `interfaces/web_ui/app.py`
- `docs/ARCHITECTURE.md`
- `docs/SAFETY.md`
- `docs/USER_GUIDE.md`
- `tests/test_marketplace.py`
- `tests/test_federation.py`
- `tests/test_distributed.py`
- `tests/test_multimodal.py`
- `tests/test_self_improving.py`

### Done When

- No advanced subsystem has ambiguous support status.
- Stable docs do not imply advanced systems are baseline-ready.
- Promotion path is explicit for each advanced subsystem.

### Verification Gate

```powershell
pytest -q tests/test_marketplace.py tests/test_federation.py tests/test_distributed.py tests/test_multimodal.py tests/test_self_improving.py
python scripts/check-agent-instructions.py
```

---

## 🔴 Phase 9 - Baseline Release Gate

**Goal:** Declare the baseline reliable enough to build on.

### Required Criteria

1. Support-state matrix complete and current.
2. Tier-1 contract matrix complete and current.
3. Tool invocation path unified and policy-gated.
4. Run summary canonical across CLI/API/Web.
5. Top 3 provider lanes documented and proven.
6. Stable presets pass unit, smoke, and live gates.
7. CLI/API parity tests pass.
8. Web/Desktop have at least beta-grade browser/launch evidence or remain experimental.
9. Troubleshooting catalog covers all stable failure categories.
10. Docs and instruction checks pass.
11. Broad or full devtest pass in a clean checkout.
12. Live AI gate pass recorded with bounded attempts.

### Final Verification

```powershell
python scripts/check-agent-instructions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode broad -NoPrompt
pytest -q --override-ini="addopts="
powershell -ExecutionPolicy Bypass -File .\devtest\ai_test.ps1
```

If `ai_test.ps1` fails twice consecutively with 120-second timeouts, stop and record the failure category instead of retrying.

## Recommended Execution Order

1. Phase 0 - clean evidence and support-state docs
2. Phase 1 - unify tool safety path
3. Phase 2 - harden provider lanes
4. Phase 3 - canonical run diagnostics
5. Phase 4 - stable workflow/preset set
6. Phase 5 - interface contract freeze
7. Phase 6 - live validation program
8. Phase 7 - troubleshooting/operator experience
9. Phase 8 - advanced subsystem decisions
10. Phase 9 - baseline release gate

## Immediate Next Sprint

The next sprint should be small and high-leverage:

1. Fix instruction/doc drift and add support-state matrix.
2. Replace `live-ai-testing.md` with current non-contradictory evidence.
3. Add `context-maintainer` to preset smoke expectations.
4. Create the Tier-1 contract matrix.
5. Start the unified tool invocation service design and tests.

Do not start new presets, providers, dashboards, marketplace features, federation features, or analytics until Phase 0 and Phase 1 gates pass.
