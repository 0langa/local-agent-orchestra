# Support Matrix

This matrix records what Agentheim currently promises. A surface is not stable unless the current repository has docs, tests, and live or smoke evidence for the promised path.

## States

| State | Meaning | Promotion Gate |
| --- | --- | --- |
| Stable | Default path for new users | Unit tests, smoke tests, docs, current validation evidence, troubleshooting coverage |
| Beta | Intended for real use with known limits | Unit tests, docs, at least one smoke/live path, documented limits |
| Experimental | Useful but not baseline-critical | Import/unit coverage and explicit limits |
| Internal | Implementation detail | Owner subsystem tests only |

## Provider Lanes

| Lane | State | Owner | Entry Points | Evidence | Known Limits |
| --- | --- | --- | --- | --- | --- |
| OpenAI-compatible, including Azure OpenAI/Foundry-compatible endpoints | Stable for Azure Foundry/OpenAI-compatible path | Providers | CLI provider commands, API provider routes | Provider templates load; `azure-real` / `gpt-5.4` live evidence on 2026-05-15: doctor, ping-models, planner/executor/verifier provider tests, `command-assistant`, text/JSON, and vision pass | Broader hosted compatible vendors remain advanced until separately proven; `codebase-assistant` remains a workflow blocker, not a provider blocker |
| Google AI services: Gemini API and Vertex AI | Stable for Gemini API; Beta for Vertex AI | Providers | CLI provider commands, API provider routes | Templates/adapters load; `gemini-key-test` / `gemini-2.5-flash` live evidence on 2026-05-15: doctor, ping-models, planner/executor/verifier provider tests, text/JSON, vision, and multiple presets pass without 429 | Vertex ADC/project/location live proof still needed before the whole Google lane is stable |
| Self-hosted OSS through OpenAI-compatible endpoints | Beta | Providers | CLI provider commands | Ollama, LM Studio, vLLM, TGI, llama.cpp server, and generic compatible templates exist; localhost compatibility shim smoke passed on 2026-05-15 via `.localtest/mock-ai-server/` — all 17 provider adapter types verified through localhost-shaped configs | Still needs fresh real local endpoint smoke and model-quality guidance validation |
| Other integrated providers | Experimental | Providers | CLI provider commands | Templates/adapters exist for current registry | Functional in theory; not polished/proven like top 3 lanes |

## Provider Adapters

| Provider | State | Evidence | Notes |
| --- | --- | --- | --- |
| `openai_v1` | Beta | Template, adapter, provider tests | Promote with fresh OpenAI live smoke |
| `openai_compatible` | Beta | Template and shared compatible path | Includes many hosted/local gateways |
| `azure_foundry` | Stable | Template, adapter, fresh live evidence on 2026-05-15 via live_validate runner and direct vision smoke | Main dev lane; provider smoke, text/JSON, vision, and command-assistant preset passed on `gpt-5.4` |
| `gemini` | Stable | Template, adapter, provider tests, fresh live evidence on 2026-05-15 via `gemini-key-test`: provider smoke, text/JSON, vision, and multiple presets pass | Temporary test key should be replaced with durable user key for ongoing validation |
| `vertex_ai` | Beta | Template, adapter, provider tests | Needs ADC/project/location live rerun |
| `ollama`, `lm_studio`, `vllm`, `tgi`, `llama_cpp` | Beta | Templates via compatible path | Needs local live endpoint evidence |
| `anthropic`, `aws_bedrock`, `oci_genai`, `cohere`, `perplexity`, `ollama_cloud` | Experimental | Templates/adapters/tests vary by provider | Keep available; do not present as first-run path |
| `groq`, `openrouter`, `together`, `mistral`, `deepseek`, `kimi_moonshot`, `xai_grok` | Experimental | OpenAI-compatible templates | Advanced compatible endpoints until live scorecards exist |

## Presets

| Preset | Workflow | State | Entry Points | Evidence | Known Limits |
| --- | --- | --- | --- | --- | --- |
| `command-assistant` | `command_assistant` | Stable candidate | CLI, API, Web route | Smoke/unit coverage; unsafe-command propagation and parse-failure negative tests added; fresh live pass on 2026-05-15 via azure-real / gpt-5.4 and gemini-key-test / gemini-2.5-flash | Needs report/resume and non-CLI evidence before `stable` |
| `local-document-chat` | `documents` | Stable candidate | CLI, API, Web route | Smoke/unit coverage; fresh live pass on 2026-05-15 via azure-real / gpt-5.4 and gemini-key-test / gemini-2.5-flash after provider-map fix | Needs report/resume and non-CLI evidence before `stable` |
| `codebase-assistant` | `coding` | Stable candidate | CLI, API, Web route | Broad tests and historical capable-model live pass; patch rollback, repeated-failure guard, max-diff-lines, dirty-repo bypass, no-tests skip, and allowed-files guard covered by tests; fresh live runs on 2026-05-15 via azure-real / gpt-5.4 still returned `status='blocked'` or empty PatchPlan | Still blocks on coding workflow repair-loop/verifier behavior; not stable-ready |
| `context-maintainer` | `context_maintainer` | Stable candidate | CLI, API/Web context routes | ContextOps tests and historical dry-run evidence; golden-path e2e workflow execution test added; fresh live pass on 2026-05-15 via azure-real / gpt-5.4-mini | Apply/write paths remain review-first; needs stable-promotion report/resume evidence |
| `file-organizer` | `file_organization` | Beta | CLI, API, Web route | Fresh live pass 2026-05-15 (dry-run via azure-real / gpt-5.4-mini); missing-source, overwrite-block, and dry-run smoke tests |
| `docs-maintainer` | `docs_maintenance` | Beta | CLI, API, Web route | Fresh live pass 2026-05-15 (plan mode via azure-real / gpt-5.4-mini); golden-path e2e test added; detect-failure halt, update-failure halt, and empty-stale-docs graceful paths covered by smoke tests | Apply and aligner paths need live proof |
| `research-report` | `research` | Beta | CLI, API, Web route | Unit/deep path evidence; gather-failure halt and empty-sources graceful paths covered by smoke tests; fresh CLI live pass on 2026-05-15 via azure-real / gpt-5.4 | API/Web live reruns still needed |
| `github-maintainer` | `github_maintenance` | Beta | CLI, API, Web route | Fresh live pass 2026-05-15 (issue summary + PR draft via azure-real / gpt-5.4-mini); summarize-failure halt and empty-issues graceful paths covered by smoke tests | |

## Workflow Readiness Checklists (Stable Candidates)

| Checklist Item | `command-assistant` | `local-document-chat` | `codebase-assistant` | `context-maintainer` |
| --- | --- | --- | --- | --- |
| **Structured I/O schemas** | ✅ ParsedIntent, GeneratedCommand, ValidationResult | ✅ IndexerOutput, RetrieverOutput, AnswererOutput | ✅ ImplementationPlan, PatchPlan, VerificationReport | ⚪ Delegates to AICtx; no Agentheim workflow schemas |
| **Artifacts produced** | ✅ FinalReport (commands, validation) | ✅ Answer metadata with citations | ✅ plan.json, patch.diff, verification.json, final_report.md/json | ⚪ AICtx shards in `docs/AIprojectcontext/` |
| **Final report** | ✅ FinalReport.status + commands | ✅ AnswererOutput parsed in metadata | ✅ FinalReport with changed_files, tests, risks | ⚪ No canonical Agentheim final report |
| **Failure modes documented** | ✅ parse failure → failed; unsafe → safe=false | ✅ empty repo fallback | ✅ dirty repo block, planning failure, patch failure, max tasks/fix attempts, repeated failure | ⚪ No explicit runtime failure modes tested |
| **Negative-path tests** | ✅ unsafe command propagation, parse failure | ✅ binary/dir exclusion, empty repo | ✅ rollback, repeated-failure, max-diff, no-tests skip, allow-dirty bypass | ⚪ Only import/instantiation tests |
| **CLI path** | ✅ `start command-assistant` | ✅ `start local-document-chat` | ✅ `run`, `plan`, `start codebase-assistant` | ✅ `ctx scan/run/verify/status` |
| **API path** | ✅ `POST /api/presets/{preset_id}/run` | ✅ `POST /api/presets/{preset_id}/run` | ✅ `POST /api/presets/{preset_id}/run` | ✅ `POST /api/ctx/*` routes |
| **Docs** | ✅ USER_GUIDE.md, CLI-COMMANDS.md | ✅ USER_GUIDE.md | ✅ USER_GUIDE.md, CLI-COMMANDS.md | ✅ USER_GUIDE.md ctx section |
| **Live evidence** | 🟢 Fresh pass on azure-real / gpt-5.4 and Gemini | 🟢 Fresh pass on azure-real / gpt-5.4 and Gemini | 🔴 Fresh gpt-5.4 run blocked on verifier/repair-loop outcome | 🟢 Fresh pass on azure-real / gpt-5.4-mini and Gemini |

**Notes:**
- `context-maintainer` is architecturally different: it delegates execution to the AICtx runtime rather than using Agentheim's workflow agent pipeline. Its readiness checklist reflects this boundary. Agentheim-native artifacts, final reports, and negative-path tests are gaps that must close before stable promotion.
- Provider compatibility evidence is now strong for Azure Foundry and Gemini API. Preset promotion still needs report/resume and non-CLI evidence, and `codebase-assistant` still needs green live repair-loop behavior.

## Workflow Readiness Checklists (Beta Candidates)

| Checklist Item | `file-organizer` | `docs-maintainer` | `research-report` | `github-maintainer` |
| --- | --- | --- | --- | --- |
| **Structured I/O schemas** | ✅ AnalyzerResult, ProposerResult, ApplierResult | ✅ DetectionResult, UpdateResult, AlignmentResult | ✅ GatherResult, SummaryResult, ResearchReport | ✅ SummaryResult, DraftResult |
| **Artifacts produced** | ✅ working_memory.json, moves_executed metadata | ✅ updates metadata | ✅ ResearchReport in metadata | ✅ DraftResult in metadata |
| **Final report** | ✅ ApplierResult with moves + summary | ✅ AlignmentResult in metadata | ✅ ResearchReport in metadata | ✅ DraftResult (pr_title, pr_body, branch_name) |
| **Failure modes documented** | ✅ missing source, destination exists | ✅ detect failure halt, update failure halt | ✅ gather failure halt | ✅ summarize failure halt |
| **Negative-path tests** | ✅ missing source, dest exists, dry_run | ✅ detect failure halt, update failure halt, empty stale_docs | ✅ gather failure halt, empty sources | ✅ summarize failure halt, empty issues_text |
| **CLI path** | ✅ `start file-organizer` | ✅ `start docs-maintainer` | ✅ `start research-report` | ✅ `start github-maintainer` |
| **API path** | ✅ `POST /api/presets/{preset_id}/run` | ✅ `POST /api/presets/{preset_id}/run` | ✅ `POST /api/presets/{preset_id}/run` | ✅ `POST /api/presets/{preset_id}/run` |
| **Docs** | ✅ USER_GUIDE.md | ✅ USER_GUIDE.md | ✅ USER_GUIDE.md | ✅ USER_GUIDE.md |
| **Live evidence** | 🟢 Pass 2026-05-15 (dry-run) | 🟢 Pass 2026-05-15 (plan mode) | 🔴 Fail 2026-05-15 (exit 1) | 🟢 Pass 2026-05-15 (issue summary + PR draft) |

## Interfaces

| Interface | State | Evidence | Known Limits |
| --- | --- | --- | --- |
| CLI | Beta | Smoke tests, directive/baseline gates, docs | Commands grouped into `Getting Started`, `Repository Work`, `Presets`, `Context`, `Advanced` panels since 2026-05-15 |
| API server | Beta | TestClient tests and OpenAPI route tests | Tool approval UX returns approval payload; explicit `/api/tools/approvals/{request_id}/grant` and `/deny` continuation routes exist and are tested |
| Web UI | Beta | TestClient tests + browser smoke 2026-05-15 | Root loads, provider health visible, presets with Run buttons, Active Runs polling, artifacts/errors visible; full provider-backed preset-run end-to-end not yet complete |
| Guided TUI | Beta | Unit tests and historical scripted live run | Interactive flow needs current live pass for stable |
| Desktop UI | Beta | Unit tests + server integration test 2026-05-15 | Inherits Web UI via pywebview wrapper; server thread start verified; pywebview/tkinter/browser fallback paths tested; actual window launch needs GUI environment |

## Tools

| Tool | State | Risk | Evidence | Notes |
| --- | --- | --- | --- | --- |
| `filesystem` | Beta | Operation-level: read/list/stat none, write/copy medium | Tool tests, API/Web approval-flow tests, centralized invoker tests | Medium operations now return approval-required in API/Web and can be granted/denied explicitly |
| `git` | Beta | none currently declared | Tool tests | Mutating git operations need operation-level risk follow-up |
| `shell.execute` | Beta | high | Tool tests, policy tests | API/Web deny high-risk path |
| `browser` | Experimental | high | Unit tests | Live browser evidence incomplete |
| `http.request` | Beta | high | HTTP tests | Network policy remains strict by default |
| `local_db` | Experimental | medium | Local DB tests | Requires configured DB for meaningful use |
| `memory` | Beta | low | Memory and Web/API tests | Advanced consistency matrix remains future work |
| MCP tools | Experimental | varies | MCP list/call tests | Must remain policy-routed |

## Advanced Subsystems

| Subsystem | State | Reason |
| --- | --- | --- |
| Marketplace | Experimental | Needs install/load/signature UX, threat model, live smoke |
| Federation | Experimental | Needs cross-machine auth, transport security, and failure recovery proof |
| Distributed workflows | Experimental | Scheduler/worker lifecycle and resume semantics not baseline-proven |
| OCI/remote context | Beta | Optional AICtx/OCI path; advanced opt-in |
| Multimodal | Beta for proven provider lanes, experimental otherwise | Needs current vision live matrix |
| Self-improving agents | Internal | Needs governance, rollback, and audit model before exposure |

## Current Validation Evidence

Last docs baseline sweep on 2026-05-15:

- `python scripts/check-agent-instructions.py` passed.
- `powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt` passed.
- `powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt` passed.
- Markdown local link scan passed across 94 repo docs.
- `pytest --collect-only -q` collected 1256 total tests; default lane selected 1220 and deselected 36.
- Full live validation matrix plus safety negatives (18 checks) run against azure-real / gpt-5.4-mini: 14 pass, 4 fail.
- Focused capable-model rerun against azure-real / gpt-5.4: provider smoke, `command-assistant`, `local-document-chat`, `research-report`, and vision pass; `codebase-assistant` remains blocked.
- Gemini API rerun against `gemini-key-test` / `gemini-2.5-flash`: provider smoke, text/JSON, vision, `command-assistant`, `local-document-chat`, `context-maintainer`, `file-organizer-dry-run`, `docs-maintainer-plan`, `github-maintainer`, and `research-report` pass.
- Localhost mock-shim provider smoke passed across 17 provider adapter types; this is wiring evidence, not real local model-quality evidence.
