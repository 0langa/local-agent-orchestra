---
name: agentheim-devtest-runner
description: >
  Run the Agentheim devtest runner with the correct mode for the change type.
  Wraps devtest/run-devtest.ps1 and interprets PowerShell output. Use when
  validating changes, before committing, or when user says "run devtest",
  "run tests", or "validate". Auto-triggers when validating Agentheim changes
  or interpreting test results.
---

# Agentheim DevTest Runner

Run targeted validation via `devtest/run-devtest.ps1` instead of full pytest suite.

## Modes

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode <mode> [-NoPrompt]
```

| Mode | When to Use | What It Runs |
|------|-------------|--------------|
| `narrow` | Quick sanity, single file changed | Focused subset (~30s) |
| `targeted` | Feature area changed, medium confidence | Specific test areas (~60s) |
| `directive` | Docs/instructions changed | Docs, GitHub instructions, governance checks |
| `phase7` | Pre-release hardening | Legacy roadmap-era production gates |
| `broad` | Cross-cutting change | Functional + memory suites (~90s) |
| `full` | Pre-release or big refactor | Complete validation (~120s) |

## Mode Selection Guide

### Changed one file in core/
```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode narrow
```

### Changed workflow or preset
```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted
```

### Changed docs or instructions
```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
```

### Pre-commit on feature branch
```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode broad -NoPrompt
```

### Pre-release validation
```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -NoPrompt
```

## Filtering

```powershell
# By keyword
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted -K registry

# Exclude slow tests
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode full -K "not slow" -NoPrompt
```

## Output Interpretation

- **PASS**: All gates cleared. Safe to commit.
- **FAIL with test errors**: Fix tests before commit.
- **FAIL with directive errors**: Run `python scripts/check-agent-instructions.py` and fix.
- **FAIL with lint errors**: Run `ruff check .` and `ruff format .` then retry.

## When Not to Use DevTest

- E2E browser tests: use `pytest tests/test_browser_e2e.py -m e2e` directly
- Single test debug: use `pytest tests/core/test_specific.py -v` directly
- Coverage report: use `pytest --cov` directly
