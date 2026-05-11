# Changelog

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
- Fixed CI workflow `.github/workflows/architecture.yml` to use `pip install -e ".[dev]"` ensuring all dependencies and the package itself are installed.

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
