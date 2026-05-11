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

## M0 Architecture Freeze

### Goal

Define the integration contract before code movement begins.

### Backlog

- Write an ADR defining canonical runtime ownership and subsystem boundaries.
- Decide the canonical transient artifact location (`.ai-team/` vs `.aictx/`).
- Define compatibility guarantees for `AGENTS.md`, `docs/AIprojectcontext/**`, and `context.lock.json`.
- Define deprecation policy for the standalone AICtx CLI.
- Record integration risks, ownership, and success criteria.

### Deliverables

- Approved ADR
- target module map
- compatibility contract
- deprecation policy
- definition of done for “fully integrated”

### Test Gates

- Architecture review sign-off
- explicit decision on transient state ownership
- explicit decision on whether standalone `aictx` remains as a compatibility CLI

---

## M1 Source Import And Boundary

### Goal

Bring AICtx into Agentheim without losing history or collapsing boundaries.

### Backlog

- Import AICtx into a bounded namespace with preserved history.
- Separate AICtx domain modules from shell modules.
- Define an internal `ContextOps` service interface for Agentheim.
- Document which AICtx modules are preserved, adapted, or replaced.

### Deliverables

- imported subtree or filtered-history merge
- initial `ContextOps` API contract
- dependency map of reused vs replaced AICtx modules

### Test Gates

- repository still builds/imports cleanly
- no namespace collisions
- existing Agentheim tests still pass for untouched subsystems

---

## M2 Local Context Domain Integration

### Goal

Expose AICtx core behavior through Agentheim internals.

### Backlog

- Adapt AICtx scanner, planner, writer, verifier, and public-doc logic behind `ContextOps`.
- Keep committed output compatibility.
- Map context outputs into Agentheim artifact/report conventions.
- Add support for baseline/init, scan, generate, verify, status, and public-doc review operations.

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

## M3 Workflow And Preset Exposure

### Goal

Make the integrated context system usable from Agentheim surfaces.

### Backlog

- Add a `context-maintainer` workflow pack.
- Add a matching preset.
- Add CLI/API/web entrypoints for context operations.
- Emit Agentheim ledgers and artifacts around context runs.

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

## M4 Context-Aware Workflow Adoption

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

## M5 Public Docs And Change Impact Integration

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

## M6 Runtime And Storage Convergence

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

---

## M7 Provider And Execution Unification

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

---

## M8 OCI And Remote Backend Adoption

### Goal

Adopt AICtx remote execution as an optional Agentheim backend, not as a separate operating model.

### Backlog

- Wrap AICtx snapshot/export and OCI execution behind Agentheim execution interfaces.
- Keep patch-first semantics.
- Surface OCI readiness checks through Agentheim diagnostics.
- Rehydrate remote results into local ledgers and artifacts.

### Deliverables

- optional remote context backend
- snapshot artifact support
- OCI readiness diagnostics

### Test Gates

- local-only environments still work without OCI configured
- OCI-disabled tests skip cleanly
- snapshot integrity verified
- remote results rehydrate into local report/ledger structure

---

## M9 Compatibility And Decommissioning

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

## First 10 Implementation Tickets

1. Write the integration ADR.
2. Import AICtx with preserved history into a bounded namespace.
3. Define the `ContextOps` service contract.
4. Adapt lockfile read/write behind `ContextOps`.
5. Adapt verifier logic behind `ContextOps`.
6. Adapt deterministic context generation behind `ContextOps`.
7. Add golden tests for lockfile and generated context artifacts.
8. Create the `context-maintainer` workflow pack.
9. Add CLI/API/web entrypoints for context operations.
10. Add one end-to-end context run test with ledger and artifact assertions.

---

## Definition Of Fully Integrated

The integration is complete only when all of the following are true:

- a user can complete the AICtx lifecycle through Agentheim surfaces
- Agentheim workflows can consume and trust lockfile-backed context artifacts
- there is one canonical transient runtime store
- public-doc freshness gates run through Agentheim
- the standalone AICtx CLI is optional rather than required
- optional remote execution features are Agentheim capabilities, not a parallel platform
