# Tier-1 Journey Contracts

Tier-1 journeys are the baseline user promises. Each row maps the user action to the current CLI/API/UI surface, output contract, docs, and evidence state.

| Journey | CLI | API | Web/Desktop | Output Contract | Docs | Evidence State |
| --- | --- | --- | --- | --- | --- | --- |
| Install and run diagnostics | `agentheim doctor`, `agentheim doctor --skip-connectivity` | `GET /api/health` | Web `/api/health`; Desktop launch experimental | Diagnostic table or JSON health response | `README.md`, `USER_GUIDE.md`, `DEV_TESTING.md` | Baseline/directive smoke passes skip-connectivity |
| Add provider and ping models | `provider templates`, `provider add`, `provider assign`, `provider test`, `ping-models` | `GET /api/providers`, `GET /api/providers/templates`, `POST /api/providers`, `POST /api/providers/assign`, `GET /api/models` | Web provider profile/template views with support-state badges | Redacted provider/profile state; no raw secrets | `USER_GUIDE.md`, `API_REFERENCE.md`, `TROUBLESHOOTING.md` | Azure `azure-real` / `gpt-5.4` and Gemini `gemini-key-test` / `gemini-2.5-flash` provider smoke passed 2026-05-15; self-hosted mock-shim 17/17 wiring pass |
| Inspect repository | `inspect --repo <path>` | Planned through workflow/preset context rather than dedicated stable route | Not stable | Compact repo summary | `USER_GUIDE.md`, `CLI-COMMANDS.md` | CLI smoke coverage |
| Plan repository work | `plan <task> --repo <path>` | Workflow execute route can run coding workflow but contract is not frozen | Not stable | Implementation plan/work orders | `USER_GUIDE.md`, `CLI-COMMANDS.md` | Unit/smoke coverage; live evidence historical |
| Run stable candidate presets | `start command-assistant`, `start local-document-chat`, `start codebase-assistant`, `start context-maintainer` | `POST /api/presets/{preset_id}/run` | Web route exists with Run buttons; Desktop wraps Web UI | `run_id`, canonical run summary when persisted artifacts exist | `USER_GUIDE.md`, `API_REFERENCE.md`, `SUPPORT_MATRIX.md` | `command-assistant` and `local-document-chat` pass on Azure and Gemini; `context-maintainer` passes on Azure mini and Gemini; `codebase-assistant` still blocks |
| Report run | `report --repo <path> --run-id <id>` | `GET /api/runs/{run_id}` | Web status route | Canonical run summary: status, summary, artifacts, verification, approvals, error guidance | `USER_GUIDE.md`, `API_REFERENCE.md`, `TROUBLESHOOTING.md` | Unit/API/Web stream coverage; command-assistant report follow-up passed 2026-05-15 |
| Resume run | `resume --repo <path> --run-id <id>` | Not frozen as API contract | Not stable | Resume result or explicit unsupported reason | `USER_GUIDE.md`, `TROUBLESHOOTING.md` | Unit coverage; command-assistant resume follow-up passed 2026-05-15; other stable candidates still need proof |
| Inspect artifacts | `.ai-team/runs/<run-id>/` and `list-runs` | `GET /api/runs/{run_id}` | Web status route | Artifact filenames plus canonical run status/summary | `USER_GUIDE.md`, `API_REFERENCE.md`, `ARCHITECTURE.md` | Unit/API tests; failed-run diagnostics bundle (`run_summary.json`, `diagnostics.md`) auto-written on failure since 2026-05-15 |
| Invoke tools through interfaces | `copy <source> <destination>` for filesystem copy; workflow tools internal | `POST /api/tools/{tool_id}/invoke` | `POST /api/tools/invoke` | Tool result, policy metadata, approval-required response for medium operations | `API_REFERENCE.md`, `SAFETY.md`, `SUPPORT_MATRIX.md` | Phase 1 slice adds centralized policy path for API/Web |

## Run State Contract

Current canonical executor states are:

| State | Meaning |
| --- | --- |
| `pending` | Submitted but not yet running |
| `running` | Active task execution |
| `completed` | Finished without uncaught failure |
| `failed` | Finished with error |
| `cancelled` | Cancelled before completion |

Roadmap Phase 3 may add or map richer user-facing states such as `blocked`, but until then active docs and APIs must not claim `blocked` as a current executor status.

## Stable Artifact Minimum

Stable preset runs should produce or clearly explain absence of:

- `run.json`
- `ledger.jsonl`
- `ledger.hash`
- `final_report.md` or `final_report.json`
- relevant workflow artifacts such as plan, patch, context, or citations

Failed runs should additionally produce:

- `run_summary.json`
- `diagnostics.md`

Missing artifacts must be treated as a support-state limit.
