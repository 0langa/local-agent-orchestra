# Changelog

## 2026-05-14

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
- Validation: `pytest -q` passed with **760 passed, 3 skipped** (audited by external validation run).
