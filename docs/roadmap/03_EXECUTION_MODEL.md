# 03 — EXECUTION MODEL
## Event-Sourced Runtime, Phase Machine, and Bounded Execution

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE
**Enforcement:** All runtime behavior must conform to this model.
**Violation Classification:** ARCHITECTURAL BREACH (Level 3)

---

## 1. Event-Sourced State Model

### 1.1 Fundamental Principle
Run state is not mutated in place. It is derived from an append-only log of events. This is not a logging convenience; it is a foundational architectural decision with implications for reproducibility, fault recovery, auditability, and debugging.

### 1.2 Event Types (Canonical)

```python
class EventType(Enum):
    # Lifecycle events
    RUN_INITIATED = "run.initiated"
    CONFIG_LOADED = "config.loaded"
    WORKFLOW_SELECTED = "workflow.selected"
    PHASE_TRANSITION = "phase.transition"
    RUN_COMPLETED = "run.completed"
    RUN_INTERRUPTED = "run.interrupted"
    RUN_RESUMED = "run.resumed"

    # Agent events
    AGENT_INVOKED = "agent.invoked"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"
    AGENT_RETRY = "agent.retry"

    # Tool events
    TOOL_CALLED = "tool.called"
    TOOL_RESULT = "tool.result"
    TOOL_DENIED = "tool.denied"
    TOOL_APPROVED = "tool.approved"
    TOOL_ERROR = "tool.error"

    # Policy events
    POLICY_EVALUATED = "policy.evaluated"
    POLICY_DENIED = "policy.denied"
    POLICY_APPROVAL_REQUESTED = "policy.approval_requested"
    POLICY_APPROVAL_GRANTED = "policy.approval_granted"
    POLICY_APPROVAL_DENIED = "policy.approval_denied"

    # Artifact events
    ARTIFACT_CREATED = "artifact.created"
    ARTIFACT_UPDATED = "artifact.updated"

    # Context events
    CONTEXT_PACKED = "context.packed"
    CONTEXT_UNPACKED = "context.unpacked"

    # Budget events
    BUDGET_CHECKED = "budget.checked"
    BUDGET_EXCEEDED = "budget.exceeded"

    # Error events
    ERROR_CLASSIFIED = "error.classified"
    ERROR_RECOVERED = "error.recovered"
    ERROR_FATAL = "error.fatal"
```

### 1.3 Event Schema
Every event in the ledger:
```json
{
    "event_id": "uuid",
    "event_type": "agent.invoked",
    "timestamp": "2025-01-15T10:30:00Z",
    "run_id": "uuid",
    "phase": "EXECUTE_TASK",
    "step_id": "step-003",
    "agent_id": "executor",
    "payload": {},
    "metadata": {
        "model_used": "qwen3-coder",
        "provider": "ollama",
        "token_count": {"input": 2048, "output": 512},
        "latency_ms": 450
    }
}
```

### 1.4 Event Store Guarantees
- **Append-only:** Events are never deleted or modified.
- **Ordered:** Events are strictly ordered by monotonic timestamp within a run.
- **Immutable:** Once written, an event is frozen.
- **Tamper-evident:** Each event references the hash of the previous event.
- **Queryable:** Events can be filtered by type, agent, phase, tool, and time range.

### 1.5 State Reconstruction
At any point, the current state is derived by replaying events from the ledger:
```
State(t) = Reduce(Events[0:t], StateReducer)
```
The StateReducer is deterministic and versioned. State reconstruction must produce identical results for the same event sequence.

---

## 2. Runtime Phase Machine

### 2.1 Phase Definitions

```
INIT → LOAD_CONFIG → PREPARE_WORKSPACE → SCAN_REPOSITORY → BUILD_CONTEXT_PACK
→ PLAN → EXECUTE_TASK → BASIC_VERIFY → VERIFY_TASK → FIX_LOOP
→ FINAL_VERIFY → FINAL_REPORT → RESUME_AVAILABLE → DONE
```

### 2.2 Phase Descriptions

| Phase | Responsibility | Abortable | Retryable |
|-------|---------------|-----------|-----------|
| INIT | Allocate run ID, initialize ledger | Yes | No |
| LOAD_CONFIG | Load and validate configuration | Yes | No |
| PREPARE_WORKSPACE | Create run directory, set up environment | Yes | No |
| SCAN_REPOSITORY | Scan target directory, build file index | Yes | Yes |
| BUILD_CONTEXT_PACK | Compile context bundle for agents | Yes | Yes |
| PLAN | Generate execution plan (orchestrator) | Yes | Yes (bounded) |
| EXECUTE_TASK | Execute planned steps (executor) | Yes | Yes (bounded) |
| BASIC_VERIFY | Quick sanity check (executor self-verify) | Yes | Yes |
| VERIFY_TASK | Full verification (verifier) | Yes | Yes |
| FIX_LOOP | Address verifier findings (bounded) | Yes | Yes (bounded) |
| FINAL_VERIFY | Comprehensive final verification | Yes | Yes |
| FINAL_REPORT | Generate run report and artifacts | Yes | No |
| RESUME_AVAILABLE | Checkpoint for potential resumption | No | No |
| DONE | Finalize, cleanup | No | No |
```

### 2.3 Phase Transition Rules
- Transitions are logged as `phase.transition` events
- Failed transitions trigger error classification
- The FIX_LOOP phase is bounded by `MAX_FIX_ITERATIONS`
- RESUME_AVAILABLE is a terminal state for interrupted runs
- No phase may be skipped except through explicit error recovery

### 2.4 Error Classification

| Error Class | Behavior | Retry Strategy |
|-------------|----------|---------------|
| TRANSIENT | Provider timeout, rate limit | Exponential backoff, switch provider |
| RECOVERABLE | Tool failure, bad agent output | Retry with modified prompt |
| VERIFICATION | Verifier rejected changes | Enter FIX_LOOP (bounded) |
| CONFIGURATION | Bad config, missing dependency | Halt, report to user |
| PERMISSION | Policy denial | Log, request approval if applicable |
| FATAL | Unrecoverable system error | Halt, preserve state for debugging |

---

## 3. Bounded Execution

### 3.1 Budget Dimensions
All loops and executions are explicitly bounded:

| Budget | Default | Configurable | Behavior on Exhaustion |
|--------|---------|--------------|----------------------|
| `MAX_PLAN_RETRIES` | 3 | Per-workflow | Halt with partial plan |
| `MAX_FIX_ITERATIONS` | 5 | Per-workflow | Return best-effort result |
| `MAX_VERIFIER_ATTEMPTS` | 3 | Per-workflow | Accept with warning |
| `MAX_TOTAL_TOKENS` | 100000 | Per-run | Halt cleanly, preserve state |
| `MAX_WALL_TIME` | 3600s | Per-run | Halt cleanly, mark resumable |
| `MAX_TOOL_CALLS` | 500 | Per-run | Halt with explanation |
| `MAX_AGENT_INVOCATIONS` | 100 | Per-run | Halt with explanation |
| `MAX_CONCURRENT_AGENTS` | 5 | Per-workflow | Queue and serialize |

### 3.2 Budget Enforcement
- Budgets are checked before every agent invocation and tool call
- Budget exhaustion triggers `budget.exceeded` event
- Runs that exhaust budgets halt cleanly — they do not crash
- Budget state is included in every event's metadata
- Budget consumption is reported in the final artifact

### 3.3 Step Budget (Swarm-Aware)
For swarm execution, the total step budget is a **swarm-wide allocation**, not per-agent. Step consumption analysis:

| Activity | Typical Steps | Optimization |
|----------|---------------|--------------|
| Initial DAG generation | 50-150 | Clear prompt structure |
| Task assignment | 100-300 | Batch similar assignments |
| Sub-agent execution | 5-20 per agent | Efficient prompts |
| Cross-verification | 100-500 | Targeted verification |
| Replanning | 200-800 | **Primary optimization target** |

---

## 4. Execution Loop Patterns

### 4.1 Default: Plan-then-Execute with Reflexion
1. Orchestrator produces complete plan before any execution
2. Executor executes plan step-by-step without replanning
3. Verifier checks each step against the plan
4. FIX_LOOP uses Reflexion (self-correction with lessons learned buffer)

### 4.2 Alternative Patterns (Workflow-Defined)

**Pattern: Sequential (Default)**
- Tasks execute one at a time
- Safest, easiest to debug
- Used for strong dependencies or shared state

**Pattern: Parallel (Independent Branches)**
- Tasks with no interdependencies execute concurrently
- Requires thread-safe workspace or isolated subdirectories
- Workflow pack declares parallel safety

**Pattern: Pipeline (Stream Processing)**
- Output of task N feeds into task N+1
- Useful for: code gen → lint → test → format

**Pattern: Map-Reduce (Scatter-Gather)**
- Task fans out to N parallel subtasks, then reduce combines
- Useful for bulk operations on independent items

### 4.3 Loop Pattern Selection
- Default workflow uses Plan-then-Execute
- Workflow packs declare their supported patterns
- Pattern selection is workflow configuration, not runtime improvisation

---

## 5. Fault Recovery

### 5.1 Resume from Interruption
Any interrupted run can be resumed from its exact state:
- Event-sourced ledger captures all state transitions
- Idempotent operations where possible
- Explicit checkpointing at phase boundaries
- The `RESUME_AVAILABLE` state enables resumption

### 5.2 Resume Requirements
- Resume must reconstruct state by replaying events
- Resume must validate that the workspace matches expected state
- Resume must re-evaluate budgets (remaining budget = total - consumed)
- Resume must not re-execute already-completed steps unless explicitly requested

### 5.3 Crash Recovery
- Ledger is flushed to disk after every event
- Temporary workspace is preserved on unexpected termination
- A `doctor.py` script can inspect and recover interrupted runs
- Corrupted ledgers are detected via hash chain validation

---

## 6. Deterministic Execution Requirements

### 6.1 Deterministic Components
The following MUST be deterministic given the same inputs:
- Phase machine transitions
- Policy evaluations (same input → same decision)
- Tool invocation sequencing
- Budget calculations
- Event ordering
- Artifact naming and placement

### 6.2 Non-Deterministic Components
The following are acknowledged non-deterministic:
- Model inference outputs
- Provider latency and availability
- External tool responses (filesystem state, network calls)
- User approval decisions

### 6.3 Determinism Preservation
Non-deterministic outputs are captured as events and become part of the deterministic replay state. A replay uses captured outputs, not live inference.

---

*End of 03_EXECUTION_MODEL.md*
