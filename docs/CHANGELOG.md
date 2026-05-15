# Changelog

## 2026-05-15

### Provider Stability Sweep — Azure Foundry and Gemini API
- Promoted Azure Foundry/OpenAI-compatible provider compatibility evidence: `azure-real` / `gpt-5.4` passed doctor, ping-models, planner/executor/verifier provider tests, `command-assistant`, and direct PNG vision smoke.
- Promoted Gemini API compatibility evidence: `gemini-key-test` / `gemini-2.5-flash` passed provider smoke, text/JSON, direct PNG vision smoke, `command-assistant`, `local-document-chat`, `context-maintainer`, `file-organizer-dry-run`, `docs-maintainer-plan`, `github-maintainer`, and `research-report` without 429s.
- Fixed documents workflow provider map to use the shared provider registry so Gemini/Vertex-compatible providers can run `local-document-chat`.
- Disabled Typer local-variable tracebacks in the CLI to avoid raw provider secret exposure in failure artifacts.
- Added coding runtime metadata/output-budget hardening: `run.json` now records `workflow_id="coding"` and `preset_id="codebase-assistant"`, and coding `run_task` planning uses the same 6000-token structured-output cap as `plan_task`.
- Clarified verifier prompt handling for cumulative diffs in repair loops. `codebase-assistant` remains blocked by live repair-loop/model-output behavior, so it was not promoted.
- Updated `live-ai-testing.md`, `docs/SUPPORT_MATRIX.md`, `docs/TIER1_CONTRACTS.md`, and `BASELINE-ROADMAP.md` from exact evidence.
- Updated README/DEV_TESTING/support/live evidence test counts to 1256 collected, 1220 selected, 36 deselected from the baseline gate.

### Azure `gpt-5.4` Live Rerun — Documents/Research Pass, Codebase Blocked
- Updated the local `azure-real` provider profile from `gpt-5.4-mini` to deployed `gpt-5.4` for all roles.
- Ran `scripts/live_validate.py --profile azure-real --only local-document-chat,codebase-assistant,research-report --max-attempts 2` against a clean clone of the test repo.
- `local-document-chat` passed on `azure-real` / `gpt-5.4`; `research-report` passed after aligning live-runner expectations with `ResearchReport(...)` output; `codebase-assistant` still returned `status='blocked'` after verifier pytest failed on the generated boolean-exclusion test.
- Hardened research report parsing for object-shaped `executive_summary` and `recommendations`, and raised structured-output caps for research summarization and coding planning to avoid truncated JSON on capable-model runs.
- Updated `live-ai-testing.md`, `docs/SUPPORT_MATRIX.md`, `docs/TIER1_CONTRACTS.md`, and `BASELINE-ROADMAP.md` with exact capable-model evidence and remaining work.

### Docs Cleanup — Baseline Roadmap Remaining Work
- Reworked `BASELINE-ROADMAP.md` current-state summary into a compact done/remaining baseline board.
- Expanded remaining paths for Azure `gpt-5.4` live reruns, Google/Vertex validation, real self-hosted endpoint proof, Web/Desktop live e2e, and remaining safety/failure evidence.
- Updated `live-ai-testing.md`, `docs/SUPPORT_MATRIX.md`, and `docs/TIER1_CONTRACTS.md` to stop treating stale historical/mini-model results as current promotion proof.
- Updated README/DEV_TESTING/support/live evidence test counts to 1252 collected, 1216 selected, 36 deselected from the baseline gate.
- Validation: `python scripts/check-agent-instructions.py`, directive devtest, and baseline devtest pass.

### Phase 6 Safety-Negative Expansion — Patch Outside Allowed Scope Test
- Added `TestPatchApplierAllowedFiles` to `tests/core/test_patching.py`.
- `test_allowed_files_blocks_outside_scope`: verifies `PatchApplier.apply_changes`
  rejects files not in `allowed_files` with `"outside work order scope"` error,
  while still applying allowed changes.
- `test_allowed_files_allows_all_when_none`: verifies `allowed_files=None` does
  not block any file.
- Closes Phase 6 gap: "patch-outside-allowed" negative path now covered by unit
  test (dirty-repo already covered in `tests/test_negative_paths.py`).
- Validation: `pytest -q tests/core/test_patching.py` 6 pass.

### Phase 8 Slice — Promotion Criteria Docs + Roadmap Sprint Update
- Added `Support States and Promotion Criteria` section to `docs/ARCHITECTURE.md`.
- Documents four states (stable, beta, experimental, internal), promotion gates,
  and per-subsystem criteria: owner, entrypoints, security model, docs, tests,
  live evidence, known limits.
- Added first-run path protection rule: experimental surfaces hidden from default
  CLI/Web/API views.
- Updated `BASELINE-ROADMAP.md` `Immediate Next Sprint` to reflect actual
  2026-05-15 state instead of stale pre-baseline tasks.
- Validation: `python scripts/check-agent-instructions.py` pass.

### Phase 2/6 Slice — Self-Hosted Lane Mock-Server Provider Smoke (17/17 pass)
- Ran `.localtest/mock-ai-server/server.py` in `MOCK_ALLOW_FAKE=1` mode against
  all 17 generated local provider profiles.
- `smoke_agentheim_http_providers.py` result: 17/17 pass (anthropic, azure,
  cohere, compatible, deepseek, gemini, groq, kimi, lmstudio, mistral, ollama,
  ollama_cloud, openai, openrouter, perplexity, together, xai).
- This expands Lane 3 (self-hosted) evidence from partial shim to full provider
  registry coverage through localhost-shaped configurations.
- Updated `live-ai-testing.md`, `BASELINE-ROADMAP.md` Phase 2/Lane 3,
  `docs/SUPPORT_MATRIX.md`.
- Validation: server health ok, all provider tests return non-empty responses.

### Phase 2/6 Slice — Automate Mock-Server Lane 3 Smoke as Pytest Test
- Added `tests/smoke/test_mock_server_providers.py` with
  `TestMockServerProviderSmoke::test_all_local_provider_profiles_respond`.
- Starts mock AI server in daemon thread, waits for health, then invokes all
  17 local provider profiles through Agentheim provider registry.
- Marked `@pytest.mark.slow` so it runs with `-m slow` but not in default lane.
- Makes Lane 3 compatibility shim evidence reproducible in CI without manual
  server startup.
- Updated `live-ai-testing.md` to reference the pytest command.
- Validation: `pytest tests/smoke/test_mock_server_providers.py -m slow` passes
  in ~7s.

### Phase 5 Slice — Desktop UI Server Integration Test
- Added `TestDesktopUIServerIntegration` to `tests/test_desktop_ui.py`:
  - `test_server_starts_and_health_responds`: starts `_run_server` in a daemon
    thread, waits for health endpoint, verifies `/api/health` and `/api/presets`
    respond correctly.
- Desktop UI server start path now has real integration evidence.
- Updated `live-ai-testing.md`, `BASELINE-ROADMAP.md` Phase 5 status.
- Validation: `tests/test_desktop_ui.py` 10/10 pass; baseline gate pass.

### Phase 5 Slice — Web UI Browser Smoke: Root Load + Provider Health + Run Buttons
- Enhanced `interfaces/web_ui/app.py` dashboard:
  - Added "Active Runs" card with run status polling.
  - Added "Run" buttons to each preset via event delegation (`data-preset-id`).
  - Added `runPreset()`, `renderRuns()`, `pollRun()` JS functions for starting
    runs and polling `/api/runs/{run_id}` every second.
  - Active Runs card shows artifacts and errors when run completes/fails.
- Verified with Playwright: root loads, "API connected" visible, all 4 provider
  profiles listed, all 8 presets with Run buttons, 0 JS console errors.
- Updated `live-ai-testing.md`, `BASELINE-ROADMAP.md` Phase 5 status.
- Validation: `tests/test_web_ui.py` 22/22 pass; baseline gate pass.

### Phase 6 Slice — Archive Contradictory Historical Results
- Added `Current status` column to Historical Live Evidence table in
  `live-ai-testing.md` marking entries as ✅ Still valid, ⚠️ Superseded, or
  ❌ Contradicted by fresh evidence.
- Added archive-note banner at top of historical section warning readers not
  to treat dated results as current truth.
- Updated `BASELINE-ROADMAP.md` Phase 6 status to reflect archive completion.
- Key contradictions flagged: `local-document-chat` (fails on mini/Gemini),
  `codebase-assistant` (fails on mini), `research-report` (fails on mini).
- Validation: baseline gate pass.

### Phase 6 Slice — Runner Delay Feature + Gemini Rate-Limit Retest
- Added `--delay-between-tests` and `--delay-between-attempts` CLI args to
  `scripts/live_validate.py` for rate-limit mitigation.
- Re-ran Gemini lane with 45s inter-test delays: still fails with 429 on most
  provider tests. Free-tier rate limit requires minutes-level cooldown.
- Updated `live-ai-testing.md` and `BASELINE-ROADMAP.md` with delay-test results.
- Validation: delay feature works; evidence JSONL verified; baseline gate pass.

### Phase 2 Slice — Google Lane Live Matrix Attempt + Rate Limit Discovery
- Created `gemini-lane2` profile with 14 roles (same provider/secret as `gemini-live`).
- Ran full 18-check matrix against `gemini-lane2` / `gemini-2.5-flash`.
- Results: 8 pass, 8 fail, 2 skipped. Most failures = 429 Too Many Requests.
- Key passes: doctor, provider-executor, provider-verifier, context-maintainer,
  file-organizer-dry-run, 3 safety-negative checks.
- Key finding: Gemini free-tier rate limiting is aggressive — blocks reliable
  sequential matrix testing without delays/backoff.
- Updated runner `classify_failure` to detect 429 / "Too Many Requests" as
  `provider_rate_limit`.
- Updated `live-ai-testing.md`, `docs/SUPPORT_MATRIX.md`, `BASELINE-ROADMAP.md`
  with honest rate-limit evidence.
- Validation: runner correctly classifies 429; evidence JSONL verified.

### Phase 6 Slice — Safety-Negative Checks in Live Validation Matrix
- Added `expect_failure` support to `scripts/live_validate.py` (`build_result` logic).
- Added 3 safety-negative checks to runner matrix:
  - `invalid-role`: `provider test --role nonexistent-role` → rejected cleanly
  - `invalid-profile`: `provider test --profile nonexistent-profile` → rejected cleanly
  - `copy-denied`: `copy` outside workspace without approval → `Aborted`
- All 3 safety-negative tests pass against `azure-real`.
- Updated `live-ai-testing.md`, `BASELINE-ROADMAP.md` with safety-negative evidence.
- Validation: safety-negative subset pass; existing doctor/command-assistant/report subset still pass.

### Phase 2/6 Slice — Full Live Validation Matrix + Report/Resume Closure
- Ran `scripts/live_validate.py --profile azure-real` full matrix (15 checks).
- Results: 11 pass, 4 fail. New passes: `file-organizer-dry-run`, `docs-maintainer-plan`, `github-maintainer`, `resume-command-assistant`.
- Fixed `report-command-assistant` `must_contain` pattern in runner matrix (`Status: done` → `"status": "completed"` to match JSON output).
- Re-ran `report-command-assistant` → pass.
- Updated `live-ai-testing.md` with full 15-check evidence table.
- Updated `docs/SUPPORT_MATRIX.md` beta preset rows with fresh evidence.
- Updated `BASELINE-ROADMAP.md` Phase 2 and Phase 6 status.
- Validation: runner exit code 1 (4 known failures); evidence JSONL verified; report fix re-run pass.

### Phase 4 Slice — Stable Preset Live Promotion Evidence
- Ran `scripts/live_validate.py --profile azure-real --only local-document-chat,codebase-assistant,context-maintainer`.
- `context-maintainer` passed (2.2s). `local-document-chat` and `codebase-assistant` returned `status='failed'` against test repo.
- Updated `live-ai-testing.md` with stable preset evidence table.
- Updated `docs/SUPPORT_MATRIX.md` stable candidate rows with honest fresh evidence.
- Updated `BASELINE-ROADMAP.md` Phase 4 status.
- Validation: runner exit code 1 (2 failed, 1 passed); evidence JSONL verified.

### Phase 2 Slice — Azure Foundry Live Lane Evidence
- Ran `scripts/live_validate.py --profile azure-real --only doctor,ping-models,provider-planner,provider-executor,provider-verifier,command-assistant`.
- All 6 checks passed against `azure-real` profile (`azure_foundry` provider, `gpt-5.4-mini` model).
- Updated `live-ai-testing.md` with structured fresh evidence table.
- Updated `docs/SUPPORT_MATRIX.md` OpenAI-compatible lane and `azure_foundry` adapter rows.
- Updated `BASELINE-ROADMAP.md` Phase 2 status to reflect Lane 1 fresh evidence.
- Runner fix: `--profile` now temporarily switches the active project provider profile via `.ai-team/provider-profile.json` and restores it after the run, so evidence accurately reflects the tested profile.
- Validation: runner exit code 0, 6/6 passed.

### Phase 6 Slice — Live Validation Program Foundation
- Created `scripts/live_validate.py`: repeatable bounded live validation runner with built-in matrix.
- Records per-test: command, provider/profile, model, repo path, run ID, result, artifact path, timestamp, failure category.
- Supports configurable `--max-attempts` (default 2) and 120-second per-test timeout.
- Failure categories: timeout, provider_auth, provider_rate_limit, provider_error, policy_denial, approval_required, model_misformat, missing_output, exit_failure, skipped, unexpected_error.
- Creates `evidence.jsonl`, `summary.json`, `summary.md`, and per-test stdout/stderr logs.
- Added `devtest/live_validate.ps1` Windows wrapper.
- Updated `live-ai-testing.md` and `docs/DEV_TESTING.md` with runner usage and output format.
- Updated `BASELINE-ROADMAP.md` Phase 6 status from 🔴 to 🟡.
- Validation: runner lists 15 checks, doctor smoke passes, retry logic verified, evidence JSONL schema confirmed.

### Janitor — Roadmap Status Drift Fix
- Fixed BASELINE-ROADMAP.md Phase 7 status paragraph: removed stale "Remaining gap: Web/Desktop still do not present..." now that structured error middleware + ctx route wrappers are implemented and tested.
- Updated Phase 8 header from 🔴 to 🟡 with status note reflecting completed regression-guard slice.
- Validation: directive + baseline gates pass.

### Phase 8 Slice — Experimental Surface Regression Tests
- Added `tests/smoke/test_experimental_surfaces.py` with 6 tests verifying:
  - All presets have support_state and no experimental presets are in registry
  - All workflows have support_state and no experimental workflows are in registry
  - CLI commands don't contain marketplace/federation/distributed/multimodal/self-improving tokens
  - API routes don't contain experimental subsystem paths
- Validation: 6 passed.

### Phase 7 Slice — Web UI Structured Error Responses
- Replaced raw exception leakage in `interfaces/web_ui/app.py` with structured diagnostics.
- Added `_structured_error_middleware` (HTTP middleware) that catches unhandled exceptions and returns `error_summary` JSON.
- Wrapped all `/api/ctx/*` routes with try/except + `_ctx_exc()` returning `JSONResponse` with structured error payload.
- Added `TestStructuredErrors` in `tests/test_web_ui.py` verifying both ctx-route and global-middleware structured error shapes.
- Validation: `tests/test_web_ui.py` 22 passed.

### Phase 7 Slice — Fix API Server Core Boundary Violation
- Replaced direct `core.error_classification` import with `core.public_api` in `interfaces/api_server/app.py` `_ctx_exc()`.
- Fixes `TestInterfaceIsolation::test_no_direct_core_imports[interfaces/api_server/app.py]` which was failing with `AssertionError: interfaces/api_server/app.py imports directly from core internals: [(432, 'core.error_classification')]`.
- Validation: `tests/test_interface_isolation.py` 6 passed.

### Phase 4 Slice — Beta Candidate Workflow Readiness Checklists
- Added "Workflow Readiness Checklists (Beta Candidates)" table to `docs/SUPPORT_MATRIX.md`.
- Covers 9 checklist items per workflow for file-organizer, docs-maintainer, research-report, github-maintainer.
- All beta workflows show solid structured I/O, negative-path tests, CLI/API paths, and docs coverage.
- Live evidence remains 🟡 for all four; promotion to stable requires fresh live proof.
- Validation: `python scripts/check-agent-instructions.py` passed; directive devtest passed.

### Phase 4 Slice — Stable Candidate Workflow Readiness Checklists
- Added "Workflow Readiness Checklists (Stable Candidates)" table to `docs/SUPPORT_MATRIX.md`.
- Covers 9 checklist items per workflow: structured I/O schemas, artifacts, final report, failure modes, negative tests, CLI path, API path, docs, live evidence.
- Documents honest gaps: `context-maintainer` lacks Agentheim-native schemas, artifacts, final report, and negative-path tests because it delegates to AICtx runtime.
- All four stable candidates marked as needing fresh live evidence before `stable` promotion.
- Validation: `python scripts/check-agent-instructions.py` passed; directive devtest passed.

### Phase 4 Slice — Context-maintainer & Docs-maintenance Golden-Path Tests
- Added `TestDocsMaintenanceWorkflowExecution`: end-to-end test proving public_docs_impact → detect → update → align DAG completes with `_fake_invoke`.
- Added `TestContextMaintainerWorkflowExecution`: end-to-end test proving 7-step DAG (scan → plan → generate → write → verify → public_docs_impact → produce_report) completes; `run_context_maintainer` mocked to avoid AICtx dependency.
- Closed roadmap drift: item #5 "Add context-maintainer to preset smoke expectations" was already implemented in `test_presets.py`; marked done and extended with workflow execution coverage.
- Validation: `tests/smoke/test_workflow_execution.py` 25 passed.

### Phase 4 Slice — Coding Workflow Gap Closure
- Added `TestCodingRuntimeRollback`: asserts `rollback()` called on first-task patch apply failure and on fix-loop patch apply failure.
- Added `TestCodingRuntimeRepeatedFailure`: same verifier failure twice triggers `reason="same_failure_repeated_twice"` BLOCKED transition.
- Added `TestBasicVerify`: `no_tests=True` skips expected commands and records `status="skipped"` with `--no-tests passed` detail.
- Added `test_run_task_allow_dirty_bypasses_block` to `TestCodingRuntimeNegative`: proves `--allow-dirty` bypasses dirty-repo block (hits planning failure instead).
- Added `tests/core/test_patching.py` with `TestPatchApplierMaxDiff` and `TestPatchApplierRollback`: max-diff-lines rejection, rollback restores original content, rollback deletes created files.
- Validation: `tests/test_coding_runtime.py` + `tests/test_negative_paths.py` + `tests/core/test_patching.py` 25 passed.

### Phase 4 Slice — GitHub Maintainer Workflow Negative-Path Coverage
- Added `TestGitHubMaintenanceWorkflowExecution` end-to-end test proving summarize → draft DAG completes.
- Added `TestGitHubMaintenanceNegativePaths` with 2 tests:
  1. `test_summarize_failure_halts_before_draft` — invalid summarizer output halts DAG before draft.
  2. `test_empty_issues_text_graceful` — empty `issues_text` propagates through summarize → draft without crashing.
- Added `DraftResult` response to `_fake_invoke` fixture.
- Updated `docs/SUPPORT_MATRIX.md` `github-maintainer` known limits to reflect stronger coverage.
- Validation: `tests/smoke/test_workflow_execution.py` 21 passed.

### Phase 4 Slice — Docs Maintenance Workflow Apply/Aligner Path Coverage
- Added `TestDocsMaintenanceWorkflowNegativePaths` with 3 tests:
  1. `test_detect_failure_halts_before_update` — invalid detector output halts DAG before update/align.
  2. `test_update_failure_halts_before_align` — invalid updater output halts DAG before align.
  3. `test_empty_stale_docs_graceful` — empty `stale_docs` propagates through update → align without crashing; all 4 steps succeed.
- Updated `docs/SUPPORT_MATRIX.md` `docs-maintainer` known limits to reflect stronger coverage.
- Validation: `tests/smoke/test_workflow_execution.py` 18 passed.

### Phase 4 Slice — Research Workflow Negative-Path Coverage
- Added `TestResearchWorkflowNegativePaths` with 2 tests:
  1. `test_research_workflow_gather_failure_halts` — invalid gather output halts DAG before summarize/report; runner returns single failed step.
  2. `test_research_workflow_empty_sources_graceful` — empty sources list propagates through summarize → report without crashing; all 3 steps succeed.
- Updated `docs/SUPPORT_MATRIX.md` `research-report` known limits to reflect stronger coverage.
- Validation: `tests/smoke/test_workflow_execution.py` 15 passed.

### Phase 4 Slice — File Organization Negative-Path Coverage
- Added explicit overwrite guard in `workflows/file_organization/workflows/file_organization.py` `_execute_apply`: destination existence checked before `src.rename(dst)` with clear error `"Destination already exists"`.
- Added `TestFileOrganizationNegativePaths` with 3 tests:
  1. `test_missing_source_file_reported` — missing source yields `success=False` with `"does not exist"` error.
  2. `test_destination_exists_reported` — existing destination blocked, source preserved.
  3. `test_dry_run_does_not_move_files` — `dry_run=True` records moves without touching filesystem.
- Updated `docs/SUPPORT_MATRIX.md` `file-organizer` known limits to reflect stronger coverage.
- Validation: `tests/smoke/test_workflow_execution.py` 13 passed.

### Phase 4 Slice — Documents Workflow Edge-Case Readiness
- Added `TestDocumentsWorkflowExecution` with end-to-end and empty-repo fallback tests.
- Added `TestDocumentsCollectTextFiles` proving binary suffixes (`.png`, `.exe`) and excluded directories (`.git`, `node_modules`) are skipped by `_collect_text_files`.
- Empty repo gracefully falls back through index → retrieve → answer without crashing.
- Updated `docs/SUPPORT_MATRIX.md` `local-document-chat` known limits to reflect new coverage.
- Validation: `tests/smoke/test_workflow_execution.py` 10 passed.

### Phase 3 Slice — Desktop UI Shell Parity Acknowledgment
- Confirmed Desktop UI (`interfaces/desktop_ui/app.py`) is a pywebview wrapper around Web UI; canonical run summary parity is inherited from Web UI `/api/runs/{run_id}` route.
- Updated `BASELINE-ROADMAP.md` Phase 3 to mark Desktop UI shell as implemented by architecture inheritance.
- No code change required; existing `tests/test_desktop_ui.py` import and launch coverage is sufficient.

### Phase 4 Slice — Command Assistant Readiness Negative Tests
- Added `test_command_assistant_run_task_unsafe_command` proving unsafe commands (`safe=false`) propagate through `run_task` into `FinalReport`.
- Added `test_command_assistant_run_task_parse_failure` proving parse failures produce `status="failed"` with empty commands list.
- Validation: `tests/smoke/test_workflow_execution.py` 5 passed.

### Phase 7 Slice — Structured API Error Responses for Ctx Routes
- Updated `_ctx_exc()` in `interfaces/api_server/app.py` to use `core.error_classification.error_summary()` for structured error responses.
- API ctx route errors now include `type`, `message`, `category`, `retryable`, `halt`, `next_action`, `troubleshooting_doc`, `troubleshooting_section`.
- Added `tests/api_server/test_ctx_routes.py::test_ctx_scan_structured_error` verifying 400 response with structured detail.
- Validation: `tests/api_server/test_ctx_routes.py` 9 passed, `tests/test_api_server.py` 34 passed, baseline gate passes.

### Phase 5 Slice — Interface Parity Tests
- Added `tests/smoke/test_parity.py` with 4 parity tests:
  1. `test_preset_registry_matches_api_preset_list` — compares `PresetRegistry` with `GET /api/presets`
  2. `test_workflow_registry_matches_api_workflow_list` — compares `WorkflowRegistry` with `GET /api/workflows`
  3. `test_cli_commands_match_docs_reference` — introspects Typer app and compares against `docs/CLI-COMMANDS.md`
  4. `test_api_openapi_paths_match_docs_reference` — compares OpenAPI schema paths against `docs/API_REFERENCE.md`
- Added missing `copy` and `desktop` rows to `docs/CLI-COMMANDS.md` root commands table.
- Validation: `tests/smoke/test_parity.py` 4 passed, full smoke suite 65 passed.

### Phase 5 Slice — CLI Help Grouping
- Grouped CLI commands into `rich_help_panel` panels: `Getting Started`, `Repository Work`, `Presets`, `Context`, `Advanced`.
- Added missing docstrings to `list-runs`, `report`, `resume` commands so help table shows descriptions.
- Updated `docs/SUPPORT_MATRIX.md` CLI known limits to reflect grouped help.
- Validation: `tests/smoke/test_cli.py` 14 passed, baseline gate passed.

### Phase 5 Slice — API `/api/ctx/scan` Route Parity
- Added `POST /api/ctx/scan` to the API server (`interfaces/api_server/app.py`) for parity with CLI `ctx scan` and Web UI `/api/ctx/scan`.
- Response includes `repo_root`, `head_commit`, `branch`, `dirty_state`, `file_count`, `manifest_count`.
- Added `CtxScanRequest`/`CtxScanResponse` Pydantic models.
- Added `tests/api_server/test_ctx_routes.py::test_ctx_scan_route` — passes.
- Updated `docs/API_REFERENCE.md` with scan route documentation.

### Phase 4 Slice — Preset + Workflow Support-State Metadata
- Added `support_state` field to `Preset` dataclass in `presets/base.py` with default `"experimental"`.
- Updated `PresetRegistry.register()` to emit `support_state` into capability registry metadata.
- Set support states on all 8 presets to match `docs/SUPPORT_MATRIX.md`:
  - `stable_candidate`: command-assistant, local-document-chat, codebase-assistant, context-maintainer
  - `beta`: file-organizer, docs-maintainer, research-report, github-maintainer
- Added `support_state` class attribute to `Workflow` base in `workflows/base.py` with default `"experimental"`.
- Set support states on all 8 workflow classes matching their preset tiers:
  - `stable_candidate`: coding, documents, command_assistant, context_maintainer
  - `beta`: file_organization, docs_maintenance, github_maintenance, research
- Updated `workflows/registry.py` to pass `support_state` in workflow registration metadata.
- Added `context-maintainer` to preset smoke test expectations (was missing).
- Added `tests/smoke/test_presets.py` coverage for preset `support_state` presence, valid values, stable-candidate grouping, and beta grouping.
- Added `tests/smoke/test_workflows.py` coverage for workflow `support_state` in registry, stable-candidate workflows, and beta workflows.
- Validation: `tests/smoke/test_presets.py` 14 passed, `tests/smoke/test_workflows.py` 30 passed, baseline gate passed.

### Phase 3 Slice — Failed-Run Diagnostics Bundle
- Added `write_diagnostics_bundle()` to `core/run_summary.py` that writes `run_summary.json` and `diagnostics.md` into the run artifact directory.
- Markdown output includes error category, retryable/halt flags, next action, troubleshooting links, state transitions, tool counts, policy decisions, approvals, verification checks, and artifact list.
- Wired into `core/workflow_runner.py` failure paths: step failure halt and exception catch both call `write_diagnostics_bundle()` after emitting `RUN_FAILED`.
- Added tests in `tests/test_workflow_runner.py` proving bundle creation on both step failure and exception paths.
- Updated `BASELINE-ROADMAP.md` Phase 3 diagnostics bundle status to implemented.
- Updated `docs/TIER1_CONTRACTS.md` stable artifact minimum to include `run_summary.json` and `diagnostics.md` for failed runs.
- Validation: `tests/test_workflow_runner.py` 17 passed, baseline gate passed.

### Docs Janitor — SUPPORT_MATRIX Drift Fix
- Fixed stale `docs/SUPPORT_MATRIX.md` interface rows that claimed API server had "no approval continuation yet" and omitted approval continuation from Web UI description.
- Both API server and Web UI now correctly documented as having explicit `/api/tools/approvals/{request_id}/grant` and `/deny` continuation routes with TestClient coverage.
- Validation: `check-agent-instructions.py` passed, directive devtest passed, baseline devtest passed.

## 2026-05-14

### Phase 3 Slice — Canonical Run Summary Across CLI/API/Web
- Added shared canonical run summary builder in [`core/run_summary.py`](../core/run_summary.py) that normalizes run status, summary text, duration, model selection, state transitions, tool/policy/approval counts, verification, artifacts, and actionable error guidance from ledger/events plus persisted artifacts.
- Extended [`core/error_classification.py`](../core/error_classification.py) with `error_summary_from_text()` so persisted run failures can reuse the same troubleshooting guidance when only serialized error payloads remain.
- Updated CLI/API/Web consumers to use the same payload:
  - [`interfaces/cli/cli.py`](../interfaces/cli/cli.py) `report` now emits canonical run summary JSON
  - [`interfaces/api_server/app.py`](../interfaces/api_server/app.py) `GET /api/runs/{run_id}` now returns the canonical summary
  - API/Web SSE and WebSocket status streams now emit the same payload shape on initial/final status updates
- Added/updated focused coverage in [`tests/test_resume.py`](../tests/test_resume.py), [`tests/test_api_server.py`](../tests/test_api_server.py), [`tests/test_web_ui.py`](../tests/test_web_ui.py), [`tests/smoke/test_cli.py`](../tests/smoke/test_cli.py), and [`tests/test_error_classification.py`](../tests/test_error_classification.py).
- Updated [`BASELINE-ROADMAP.md`](../BASELINE-ROADMAP.md), [`docs/API_REFERENCE.md`](API_REFERENCE.md), [`docs/USER_GUIDE.md`](USER_GUIDE.md), and [`docs/TIER1_CONTRACTS.md`](TIER1_CONTRACTS.md) to reflect the implemented Phase 3 parity and remaining bundle/Desktop gaps.

### Phase 1 Slice — API/Web Approval Continuation Flow
- Added shared interface approval state in [`interfaces/tool_approval.py`](../interfaces/tool_approval.py) so API and Web UI medium-risk tool calls create ledger-backed approval requests and can continue safely after explicit approval.
- Extended [`interfaces/api_server/app.py`](../interfaces/api_server/app.py) and [`interfaces/web_ui/app.py`](../interfaces/web_ui/app.py) with approval grant/deny routes for pending tool requests.
- Focused tests now prove request, grant, deny, execution, and ledger event emission across API/Web flows in [`tests/test_api_server.py`](../tests/test_api_server.py) and [`tests/test_web_ui.py`](../tests/test_web_ui.py).
- Updated roadmap and operator docs so Phase 1 now reflects the implemented approval continuation path.

### Phase 2 Lane 3 — Localhost Compatibility Shim Evidence
- Added a gitignored local helper wrapper at `.localtest/mock-ai-server/start-gpt54-mini-azure.ps1` to start the existing localhost Azure/OpenAI-compatible proxy with `gpt-5.4-mini` defaults.
- Verified the localhost compatibility shim path with `powershell -ExecutionPolicy Bypass -File .\.localtest\mock-ai-server\start-gpt54-mini-azure.ps1 -Fake` and `python .\.localtest\mock-ai-server\smoke_agentheim_http_providers.py`.
- Updated `BASELINE-ROADMAP.md`, `live-ai-testing.md`, and `docs/SUPPORT_MATRIX.md` to record this as partial evidence for self-hosted-shaped localhost configurations without overstating real OSS local-server validation.

### Phase 7 Slice — Error Classification + Troubleshooting Hardening
- Expanded `classify_error()` coverage in `core/error_classification.py` for Agentheim runtime errors and added provider message sub-classification for permission-denied, auth/config, rate-limit, timeout, and service-unavailable cases.
- Enriched `error_summary()` in `core/error_classification.py` to include `retryable`, `halt`, `next_action`, and troubleshooting document/section hints so ledger/report consumers can surface actionable remediation links.
- Added targeted tests in [`tests/test_error_classification.py`](../tests/test_error_classification.py) for Agentheim-specific exceptions, provider permission/error variants, and enriched error summary fields.
- Expanded [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md) with explicit remediation entries for provider auth failures, forbidden/permission-denied errors, transient provider outages/rate limits, run error-category triage, and older ledger resume/report compatibility.
- Expanded `agentheim doctor` with role coverage, first-class lane readiness, localhost endpoint reachability, and ContextOps availability checks, and updated [`docs/USER_GUIDE.md`](USER_GUIDE.md) accordingly.
- Updated [`monitoring/health.py`](../monitoring/health.py) to inspect the current lazy provider registry instead of a stale fixed provider list.


### Phase 2 Lane 1 — OpenAIV1Provider + AzureFoundryProvider Hardening
- `OpenAIV1Provider` now supports `auth_mode="none"` by substituting `"no-key-required"` for the OpenAI client key (`providers/openai_v1.py`).
- Added structured error classification: `_NON_RETRYABLE` (`AuthenticationError`, `PermissionDeniedError`, `BadRequestError`, `NotFoundError`, `UnprocessableEntityError`, `ConflictError`) raises `ProviderError` immediately; `_RETRYABLE` (`RateLimitError`, `APITimeoutError`, `APIConnectionError`, `InternalServerError`) follows existing retry/backoff logic (`providers/openai_v1.py`).
- `AzureFoundryProvider` hardened (`providers/azure_foundry.py`):
  - Validates endpoint is HTTP(S) URL, raises clear `ProviderError` if not.
  - `auth_mode="api_key"` with missing/empty/`"-"` api_key raises clear `ProviderError` at init time.
  - `auth_mode="none"` correctly omits `api-key` header.
  - Inherits structured retry/error classification from `OpenAIV1Provider`.
- Added provider unit tests for both adapters (`tests/test_providers_individual.py`).
- Added local/self-hosted OpenAI-compatible provider templates: `vllm`, `tgi`, `llama_cpp` (`config/config.py`).
- Updated `docs/SUPPORT_MATRIX.md` to include new self-hosted templates.
- `GeminiProvider` + `VertexAIProvider` hardened (`providers/gemini.py`):
  - Extracted shared helpers `_build_parts`, `_build_payload`, `_parse_response`, `_is_non_retryable_http_error` to reduce duplication.
  - JSON mode support: when `json` capability is present in config metadata, `responseMimeType` is set to `application/json`.
  - Structured retry/error classification for both providers: HTTP 400/401/403/404/409/422 raise `ProviderError` immediately; HTTP 429/5xx, timeout, and connection errors follow 3-attempt backoff.
  - `VertexAIProvider` now has retry parity with `GeminiProvider`.
  - Vision input mapping fixed: data URLs (`data:image/jpeg;base64,...`) are parsed and sent as `inline_data`; GCS/file URIs continue using `file_data`.
  - Vertex setup UX: clear `ProviderError` for missing model name, ADC failure (`DefaultCredentialsError` detected by name), and HTTP 403 permission denied with actionable guidance.
- Added tests for JSON mode, vision data URL/file URI, auth error immediate raise, rate-limit retry exhaustion, and Vertex setup errors.
- All 52 provider tests pass; baseline gate passes.

### Phase 1 Complete — Safety And Runtime Spine
- Unified tool invocation path across API, Web UI, and CLI (`core/tool_invocation.py`, `interfaces/api_server/app.py`, `interfaces/web_ui/app.py`, `interfaces/cli/cli.py`).
- Operation-level filesystem risk: read/list/stat → none, write/copy → medium.
- CLI interactive approval UX for medium-risk operations.
- Core runtime no longer imports `agents.self_improving` or `monitoring.metrics`; injected via `RunHook` protocol from `interfaces/run_hooks.py`.
- Runtime state transitions emit canonical `EventType.STATE_TRANSITION` with legacy JSONL mirror preserved.
- Updated `docs/SAFETY.md` to describe unified `ToolInvoker` path, operation-level risk, and interface approval behavior.
- Marked `BASELINE-ROADMAP.md` Phase 1 as complete.

### Phase 1 Slice 4 — State Machine Event Truth
- `RuntimeStateMachine._record()` now emits `EventType.STATE_TRANSITION` via `ledger.emit_event()` instead of only writing legacy `state_transitions.jsonl` (`core/state_machine.py`).
- Legacy `state_transitions.jsonl` mirror still written for backward compatibility.
- Added tests verifying canonical ledger events and legacy JSONL are both produced (`tests/test_negative_paths.py`).

### Phase 1 Slice 3 — Core Side Dependencies Moved Outward
- Removed `agents.self_improving` and `monitoring.metrics` lazy imports from `core/run_executor.py` — replaced with generic `RunHook` protocol and `add_hook()` registration.
- Added `interfaces/run_hooks.py` with `_DefaultRunHook` adapter and `register_default_run_hooks()` to inject concrete hooks from outside `core/`.
- Registered default hooks in `interfaces/api_server/app.py` and `interfaces/web_ui/app.py` so `RunExecutor` behavior is preserved without core knowing concrete implementations.
- Added hook invocation and idempotency tests in `tests/test_run_executor.py`.

### Phase 1 Slice 2 — CLI Tool Invocation Unified
- Routed CLI `copy` command through `ToolInvoker` with `interface_policy_config()` instead of direct `FilesystemTool.invoke()` (`interfaces/cli/cli.py`).
- Added interactive approval prompt to CLI `copy`: medium-risk operations display 6-field disclosure and prompt `[y/N]`; granted requests re-invoke via `granted_request` bypass (`interfaces/cli/cli.py`).
- Added `granted_request: ApprovalRequest | None = None` to `ToolInvoker.invoke()` so approved requests skip policy evaluation and execute directly (`core/tool_invocation.py`).
- Expanded `tests/test_filesystem_tool.py` with actual CLI copy execution test and approval-deny/grant prompt tests.
- Added `test_granted_request_bypasses_policy_and_executes` in `tests/test_tool_invocation.py`.
- Updated `core/public_api.py` exports to include `ApprovalRequest`, `ApprovalWorkflow`, `ToolInvoker`, `interface_policy_config`.

### Agent Roadmap Governance
- Added binding roadmap execution instructions covering `BASELINE-ROADMAP.md`, provider hardening priority, support-state evidence requirements, and baseline success gates.
- Updated agent operations, autonomous engineer instructions, boundary/docs/devtest skills, and instruction drift checks so future agents use the baseline roadmap contracts before implementing roadmap batches.

### Baseline Roadmap Phase 0 + Phase 1 Tool Slice
- Renamed the active baseline blueprint to `BASELINE-ROADMAP.md` and marked Phase 0 complete with evidence links.
- Added `docs/SUPPORT_MATRIX.md` for stable/beta/experimental/internal support states across providers, presets, interfaces, tools, and advanced subsystems.
- Added `docs/TIER1_CONTRACTS.md` mapping baseline user journeys to CLI/API/Web/Desktop surfaces, output contracts, docs, and evidence.
- Added `baseline` devtest mode covering instruction drift, CLI help, doctor skip-connectivity, provider templates, preset registry load, tool registry load, and pytest collection.
- Added centralized `core.tool_invocation.ToolInvoker` for policy-gated tool calls, operation-level filesystem risk, approval-required responses, and ledger tool events.
- Routed API and Web UI tool invocation endpoints through the centralized tool invocation service.
- Added `tests/test_tool_invocation.py` and expanded API/Web tool tests for medium-risk approval responses.
- Updated docs and live evidence records to current collection count: 1133 total tests collected, default lane selects 1098 and deselects 35.

### Resume + HTTP Tool + Adapter Tests (Verifier Blockers)
- Fixed CLI `resume` to fallback to `run.json` when `RUN_INITIATED` event is missing or `workflow_id` is empty (`interfaces/cli/cli.py`)
- Added `ledger.verify_chain()` integrity check in resume command (warning only, non-blocking)
- Added `tests/test_resume.py` with 3 fallback tests (missing RUN_INITIATED, empty workflow_id, both missing)
- Added `tests/test_http_tool.py` with 12 tests covering GET/POST success, network policy denial (private IP, http scheme, context.network_allowed), timeout/404/URLError handling, param validation
- Added `tests/test_adapters.py` with 12 tests covering WebResearchAdapter dispatch chain, GitHubCliAdapter subprocess wrapping, MCPClientAdapter allowlist/enabled behavior

### Test Suite Optimization
- Marked 35 slow tests (`@pytest.mark.slow`) across stress, integration, e2e, and lint check suites
- Default `pytest` now runs 790 fast tests in ~27s instead of 825 tests in ~122s
- Parallel execution (`pytest -n auto`) runs fast subset in ~15s (requires pytest-xdist)
- Updated `pyproject.toml` pytest config and `devtest/all-test-commands.md` with new commands

### Negative / Failure-Mode Tests
- Added `tests/test_negative_paths.py` covering state machine invalid transitions, coding runtime planning failure, dirty repo blocking, model registry missing role, and filesystem tool safety boundaries

### Filesystem Copy Operation
- Added `copy` operation to `FilesystemTool` supporting files and directories with path confinement (`tools/filesystem/__init__.py`)
- Added `agentheim copy <source> <destination>` CLI command (`interfaces/cli/cli.py`)
- Added `tests/test_filesystem_tool.py` with coverage for file copy, directory copy, missing source, existing destination, and path-escape safety

### DesktopUI
- Rewrote `interfaces/desktop_ui/app.py` with pywebview as primary engine (lighter than PyQt6, uses OS native webview)
- Added system tray icon with Show / Open in Browser / Quit menu (pystray)
- Added server health-check (`_wait_for_server`) before opening window
- Added `agentheim desktop [--port PORT] [--no-tray]` CLI command
- Added `[desktop]` optional dependencies: `pywebview>=5.0`, `pystray>=0.19`
- Expanded `tests/test_desktop_ui.py` with mock-based tests for all fallback tiers and CLI command

### Vision / Multimodal Auto-Resolution
- Added `GenericOpenAIVisionProcessor` supporting any OpenAI-compatible chat completions endpoint (`multimodal/generic_openai_vision.py`)
- Updated `_resolve_processor()` to auto-discover vision-capable providers from the active Agentheim profile when no explicit `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` is set; Azure Foundry `gpt-4.1` now works out of the box for `multimodal.image` describe + OCR operations (`multimodal/image.py`)
- Verified `describe_image` and `extract_text_from_image` end-to-end with Azure Foundry `gpt-4.1`

### Bug Fixes
- Added missing `safe_text_excerpt` to `core.public_api.__all__` (`core/public_api.py`)

### Research Workflow Happy Path
- Fixed `SummarizerAgent._parse()` to normalize `summaries[]` items: `url`/`link`/`source`, `key_points`/`summary`/`findings`/`description`/`points`, `credibility`/`trustworthiness`/`reliability` (`workflows/research/agents/summarizer.py`)
- Fixed `SummarizerAgent._parse()` to normalize `conflicts[]` and `gaps[]` dict items to strings
- Fixed `ReporterAgent._parse()` to normalize `sources[]` dict items to `"title (url)"` strings (`workflows/research/agents/reporter.py`)
- Fixed research workflow to propagate `agent_result.error` into `StepResult.metadata` for diagnostics (`workflows/research/workflows/research.py`)
- Verified research-report preset end-to-end with Azure Foundry `gpt-4.1`

### Coding Workflow Happy Path
- Fixed `PatchPlan`/`FileChange` schema aliases to accept PascalCase and snake_case variants: `FileChanges`, `fileChanges`, `patchPlan`, `patches`, `changes`, `FilePath`, `filePath`, `file_path`, `file`, `filename`, `Patch`, `ChangeType`, `PatchType` (`core/schemas_runtime.py`)
- Added empty `file_changes` guard in coding runtime: valid JSON with no file changes now triggers retry instead of silent no-op (`workflows/coding/runtime.py`)
- Added work order scope widening: runtime auto-adds files mentioned in title/objective to `relevant_files` if they exist in repo snapshot (`workflows/coding/runtime.py`)
- Fixed state machine: added `FIX_LOOP → BASIC_VERIFY` transition (`core/state_machine.py`)
- Fixed CLI `run --max-fix-attempts` default from `0` to `3` to match `run_task()` default (`interfaces/cli/cli.py`)
- Improved planner prompt: explicit rule to create dedicated test tasks when user mentions tests, and require `relevant_files` to cover all intended edits (`workflows/coding/runtime.py`)
- Verified coding happy path end-to-end with Azure Foundry `gpt-4.1` and `gpt-5.4` on division-by-zero task; `gpt-4.1-mini` insufficient for this task

### Resume / Report Fixes
- Fixed `command-assistant` and `context-maintainer` runtimes to emit `RUN_INITIATED` event, enabling resume/report for fresh runs (`workflows/command_assistant/runtime.py`, `workflows/context_maintainer/runtime.py`)
- Fixed `context-maintainer` to write `final_report.json` (`workflows/context_maintainer/runtime.py`)
- Fixed generic CLI `report` command to handle dict-shaped final reports from context-maintainer (`interfaces/cli/cli.py`)

### Provider Profiles
- Replaced AI provider `.env` runtime loading with provider profiles and vault-backed `secret://provider/<id>/<name>` refs.
- Added provider CLI namespace for templates, add, list, use, assign, test, import-env, rotate-secret, and remove.
- Added profile-backed provider templates for current providers plus Gemini, Vertex AI, Anthropic, Kimi/Moonshot, Mistral, Groq, DeepSeek, OpenRouter, Together AI, Cohere, Perplexity, Ollama, Ollama Cloud, and LM Studio.
- Added native Gemini, Anthropic, Cohere, Perplexity, Vertex AI, and Ollama Cloud provider adapters plus multimodal request content parts.
- Added API/Web provider template/profile surfaces and updated docs/test guidance for the new setup flow.

## 2026-05-13

### AICtx Integration — M6-M9 Complete
- M6 Runtime/storage convergence: canonical transient store moved to `.ai-team/runs/`; `LegacyAictxReader` provides backward compatibility for `.aictx/runs/`
- M7 Provider unification: `AgentheimToAictxAdapter` bridges Agentheim `providers/base.py` to AICtx `llm/base.py`; OCI GenAI provider routed through unified adapter
- M8 OCI/remote backend adoption: `agentheim ctx oci` CLI commands (doctor, snapshot, bundle) expose OCI operations; OCI is an optional extra (`pip install agentheim[oci]`)
- M9 Compatibility/decommissioning: legacy `build_context_pack` deprecated via `DeprecationWarning` in `core.public_api` but retained as fallback; standalone `aictx` CLI deprecated; final docs sweep complete

### AICtx Integration — M3-M5 Complete
- Added `agentheim ctx` CLI namespace with 8 commands: init, scan, run, verify, status, clean, public-docs impact, public-docs update (`interfaces/cli/ctx_commands.py`)
- Added API server routes under `/api/ctx/*` for all context operations (`interfaces/api_server/app.py`)
- Added Web UI context operations section with dashboard controls (`interfaces/web_ui/app.py`)
- Created `context-maintainer` workflow pack with full DAG (scan → plan → generate → write → verify + public_docs_impact → produce_report) (`workflows/context_maintainer/`)
- Created `context-maintainer` preset with guided questions for scope, write mode, project path (`presets/context_maintainer.py`)
- Added context operation event types to `core/events.py`: CONTEXT_INITIALIZED, CONTEXT_SCANNED, CONTEXT_PLANNED, CONTEXT_GENERATED, CONTEXT_WRITTEN, CONTEXT_VERIFIED, CONTEXT_STALE_DETECTED, PUBLIC_DOCS_IMPACT_MAPPED, PUBLIC_DOCS_UPDATED
- Added `ArtifactStore` methods for context run reports, lockfiles, and public docs impact
- Added `ContextRunLedger` helper for emitting context events to ledgers (`agentheim/context_run_ledger.py`)
- Made coding workflow context-aware: uses AICtx pipeline with fallback to legacy `build_context_pack` (`workflows/coding/runtime.py`)
- Made docs maintenance workflow context-aware with stale-context preflight and public-docs impact mapping (`workflows/docs_maintenance/runtime.py`)
- Made research workflow context-aware with AICtx-derived shards (`workflows/research/runtime.py`)
- Added stale-context preflight hook to `WorkflowRunner` with `stale_context_check` parameter and `context_fresh`/`context_stale` step conditions (`core/workflow_runner.py`)
- Implemented review-first public-doc update path: patches generated but never auto-applied, workflow marks as "pending_review" (`workflows/docs_maintenance/runtime.py`)
- Full suite: **638 passed**, 2 skipped, 1 unrelated playwright failure

### AICtx Integration — M2.5 Complete
- Expanded `ContextOps` ABC with 4 new methods: `init()`, `clean()`, `run_pipeline()`, `public_docs_update()` (`agentheim/context_ops.py`)
- Implemented all 11 methods in `AictxContextOps` (`agentheim/context_ops_impl.py`)
- Enriched `WriteReport` with AICtx telemetry: `run_report`, `timing`, `entropy`
- Added `CleanResult` dataclass for `clean()` operation results
- ContextOps tests: **18 passed** (was 10; +8 new tests for init, clean, run_pipeline, public_docs_update)
- Removed old `AICtx/` local reference copy; updated all instructions/skills to reference `../AICtx` workspace project
- Reverted runtime imports to `agentheim.vendor.aictx` so AICtx ships with Agentheim
- Updated `docs/AICTX_INTEGRATION_PLAN.md` with M2.5 milestone and expanded API contract
- Updated `scripts/check-agent-instructions.py` to verify `AICtx/` is absent rather than gitignored
- Full suite: **676 passed**, 1 skipped (playwright env issue), 1 unrelated failure

### AICtx Integration — M2 Complete
- Implemented `agentheim/context_ops_impl.py` — concrete `AictxContextOps` delegating all 7 ContextOps methods to AICtx internals:
  - `scan` → `scan_repository`
  - `plan` → `plan_context`
  - `generate` → `extract_facts` (dry_run provider for tests)
  - `write` → `write_context_scaffold` + `build_context_lock` + `write_lockfile`
  - `verify` → `verify_detailed`
  - `status` → derived from `verify_detailed`
  - `public_docs_impact` → `build_public_docs_map`
- Updated `agentheim/context_ops.py` placeholder dataclasses into proper containers with `raw` delegation fields.
- Added `tests/test_context_ops_impl.py` with 10 tests covering scan, plan, generate, write, verify, status, public_docs_impact.
- Added `tests/test_context_ops_impl.py` to `scripts/roadmap-check.py` `SUBPROCESS_EXEMPTIONS` (git init for synthetic repos).
- Full suite: **705 passed, 3 skipped** (was 695; +10 new ContextOps tests).

### MCP Configuration
- Added `@upstash/context7-mcp` to global `~/.kimi/mcp.json`.
- Added personal MCP servers to global `~/.kimi/mcp.json` for use while working on the project:
  - `chrome-devtools-mcp`
  - `mcp-server-semgrep`
  - `markitdown-mcp-npx`
  - `@modelcontextprotocol/inspector`

### Playwright E2E Tests
- Created `tests/test_browser_e2e.py` with 10 real-browser end-to-end tests covering:
  - `navigate`, `get_text` (with/without selector), `get_links`
  - `screenshot` (base64 and file save)
  - `click`, `evaluate`
  - Session lifecycle (`create_session` → `navigate` → `get_text` → `close_session`)
  - Network policy denial
- All E2E tests use `ThreadPoolExecutor` worker threads to avoid Playwright sync API / pytest-anyio asyncio loop conflict.
- Added `e2e` marker to `[tool.pytest.ini_options]` in `pyproject.toml`.

### Public Docs Sync
- Updated test counts across `README.md` and `docs/DEV_TESTING.md` → **695 passed, 3 skipped**.
- Fixed mismatched email link in `CODE_OF_CONDUCT.md`.
- Added `.github/instructions/07-chat-output.md` to `AGENTS.md` binding instructions list.
- Fixed dirty-repo troubleshooting example in `docs/TROUBLESHOOTING.md` to use `agentheim run ... --allow-dirty`.
- Added historical-note header to `REPOSITORY_AUDIT_REPORT.md` about moved documentation paths.
- Added missing CLI commands (`memory`, `mcp-list`, `mcp-call`) to `docs/USER_GUIDE.md` with beginner-friendly explanations and copy-paste examples.
- Fixed Workflow Model Roles table in `docs/USER_GUIDE.md` to list actual `ModelRole` enum values (`planner`, `executor`, `verifier`, `indexer`, etc.) rather than conceptual agent names.
- Fixed `docs/API_REFERENCE.md` Memory endpoints to document actual `{backend}/{key}` path (`jsonl`, `sqlite`, `vector`) instead of incorrect `{scope}/{key}` (`run`, `repository`, `global`).

### AICtx Integration — M1 Complete
- Imported AICtx source via filtered-history subtree merge into `agentheim/vendor/aictx/`.
- Renamed `agentheim/vendor/aictx/logging.py` → `_logging.py` to prevent stdlib `logging` shadowing.
- Added `agentheim*` to `pyproject.toml` package discovery and `pathspec>=0.12.0` to dependencies.
- Added AICtx vendor subprocess/git paths to `scripts/roadmap-check.py` `SUBPROCESS_EXEMPTIONS` so legacy architecture checks pass.
- Defined `ContextOps` ABC in `agentheim/context_ops.py` as the boundary between Agentheim and AICtx.
- Created `agentheim/vendor/MODULE_MAP.md` documenting preserved / adapted / replaced modules and provider interface delta.
- Updated `docs/AICTX_INTEGRATION_PLAN.md` marking M1 complete.
- Fixed all vendor internal imports (`from aictx.` → `from agentheim.vendor.aictx.`) so tests run without namespace collisions.
- Hardened `agentheim/vendor/aictx/llm/oci_genai.py` `_require_oci_sdk()` to detect vendor-package namespace collisions and fail with `ConfigError`.
- Vendor unit tests: **101 passed**.

## 2026-05-12

### Directive System Governance
- Added binding instruction priority, instruction index, documentation-integrity rules, tooling/verification rules, and canonical US-spelling forbidden-behavior instructions under `.github/instructions/`.
- Added executable directive linting via `scripts/check-agent-instructions.py`, directive devtest mode, and CI governance replacement for the legacy roadmap checker.
- Updated agent, skill, docs, PR template, and devtest guidance to use `docs/CHANGELOG.md`, directive checks, and current GitHub instruction files.

### Critical Bug Fixes — Audit Findings Resolved
- **Package discovery (namespace packages):** Added missing `__init__.py` to `workflows/`, `config/`, `interfaces/cli/`. Verified wheel build includes all 54 packages. Entry point `agentheim` resolves correctly.
- **Provider map centralization:** All callers already use `build_model_registry()` from `core/model_registry.py`. Fixed remaining bare `from_team_config()` calls in `devtest/ai_test.ps1` and `Agent-Team/tests/test_model_registry.py` to use `build_model_registry()`.
- **Default API key exposure:** `auth.py` already requires explicit `AI_TEAM_API_KEYS` or dev mode — no hardcoded fallback exists. No change needed.

## 2026-05-10

### Phase 7 Slice 5 — Safety & Privacy
- Added `core/privacy_enforcer.py` with `PrivacyMode` enum (STANDARD, LOCAL_ONLY, STRICT_PRIVATE, ENCRYPTED) and `PrivacyEnforcer` class for structured privacy evaluation, param redaction, and sensitive-path detection.
- Added `core/approval_workflow.py` with `ApprovalRequest` frozen dataclass (6-field disclosure: tool_id, action, target, risk_level, justification, params_redacted) and `ApprovalWorkflow` class for managing pending approvals and emitting `APPROVAL_REQUESTED` / `APPROVAL_GRANTED` / `APPROVAL_DENIED` ledger events.
- Enhanced `core/policy_engine.py` — `evaluate()` now accepts optional `ledger`, `step_id`, `agent_id` keyword arguments and emits `POLICY_EVALUATED` events for every evaluation (allow/deny/ask). Fully backward-compatible.
- Exported new symbols in `core/public_api.py`: `PrivacyMode`, `PrivacyEnforcer`, `ApprovalRequest`, `ApprovalWorkflow`.
- Added `tests/test_privacy_enforcer.py` (17 tests), `tests/test_approval_workflow.py` (13 tests), `tests/test_policy_audit.py` (6 tests), `tests/test_policy_engine.py` (24 tests) — 64 new tests total.
- Full suite: **667 passed, 2 skipped**.
- Architecture check: **0 violations**.

## 2026-05-10

### Phase 7 Slice 4 — Boundaries & Loading Tests
- Added `tests/test_provider_lazy_loading.py` (6 tests) verifying `providers/__init__.py` lazy-loading: listing metadata does not import heavy modules, creating a provider loads only the requested module.
- Added `tests/test_interface_isolation.py` (7 tests) enforcing that all `interfaces/*` files import exclusively from `core.public_api`, with AST-based verification of no direct `core.*` imports.
- Added `tests/test_import_linting.py` (2 tests) invoking `scripts/roadmap-check.py` as a subprocess to confirm the architecture checker itself reports zero Phase-7 violations.
- Added `tests/test_boundaries.py` to `SUBPROCESS_EXEMPTIONS` in `scripts/roadmap-check.py` so the test's legitimate `subprocess.run` calls do not trigger false Law-7 violations.
- Updated `devtest/run-devtest.ps1` and `devtest/all-test-commands.md` to include the new Slice 4 test modules.
- Full suite: **607 passed, 2 skipped**.

## 2026-05-10

### Roadmap Rewrite — Honest Audit + Phase 7 Definition
- **Full codebase audit** against roadmap docs 00-18 completed by 5 parallel agents.
- **Verdict:** Phases 0-6 are feature-complete (418 tests pass) but large foundational subsystems are missing or incomplete.
- **Rewrote `docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md`** with honest "As-Built" notes for every phase, cataloguing what exists vs. what was planned.
- **Defined Phase 7: Production Hardening** — 6 exit gates covering ledger hash chain, replay/resume, missing core runtime files, public API facade, provider lazy loading, and approval workflow.
- **Defined Phase 8: Future Expansion** — IDE extensions, CI/CD integration, AICtx, formal verification.
- **Rewrote `docs/roadmap/19_FUTURE_RESERVED_ARCHITECTURE.md`** — removed all Phase 6 completed items, moved missing foundational pieces to Phase 7, kept only truly future integrations.

## 2026-05-10

### Approach B Completion — Async Tool Protocol & WebSocket Streaming
- **Async tool protocol**: Added `AsyncToolProtocol` and `AsyncBaseTool` to `core/tool_protocol.py`. `ToolRegistry` now supports mixed sync/async tool registration with `get_async()` helper.
- **Async browser tool**: Added `AsyncBrowserTool` in `tools/browser/__init__.py` using `playwright.async_api` for transient mode and `asyncio.to_thread()` for session mode.
- **Async MCP tool**: Added `AsyncMCPTool` in `tools/mcp/tool_adapter.py` that delegates sync MCP client calls to a thread pool via `asyncio.get_event_loop().run_in_executor()`.
- **WebSocket streaming**: Added `GET /api/runs/{id}/ws` WebSocket endpoints to both API server and Web UI. Bridges sync `RunExecutor` notifications to async WebSocket handlers via `asyncio.Queue`. Closes cleanly for already-completed runs.

## 2026-05-12

### Docs Unification + AICtx Planning
- Consolidated user-facing docs under `docs/`, removed duplicated legacy doc paths, and kept GitHub root surfaces (`README.md`, `CONTRIBUTING.md`) as pointers into the new structure.
- Added `docs/AICTX_INTEGRATION_PLAN.md` with milestone-based AICtx absorption plan, backlog slices, deliverables, and test gates.
- Corrected stale operational docs around CLI entrypoints, API auth/tool behavior, privacy-mode naming, ledger examples, and local verification commands.
- Updated `devtest/all-test-commands.md` and `docs/DEV_TESTING.md` with repo-local CLI smoke commands and a Markdown-link smoke check for the new docs layout.
- **RunExecutor unsubscribe**: Added `unsubscribe()` method to support WebSocket cleanup on disconnect.
- **Tests**: Added `tests/test_tool_protocol.py` (11 tests) and WebSocket tests in `test_api_server.py`/`test_web_ui.py`. Total suite: **418 passed, 2 skipped**.

## 2026-05-10

### Phase 6 Full Implementation (Approach B)
- **MCP integration**: Added `MCPConnectionPool` for persistent connections. Fixed client lifecycle bug where `register_mcp_tools()` disconnected clients after registration, leaving tools with stale references.
- **Browser tool**: Added `BrowserSessionManager` for persistent browser contexts. New operations `create_session` and `close_session` enable multi-step workflows (navigate → click → fill) without launching a new browser per operation.
- **API server**: Added `POST /api/workflows/{id}/execute`, `POST /api/presets/{id}/run`, `GET /api/runs/{id}/stream` (SSE), and `GET /api/metrics` (Prometheus). Added request logging middleware. Replaced fake provider health with dynamic `_check_provider_health()`.
- **Web UI**: Added execution endpoints for workflows and presets, run status polling, and SSE streaming.
- **Plugin marketplace**: Wired sandbox into `PluginManager.load()` — calls `activate()`/`register()` through `Sandbox.call()`. Added signature verification on load.
- **Distributed workers**: Added HTTP transport (`CoordinatorClient`, `RemoteWorker`) and FastAPI coordinator server (`create_coordinator_app`) with endpoints for registration, heartbeat, task polling, submission, and completion.
- **Multimodal**: Added `OpenAIVisionProcessor` and `ClaudeVisionProcessor` with auto-detection via `AGENTHEIM_VISION_PROVIDER` env var. Replaced 100% stub with real vision model integration.
- **Self-improving agents**: Added `SelfImprovingHook` that captures run feedback in `RunExecutor` and applies `PromptEvolutionStrategy`, `ParameterTuningStrategy`, and `ToolSelectionStrategy` automatically.
- **Monitoring**: Wired `MetricsCollector` into `RunExecutor` so all background runs record start/end/error metrics. Prometheus endpoint serves live metrics.
- **Federation**: Added HTTP transport (`FederationClient`) and FastAPI server (`create_federation_app`) for peer discovery, task delegation, and result relay.
- **Tests**: Added 21 new tests across `test_mcp_pool.py`, `test_run_executor.py`, `test_distributed_transport.py`, `test_federation_transport.py`. Total suite: **403 passed, 2 skipped**.

## 2026-05-10

### Validation & Production Hardening
- Fixed missing `os` import in `interfaces/cli/cli.py` causing `doctor` command to crash with `NameError`.
- Added root `pyproject.toml` making project installable via `pip install -e .` with `agentheim` console script entry point.
- Fixed all "Agentwerk" → "Agentheim" branding in README.md and public docs.
- Fixed all API/Web/Desktop UI titles from "Local Agent Orchestra" → "Agentheim".
- Updated all public docs (README, CONTRIBUTING, INSTALL, CONFIGURATION, API) to reference `agentheim` CLI instead of broken `python -m ai_team`.
- Improved config loading error message to tell users exactly how to set up `.env`.
- Added required-input validation to `agentheim start <preset>` command.
- Fixed `tests/test_api_server.py` and `tests/test_web_ui.py` to match new API/Web UI titles.
- Rewrote `devtest/` scripts (`run-devtest.ps1`, `ai_test.ps1`, `all-test-commands.md`) to reflect current root-project test structure.
- Updated `Agent-Team/docs/` internal references from `python -m ai_team` → `agentheim`.
- Full test suite: **372 passed, 1 skipped**. Architecture check: PASSED.
- Fixed CI workflow `.github/workflows/architecture.yml` to explicitly install all Python dependencies, link package with `--no-deps`, and install Playwright Chromium browsers. CI now passes.

## 2026-05-10

### unreleased (Phase 6 scaffolds)
- Fixed `StubMultimodalProcessor` import path in `tests/test_multimodal.py`.
- Fixed `TaskScheduler` test: `test_task_retry_on_failure` now registers worker with matching capabilities.
- Fixed `WorkerPool` default handler signature (`_execute_task` now takes `payload` only).
- Added `use_threads` parameter to `WorkerPool` to support lambda handlers in tests on Windows (ProcessPoolExecutor spawn + pickle limitation).
- Full test suite: **372 passed, 1 skipped** (all Batch 2–5 scaffold tests green).
- Cleared all entries from `RESERVED_SUBSYSTEMS` in `scripts/roadmap-check.py`.

## 2026-05-09

### cc2059b
- Added initial local CLI runner using Grok-4-1-fast-reasoning.
- Established base command execution path for single-agent workflow.

### cc78c78
- Restructured repository layout around `Agent-Team`.
- Removed absolute-path coupling from persisted artifacts for move/rename safety.

### fb5e158
- Refactored provider/model wiring toward provider-agnostic registry flow.
- Introduced workflow-pack direction and strengthened runtime abstraction boundaries.

### f1cdc21
- Added `devtest/ai_test.ps1` for live role-model connectivity checks.
- Expanded `devtest` command surface for narrow/targeted/broad/full testing flows.

### unreleased (working tree)
- Added interactive `Y/N/A` post-run actions in `devtest/run-devtest.ps1`.
- Added timeout/retry policy guidance in `AGENTS.md` for `devtest/ai_test.ps1`.
- Renamed docs usage file to `Agent-Team/docs/CLI_RUNBOOK.md`.
- Added centralized repo-level agent rules and evolving `devtest` governance.
- Fixed cross-platform patch path normalization for Windows-style separators.
- Fixed `ai_team/workflows/base.py` provider creation call to match registry interface.
- Made `ModelRegistry` model mapping generic over configured model entries (not hardcoded IDs).
- Added optional `AI_TEAM_MODELS_JSON` for explicit model registry definitions.
- Added legacy compatibility capabilities so planner/executor/verifier resolution works.
- Activated Phase 4 — PRESET SYSTEM & CLI in `AGENT_POCKET_CARD.md` and CI (`architecture.yml`).
- Activated Phase 5 — EXPANSION. Unlocked documents/research/file_org/docs_maintenance/github_maintenance/command_assistant workflows, guided TUI, and memory backends.
- Switched neutral default model placeholders and removed Grok-implied defaults from `.env.example`.
- Added lazy provider class loading in registry to avoid eager provider imports.
- Implemented `workflows/research/` workflow pack: `ResearchWorkflow` with gatherer/summarizer/reporter DAG, agent classes, output schemas, system prompts, markdown renderer, and runtime entrypoints (`plan_task`, `run_task`).
- Extended `ModelRole` and `TeamConfig.by_role()` to support dynamic research agent roles (gatherer, summarizer, reporter).

- Implemented `workflows/documents/` workflow pack: `DocumentsWorkflow` with indexer/retriever/answerer DAG, agent classes with Pydantic output schemas, system prompts, markdown report renderer, and runtime entrypoints (`plan_task`, `run_task`).
- Implemented `workflows/file_organization/` workflow pack: `FileOrganizationWorkflow` subclassing `Workflow` with analyzer/proposer/applier DAG (analyze → propose → preview → apply), agent classes with Pydantic output schemas, system prompts, markdown report renderer, and runtime entrypoints (`plan_task`, `run_task`).
- Implemented `presets/` base class (`Preset`, `Question`), `PresetRegistry`, and 7 preset definitions mapping to all workflow packs.
- Added `presets`, `start`, and `guided` CLI commands in `interfaces/cli/cli.py` using Rich tables and Typer.
- Fixed CLI imports to use root-level modules (`config.config`, `core.*`, `providers.base`, `workflows.coding.runtime`).
- Added `interfaces/guided_tui/app.py` with interactive preset picker using Rich prompts.
- Implemented `interfaces/guided_tui/` beginner-friendly TUI: `app.py` orchestrates preset discovery, questionnaire, confirmation, and execution; `picker.py` lists presets by number; `questionnaire.py` handles text/choice/path/boolean inputs with validation; `render.py` provides rich tables, panels, and styled messages.
- Added brain-like memory system: `memory/embeddings.py` (hash-based random projection embeddings), `memory/backends/vector.py` (cosine-similarity vector search), `memory/episodic.py` (timeline-based episodic memory), `memory/semantic.py` (concept graph semantic memory), `memory/brain.py` (unified Brain orchestrator with perceive/remember/learn/relate/summarize).
- Added comprehensive memory test suite: 60 tests covering embeddings, all 3 backends (jsonl/sqlite/vector), episodic memory, semantic memory, brain integration, registry, and project scoping. All passing.
- Fixed `_sanitize_key` to block path traversal characters (`.` and `/`) in all backends.
- Fixed `SqliteBackend` to create parent directories before opening database.
- Fixed `datetime.utcnow()` deprecation warnings in episodic memory.
- Enforced project-scoped memory: `Brain`, `MemoryRegistry`, and all backends now require explicit `repo_root`. Memory lives at `<repo_root>/.ai-team/memory/`.
- Added `.project_scope` fingerprint file: Brain validates on init and raises `RuntimeError` if memory directory belongs to a different project.
- Updated `MemoryRegistry` singleton to key by `repo_root`, giving each project its own isolated registry instance.
- Implemented `memory/bus.py` `MemoryBus` singleton with cross-process file locking (`filelock`) and intra-process `threading.RLock`. Reentrant exclusive lock prevents deadlocks on nested operations.
- Integrated `MemoryBus` into `Brain`: `perceive()`, `learn()`, `relate()` use `exclusive()` lock; `remember()`, `recent()`, `summarize()` use `shared()` lock.
- Added `tests/memory/test_bus.py` with 12 tests covering singleton behavior, write/read, shared/exclusive locking, reentrancy, concurrent threads, and backend reuse. Suite now 72 tests, all passing.

- Implemented Tier 1 WorkingMemory (`memory/tiers/working.py`): ephemeral single-run context with set/get/append/snapshot/flush API, auto-persists to RunLedger.
- Implemented Tier 3 GlobalMemory (`memory/tiers/global_.py`): cross-project persistent memory using SQLite with WAL mode. Stores preferences, approval history, and model performance profiles. Uses `platformdirs` for cross-platform data directory.
- Integrated WorkingMemory into workflow runtime: `StepContext` now carries `working_memory`; `Workflow.run()` instantiates and passes it to each step.
- Added CLI `memory` command with get/set/history/profile subcommands.
- Added `tests/memory/test_tiers.py` with 19 tests covering WorkingMemory and GlobalMemory. Total memory suite: 103 tests, all passing.
- Updated `scripts/roadmap-check.py` SUBPROCESS_EXEMPTIONS to include `tests/memory/test_stress.py`.
- Updated `devtest/` files to reflect current test structure and recommended execution paths.

- Fixed file_organization workflow capability mismatch: changed analyzer to use indexer role with file_read capability, applier to use executor with code_edit capability, added cross-role fallback in _resolve_agent_model.
- Rewired guided TUI to use rich components: app.py now delegates to picker.pick_preset(), questionnaire.run_questionnaire(), and render helpers instead of inline bare-bones logic.
- Added CLI `doctor` command: diagnoses Python version, required packages, provider config, workspace writability, git availability, and optional model connectivity.
- Added 36 smoke tests in tests/smoke/: 7 workflow import tests, 7 runtime import tests, 9 preset registry tests, 12 CLI command tests.
- Updated scripts/roadmap-check.py SUBPROCESS_EXEMPTIONS to include interfaces/cli/cli.py (doctor command git check).

- Rewrote `tools/integrations/web_research.py` with tiered fallback: DuckDuckGoSearchAdapter (duckduckgo-search) → UrllibSearchAdapter (HTML scraping) → stub. WebResearchAdapter dispatches automatically.
- Added core module unit tests (`tests/core/`): ledger (6 tests), schemas (8 tests), errors (11 tests), redaction (10 tests), model_registry (6 tests). Total: 41 core tests.
- Expanded workflow smoke tests with instantiation tests: all 6 Workflow subclasses instantiate with mocked ModelRegistry; DAG cycle/ordering verified; file_organization capability fix regression-tested.
- Fixed `tests/core/` pytest shadowing issue by removing `__init__.py` (pytest imports test modules as flat names when parent has no `__init__.py`).
- Fixed redaction tests to use labeled secrets (`api_key: xxx`) since `redact_text` regex requires a label prefix.

- Fixed policy bypass in docs_maintenance/runtime.py: file writes now logged to ledger via `append_jsonl("file_changes.jsonl")` before execution.
- Fixed policy bypass in file_organization/workflows/file_organization.py: file renames now logged to ledger via `append_jsonl("file_changes.jsonl")` before execution.
- Fixed `Workflow.run()` in workflows/base.py: added `working_mem.flush()` at run completion so WorkingMemory persists to ledger.
- Fixed `StepContext` pydantic serialization: added `arbitrary_types_allowed=True` to support `ToolRegistry` and `WorkingMemory` fields.
- Fixed `Workflow.run()` ledger access: changed `self.ledger.run_id` to `self.ledger.run_dir.name` (RunLedger has no run_id attribute).
- Added end-to-end workflow execution tests (`tests/smoke/test_workflow_execution.py`): research, command_assistant, and file_organization workflows run with mocked `BaseAgent._invoke`, verifying full step completion and artifact production.
- Updated `docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md`: Phase 5 marked complete, Phase 6 unlocked with subsystem priorities and exit gates.
- Updated `docs/roadmap/AGENT_POCKET_CARD.md`: Current Phase updated to 6, Phase 5 gates marked passed, forbidden one-liners updated.

- Implemented Phase 6 MCP integration (`tools/mcp/`):
  - `tools/mcp/client.py` — Lightweight stdio JSON-RPC MCP client with initialize handshake, tool discovery, and invocation. No external `mcp` package dependency.
  - `tools/mcp/tool_adapter.py` — `MCPTool` class wrapping MCP server tools as `BaseTool` instances with schema conversion.
  - `tools/mcp/config.py` — MCP server configuration loading from `.ai-team/mcp.json` or `AI_TEAM_MCP_SERVERS_JSON` env var.
  - `tools/mcp/__init__.py` — `register_mcp_tools()` for automatic discovery and ToolRegistry registration.
  - Added CLI commands: `mcp-list` (discover tools) and `mcp-call` (invoke tool directly).
- Added 18 MCP tests (`tests/test_mcp.py`): type mapping, schema conversion, MCPTool wrapping, client mocked transport, config loading.
- Updated `scripts/roadmap-check.py`: removed `tools/mcp/` from RESERVED_SUBSYSTEMS, added `tools/mcp/client.py` to SUBPROCESS_EXEMPTIONS.
- Total test count: 214 passing.

- Implemented Phase 6 Browser tool (`tools/browser/`):
  - `BrowserTool` class with 7 operations: `navigate`, `get_text`, `get_links`, `screenshot`, `click`, `fill`, `evaluate`.
  - Primary backend: Playwright (full JS rendering, screenshots, interactions).
  - Fallback chain: requests + BeautifulSoup → urllib + regex for static content extraction.
  - Screenshots support base64 return or file save with workspace path confinement.
  - Risk level: HIGH with network policy enforcement.
- Added 24 browser tests (`tests/test_browser_tool.py`): schema validation, policy blocking, fallback chain, mocked Playwright operations, HTTP fallback methods, save path validation, and lightweight network integration tests.
- Wired `BrowserTool` into `ToolRegistry` (`tools/registry.py`).
- Total test count: 238 passing.

- Implemented Phase 6 Local DB tool (`tools/local_db/`):
  - `LocalDBTool` class with 3 operations: `query`, `list_tables`, `describe`.
  - Read-only SQLite access via `file:{path}?mode=ro` URI connections.
  - SQL sanitization: whitelist prefix check (SELECT, PRAGMA, EXPLAIN, WITH) + dangerous keyword scan.
  - Path confinement to workspace with traversal and symlink escape protection.
  - Returns structured data: columns/rows for queries, schema info for describe, table/view list.
- Added 26 local DB tests (`tests/test_local_db_tool.py`): schema validation, path safety, SQL sanitization (allowed/blocked), query results, limit/has_more, list_tables, describe, and invalid table name rejection.
- Wired `LocalDBTool` into `ToolRegistry` (`tools/registry.py`).
- Updated `scripts/roadmap-check.py`: removed `tools/local_db/` and `tools/browser/` from RESERVED_SUBSYSTEMS.
- Updated `devtest/all-test-commands.md`: added browser and local_db test commands.
- Total test count: 272 passing.

- Implemented Phase 6 Web UI prototype (`interfaces/web_ui/`):
  - FastAPI application (`interfaces/web_ui/app.py`) with `create_app()` factory.
  - Endpoints: `/api/health`, `/api/tools` (list + invoke), `/api/workflows`, `/api/presets`, `/api/memory/{scope}/{key}` (read + write).
  - Built-in HTML dashboard at `/` with live fetch of tools, workflows, and presets.
  - Safety: high/critical risk tools blocked from web invocation; network disabled in tool context.
- Added 12 Web UI tests (`tests/test_web_ui.py`): health, dashboard HTML, tools list, tool invocation (found/not-found/blocked/safe), workflows list, presets list, memory read/write.
- Updated `scripts/roadmap-check.py`: removed `interfaces/web_ui/` from RESERVED_SUBSYSTEMS.
- Updated `devtest/all-test-commands.md`: added Web UI test command.
- Total test count: 284 passing.

- Implemented Phase 6 API Server (`interfaces/api_server/`):
  - FastAPI application with OpenAPI spec auto-generation (`/openapi.json`, `/docs`, `/redoc`).
  - Endpoints: health, tools (list + schema + invoke), workflows (list + detail), presets, memory, models, providers, runs.
  - API key authentication (`X-API-Key` header) with env-based allowlist.
  - Rate limiting (sliding window, 60 req/min).
  - CORS middleware.
  - Safety: high/critical risk tools blocked from API invocation.
- Added 22 API server tests (`tests/test_api_server.py`): health, auth (missing/invalid/valid), tools list/invoke, workflows, presets, memory, models, providers, runs, OpenAPI schema, docs endpoint.
- Implemented Phase 6 Desktop UI scaffold (`interfaces/desktop_ui/`):
  - PyQt6 primary backend with QWebEngineView loading the Web UI.
  - Tkinter fallback for systems without PyQt6.
  - Server runs in background thread; browser fallback if no GUI framework.
- Implemented Phase 6 Distributed Worker Protocol (`workflows/distributed/`):
  - Message schemas: `WorkerRegistration`, `TaskAssignment`, `TaskResult`, `Heartbeat` with JSON serialization.
  - `TaskScheduler` with round-robin + capability-based routing, heartbeat pruning, retry logic.
  - `WorkerPool` using `ProcessPoolExecutor` for isolated task execution.
- Added 21 distributed tests (`tests/test_distributed.py`): message roundtrips, scheduler registration/assignment/retry/pruning, worker pool start/stop/submit.
- Implemented Phase 6 Plugin Marketplace (`marketplace/`):
  - `PluginManifest` schema with validation, JSON roundtrip, file loading, SHA-256 signature.
  - `PluginManager` with discovery, load, unload, scan paths.
  - `Sandbox` with restricted `ToolContext` and exception containment.
- Added 16 marketplace tests (`tests/test_marketplace.py`): manifest validation, JSON roundtrip, file loading, signature, discovery, load/unload, sandbox.
- Implemented P5 research scaffolds:
  - `monitoring/`: `MetricsCollector` (Prometheus export) + `HealthReporter` (disk, memory, providers).
  - `agents/self_improving/`: `FeedbackLoop` + `PromptEvolutionStrategy`, `ParameterTuningStrategy`, `ToolSelectionStrategy`.
  - `multimodal/`: `MultimodalProcessor` protocol + `ImageTool` with stub backend.
  - `federation/`: `FederationProtocol` with message schemas (Discovery, Capability, TaskDelegation, ResultRelay) and trust model.
- Added tests for all P5 scaffolds: monitoring (8), self-improving (10), multimodal (5), federation (7), desktop UI (3).
- Updated `scripts/roadmap-check.py`: removed all Phase 6 subsystems from RESERVED_SUBSYSTEMS (empty list).
- Updated `devtest/all-test-commands.md`: added API server, distributed, marketplace, monitoring, self-improving, multimodal, federation, desktop UI test commands.
- Total test count: 380+ passing.

## [unreleased] Phase 7: Production Hardening — Plan & Preparation

- Created `PHASE7_PLAN.md` at repo root with 6 logical implementation slices (Event Foundation, Runtime Engine, Artifacts & Protocols, Boundaries & Loading, Safety & Privacy, Advanced Routing & Resume).
- Defined 17 deliverables, 6 exit gates, 12 new source files, 16 modified files, ~34 new tests.
- Updated `scripts/roadmap-check.py`:
  - Added Phase 7 phase lock configuration (all subsystems unlocked for hardening).
  - Added `check_import_boundaries()`: AST-based enforcement that `interfaces/` MUST import only from `core.public_api`.
  - Script now detects 20 architectural boundary violations across `interfaces/api_server/`, `interfaces/cli/`, `interfaces/web_ui/`.
- Updated `devtest/all-test-commands.md`:
  - Architecture check command now uses `--phase 7`.
  - Added Phase 7 test command reference with all 24 new test modules.
- Updated `devtest/run-devtest.ps1`:
  - Added `phase7` mode to `[ValidateSet]`.
  - Added `phase7` switch case running all Phase 7 test modules.


## [unreleased] Phase 7 — Slice 1: Event Foundation

- Created `core/events.py`:
  - `EventType` enum with 24 canonical event types covering run lifecycle, phase/workflow, agent/model, tool/safety, budget/resource, retry/error, artifact/context, state/memory.
  - `Event` dataclass (frozen, slots) with `event_id` (UUID4), `sequence` (monotonic int), `timestamp` (UTC), `event_type`, `run_id`, `step_id`, `agent_id`, `tool_id`, `phase`, `payload`, `metadata`, `parent_event_id`, `previous_hash`.
  - Deterministic `to_json()` (sorted keys, compact separators) for hash stability.
  - `compute_hash()` returns SHA-256 of canonical JSON **excluding** `previous_hash` to avoid circular dependency.
  - `from_dict()`, `from_json()`, `create()` factory for deserialization and construction.
- Rewrote `core/ledger.py` — `RunLedger` upgraded from thin file-writing helper to production-grade event-sourced ledger:
  - **Unified ledger**: `emit_event()` appends structured `Event` records to `ledger.jsonl` with automatic sequence numbering and thread safety (`threading.Lock`).
  - **Hash chain**: Each event stores `previous_hash` linking to the prior event. `verify_chain()` validates both event-to-event linkage AND hash file consistency. Tampering with either `ledger.jsonl` or `ledger.hash` is detected.
  - **Indexing**: In-memory index by `event_type`, `phase`, `agent_id`, `tool_id`, `step_id`. `query_index()` supports single-dimension and combined (intersection) queries. Index persists to `ledger.index` on checkpoint and reloads on resume.
  - **Checkpoints**: `save_checkpoint(state, sequence_num)` writes to `checkpoints/NNNNNNNN.json`. `load_last_checkpoint()` returns most recent state. `list_checkpoints()` returns sorted list.
  - **Resume support**: `create()` detects existing `ledger.jsonl` and restores `_sequence` via `_restore_sequence_from_ledger()` so resumed runs continue correct numbering.
  - **Backward compatibility**: All pre-Phase 7 methods (`write_json`, `write_text`, `append_jsonl`) unchanged. Legacy `tool_calls.jsonl` and `state_transitions.jsonl` still created on run init.
- Added 57 tests:
  - `tests/test_events.py` (11 tests): event type uniqueness, count, serialization round-trip, hash determinism, hash excludes previous_hash, factory behavior.
  - `tests/test_ledger_hash.py` (10 tests): empty/single/chain verification, tampered event detection, tampered hash file detection, first event previous_hash, linkage, hash file matching.
  - `tests/test_ledger_index.py` (12 tests): query by all 5 dimensions, combined filters, no-match, empty ledger, string event_type, index persistence/load, incremental updates.
  - `tests/test_ledger_checkpoints.py` (9 tests): save/load/list, timestamp inclusion, checkpoint dir creation, sequence restore, multiple run isolation.
  - `tests/core/test_ledger.py` (15 tests, 6 legacy + 5 new): backward compat for all legacy methods + unified ledger integration (emit creates files, increments sequence, legacy+unified coexist).
- Updated `devtest/` files:
  - `all-test-commands.md`: Added "Slice 1: Event Foundation" section.
  - `run-devtest.ps1`: Added Slice 1 test paths to `broad` mode.
- Full test suite: **468 passed, 2 skipped** (+50 from Slice 1).


## [unreleased] Phase 7 — Slice 2: Runtime Engine

- Created `core/error_classification.py`:
  - `ErrorCategory` enum with 6 canonical categories: TRANSIENT, RECOVERABLE, VERIFICATION, CONFIGURATION, PERMISSION, FATAL.
  - `classify_error()` walks the exception MRO to assign the most specific category.
  - Strategy helpers: `should_retry()`, `should_halt()`, `max_retries_for()`, `backoff_for()`, `error_summary()`.
- Created `core/retry_engine.py`:
  - `RetryEngine` class executes callables with bounded retry and exponential backoff.
  - Integrates with error classification: TRANSIENT/RECOVERABLE/VERIFICATION → retry; CONFIGURATION/PERMISSION/FATAL → immediate halt.
  - Emits `RETRY_ATTEMPTED` and `RETRY_EXHAUSTED` events to ledger.
  - `execute_with_budget()` variant checks a budget predicate before every attempt.
- Created `core/step_budget.py`:
  - `BudgetSnapshot` and `BudgetLimits` dataclasses for tracking consumption and defining ceilings.
  - `StepBudgetEnforcer` tracks cumulative tokens, time, tool_calls, agent_invocations per run.
  - `check_budget()` validates all limits before every operation; raises `BudgetExceededError` with structured info.
  - `record_tokens()`, `record_tool_call()`, `record_agent_invocation()` increment counters and enforce `>=` semantics.
  - Emits `BUDGET_CHECKED` on every check and `BUDGET_EXCEEDED` when any limit hit.
- Created `core/workflow_runner.py`:
  - `WorkflowRunner` — production DAG execution engine replacing the sequential `for` loop in `workflows/base.py`.
  - Executes `ExecutionDAG.parallel_groups()` in topological order.
  - **Parallel execution**: groups where all steps have `parallel_safe=True` run concurrently via `ThreadPoolExecutor` (configurable `max_workers`).
  - **Workspace isolation**: per-step workspace dirs created under `run_dir/workspaces/{step_id}/` when `workspace_isolation=True`.
  - **Retry integration**: `step.max_iterations` drives retry count; errors are classified and retried by `RetryEngine`.
  - **Budget enforcement**: `StepBudgetEnforcer` checks budget before each step; `BudgetExceededError` returns failed `StepResult` instead of crashing the run.
  - **Event emission**: emits `RUN_INITIATED`, `PHASE_TRANSITION`, `AGENT_INVOKED`, `STATE_TRANSITION`, `RUN_COMPLETED`, `RUN_FAILED`.
  - **WorkingMemory**: creates and flushes ephemeral working memory at run boundaries.
  - **Graceful error handling**: catches exceptions in `execute_step`, classifies them, and either retries, returns a failed result, or halts the run.
- Refactored `workflows/base.py`:
  - `Workflow.run()` now delegates to `WorkflowRunner.run()` via lazy import (avoids circular dependency).
  - All legacy behavior preserved: `WorkingMemory` creation, `StepContext` construction, condition evaluation, lifecycle hooks.
- Added 84 tests:
  - `tests/test_error_classification.py` (22 tests): classify all exception types, retry/halt strategies, config defaults, summary structure.
  - `tests/test_retry_engine.py` (10 tests): success, retry-then-success, exhausted, no-retry for fatal/config, explicit category override, ledger events, budget checker.
  - `tests/test_step_budget.py` (12 tests): snapshot/limits, within/over budget for all dimensions, events emitted, snapshot method.
  - `tests/test_workflow_runner.py` (17 tests): sequential execution, events, conditions, halt on failure, retry success/exhausted, workspace isolation, working memory flush, budget enforcement, DAG missing.
  - `tests/test_workflow_runner_parallel.py` (9 tests): concurrent execution, mixed groups, dependency ordering, single step, sequential fallback, parallel failure handling, event attribution.
- Updated `devtest/` files:
  - `all-test-commands.md`: Added Slice 2 section.
  - `run-devtest.ps1`: Added Slice 2 test paths to `broad` mode.
- Full test suite: **552 passed, 2 skipped** (+84 from Slice 2).


## [unreleased] Phase 7 — Slice 3: Artifacts & Protocols

- Created `core/agent_protocol.py`:
  - `AgentMessage` (frozen dataclass): `role`, `content`, `metadata` — aligns with standard LLM APIs.
  - `AgentRequest`: `agent_id`, `messages`, `tools`, `context`.
  - `AgentResponse`: `content`, `tool_calls`, `usage`, `finish_reason`.
  - `AgentContext`: `run_id`, `step_id`, `repo_root`, `tools`, `policy`, `ledger`, `working_memory`, `prior_results`. Includes `to_dict()` for serialization and `from_step_context()` factory to build from `StepContext`.
- Created `core/artifact_store.py`:
  - `ArtifactSpec` dataclass defining each artifact's name, required status, and validator.
  - Canonical `RUN_ARTIFACTS` list of 15 artifacts: run.json, config.redacted.json, plan.md, context_bundle.md, context_manifest.json, ledger.jsonl, ledger.index, ledger.hash, timeline.jsonl, tool_calls.jsonl, policy_decisions.jsonl, patch.diff, verification.json, final_report.md, checkpoints/.
  - `ArtifactStore` class: `create_run()` initializes directory with generic artifacts (`run.json`, `config.redacted.json`). `validate_completeness()` checks all required artifacts exist and pass schema validation (JSON/JSONL). `is_complete()` / `list_artifacts()` for status queries. Producer methods for workflow artifacts: `produce_context_artifacts()`, `produce_plan()`, `produce_final_report()`, `produce_verification()`, `produce_patch()`.
- Created `core/context_packer.py`:
  - `ContextPacker` class: `pack(repo_root, run_config, tool_registry) → (bundle_md, manifest)`.
  - Scans repository via `inspect_repository()`, sorts files by relevance (docs/config first, then code), excludes binaries and build artifacts.
  - Respects configurable token budget using `chars_per_token` heuristic (default 4 chars/token, 128k tokens).
  - Redacts secrets via `redact_text()` before inclusion.
  - Produces `ContextManifest` with per-file metadata: path, size, language, summary, included/excluded status.
- Created `core/public_api.py`:
  - Stable facade: the ONLY module interfaces may import from `core/`.
  - Exports 40+ symbols across events, ledger, error/retry, budget, tools, models, policy, capabilities, workflow runtime, agent protocol, artifacts, context, redaction, schemas.
  - `__all__` explicitly lists every export; no module objects leaked.
- Added 41 tests:
  - `tests/test_artifact_store.py` (13 tests): create run, run.json, config redaction, completeness validation, invalid JSON/JSONL detection, missing checkpoints, all producer methods, artifact count.
  - `tests/test_context_packer.py` (12 tests): bundle generation, secret redaction, budget respect, file prioritization, manifest serialization, tools section, config section, binary/venv exclusion, language detection.
  - `tests/test_agent_protocol.py` (9 tests): message/request/response/context defaults, frozen messages, to_dict serialization, from_step_context factory.
  - `tests/test_public_api.py` (7 tests): all expected symbols exist, no internal modules exposed, __all__ coverage, import safety (no provider loading), AST verification of re-exports.
- Updated `devtest/` files:
  - `all-test-commands.md`: Added Slice 3 section.
  - `run-devtest.ps1`: Added Slice 3 test paths to `broad` mode.
- Full test suite: **593 passed, 2 skipped** (+41 from Slice 3).


## [unreleased] Phase 7 — Recovery, Boundary Cleanup, and Prerelease Validation

- Fixed `core/cascading_router.py` health TTL expiration and healthy-candidate selection so fallback/routing behavior is deterministic under test and resume validation.
- Hardened `scripts/roadmap-check.py`:
  - ignores docstring/string-literal false positives in core keyword scans,
  - adds explicit workflow-facing `core.public_api` boundary enforcement alongside interface enforcement.
- Removed workflow import-time registration side effects; added explicit builtin registration entrypoint in `workflows/registry.py`.
- Migrated workflow-facing modules and runtimes from direct `core.*` imports to `core.public_api`, and expanded `core/public_api.py` with the workflow-facing runtime symbols still required by shipped workflow packs.
- Upgraded CLI resume path in `interfaces/cli/cli.py` from run JSON dump to actual workflow-runner resume for ledger-backed workflow executions.
- Synced release/devtest assets:
  - added `tests/test_workflow_isolation.py`,
  - updated `devtest/run-devtest.ps1` Phase 7/broad coverage and non-interactive `-NoPrompt` mode,
  - updated `devtest/all-test-commands.md`,
  - refreshed README Phase/Test status,
  - added root forensic report `PHASE7_AUDIT.md`.
- Validation:
  - `python scripts/roadmap-check.py --phase 7 --ci` passed,
  - `devtest` phase7/broad/full modes passed,
  - final `pytest -q` passed with **692 passed, 3 skipped**.

## [unreleased] AICtx Integration (M2.5–M9)

- **M2.5**: Expanded `ContextOps` ABC with `init()`, `clean()`, `run_pipeline()`, `public_docs_update()`. Enriched `WriteReport` with timing/entropy/run_report.
- **M3**: Added `agentheim ctx` CLI (8 commands), `/api/ctx/*` API routes, `context-maintainer` workflow pack + preset, `ContextRunLedger` helper, 9 new `EventType`s.
- **M4**: Made coding/docs/research workflows context-aware via AICtx pipeline. `WorkflowRunner` gained `stale_context_check` param and `context_fresh`/`context_stale` step conditions.
- **M5**: Added public-docs impact preflight to docs-maintenance workflow. Review-first update path — patches generated to artifact store, never auto-applied.
- **M6**: Migrated transient paths from `.aictx/runs/` → `.ai-team/runs/`. Created `LegacyAictxReader` for backward compatibility.
- **M7**: Built `AgentheimToAictxAdapter` bridging Agentheim `ModelProvider` ↔ AICtx `ModelProvider`. Replaced `providers/oci_genai.py` stub with bridge to AICtx OCI provider.
- **M8**: Added `agentheim ctx oci <doctor|snapshot|bundle>` commands. `agentheim doctor --oci` and `/api/health/oci` endpoint. `ArtifactStore.produce_snapshot()` method.
- **M9**: Removed legacy `build_context_pack` fallback from all workflows. Deprecated `ContextPacker`/`ContextManifest`/`build_context_pack` in `core.public_api` (emits `DeprecationWarning`). Final docs sweep.
- Validation: `pytest -q` passed with **785 collected, 3 skipped** (audited by external validation run).
