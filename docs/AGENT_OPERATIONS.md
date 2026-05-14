# Agent Operations

This document explains how agents should operate in Agentheim. Binding rules live in `.github/instructions/`; this file provides rationale, workflow guidance, and examples.

## Directive System

Agentheim uses a layered directive system:

- `AGENTS.md` is the GitHub-facing entry point.
- `.github/agents/agentheim-autonomous-engineer.agent.md` is the main autonomous engineering agent.
- `.github/instructions/*.md` contains binding project rules.
- `skills/` contains task-specific operational helpers.
- `docs/` contains human-readable project documentation.
- `devtest/` contains local validation command references.
- `docs/SUPPORT_MATRIX.md` records stable, beta, experimental, and internal support states.
- `docs/TIER1_CONTRACTS.md` maps baseline user journeys to CLI/API/docs/tests.

Agents must read `.github/instructions/README.md` and every binding instruction file before planning or editing.

## Instruction Priority

The active priority order is:

1. current user request
2. repository `AGENTS.md`
3. `.github/instructions/*.md`
4. `.github/agents/*.agent.md`
5. repository docs
6. skills

If a conflict appears, the agent must stop, cite the conflicting files or rules, and ask for direction.

## Documentation Enforcement

Documentation is part of the implementation. If behavior, commands, paths, configuration, CI, safety, workflow registration, or integration rules change, update the affected docs in the same change.

Historical entries in `docs/CHANGELOG.md` are exempt from stale-link cleanup because they preserve repository history.

## AICtx Workspace Project

AICtx lives in the co-developed workspace project at `../AICtx` and is installed as an editable package (`pip install -e ../AICtx`).

Agents may inspect `../AICtx/src/aictx/` for parity and implementation details, but must route all integration through the ContextOps boundary.

## Validation

For directive, docs, GitHub template, or skill changes, run:

```powershell
python scripts/check-agent-instructions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
```

For runtime code changes, combine directive checks with focused pytest or devtest modes that match the risk surface.

For roadmap-entry baseline checks, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt
```

`scripts/roadmap-check.py` and `phase7` devtest mode are legacy validation paths. Use them only for roadmap-era investigation or explicit user requests.

## Future MCP

MCP support should follow the same governance model:

- MCP instructions belong in `.github/instructions/` when binding.
- MCP usage examples belong in docs.
- MCP validation commands belong in `devtest/`.
- MCP tools must still respect Agentheim policy, approval, privacy, redaction, and traceability rules.
