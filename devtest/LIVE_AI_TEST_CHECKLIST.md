# Live AI Test Checklist — Agentheim

Complete checklist for live-AI validation at repo root.  
Run from `C:\Users\juliu\source\repos\agentheim` with `.venv` active and AWS credentials configured.

---

## Legend

- `[ ]` = not tested yet  
- `[x]` = tested this round  
- `[-]` = intentionally skipped / not applicable  

---

## 1. CLI Commands

### 1.1 Core commands
- [x] `config-dump` — prints loaded config  
- [x] `ping-models` — pings all configured models  
- [x] `doctor` — health checks (provider config, models, tools)  
- [ ] `provider templates` — lists every provider template  
- [ ] `provider add` — adds provider + vault secret  
- [ ] `provider list` — prints redacted provider/profile state  
- [ ] `provider assign` — binds role to provider/model  
- [ ] `provider use` — switches default/project profile  
- [ ] `provider test` — pings one role binding  
- [ ] `provider import-env` — migrates old env once  
- [ ] `provider rotate-secret` — replaces stored secret  
- [ ] `provider remove` — removes provider + secret ref  
- [ ] `run` — direct run (not via preset) with `--repo`, `--mode`, `--allow-dirty`  
- [ ] `resume` — resume a previous run by `--repo` + `--run-id`  
- [ ] `report` — show final report (also test plan-run fallback)  
- [ ] `list-runs` — enumerate `.ai-team/runs/`  
- [ ] `copy` — copy preset or config template  

### 1.2 Context commands (`ctx`)
- [ ] `ctx init` — initialize AICtx in target repo  
- [ ] `ctx scan` — scan repository with AICtx  
- [ ] `ctx run` — run AICtx pipeline (`allow_ai=False` default)  
- [ ] `ctx run --allow-ai` — run AICtx with real AI invocation  
- [ ] `ctx verify` — verify AICtx context pack  
- [ ] `ctx status` — show AICtx status  
- [ ] `ctx clean` — remove AICtx artifacts  
- [ ] `ctx public-docs` — generate public docs via AICtx  
- [ ] `ctx oci` — OCI-specific AICtx path  

### 1.3 Memory commands (`memory`)
- [ ] `memory --key <k> --value <v>` — write to memory  
- [ ] `memory --key <k>` — read from memory  
- [ ] `memory --model-id <id>` — model-scoped memory ops  

### 1.4 MCP commands
- [ ] `mcp-list` — list available MCP servers  
- [ ] `mcp-call` — call an MCP tool  

### 1.5 Preset commands
- [x] `presets` — list presets  
- [x] `start <preset-id>` — run a preset  
- [ ] `guided` — launch guided TUI preset picker  

---

## 2. Presets

- [x] `command-assistant` — run shell commands  
- [x] `codebase-assistant` — plan + apply code changes  
- [x] `file-organizer` — analyze + move files  
- [ ] `docs-maintainer` — update docs  
- [ ] `github-maintainer` — summarize issues / draft PRs  
- [ ] `local-document-chat` — RAG over local docs  
- [ ] `research-report` — gather + summarize web research  
- [ ] `context-maintainer` — maintain repo context packs  

---

## 3. Workflows

- [x] `coding` — plan → execute → verify → fix-loop → report  
- [x] `file_organization` — analyze → propose → preview → apply  
- [ ] `command_assistant` — command execution workflow  
- [ ] `docs_maintenance` — docs update workflow  
- [ ] `github_maintenance` — GitHub PR/issue workflow  
- [ ] `research` — web research workflow  
- [ ] `documents` — document processing workflow  
- [ ] `distributed` — multi-node / federation workflow  
- [ ] `context_maintainer` — context pack maintenance workflow  

---

## 4. Providers

### 4.1 Provider smoke tests
- [x] `aws_bedrock` — native Converse API  
- [ ] `openai_v1` — OpenAI-compatible API  
- [ ] `azure_foundry` — Azure AI Foundry  
- [ ] `oci_genai` — OCI GenAI  
- [ ] `anthropic` — Anthropic Messages API
- [ ] `gemini` — Gemini API key path
- [ ] `vertex_ai` — Google ADC path
- [ ] `xai_grok` — xAI OpenAI-compatible preset
- [ ] `kimi_moonshot` — Kimi OpenAI-compatible preset
- [ ] `mistral` — Mistral OpenAI-compatible preset
- [ ] `groq` — Groq OpenAI-compatible preset
- [ ] `deepseek` — DeepSeek OpenAI-compatible preset
- [ ] `openrouter` — OpenRouter OpenAI-compatible preset
- [ ] `together` — Together AI OpenAI-compatible preset
- [ ] `cohere` — Cohere native adapter
- [ ] `perplexity` — Perplexity adapter
- [ ] `ollama` — local no-auth OpenAI-compatible endpoint
- [ ] `ollama_cloud` — cloud bearer auth
- [ ] `lm_studio` — local no-auth OpenAI-compatible endpoint

### 4.2 Provider error paths
- [ ] Rate limit handling  
- [ ] Timeout handling  
- [ ] Invalid model ID handling  
- [ ] Auth failure handling  
- [ ] Network failure / retry  

---

## 5. Tools

- [ ] `browser` — BrowserTool, page fetch, screenshot  
- [ ] `filesystem` — read/write/list/search files  
- [x] `git` — `status`, `diff_patch` (tested via coding workflow)  
- [ ] `git` — `commit`, `push`, `branch`, `log`  
- [ ] `http` — HTTP requests  
- [ ] `integrations` — third-party integrations  
- [ ] `local_db` — SQLite ops  
- [ ] `mcp` — MCP server interactions  
- [ ] `memory` — memory store read/write  
- [ ] `network` — network diagnostics  
- [ ] `shell` — shell command execution  
- [ ] `registry.py` — tool registry  
- [ ] `tests.py` — tool test harness  

---

## 6. Subsystems / Interfaces

- [ ] `interfaces/api_server/` — REST API server  
- [ ] `interfaces/cli/` — CLI beyond commands tested  
- [ ] `interfaces/desktop_ui/` — desktop GUI  
- [ ] `interfaces/guided_tui/` — guided terminal UI  
- [ ] `interfaces/web_ui/` — web dashboard  
- [ ] `agents/self_improving/` — self-improvement agents  
- [ ] `federation/` — federation protocol + transport  
- [ ] `marketplace/` — marketplace manager + manifest + sandbox + signing  
- [ ] `monitoring/` — health checks + metrics  
- [ ] `multimodal/` — vision (Claude, OpenAI) + image protocol  

---

## 7. Core Modules

- [ ] `agent_protocol` — agent message protocol  
- [ ] `approval_workflow` — approval gates  
- [ ] `artifact_store` — artifact persistence  
- [ ] `capability_registry` — capability discovery  
- [ ] `cascading_router` — request routing  
- [ ] `context_packer` — context packing (legacy)  
- [ ] `error_classification` — error taxonomy  
- [x] `errors` — error types (used indirectly)  
- [ ] `events` — event bus  
- [ ] `json_repair` — JSON repair for model output  
- [ ] `ledger` — run ledger  
- [ ] `logging` — structured logging  
- [ ] `model_registry` — model resolution  
- [ ] `patching` — diff patch application  
- [ ] `policies` — safety policies  
- [ ] `policy_engine` — policy enforcement  
- [ ] `privacy_enforcer` — privacy rules  
- [ ] `public_api` — public API surface  
- [ ] `redaction` — secret redaction  
- [ ] `replay_engine` — run replay  
- [x] `resume` — resume orchestrator (used via preset)  
- [ ] `retry_engine` — retry logic  
- [ ] `run_executor` — direct run execution  
- [ ] `schemas` — core schemas  
- [x] `schemas_runtime` — runtime schemas (tested via coding workflow)  
- [x] `state_machine` — runtime state machine (tested via coding workflow)  
- [ ] `step_budget` — step-level budgeting  
- [ ] `tool_protocol` — tool call protocol  
- [ ] `workflow_runner` — generic workflow runner  

---

## 8. AICtx Integration

- [x] `allow_ai=False` default path (dry-run transfer plan)  
- [ ] `allow_ai=True` — real AI context packing  
- [ ] AICtx `ctx run` with large repos  
- [ ] AICtx stale context detection  
- [ ] AICtx OCI backend  

---

## 9. Coding Workflow — Deep Paths

- [x] `INIT → LOAD_CONFIG → PREPARE_WORKSPACE → SCAN_REPOSITORY → BUILD_CONTEXT_PACK → PLAN`  
- [x] `PLAN → EXECUTE_TASK`  
- [x] `EXECUTE_TASK → BASIC_VERIFY → VERIFY_TASK`  
- [ ] `VERIFY_TASK → FIX_LOOP` — fix-loop retry path  
- [ ] `FIX_LOOP → EXECUTE_TASK` — re-execution after fix  
- [ ] `FIX_LOOP → BLOCKED` — max fix attempts reached  
- [x] `BLOCKED → RESUME_AVAILABLE` (fixed)  
- [ ] `RESUME_AVAILABLE → DONE`  
- [ ] `FAILED_AND_ROLLED_BACK` path  
- [ ] Dirty repo handling (`--allow-dirty`)  
- [ ] Max task limit (`max_total_tasks_exceeded`)  
- [ ] Same failure repeated twice → blocked  

---

## 10. Adapters / Integrations

- [ ] `WebResearchAdapter` — web search / fetch  
- [ ] `GitHubCliAdapter` — GitHub CLI ops  
- [ ] `MCPClientAdapter` — MCP server calls  

---

## 11. Safety & Policy

- [ ] `SafetyError` — blocked file access  
- [ ] `PolicyEngine` — runtime policy checks  
- [ ] `PrivacyEnforcer` — secret scrubbing  
- [ ] `NetworkEnforcer` — `file://` block  
- [ ] Browser tool sandbox  

---

## 12. Regression Checks

Run after any provider or core change:

- [ ] `pytest tests/core/test_state_machine.py`  
- [ ] `pytest tests/core/test_schemas_runtime.py`  
- [ ] `pytest tests/providers/`  
- [ ] `pytest tests/tools/`  
- [ ] `pytest tests/workflows/coding/`  
- [ ] Full suite: `pytest tests/` (760 tests)  

---

## Test Metadata

| Round | Date | Model | Provider | Notes |
|-------|------|-------|----------|-------|
| 1 | 2026-05-14 | openai.gpt-oss-120b-1:0 | AWS Bedrock (eu-central-1) | Phase 1-3 partial; empty diffs from model |
