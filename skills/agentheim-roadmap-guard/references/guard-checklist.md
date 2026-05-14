# Governance Guard Checklist

Run this checklist before finalizing substantial changes.

## 1. Directive Integrity

- run `python scripts/check-agent-instructions.py`
- confirm `.github/instructions/*.md` are non-empty
- confirm canonical `02-forbidden-behaviors.md` exists
- confirm the main autonomous engineer agent references required instructions

## 2. Static Boundary Audit

- no provider imports introduced into `core/`
- no preset/workflow identifiers hardcoded into generic runtime paths
- no AICtx implementation details introduced into `core/`
- no policy bypass shortcuts in tool execution paths

## 3. Runtime Risk Audit

- verify retry limits and error classification are still coherent
- verify ledger/events remain durable and queryable
- verify approval workflow still gates risky operations
- verify provider wiring still flows through Agentheim provider abstractions

## 4. AICtx Hard Boundaries

- AICtx editable install from `../AICtx` is current
- generated context compatibility is preserved or migrated deliberately
- `docs/AIprojectcontext/**` and `context.lock.json` behavior is tested if touched

## 5. Documentation Sync

- update stale active docs in the same patch
- keep historical `docs/CHANGELOG.md` references intact
- run directive checks after docs or instruction edits
