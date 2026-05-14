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
| OpenAI-compatible, including Azure OpenAI/Foundry-compatible endpoints | Beta | Providers | CLI provider commands, API provider routes | Provider templates load; Azure `azure-real` historical live evidence; provider tests exist | Needs fresh OpenAI-compatible live lane gate before stable |
| Google AI services: Gemini API and Vertex AI | Beta | Providers | CLI provider commands, API provider routes | Templates and adapters load; provider unit coverage exists | Needs fresh Gemini API and Vertex ADC live evidence |
| Self-hosted OSS through OpenAI-compatible endpoints | Beta | Providers | CLI provider commands | Ollama, LM Studio, and generic compatible templates exist | Needs fresh local endpoint smoke and model-quality guidance validation |
| Other integrated providers | Experimental | Providers | CLI provider commands | Templates/adapters exist for current registry | Functional in theory; not polished/proven like top 3 lanes |

## Provider Adapters

| Provider | State | Evidence | Notes |
| --- | --- | --- | --- |
| `openai_v1` | Beta | Template, adapter, provider tests | Promote with fresh OpenAI live smoke |
| `openai_compatible` | Beta | Template and shared compatible path | Includes many hosted/local gateways |
| `azure_foundry` | Beta | Template, adapter, historical live evidence | Main dev lane; needs current baseline live rerun |
| `gemini` | Beta | Template, adapter, provider tests | Needs current Gemini API live rerun |
| `vertex_ai` | Beta | Template, adapter, provider tests | Needs ADC/project/location live rerun |
| `ollama`, `lm_studio` | Beta | Templates via compatible path | Needs local live endpoint evidence |
| `anthropic`, `aws_bedrock`, `oci_genai`, `cohere`, `perplexity`, `ollama_cloud` | Experimental | Templates/adapters/tests vary by provider | Keep available; do not present as first-run path |
| `groq`, `openrouter`, `together`, `mistral`, `deepseek`, `kimi_moonshot`, `xai_grok` | Experimental | OpenAI-compatible templates | Advanced compatible endpoints until live scorecards exist |

## Presets

| Preset | Workflow | State | Entry Points | Evidence | Known Limits |
| --- | --- | --- | --- | --- | --- |
| `command-assistant` | `command_assistant` | Stable candidate | CLI, API, Web route | Smoke/unit coverage; historical live pass | Needs current top-3 lane live evidence |
| `local-document-chat` | `documents` | Stable candidate | CLI, API, Web route | Smoke/unit coverage; historical live pass | Binary/excluded-dir negative paths still need promotion proof |
| `codebase-assistant` | `coding` | Stable candidate | CLI, API, Web route | Broad tests and historical capable-model live pass | Smaller models can fail coding quality |
| `context-maintainer` | `context_maintainer` | Stable candidate | CLI, API/Web context routes | ContextOps tests and historical dry-run evidence | Apply/write paths remain review-first |
| `file-organizer` | `file_organization` | Beta | CLI, API, Web route | Historical dry-run/apply evidence | Unsafe/missing move reporting needs stronger coverage |
| `docs-maintainer` | `docs_maintenance` | Beta | CLI, API, Web route | Plan-mode evidence | Apply and aligner paths need live proof |
| `research-report` | `research` | Beta | CLI, API, Web route | Unit/deep path evidence and mixed historical live notes | Needs clean CLI/API/Web live rerun |
| `github-maintainer` | `github_maintenance` | Beta | CLI, API, Web route | Historical issue-summary evidence | GitHub credential/live path needs fresh proof |

## Interfaces

| Interface | State | Evidence | Known Limits |
| --- | --- | --- | --- |
| CLI | Beta | Smoke tests, directive/baseline gates, docs | Stable command grouping still needs polish |
| API server | Beta | TestClient tests and OpenAPI route tests | Tool approval UX now returns approval payload, but no approval continuation yet |
| Web UI | Experimental | TestClient tests | Prototype UI; provider-backed full preset matrix not complete |
| Guided TUI | Beta | Unit tests and historical scripted live run | Interactive flow needs current live pass for stable |
| Desktop UI | Experimental | Unit/import/fallback tests | Needs launch and preset-run verification |

## Tools

| Tool | State | Risk | Evidence | Notes |
| --- | --- | --- | --- | --- |
| `filesystem` | Beta | Operation-level: read/list/stat none, write/copy medium | Tool tests, API/Web tests, centralized invoker tests | Medium operations now return approval-required in API/Web |
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

Last docs baseline sweep on 2026-05-14:

- `python scripts/check-agent-instructions.py` passed.
- `powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt` passed.
- Markdown local link scan passed across 94 repo docs.
- `pytest --collect-only -q` collected 1133 total tests; default lane selected 1098 and deselected 35.

Full pytest execution and live AI provider matrix were not rerun in that sweep.
