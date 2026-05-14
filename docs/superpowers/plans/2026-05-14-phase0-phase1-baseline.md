# Phase 0 And Phase 1 Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish roadmap Phase 0 evidence governance and deliver the smallest Phase 1 runtime-safety slice.

**Architecture:** Phase 0 is documentation and validation-contract work: support states, Tier-1 journey contracts, current live evidence, and a baseline smoke gate. Phase 1 starts with one reusable tool invocation service that centralizes policy evaluation, operation-level risk, and interface-safe non-execution for approval-required tools.

**Tech Stack:** Python 3.12, Typer/FastAPI, pytest, PowerShell devtest runner, Markdown docs.

---

### Task 1: Phase 0 Evidence Docs

**Files:**
- Create: `docs/SUPPORT_MATRIX.md`
- Create: `docs/TIER1_CONTRACTS.md`
- Modify: `docs/README.md`
- Modify: `docs/API_REFERENCE.md`
- Modify: `docs/USER_GUIDE.md`
- Modify: `docs/AGENT_OPERATIONS.md`
- Modify: `BASELINE-ROADMAP.md`
- Modify: `live-ai-testing.md`

- [ ] **Step 1: Document support states**

Create `docs/SUPPORT_MATRIX.md` with explicit stable/beta/experimental/internal states for provider lanes, providers, presets, workflows, interfaces, tools, and advanced subsystems. Use `stable`, `beta`, `experimental`, and `internal` only.

- [ ] **Step 2: Document Tier-1 contracts**

Create `docs/TIER1_CONTRACTS.md` mapping install/doctor, provider setup, inspect/plan, stable presets, report/resume, artifacts, API, Web, and Desktop availability to CLI/API/docs/tests.

- [ ] **Step 3: Wire docs index and references**

Link both new docs from `docs/README.md`, mention them in `docs/AGENT_OPERATIONS.md`, and update API/User Guide support-state language so exposed claims do not exceed evidence.

- [ ] **Step 4: Mark roadmap Phase 0 complete**

Update `BASELINE-ROADMAP.md` Phase 0 with dated completion evidence and leave Phase 1 in progress with the smallest slice scoped to tool invocation service.

### Task 2: Baseline Smoke Gate

**Files:**
- Modify: `devtest/run-devtest.ps1`
- Modify: `devtest/all-test-commands.md`
- Modify: `docs/DEV_TESTING.md`
- Test: command-line invocation of `run-devtest.ps1 -Mode baseline -NoPrompt`

- [ ] **Step 1: Verify missing baseline mode fails**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt
```

Expected before implementation: parameter validation rejects `baseline`.

- [ ] **Step 2: Add baseline mode**

Add `baseline` to the mode set. It must run instruction drift, CLI help, doctor skip-connectivity, provider templates, preset registry load, tool registry load, and pytest collect-only.

- [ ] **Step 3: Document baseline mode**

Add the command to `devtest/all-test-commands.md` and `docs/DEV_TESTING.md`.

### Task 3: Smallest Phase 1 Tool Invocation Slice

**Files:**
- Create: `core/tool_invocation.py`
- Modify: `core/public_api.py`
- Modify: `interfaces/api_server/app.py`
- Modify: `interfaces/web_ui/app.py`
- Test: `tests/test_tool_invocation.py`
- Test: `tests/test_api_server.py`
- Test: `tests/test_web_ui.py`

- [ ] **Step 1: Write failing service tests**

Add tests proving filesystem `read` is allowed, filesystem `write` requires approval and does not write, high-risk shell is denied for interface policy, and ledger receives policy/tool events for allowed calls.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
pytest -q tests/test_tool_invocation.py tests/test_api_server.py::TestTools tests/test_web_ui.py::TestTools
```

Expected before implementation: import or assertion failure for missing centralized service and approval-required response.

- [ ] **Step 3: Implement minimal service**

Create `ToolInvoker` that resolves operation-level risk, calls `PolicyEngine.evaluate()`, returns `approval_required` without executing on `ask`, emits `TOOL_CALLED` and `TOOL_RESULT_RECEIVED` around allowed execution, and exposes a strict interface policy with high/critical denied.

- [ ] **Step 4: Route API/Web through the service**

Replace direct tool invocations in API and Web UI tool endpoints with `ToolInvoker`. Add `requires_approval` and `policy` fields to response models.

- [ ] **Step 5: Run green tests**

Run the same focused pytest command and then directive/baseline devtest.

### Task 4: Docs Sync And Verification

**Files:**
- Modify: `docs/CHANGELOG.md`
- Modify: `.kimi/memory.jsonl`

- [ ] **Step 1: Append changelog entry**

Add a 2026-05-14 entry for Phase 0 completion, baseline devtest mode, and Phase 1 tool invocation service slice.

- [ ] **Step 2: Update memory graph**

Append session facts to `.kimi/memory.jsonl`.

- [ ] **Step 3: Run gates**

Run:

```powershell
python scripts/check-agent-instructions.py
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode baseline -NoPrompt
powershell -ExecutionPolicy Bypass -File .\devtest\run-devtest.ps1 -Mode directive -NoPrompt
pytest -q tests/test_tool_invocation.py tests/test_api_server.py::TestTools tests/test_web_ui.py::TestTools
```

Expected: all pass. If full or live AI tests are not run, state that explicitly.
