# Repository Audit Report

## Executive Summary

This repository is `agentheim` (`pyproject.toml:6`), a Python 3.12+ local-first AI orchestration platform with a Typer CLI, FastAPI API server, FastAPI web UI, workflow packs, tool adapters, and memory/ledger infrastructure. From source checkout, the codebase is in generally good shape: `pytest -q` passed with `692 passed, 3 skipped` and the architecture checker passed phase 7.

Main risks are not broad test failures; they are integration and release defects that the current tests miss. Highest-impact issues: the published package configuration would omit major runtime namespaces, configured provider-based entry points fail because some code paths build `ModelRegistry` without any provider map, and the API server silently accepts a known default API key when no keys are configured. There is also architectural drift around the coding workflow: it is advertised and available as a preset, but not exposed as a registered workflow.

## Repository Understanding

The project is structured around a generic workflow runtime in `core/`, with workflow definitions in `workflows/`, tools in `tools/`, provider adapters in `providers/`, memory tiers/backends in `memory/`, and user-facing interfaces in `interfaces/`. Packaging and CLI entry point are defined in `pyproject.toml:1-79`; the console script points at `interfaces.cli.cli:main` (`pyproject.toml:49-50`).

Runtime flow is DAG-based. `workflows/base.py:11-171` defines `Step`, `ExecutionDAG`, `Workflow`, and the handoff to `core.workflow_runner.WorkflowRunner`. `core/workflow_runner.py` handles topological execution, optional parallel groups, retry, budget enforcement, checkpointing, and ledger emission. `core/ledger.py` implements the append-only run ledger with a hash chain, indexes, and checkpoints.

A representative workflow is `workflows/research/workflows/research.py:12-107`: it declares a three-step DAG (`gather -> summarize -> report`), resolves models through `ModelRegistry`, creates provider-backed agents, and returns structured results that are rendered by `workflows/research/runtime.py`. The coding flow is different: `workflows/coding/runtime.py` contains its own planning/patch/verify orchestration, while `workflows/coding/workflows/coding.py:11-50` only exposes agent factory helpers and `WORKFLOW_ID = "coding"`, not a `Workflow` subclass.

Interfaces are split across CLI (`interfaces/cli/cli.py`), API server (`interfaces/api_server/app.py`), web UI (`interfaces/web_ui/app.py`), guided TUI, and desktop UI. Background execution for API/web routes is handled by `core/run_executor.py`. Configuration is environment-driven via `config/config.py`. Documentation is spread across root docs (`README.md`, `docs/INSTALL.md`, `docs/CONFIGURATION.md`, `docs/API.md`), roadmap docs under `docs/roadmap/`, generated docs under `docs/generated/`, and a legacy-looking embedded `Agent-Team/` subtree with its own docs/tests/pyproject.

## Verification Performed

Commands run:

- `Get-Location` — pass — confirmed cwd `C:\Users\juliu\source\repos\local-agent-orchestra`.
- `git status --short` — pass — clean working tree.
- `Get-ChildItem -Force | Select-Object Mode,Length,LastWriteTime,Name` — pass — mapped top-level structure.
- `rg --files -g "*AGENTS.md" -g "*.sln" -g "*.csproj" -g "*.py" -g "pyproject.toml" -g "requirements*.txt" -g "Pipfile*" -g "poetry.lock" -g "package.json" -g "*.yml" -g "*.yaml" -g "Dockerfile*" -g "*.md"` — pass — mapped source/docs/manifests.
- `Get-Content -Path 'pyproject.toml' -TotalCount 250` — pass — inspected build/package config.
- `Get-Content -Path 'README.md' -TotalCount 250` — pass — inspected product positioning and documented commands.
- `Get-Content -Path 'docs\INSTALL.md' -TotalCount 250` — pass — inspected install flow.
- `Get-Content -Path 'docs\CONFIGURATION.md' -TotalCount 250` — pass — inspected env/provider model.
- `Get-Content -Path 'interfaces\cli\cli.py' -TotalCount 320` — pass — inspected CLI entry paths.
- `Get-Content -Path 'core\__main__.py' -TotalCount 200` — pass — confirmed module entry delegates to CLI.
- `Get-Content -Path 'config\config.py' -TotalCount 320` — pass — inspected config resolution.
- `Get-Content -Path 'workflows\registry.py' -TotalCount 320` — pass — inspected builtin workflow registration.
- `Get-Content -Path 'core\public_api.py' -TotalCount 360` — pass — inspected facade boundaries.
- `Get-Content -Path 'presets\__init__.py' -TotalCount 260` — pass — inspected preset registration.
- `Get-Content -Path 'presets\codebase_assistant.py' -TotalCount 260` — pass — traced coding preset to `workflow_id="coding"` and `workflows.coding.runtime.run_task`.
- `Get-Content -Path 'workflows\coding\runtime.py' -TotalCount 320` — pass — inspected coding runtime orchestration.
- `rg -n 'def (start|guided|doctor)|@app\.command\("(start|guided|doctor|presets|inspect|run|resume|ping-models)"' interfaces\cli\cli.py` — pass — located major CLI commands.
- `rg -n 'register_builtin_workflows|workflow_id="coding"|workflow_id="research"|workflow_id="documents"' presets workflows interfaces` — pass — traced workflow registration references.
- `Get-Content 'interfaces\cli\cli.py' | Select-Object -Skip 320 -First 170` — pass — inspected `start`, `guided`, `doctor`.
- `Get-Content 'interfaces\api_server\app.py' -TotalCount 280` — pass — inspected API server wiring.
- `Get-Content 'interfaces\web_ui\app.py' -TotalCount 460` — pass — inspected web UI wiring.
- `Get-Content 'devtest\all-test-commands.md' -TotalCount 260` — pass — captured repo-documented verification commands.
- `Get-Content 'devtest\project_overview.py' -TotalCount 260` — pass — inspected devtest helper.
- `Get-ChildItem '.github\workflows' | Select-Object Name,Length` — pass — found one CI workflow.
- `rg --files .github\workflows devtest tests | sort` — pass — mapped CI/devtest/test files.
- `Get-Content '.github\workflows\architecture.yml' -TotalCount 260` — pass — inspected CI logic.
- `Get-Content 'tests\smoke\test_workflows.py' -TotalCount 260` — pass — inspected smoke expectations.
- `Get-Content 'tests\smoke\test_presets.py' -TotalCount 260` — pass — inspected preset coverage.
- `Get-Content 'tools\registry.py' -TotalCount 320` — pass — inspected interface tool registry.
- `Get-Content 'tests\test_api_server.py' -TotalCount 320` — pass — inspected API coverage.
- `Get-Content 'tests\test_workflow_isolation.py' -TotalCount 260` — pass — inspected architecture-boundary tests.
- `Get-Content 'tests\test_import_linting.py' -TotalCount 260` — pass — inspected roadmap-check test coverage.
- `Get-Content 'tests\test_public_api.py' -TotalCount 260` — pass — inspected public facade tests.
- `agentheim --help` — pass — CLI executable works in this environment, but later confirmed it resolves to a separate installed checkout, so I did not use it as source-of-truth evidence.
- `agentheim doctor --skip-connectivity` — pass — environment-level smoke check only; reported Python/package/git/workspace OK and no provider env vars.
- `agentheim presets` — pass — environment-level smoke only; listed seven presets including `codebase-assistant`.
- `agentheim inspect --repo .` — pass — environment-level smoke only; reported Python repo, clean git, two detected pytest commands.
- `python -c "from workflows.registry import register_builtin_workflows; from core.capability_registry import list_workflows; register_builtin_workflows(); print([e.id for e in list_workflows()])"` — pass — proved registered workflows are `['command_assistant', 'docs_maintenance', 'documents', 'file_organization', 'github_maintenance', 'research']`; `coding` missing.
- `python scripts/roadmap-check.py --phase 7 --ci` — pass — architecture checker passed for phase 7.
- `pytest -q` — pass — `692 passed, 3 skipped, 1 warning in 91.85s`; strongest evidence that source checkout is healthy under tests.
- `Get-Content 'interfaces\api_server\app.py' | Select-Object -Skip 300 -First 260` — pass — inspected API workflow execution and `/api/models`.
- `Get-Content 'tests\smoke\test_workflow_execution.py' -TotalCount 320` — pass — inspected end-to-end workflow tests and mocking strategy.
- `Test-Path 'Agent-Team\.env.example'; if ($?) { Get-Item 'Agent-Team\.env.example' | Select-Object FullName,Length }` — pass — confirmed docs reference points to a real file.
- `Get-ChildItem 'Agent-Team' -Force | Select-Object Name,Length` — pass — confirmed embedded secondary project/subtree exists.
- `Get-Content 'workflows\coding\provider_map.py' -TotalCount 200` — pass — captured canonical provider map.
- `Get-Content 'workflows\research\runtime.py' -TotalCount 120` — pass — confirmed runtime path uses provider map correctly.
- `$env:...; python -c "from config.config import load_team_config; from core.model_registry import ModelRegistry; ...; reg.create_provider(role)"` — fail — raised `Unsupported provider type 'openai_compatible'`; proved `ModelRegistry.from_team_config()` without provider map is broken before any network call.
- `$env:...; python -c "from interfaces.api_server import create_api_app; ...; print(client.get('/api/models').json())"` — pass — returned `[]` even with model env configured; proved `/api/models` is broken.
- `$env:...; agentheim ping-models` — fail — reproduced same provider-map error, but used external installed executable; treated as corroboration, not primary repo evidence.
- `Get-Command agentheim | Format-List Source,Path,Definition` — pass — showed `agentheim.exe` comes from `C:\Python312\Scripts\agentheim.exe`.
- `rg -n '^def main|if __name__ == "__main__"|app\(\)' interfaces\cli\cli.py` — pass — confirmed repo-local CLI entry.
- `$env:...; python -m interfaces.cli.cli ping-models` — fail — primary repo-local repro of broken `ping-models`.
- `python -m interfaces.cli.cli --help` — pass — repo-local CLI module loads.
- `$env:...; python -c "import time; from interfaces.web_ui import create_app; ... post('/api/workflows/research/execute') ... get('/api/runs/{run_id}')"` — pass/fail combo — route returned `200 {"status":"pending"}`, then run status became `failed` with `Unsupported provider type 'openai_compatible'`; proved asynchronous workflow execution is broken.
- `python -c "from setuptools import find_packages; print(find_packages(...))"` — pass — package discovery only found `core`, `memory`, `presets`, `providers`, `tools` subpackages; omitted `config`, `interfaces`, `workflows`, `agents`, etc.
- `Test-Path 'interfaces\__init__.py'; Test-Path 'workflows\__init__.py'; Test-Path 'agents\__init__.py'; ...` — pass — confirmed `interfaces/`, `workflows/`, and `agents/` are namespace-package roots without `__init__.py`.
- `python -c "from interfaces.web_ui import create_app; ... print([item['workflow_id'] for item in client.get('/api/workflows').json()])"` — pass — web UI workflow list also omits `coding`.
- `python -c "from interfaces.api_server import create_api_app; ... post('/api/memory/jsonl/probe', headers={'X-API-Key':'dev-key-change-in-production'})"` — pass — returned `200`; proved hard-coded default API key grants write access.
- `rg -n 'OPENAI_API_KEY|API_KEY|sk-[A-Za-z0-9]+' . -g '!**/.git/**' -g '!**/.venv/**'` — pass — found only docs/tests/placeholders and auth/config references; no live secret leak found.
- `rg -n 'subprocess\.run|os\.system|Popen\(|shell=True|requests\.|http://|https://|unlink\(|rmtree|shutil\.move|Path\(.+\)\.write_text' core interfaces tools workflows memory providers monitoring agents -g '*.py'` — pass — found subprocess/network/file mutation sites for manual review; no `shell=True` found in runtime code.
- Several additional `Get-Content`, `rg -n`, and numbered-line views were used to capture exact file/line evidence for the findings below.

Checks I did not run:

- `devtest/ai_test.ps1` — intentionally not run. It tests live AI connectivity, would require provider credentials/external services, and your repo rules cap repeated attempts.
- `devtest/project_overview.py` — intentionally not run because it writes `PROJECT_OVERVIEW.md`, and this audit was investigation-only.
- A build/install of a fresh wheel — not run to avoid mutating the environment; package-discovery output already provides strong static evidence of the packaging defect.

## Critical Findings

1. `Critical` — Published package configuration omits major runtime namespaces, so a real wheel/sdist install is likely broken.
Affected files: `pyproject.toml:49-75`, `core/__main__.py:1`, `core/run_executor.py:81-82`, `interfaces/api_server/app.py:26-27`, `interfaces/web_ui/app.py:368-370`. Evidence: `project.scripts` points to `interfaces.cli.cli:main`, but `find_packages(...)` only returned `['core', 'memory', 'presets', 'providers', 'tools', ...]`; `interfaces/`, `workflows/`, `config/`, and `agents/` are namespace roots and were not discovered. Impact: installable artifacts can miss the CLI entry target and runtime modules, blocking release-quality packaging. Likely root cause: `setuptools.find_packages` is being used against a namespace-package layout without `__init__.py` or explicit namespace discovery. Recommended fix: switch to namespace package discovery (or add `__init__.py` where intended), include all runtime namespaces, and add a CI smoke test that builds a wheel and imports/runs the installed CLI.

2. `Critical` — Several advertised entry points construct `ModelRegistry` without any provider map, so configured providers cannot instantiate at all.
Affected files: `interfaces/cli/cli.py:56-72`, `interfaces/web_ui/app.py:207-213`, `interfaces/api_server/app.py:345-350`, `core/model_registry.py:30-61`, contrasted with the correct runtime path in `workflows/research/runtime.py:28-35` and `workflows/coding/provider_map.py:10-16`. Evidence: repo-local `python -m interfaces.cli.cli ping-models` failed immediately with `Unsupported provider type 'openai_compatible'`; direct `ModelRegistry.from_team_config(cfg)` + `create_provider(...)` reproduced the same error; web UI `/api/workflows/research/execute` returned `pending` and then failed with that exact error. Impact: documented setup verification (`ping-models`) and workflow execution through web/API fail even with valid configuration, before any external network call is made. Likely root cause: provider-map wiring lives only in workflow runtimes and was not centralized for shared interface code. Recommended fix: centralize provider-map creation in one helper used by CLI/API/web/runtime code paths, then add integration tests that execute a real background run to terminal status.

3. `Critical` — API server accepts a known hard-coded default key when no API keys are configured.
Affected files: `interfaces/api_server/auth.py:19-31`, `interfaces/api_server/app.py:143-149`. Evidence: `_load_keys()` inserts `"dev-key-change-in-production"` when `AI_TEAM_API_KEYS` is empty; I verified `POST /api/memory/jsonl/probe` succeeded with `X-API-Key: dev-key-change-in-production` and no env setup. Impact: any misconfigured deployment exposes mutating endpoints to anyone who knows the public source code. Likely root cause: insecure developer convenience fallback instead of explicit startup failure or opt-in dev mode. Recommended fix: remove the fallback, require explicit keys except in a clearly gated local-dev mode, and add a startup/config test that rejects empty API-key configuration.

## High-Value Findings

1. `High` — The coding flow is advertised as a workflow/preset, but it is not a registered `Workflow` pack.
Affected files: `presets/codebase_assistant.py:11-32`, `workflows/registry.py:5-20`, `workflows/coding/workflows/coding.py:11-50`. Evidence: the preset declares `workflow_id="coding"`, but `register_builtin_workflows()` only registers six other workflows; `python -c "...list_workflows()"` and `/api/workflows` both omitted `coding`. Also, `workflows/coding/workflows/coding.py` defines only agent factories plus `WORKFLOW_ID`, not a `Workflow` subclass. Impact: workflow discovery APIs and any registry-based workflow execution cannot expose or run the coding workflow, despite product docs advertising “Codebase Assistant.” Likely root cause: coding runtime predates the workflow-pack abstraction and was never adapted into it. Recommended fix: either implement a real `CodingWorkflow` and register it, or stop advertising it as a registry-backed workflow and adjust docs/API expectations accordingly.

2. `High` — `/api/models` is internally broken and silently returns an empty list.
Affected files: `interfaces/api_server/app.py:414-432`, `core/model_registry.py:24-49`. Evidence: the route iterates `registry._bindings.values()`, but `ModelRegistry` only stores `_providers` and `_models`; I verified `hasattr(reg, "_bindings") == False` and the endpoint returned `[]` even with model env vars configured. Impact: model introspection/observability is non-functional, and the broad `except Exception: return []` hides the defect from callers and tests. Likely root cause: stale route code left behind after a model-registry refactor. Recommended fix: use the public `list_models()` API, return structured errors instead of swallowing exceptions, and strengthen endpoint tests to assert actual content under a configured registry.

3. `Medium` — `doctor` validates Python `>=3.10`, but packaging/docs require `>=3.12`.
Affected files: `interfaces/cli/cli.py:436-438`, `pyproject.toml:10`, `docs/INSTALL.md:5`. Evidence: `doctor` marks 3.10+ as pass, while the project metadata and install guide say 3.12+. Impact: users can get a green diagnostics result on an unsupported interpreter, which makes setup/debugging misleading. Likely root cause: version gate not updated when project minimum bumped. Recommended fix: align the `doctor` check with `pyproject.toml` and add a regression test for the version threshold.

4. `Medium` — CI still enforces phase 6 architecture checks while the repository advertises phase 7.
Affected files: `.github/workflows/architecture.yml:14`, `README.md:4`, `tests/test_import_linting.py:15-33`. Evidence: GitHub Actions runs `python scripts/roadmap-check.py --phase 6 --ci`, while README badge says phase 7 and local tests assert phase 7 checks. Impact: hosted CI can miss phase-7-only violations and does not fully match the documented/project-tested architecture policy. Likely root cause: CI workflow not updated after the phase bump. Recommended fix: update CI to `--phase 7` and keep one source of truth for enforced architecture phase.

5. `Low` — `devtest/project_overview.py` is stale and not self-contained.
Affected files: `devtest/project_overview.py:7`, `devtest/project_overview.py:80`, `devtest/project_overview.py:106-107`, `pyproject.toml:26-46`. Evidence: it imports `langgraph`, which is not declared in dependencies, writes directly to tracked `PROJECT_OVERVIEW.md`, and prints `Scanned 1 Python files` because it literally evaluates `len(['files'])`. Impact: the helper is unreliable in a fresh environment and can produce misleading output while mutating a tracked artifact. Likely root cause: script drift without validation coverage. Recommended fix: either declare the dependency and test the script, or replace it with a simpler stdlib-only helper and correct the count/reporting logic.

## Security and Safety Review

The concrete security issue is the API server’s known default key in `interfaces/api_server/auth.py:28-30`; that is a real exposure, not speculative. It is made more concerning by permissive CORS in `interfaces/api_server/app.py:143-149`, although actual browser exploitability depends on deployment details.

Outside of that, I did not find evidence of committed live secrets. The repo-wide pattern scan only found docs placeholders, tests, and env-key references. I also did not find `shell=True` usage in runtime code; subprocess calls I reviewed use argument vectors (`tools/shell/__init__.py`, `tools/git/__init__.py`, `tools/mcp/client.py`), which is the safer default.

The higher-risk operational surface is intentional: this project exposes shell, git, browser, HTTP, and MCP tools. The codebase appears to rely on policy/risk gating for those, so the main safety question is whether entry points and auth enforce that policy consistently. The API key fallback is therefore the most important real security concern in the current tree.

## Test and CI Assessment

The test suite is broad and healthy: `pytest -q` passed with `692 passed, 3 skipped`. Coverage spans core runtime pieces, API/web UI, memory, tooling, replay/resume, distributed/federation pieces, and smoke tests.

The main gap is not lack of tests overall; it is that some tests assert only surface-level success and miss real integration breakage:
- `tests/test_api_server.py:167-172` only checks `/api/models` returns a list, not that configured models appear.
- `tests/test_api_server.py:211-224` patches `RunExecutor.submit` and only checks that workflow execution returns a run id, not that the background run can actually instantiate providers and complete.
- `tests/test_web_ui.py:95-112` only requires `"research"` in workflow listings and does not assert the advertised coding workflow is present.
- Smoke coverage for coding only checks preset metadata (`tests/smoke/test_presets.py:34`), not registry exposure.

What to add first:
- One non-mocked API/web integration test that sets minimal provider env vars and asserts a workflow run reaches a deterministic terminal state.
- A packaging smoke test that builds a wheel and imports/runs the installed CLI.
- A workflow-registry test that asserts the intended public workflow set explicitly, including the coding story (either present as workflow or intentionally absent and documented).
- A configured `/api/models` test that asserts non-empty structured output.

## Documentation Accuracy

Mostly good: README test count matched the local result (`README.md:97` vs `pytest -q` output), and `Agent-Team/.env.example` really exists, so the env-copy instructions are not dead links.

The most important doc mismatch is functional: `README.md:61` and `docs/INSTALL.md:62` tell users to run `agentheim ping-models`, but the repo-local command currently fails under a valid provider config because of the provider-map defect. That makes the documented connectivity check unreliable.

There is also policy drift: the repo advertises phase 7 (`README.md:4`), local tests enforce phase 7, but GitHub Actions still runs the phase-6 checker (`.github/workflows/architecture.yml:14`).

Finally, `doctor` is documentation-adjacent drift: it blesses Python 3.10+ while package metadata and install docs require 3.12+.

## Prioritized Fix Plan

1. Fix release/install blockers first.
Address packaging discovery in `pyproject.toml`, ensure `config/interfaces/workflows/agents` are packaged, and add a wheel-install smoke test.

2. Fix provider-map initialization everywhere shared interfaces construct a registry.
Create one canonical registry-builder helper; use it in CLI `ping-models`, API workflow execution, web UI workflow execution, and any other route that currently calls `ModelRegistry.from_team_config()` bare.

3. Remove the hard-coded API key fallback.
Require explicit `AI_TEAM_API_KEYS` or an explicit dev-mode flag, then add tests that fail closed.

4. Resolve the coding workflow architecture drift.
Either promote coding into a real registered `Workflow` class or clearly separate “preset-only runtime” from registry-backed workflows across API, UI, and docs.

5. Repair interface observability and validation gaps.
Fix `/api/models`, tighten the version check in `doctor`, and update CI from phase 6 to phase 7.

6. Clean up stale dev tooling and low-signal drift.
Repair or replace `devtest/project_overview.py`, then add validation coverage so `devtest/` stays trustworthy.

## Final Notes

This audit is grounded in repository files plus local commands. I did not verify live provider/network integrations, because no production credentials were configured and that would test external systems rather than the repository itself. I also did not run mutating helper scripts such as `devtest/project_overview.py`.

One environment nuance matters: the global `agentheim.exe` on this machine points to another installed checkout. I used repo-local module execution (`python -m interfaces.cli.cli ...`) for defect proofs, and I treated the global executable only as an environment smoke check.

Two `rg` attempts failed due PowerShell quoting mistakes on my side; they did not reveal repository behavior and were excluded from the findings.
