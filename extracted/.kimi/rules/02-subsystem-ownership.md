# SUBSYSTEM OWNERSHIP — KNOW YOUR BOUNDARIES

## Ownership Map

| Directory | Owner | I may modify? |
|-----------|-------|---------------|
| `core/` | Runtime Team | Only if assigned to runtime work |
| `providers/<name>/` | Provider Team | Only if assigned to provider work |
| `tools/<category>/` | Tool Team | Only if assigned to tool work |
| `workflows/<name>/` | Workflow Team | Only if assigned to workflow work |
| `memory/` | Memory Team | Only if assigned to memory work |
| `interfaces/cli/` | Interface Team | Only if assigned to CLI work |
| `interfaces/guided_tui/` | Interface Team | Phase 5 only |
| `presets/` | Product Team | Only if assigned to preset work |
| `config/` | Platform Team | Only if assigned to config work |
| `tests/` | Quality Team | Only if assigned to test work |
| `docs/roadmap/` | Architecture Lead | NEVER without explicit approval |
| `scripts/` | Platform Team | Only if assigned to script work |

## Cross-Boundary Rule
If a task requires modifying files in TWO OR MORE subsystems, I MUST:
1. Stop and identify the cross-boundary nature
2. Ask for Architecture Lead approval before proceeding
3. Create an RFC document describing the cross-boundary impact
4. Get approval from ALL affected subsystem owners

## Forbidden Edits (Always)
- `docs/roadmap/` — these files are FROZEN during active development
- Files in LOCKED subsystems (see 01-phase-lock.md)
- Files outside my assigned subsystem without approval
- CI/CD configuration without Platform Team approval

## Approval Chain
| Change Type | Required Approver |
|-------------|-------------------|
| Within my subsystem | Myself (primary owner) |
| Cross-boundary | Architecture Lead + affected owners |
| Core changes | Architecture Lead |
| Phase advancement | Architecture Lead (all gates must pass) |
| Roadmap changes | Architecture Lead + full team review |
