---
name: agentheim-boundary-guard
description: >
  Enforce Agentheim architectural boundaries before edits. Checks proposed changes
  against the Seven Immutable Laws, Forbidden Behaviors levels, and Stop Conditions.
  Use when planning or reviewing code changes in the Agentheim repository, before
  committing, or when asked to verify architectural compliance. Auto-triggers when
  core/, workflows/, providers/, tools/, or interfaces/ files are modified.
---

# Agentheim Boundary Guard

Prevent architectural breaches by validating changes against binding rules before editing.

## When to Run

- Before planning any code change
- Before committing (especially if core/ touched)
- When user says "review this for boundaries", "check compliance", "does this violate"
- When diff touches multiple subsystems

## Workflow

### 1. Load Rules

Read `references/laws.md` for full Seven Immutable Laws, Forbidden Behaviors, and Stop Conditions.

### 2. Scan Proposed Change

For each file in the change set, check:

**core/ touched?**
- Any concrete provider name imported? → Law 1 violation
- Any concrete workflow referenced? → Law 1 violation
- Any tool implementation imported directly? → Law 1 violation
- Any AICtx-specific logic? → Law 1 violation
- Hidden mutable global state added? → Level 3 breach
- Second registry/ledger/policy path created? → Level 3 breach

**workflows/ touched?**
- Direct provider import? → Law 2 violation
- Core state mutated directly? → Law 2 violation
- Policy engine bypassed? → Law 2 violation
- Pack registered in capability registry? If not → Level 2 breach
- Smoke tests added? If not → Level 2 breach

**providers/ touched?**
- Lazy-loading via importlib? If not → Law 3 violation
- Capability coverage in tests? If not → Level 2 breach

**tools/ touched?**
- Risk level declared? If not → Level 3 breach
- Policy engine path used? If direct execution → Level 3 breach

**interfaces/ touched?**
- Docs updated (USER_GUIDE.md, API_REFERENCE.md)? If not → Level 3 breach
- Tests updated? If not → Level 3 breach

**Event schemas touched?**
- Migration plan documented? If not → Level 2 breach

**Artifact layout touched?**
- Docs, tests, consumers updated? If not → Level 2 breach

**Multiple subsystems touched?**
- Cross-boundary impact explained? If not → Level 2 breach

**AICtx/ vendor touched?**
- Changes routed through ContextOps boundary? If not → Level 4 violation
- Committed to git? If AICtx/ is gitignored → Level 4 violation

### 3. Report Findings

If violations found:
- Cite exact law/level and file
- Explain smallest viable path forward
- Stop and ask for direction if Level 4 or Stop Condition triggered

If clean:
- Confirm compliance in one line
- Proceed with edit

## Severity Quick Reference

| Level | Action |
|-------|--------|
| Level 4 (Constitutional) | **STOP**. Ask user for direction. Do not proceed. |
| Level 3 (Architectural) | **Block commit**. Fix before proceeding. |
| Level 2 (Boundary) | **Flag**. Explain impact, suggest updates, proceed with caution. |
