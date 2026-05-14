# AICtx Integration Rules — BINDING

These rules govern all work involving the AICtx project and the planned integration of AICtx capabilities into Agentheim.

## Source Of Truth

- Agentheim is the host platform.
- AICtx is the repository-context subsystem being absorbed.
- `docs/adr/ADR-001-aictx-integration-contract.md` is the integration contract.
- `agentheim/vendor/MODULE_MAP.md` documents current AICtx module ownership and adaptation state.
- `BASELINE-ROADMAP.md` carries future baseline hardening work.
- AICtx is installed as an editable package from the workspace project at `../AICtx`.
- When investigating AICtx internals, inspect the workspace project at `../AICtx/src/aictx/`.

## Integration Direction

Agentheim remains authoritative for:

- CLI, API, web UI, guided TUI, and desktop surfaces
- workflow and preset registration
- provider/model selection and policy governance
- ledgers, run artifacts, resume, replay, and reporting
- safety, privacy, approval, redaction, and path confinement

AICtx remains authoritative, until adapted, for:

- repository inventory
- context planning and shard selection
- deterministic context generation
- `context.lock.json` schema and verification semantics
- stale-context detection
- public-doc impact mapping
- patch-first context and public-doc review behavior
- snapshot/export logic for optional remote execution

## Hard Boundaries

- Do not put AICtx-specific implementation logic in `core/`.
- Do not introduce a parallel provider registry, policy engine, approval path, or ledger system.
- Do not make `.aictx/` the long-term Agentheim runtime store unless the integration plan is explicitly updated.
- Do not treat generated context as arbitrary prose. Lockfiles, hashes, deterministic outputs, and public-doc impact reports are contract artifacts.
- Do not rewrite public docs directly from model output without deterministic impact mapping and review-first behavior.
- Do not send repository snapshots, context bundles, secrets, or source files to remote services before transfer preflight, secret checks, privacy policy, budget checks, and explicit user intent are satisfied.

## Compatibility Commitments

Until a migration explicitly changes them, preserve compatibility for:

- `AGENTS.md`
- `docs/AIprojectcontext/**`
- `docs/AIprojectcontext/context.lock.json`
- `.aictxignore`
- AICtx verification concepts and result meanings
- patch-first write behavior for generated context and public-doc review

If changing any of these contracts, include:

- migration path
- compatibility test fixtures
- docs update
- failure-mode explanation

## Expected Agent Workflow

For AICtx integration tasks:

1. Read this file, `docs/adr/ADR-001-aictx-integration-contract.md`, and `agentheim/vendor/MODULE_MAP.md`.
2. Inspect relevant AICtx source under `../AICtx/src/aictx/`.
3. Map the AICtx concept to the Agentheim owner subsystem before editing.
4. Build or adapt through a clear boundary, such as a future `ContextOps` service.
5. Preserve deterministic verification as code-level logic.
6. Add parity or golden tests for lockfiles, generated context, impact maps, and migration behavior.
7. Update Agentheim docs and devtest guidance in the same change.

## Local Reference Commands

Run AICtx commands only when needed and only against explicit project paths. Prefer read-only or patch-producing modes during investigation.

Reference commands from the AICtx workspace project:

```powershell
cd ../AICtx
uv run aictx scan --project .
uv run aictx verify --project . --strict
uv run aictx status --project . --strict --json
uv run aictx run --project . --mode setup-context --execution local --scope full --write patch
uv run aictx public-docs update --project . --scope changed --write patch
```

Do not run OCI, upload, publish, cleanup, or destructive remote commands unless the user explicitly asks and credentials/safety gates are understood.

## Acceptance Standard

AICtx integration work is not complete unless:

- Agentheim remains the visible user-facing runtime.
- deterministic context behavior is covered by tests.
- generated context and lockfile compatibility is preserved or migrated deliberately.
- docs describe actual behavior, not planned behavior.
- safety, provider, policy, and ledger concerns flow through Agentheim systems.
- AICtx editable install (`pip install -e ../AICtx`) is current and verified.
