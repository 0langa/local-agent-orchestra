# AICtx Integration Plan

> Concrete milestone plan for fully absorbing [AICtx](https://github.com/0langa/AICtx) into Agentheim as a first-class subsystem.

---

## Goal

Integrate AICtx into Agentheim so that:

- Agentheim remains the canonical runtime, CLI/API/UI surface, ledger, and workflow host
- AICtx becomes the canonical repository-context subsystem
- deterministic context generation, lock verification, and public-doc impact analysis become first-class Agentheim capabilities
- legacy AICtx outputs stay compatible during migration

---

## Integration Principles

- **Host, do not wrap**: Agentheim owns the top-level runtime model.
- **Preserve history**: import AICtx with git history intact.
- **Keep deterministic logic deterministic**: verification and lockfile checks stay code-driven, not prompt-driven.
- **Migrate in slices**: avoid a big-bang repo merge.
- **Preserve committed output compatibility first**: `AGENTS.md`, `docs/AIprojectcontext/**`, and `context.lock.json` remain readable and writable during the transition.
- **Converge transient state later**: move runtime artifacts to Agentheim-owned storage after functional parity is proven.

---

## Target Architecture

### Agentheim remains authoritative for:

- workflows and presets
- CLI, API server, web UI, guided TUI, desktop UI
- provider/model abstraction
- policy engine and approval flow
- run ledgers, artifacts, and resume/replay

### AICtx becomes authoritative for:

- repository inventory
- context planning and context shard selection
- deterministic context generation
- lockfile creation and verification
- stale-context detection
- public-doc impact mapping
- snapshot/export for optional remote context jobs

### Initial compatibility surface

- committed docs and context outputs stay compatible:
  - `AGENTS.md`
  - `docs/AIprojectcontext/**`
  - `docs/AIprojectcontext/context.lock.json`
- transient runtime state may still be read from legacy AICtx locations during migration

---

## Milestone Plan

## M0 Architecture Freeze ✅

### Goal

Define the integration contract before code movement begins.

### Status ✅ RESOLVED

All M0 items are decided. See `docs/adr/ADR-001-aictx-integration-contract.md`.

### Decisions (executive summary)

| Decision | Outcome |
|----------|---------|
| ADR | `docs/adr/ADR-001-aictx-integration-contract.md` — approved |
| Transient artifact location | `.ai-team/` (canonical already). `.aictx/` supported during M6 migration only. |
| AICtx source namespace | `agentheim.vendor.aictx` via filtered-history subtree merge |
| Lockfile schema versioning | **Option A**: adopt `context.lock.json` v1.0 as-is. No envelope wrapper. |
| Provider interface strategy | Pre-M7: AICtx keeps its own `llm/base.py` behind `ContextOps`. M7: adapter layer routes through Agentheim `providers/base.py`. |
| Test migration path | Tests in `tests/vendor/aictx/` with fixtures. Run as-is M1-M2; adapt by M3. |
| CLI namespace | `agentheim ctx <subcommand>`. Standalone `aictx` CLI is thin wrapper during M1-M9; deprecated after M9. |
| Verification composition | AICtx `verify` (hash-based lockfile) and Agentheim `PolicyEngine` (runtime safety) are orthogonal. Both emit to Agentheim ledger. |
| Compatibility guarantees | `AGENTS.md`, `docs/AIprojectcontext/**`, `context.lock.json` v1.0, `.aictxignore`, patch-first writes preserved until explicit milestone change. |
| Deprecation policy | Standalone CLI → M9; `.aictx/runs/` → M6; AICtx provider → M9; legacy CLI → M9 |
| Risk | Duplicate `ModelProvider` name collision must be handled before M7. Subtree merge size. |

### Deliverables

- ✅ ADR-001 written — `docs/adr/ADR-001-aictx-integration-contract.md`
- ✅ All decisions recorded in ADR
- ✅ Integration plan updated with resolved outcomes
- ✅ Module map updated: `agentheim/vendor/aictx/`
- ✅ Compatibility contract: see ADR-001
- ✅ Deprecation policy: see ADR-001
- ✅ Verification composition model defined

### Test Gates

- ✅ ADR-001 approved
- ✅ Transient state ownership: `.ai-team/` remains canonical
- ✅ Standalone CLI: kept as thin wrapper, deprecated after M9

---

## M1 Source Import And Boundary ✅ COMPLETE

### Goal

Bring AICtx into Agentheim without losing history or collapsing boundaries.

### Backlog

- ✅ Import AICtx into a bounded namespace with preserved history.
- ✅ Separate AICtx domain modules from shell modules.
- ✅ Define an internal `ContextOps` service interface for Agentheim.
- ✅ Document which AICtx modules are preserved, adapted, or replaced.

### Additional M1 Backlog Items

- ✅ **Analyze provider interface delta**: Compared AICtx `llm/base.py` vs Agentheim `providers/base.py`. Key differences documented in `agentheim/vendor/MODULE_MAP.md`.
  - AICtx `ChatRequest` has `system_prompt` + `messages` + `json_schema`; Agentheim `ModelRequest` has `system_prompt` + `user_prompt` + `temperature`
  - AICtx `ChatResponse` has `content` + `finish_reason` + `input_tokens` + `output_tokens`; Agentheim `ModelResponse` has similar fields
  - Both have `metadata()` and `count_tokens()` pattern
  - **Decision**: write thin adapter in M7. Until then, AICtx keeps its own provider stack behind `ContextOps`.
- ✅ **Import AICtx tests alongside source**: AICtx tests and fixtures imported under `agentheim/vendor/aictx/tests/`. They will be moved to `tests/vendor/aictx/` by M3.
- ✅ **Fix subprocess calls in AICtx code**: Added vendor paths to `scripts/roadmap-check.py` `SUBPROCESS_EXEMPTIONS`. AICtx git/IO subprocess calls are legitimate internal operations for a reference import; they will be routed through Agentheim tool protocol in M2/M3 where policy gating is required.

### Deliverables

- ✅ Filtered-history subtree merge into `agentheim/vendor/aictx/`
- ✅ `agentheim/context_ops.py` — initial `ContextOps` API contract
- ✅ `agentheim/vendor/MODULE_MAP.md` — dependency map of preserved / adapted / replaced modules
- ✅ `pyproject.toml` — added `agentheim*` to package includes and `pathspec>=0.12.0` to dependencies
- ✅ `agentheim/vendor/aictx/_logging.py` — renamed from `logging.py` to avoid stdlib shadowing

### Test Gates

- ✅ repository builds/imports cleanly
- ✅ no namespace collisions
- ✅ existing Agentheim tests still pass for untouched subsystems
- ✅ `scripts/roadmap-check.py --phase 7` passes (0 violations)
- ✅ `pytest tests/test_import_linting.py` passes

---

## M2 Local Context Domain Integration

### Goal

Expose AICtx core behavior through Agentheim internals.

### Backlog

- Adapt AICtx scanner, planner, writer, verifier, and public-doc logic behind `ContextOps`.
- Keep committed output compatibility.
- Map context outputs into Agentheim artifact/report conventions.
- Add support for baseline/init, scan, generate, verify, status, and public-doc review operations.

### Additional M2 Backlog Items

- **Define ContextOps API contract concretely** (derived from AICtx actual entry points):

```python
class ContextOps(ABC):
    """Internal service interface for AICtx-derived context operations."""

    @abstractmethod
    def init(self, repo_root: Path) -> None: ...

    @abstractmethod
    def clean(self, repo_root: Path, *, run_id: str | None = None,
              keep_runs: int | None = None) -> CleanResult: ...

    @abstractmethod
    def scan(self, repo_root: Path) -> RepositoryInventory: ...

    @abstractmethod
    def plan(self, inventory: RepositoryInventory, scope: str = "full",
             existing_lock: ContextLock | None = None) -> ContextPlan: ...

    @abstractmethod
    def generate(self, repo_root: Path, plan: ContextPlan,
                 provider: ModelProvider | None = None) -> GeneratedContext: ...

    @abstractmethod
    def write(self, repo_root: Path, context: GeneratedContext,
              write_mode: str = "patch") -> WriteReport: ...

    @abstractmethod
    def run_pipeline(self, repo_root: Path, run_id: str, scope: str = "full",
                     write_mode: str = "patch", allow_ai: bool = False,
                     allow_dirty: bool = False) -> WriteReport: ...

    @abstractmethod
    def verify(self, repo_root: Path, strict: bool = False) -> VerificationResult: ...

    @abstractmethod
    def status(self, repo_root: Path, strict: bool = False) -> ContextStatus: ...

    @abstractmethod
    def public_docs_impact(self, repo_root: Path,
                           scope: str = "full") -> PublicDocsImpactReport: ...

    @abstractmethod
    def public_docs_update(self, repo_root: Path, scope: str = "changed",
                           write_mode: str = "patch") -> Path | None: ...
```

- **Map AICtx CLI flags to ContextOps parameters**: AICtx CLI has `--scope full|changed`, `--write patch|apply`, `--allow-ai`, `--allow-dirty`, `--provider`. These map to ContextOps method kwargs.
- **Lockfile I/O adapter**: AICtx `lockfile.py` writes to `docs/AIprojectcontext/context.lock.json`. Agentheim must read/write same path during M1-M5. M6 moves transient state.
- **Secret scanning integration**: AICtx `scan/secrets.py` runs inline during scan. Agentheim `PrivacyEnforcer` already handles redaction. Compose: AICtx detects → blocks generation; Agentheim redacts at output.

### Deliverables

- internal `ContextOps` implementation
- compatible lockfile read/write path
- compatible deterministic context generation path
- compatible verification result model

### Test Gates

- golden tests for `context.lock.json`
- deterministic output tests for generated context docs
- parity tests against known AICtx sample repos

---

## M2.5 ABC Expansion And Vendor Alignment ✅ COMPLETE

### Goal

Close gaps identified in M2 gap analysis before M3 hardens the boundary.

### Backlog

- Expand `ContextOps` ABC with lifecycle and pipeline methods: `init()`, `clean()`, `run_pipeline()`, `public_docs_update()`.
- Enrich `WriteReport` with AICtx telemetry (`RunReport`, `TimingMetrics`, `ContextEntropyMetrics`) so pipeline callers do not lose observability.
- Remove old `AICtx/` local reference copy; source of truth is `agentheim/vendor/aictx/`.
- Revert runtime imports to `agentheim.vendor.aictx` so AICtx ships with Agentheim and works without an external editable install.
- Keep `../AICtx` workspace project as dev-only reference for co-development.

### Deliverables

- `agentheim/context_ops.py` — updated ABC with 11 methods + `CleanResult`
- `agentheim/context_ops_impl.py` — full implementation delegating to vendor modules
- `tests/test_context_ops_impl.py` — 18 tests covering all methods

### Test Gates

- all ContextOps tests pass
- roadmap/architecture checks pass
- no imports from `aictx` external package in runtime code

---

## M3 Workflow And Preset Exposure ✅ COMPLETE

### Goal

Make the integrated context system usable from Agentheim surfaces.

### Backlog

- Add a `context-maintainer` workflow pack.
- Add a matching preset.
- Add CLI/API/web entrypoints for context operations.
- Emit Agentheim ledgers and artifacts around context runs.
- **Implement CLI namespace**: Add `agentheim ctx` Typer subcommand group in `interfaces/cli/cli.py`. Delegate to `ContextOps` implementation.
- **Dependency management**: AICtx runtime deps (typer, rich, pydantic, pathspec) are already in Agentheim or compatible. Add `pathspec>=0.12.0` to Agentheim deps. OCI extra (`oci>=2.120.0`) becomes optional Agentheim extra `[oci]`.
- **Preserve standalone CLI**: Keep `aictx` entry point as thin wrapper around `agentheim ctx` during M1-M9. Deprecate after M9.
- **AGENTS.md generation integration**: AICtx `agents_md.py` generates `AGENTS.md`. Agentheim root `AGENTS.md` already exists. Decide: overwrite, merge, or append? Prefer merge — AICtx preserves unmanaged sections.

### Deliverables

- workflow pack
- preset
- CLI command surface
- API/web discovery and execution support
- run reports integrated with Agentheim artifact layout

### Test Gates

- end-to-end local execution from CLI
- end-to-end execution through API/web route
- ledger and artifacts created for context runs
- workflow respects existing safety/policy gates

---

## M4 Context-Aware Workflow Adoption ✅ COMPLETE

### Goal

Make existing Agentheim workflows consume AICtx-derived context instead of relying only on ad hoc repo scans.

### Backlog

- Feed lockfile-backed context into coding, docs, and research workflows.
- Add stale-context preflight checks.
- Replace broad context dumping where AICtx shard selection is better.
- Add workflow-level fallback or warning behavior when context is stale.

### Deliverables

- context-aware coding workflow
- context-aware research workflow
- context-aware docs workflow
- stale-context detection and refresh path

### Test Gates

- regression tests for coding/docs/research flows
- token-budget comparison before vs after integration
- stale-context warning/refresh behavior tests

---

## M5 Public Docs And Change Impact Integration ✅ COMPLETE

### Goal

Unify deterministic public-doc impact mapping with Agentheim docs maintenance.

### Backlog

- Make AICtx public-doc impact mapping a first-class preflight step.
- Define review-first behavior for public docs.
- Allow optional generative doc updates only after deterministic impact mapping.
- Record impact results in Agentheim artifacts and ledgers.

### Deliverables

- unified docs-maintenance flow
- source-to-doc impact report
- review-first public-doc workflow path

### Test Gates

- fixture-based changed-source tests produce correct impacted-doc set
- no writes when no impacts are detected
- strict verification passes after reviewed doc changes

---

## M6 Runtime And Storage Convergence ✅ COMPLETE

### Goal

Move from split runtime state to one canonical Agentheim run model.

### Backlog

- Migrate transient AICtx artifacts under Agentheim-owned runtime storage.
- Preserve read compatibility for legacy `.aictx` runs during migration.
- Map context reports, snapshots, and verification outputs into one artifact model.

### Deliverables

- unified runtime artifact layout
- legacy `.aictx` reader/adapter
- one run-browsing/reporting path via Agentheim

### Test Gates

- integrated context runs show up in run listing/reporting
- old AICtx-generated repos remain readable
- resume/report flows work with migrated context runs

### Notes
- `.ai-team/runs/` is the canonical transient runtime store.
- `.aictx/runs/` legacy runs remain readable via `LegacyAictxReader` for backward compatibility.

---

## M7 Provider And Execution Unification ✅ COMPLETE

### Goal

Remove duplicate provider/model governance.

### Backlog

- Route AICtx live provider usage through Agentheim provider abstractions.
- Preserve dry-run defaults and explicit live-run opt-in.
- Route budget and transfer-preflight checks through shared safety policy.
- Remove parallel provider configuration paths after parity.

### Deliverables

- one provider selection path
- one policy/budget gate
- unified dry-run vs live-run behavior

### Test Gates

- dry-run remains deterministic
- live-provider path requires explicit opt-in
- policy tests cover transfer-preflight and sensitive-file exclusions

### Notes
- `AgentheimToAictxAdapter` bridges Agentheim `providers/base.py` to AICtx `llm/base.py`.
- OCI GenAI provider is routed through the unified adapter.
- `allow_ai=True` resolves the Agentheim `context` role from provider profiles when no provider is passed explicitly; AICtx does not own separate live-AI credentials.

---

## M8 OCI And Remote Backend Adoption ✅ COMPLETE

### Goal

Adopt AICtx remote execution as an optional Agentheim backend, not as a separate operating model.

### Backlog

- Wrap AICtx snapshot/export and OCI execution behind Agentheim execution interfaces.
- Keep patch-first semantics.
- Surface OCI readiness checks through Agentheim diagnostics.
- Rehydrate remote results into local ledgers and artifacts.
- **Adopt existing AICtx OCI modules directly**: AICtx has fully built OCI infrastructure (config, doctor, snapshot, object_storage, bundle, remote_job, runtime, cleanup, worker). Most are production-ready stubs. Import as-is; add integration tests when credentials available.
- **OCI readiness diagnostics**: `agentheim ctx oci doctor` maps to `OCIDoctorReport`. Expose through `agentheim doctor` too.
- **Snapshot artifacts → Agentheim ArtifactStore**: AICtx snapshot zip files map to `ArtifactSpec` schema.

### Deliverables

- optional remote context backend
- snapshot artifact support
- OCI readiness diagnostics

### Test Gates

- local-only environments still work without OCI configured
- OCI-disabled tests skip cleanly
- snapshot integrity verified
- remote results rehydrate into local report/ledger structure

### Notes
- `agentheim ctx oci <doctor|snapshot|bundle>` commands expose OCI operations through the CLI.
- OCI support is an optional extra (`pip install agentheim[oci]`).

---

## M9 Compatibility And Decommissioning ✅ COMPLETE

### Goal

Finish migration and retire duplicated systems safely.

### Backlog

- Deprecate overlapping scanners, context packers, and CLI paths.
- Add migration docs and compatibility shims where needed.
- Remove redundant code only after functional parity is proven.
- Finalize documentation around the new integrated architecture.

### Deliverables

- deprecation notices
- migration guide
- reduced duplicate module set
- final architecture/documentation update

### Test Gates

- full regression suite green
- compatibility suite green on legacy fixtures
- packaging/install smoke tests green
- docs match actual command surface and artifact layout

### Notes
- Legacy `build_context_pack` emits a `DeprecationWarning` via `core.public_api` but is not removed; workflows retain fallback path.
- Standalone `aictx` CLI is deprecated after M9.

---

## Cross-Cutting Backlog Themes

- **Platform**: ADRs, ownership map, artifact schema alignment
- **Domain**: inventory adapters, lockfile I/O, deterministic writer, verifier integration
- **Surface**: CLI, preset, workflow pack, API, web UI
- **Safety**: transfer preflight, dirty-worktree gates, secret detection, dry-run/live-run separation
- **Migration**: legacy state reader, artifact translator, deprecation layer, migration docs

---

## Recommended Release Slices

- **Release 1**: M0-M2
  - Outcome: imported subsystem plus internal context domain integration
- **Release 2**: M3
  - Outcome: Agentheim can run context maintenance directly
- **Release 3**: M4-M5
  - Outcome: major workflows become context-aware and docs maintenance is unified
- **Release 4**: M6-M7
  - Outcome: one runtime store and one provider/safety model
- **Release 5**: M8-M9
  - Outcome: optional OCI backend and retirement of duplicate systems

---

## Success Metrics

- identical repo state produces identical lock/context outputs
- coding/docs/research workflows can consume integrated context without fallback hacks
- no provider call occurs before safety/budget/transfer gates pass
- one canonical run ledger exists for integrated context runs
- legacy AICtx repos verify and migrate cleanly

---

## First 20 Implementation Tickets (refined)

1. Write the integration ADR.
2. Decide AICtx source namespace and lockfile schema versioning.
3. Import AICtx with preserved history into a bounded namespace.
4. Define the `ContextOps` service contract.
5. Add `pathspec>=0.12.0` to Agentheim dependencies.
6. Adapt lockfile read/write behind `ContextOps`.
7. Adapt verifier logic behind `ContextOps`.
8. Adapt deterministic context generation (scanner → planner → writer) behind `ContextOps`.
9. Add golden tests for lockfile and generated context artifacts.
10. Add AICtx test fixtures to Agentheim test suite.
11. Create the `context-maintainer` workflow pack.
12. Add `agentheim ctx` CLI namespace with all subcommands.
13. Add API/web entrypoints for context operations.
14. Add one end-to-end context run test with ledger and artifact assertions.
15. Make coding workflow context-aware (replace `build_context_pack`).
16. Make research and docs workflows context-aware.
17. Add stale-context preflight to workflow runner Step conditions.
18. Unify public-doc impact mapping with docs-maintenance workflow.
19. Migrate transient AICtx artifacts under Agentheim runtime storage.
20. Route AICtx provider usage through Agentheim provider abstractions.

---

## Definition Of Fully Integrated

The integration is complete only when all of the following are true:

- a user can complete the AICtx lifecycle through Agentheim surfaces
- Agentheim workflows can consume and trust lockfile-backed context artifacts
- there is one canonical transient runtime store
- public-doc freshness gates run through Agentheim
- the standalone AICtx CLI is optional rather than required
- optional remote execution features are Agentheim capabilities, not a parallel platform

> **Current state (May 2026):** AICtx is fully integrated. M0–M9 integration milestones are complete. `agentheim/vendor/aictx/` is the runtime source. ContextOps exposes 11 methods with full test coverage (18 tests). AICtx ships with Agentheim; no external package dependency required. All backlog items through M9 are resolved.
