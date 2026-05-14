# Tooling And Verification — BINDING

Use the smallest validation set that covers the risk surface, then report exactly what ran.

## Canonical Commands

Directive and documentation governance:

```powershell
python scripts/check-agent-instructions.py
```

Repo-local CLI smoke:

```powershell
python -m interfaces.cli.cli --help
python -m interfaces.cli.cli doctor --skip-connectivity
```

Targeted devtest:

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode targeted
```

Directive devtest:

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
```

## Roadmap Checker Status

`scripts/roadmap-check.py` and `phase7` devtest mode are legacy validation paths. Do not use them as default completion gates for new directive-system work. Use them only when investigating historical phase-gate behavior or when a user explicitly asks.

## AI Live Connectivity Rule

`devtest/ai_test.ps1` may run at most two consecutive times for one validation attempt. Each run must have a hard 120-second timeout. If the second attempt fails, stop retrying and report the failure.

## Reporting

Final handoffs must say:

- which checks ran
- whether they passed or failed
- whether skipped checks were unnecessary, too broad for the change, or blocked by environment
