# 11 — EVENT AND LEDGER ARCHITECTURE
## Event-Sourcing, Ledger Schema, Replayability, and Auditability

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE, 03_EXECUTION_MODEL
**Enforcement:** All event handling must conform. Ledger integrity is Level 4.
**Violation Classification:** CONSTITUTIONAL VIOLATION (Level 4)

---

## 1. Event-Sourcing Principles

### 1.1 Fundamental Design
Run state is not stored as mutable state. It is derived from an append-only log of immutable events. This is the single source of truth for all execution state.

### 1.2 Event Sourcing Guarantees

| Guarantee | Description | Enforcement |
|-----------|-------------|-------------|
| Append-only | Events are never deleted or modified | Ledger file is append-only |
| Ordered | Events are strictly ordered by timestamp | Monotonic timestamp + sequence number |
| Immutable | Once written, an event is frozen | Write-once file semantics |
| Tamper-evident | Each event references previous event hash | Cryptographic hash chain |
| Complete | Every state transition is captured | All phase/tool/agent changes logged |
| Replayable | State can be reconstructed from events | Deterministic state reducer |

### 1.3 Why Event Sourcing

| Concern | How Event Sourcing Helps |
|---------|------------------------|
| Reproducibility | Same events → same state |
| Fault recovery | Replay from interruption point |
| Auditability | Complete decision chain preserved |
| Debugging | Full execution trajectory visible |
| Compliance | Immutable record of all actions |
| Resumption | Interrupted runs resume from last event |

---

## 2. Event Schema

### 2.1 Base Event Structure

```json
{
    "event_id": "evt_550e8400-e29b-41d4-a716-446655440000",
    "event_type": "agent.invoked",
    "event_version": "1.0",
    "timestamp": "2025-01-15T10:30:00.000000Z",
    "sequence": 42,
    "run_id": "run_550e8400-e29b-41d4-a716-446655440001",
    "parent_event_id": "evt_550e8400-e29b-41d4-a716-446655440039",
    "phase": "EXECUTE_TASK",
    "step_id": "step_003",
    "agent_id": "executor",
    "payload": {
        "model": "qwen3-coder",
        "provider": "ollama",
        "messages": [...],
        "tools_available": ["filesystem.read", "filesystem.write"]
    },
    "metadata": {
        "token_count": {"input": 2048, "output": 512},
        "latency_ms": 450,
        "provider_version": "ollama-0.3.0",
        "model_parameters": {"temperature": 0.7}
    },
    "previous_hash": "sha256:abc123...",
    "event_hash": "sha256:def456..."
}
```

### 2.2 Event Types (Complete)

#### Lifecycle Events
| Event Type | Payload | Description |
|-----------|---------|-------------|
| `run.initiated` | `{workflow_id, config_snapshot}` | Run started |
| `config.loaded` | `{config_hash, sources}` | Configuration loaded |
| `workflow.selected` | `{workflow_id, version}` | Workflow selected |
| `phase.transition` | `{from_phase, to_phase, reason}` | Phase changed |
| `run.completed` | `{final_status, duration_ms}` | Run finished |
| `run.interrupted` | `{reason, recoverable}` | Run interrupted |
| `run.resumed` | `{resume_from_event_id}` | Run resumed |

#### Agent Events
| Event Type | Payload | Description |
|-----------|---------|-------------|
| `agent.invoked` | `{agent_id, model, messages}` | Agent called |
| `agent.response` | `{agent_id, response, token_usage}` | Agent responded |
| `agent.error` | `{agent_id, error, classification}` | Agent error |
| `agent.retry` | `{agent_id, attempt, max_attempts}` | Agent retry |

#### Tool Events
| Event Type | Payload | Description |
|-----------|---------|-------------|
| `tool.called` | `{tool_id, params, risk_level}` | Tool invoked |
| `tool.result` | `{tool_id, success, output_size}` | Tool completed |
| `tool.denied` | `{tool_id, policy_id, reason}` | Tool denied |
| `tool.approved` | `{tool_id, approval_type}` | Tool approved |
| `tool.error` | `{tool_id, error, recoverable}` | Tool error |

#### Policy Events
| Event Type | Payload | Description |
|-----------|---------|-------------|
| `policy.evaluated` | `{tool_id, decision, policy_id}` | Policy checked |
| `policy.denied` | `{tool_id, decision, reason}` | Policy denied |
| `policy.approval_requested` | `{tool_id, risk_level, prompt}` | Approval asked |
| `policy.approval_granted` | `{tool_id, by, permanent}` | Approval given |
| `policy.approval_denied` | `{tool_id, by, permanent}` | Approval denied |

#### Budget Events
| Event Type | Payload | Description |
|-----------|---------|-------------|
| `budget.checked` | `{dimension, used, remaining, total}` | Budget checked |
| `budget.exceeded` | `{dimension, used, total}` | Budget exceeded |
| `budget.warning` | `{dimension, used, remaining, threshold}` | Budget warning |

#### Artifact Events
| Event Type | Payload | Description |
|-----------|---------|-------------|
| `artifact.created` | `{artifact_id, type, path, size}` | Artifact created |
| `artifact.updated` | `{artifact_id, diff_size}` | Artifact updated |

#### Context Events
| Event Type | Payload | Description |
|-----------|---------|-------------|
| `context.packed` | `{file_count, token_count, scope}` | Context compiled |
| `context.unpacked` | `{file_count, reason}` | Context unpacked |

---

## 3. Ledger Implementation

### 3.1 Storage Format
The ledger is stored as line-delimited JSON (JSONL) for append-only semantics.

### 3.2 Ledger File Structure

```
runs/<run-id>/
    ledger.jsonl          # Main event log
    ledger.index          # Index for fast event lookup
    ledger.hash           # Hash chain verification
    checkpoints/          # Periodic state snapshots
        checkpoint_00010.json
        checkpoint_00100.json
```

### 3.3 Hash Chain
Each event includes a hash of the previous event, creating a tamper-evident chain:

```python
def compute_event_hash(event: Event, previous_hash: str) -> str:
    data = {
        "event_type": event.event_type,
        "timestamp": event.timestamp,
        "sequence": event.sequence,
        "payload": event.payload,
        "previous_hash": previous_hash,
    }
    return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
```

### 3.4 Indexing
The ledger index enables fast queries:
```
by_event_type: {event_type → [sequence_numbers]}
by_phase: {phase → [sequence_numbers]}
by_agent: {agent_id → [sequence_numbers]}
by_tool: {tool_id → [sequence_numbers]}
by_step: {step_id → [sequence_numbers]}
```

### 3.5 Checkpoints
Periodic state snapshots for fast replay:
- Checkpoint every N events (default: 100)
- Checkpoint at phase boundaries
- Checkpoint on user approval
- Contains full reconstructed state at that point

---

## 4. Replayability

### 4.1 State Reconstruction

```python
def reconstruct_state(ledger: Ledger, 
                      up_to_sequence: Optional[int] = None) -> RunState:
    state = RunState()

    events = ledger.events(up_to_sequence=up_to_sequence)

    for event in events:
        state = apply_event(state, event)

    return state

def apply_event(state: RunState, event: Event) -> RunState:
    match event.event_type:
        case "run.initiated":
            state.status = "running"
            state.workflow_id = event.payload["workflow_id"]
        case "phase.transition":
            state.current_phase = event.payload["to_phase"]
        case "agent.invoked":
            state.current_agent = event.payload["agent_id"]
        case "tool.called":
            state.pending_tools.append(event.payload["tool_id"])
        case "tool.result":
            state.pending_tools.remove(event.payload["tool_id"])
        case "budget.exceeded":
            state.status = "halted"
        case "run.completed":
            state.status = event.payload["final_status"]
        # ... etc

    return state
```

### 4.2 Resume from Interruption

```python
async def resume_run(run_id: str) -> RunResult:
    ledger = load_ledger(run_id)

    # Find last checkpoint
    checkpoint = find_last_checkpoint(ledger)

    # Reconstruct state from checkpoint
    state = load_checkpoint(checkpoint)

    # Replay events after checkpoint
    for event in ledger.events_after(checkpoint.sequence):
        state = apply_event(state, event)

    # Validate workspace matches expected state
    await validate_workspace(state)

    # Continue execution from current phase
    return await continue_execution(state)
```

### 4.3 Deterministic Replay
- Event application must be deterministic
- Same event sequence always produces same state
- Non-deterministic components (model outputs) are captured in events
- Replay uses captured outputs, not live inference

---

## 5. Auditability

### 5.1 Inspectable Questions
From the ledger alone, a user must be able to answer:

| Question | Required Events |
|----------|----------------|
| What happened? | All events, ordered |
| Which model was used? | agent.invoked, agent.response |
| Which tools were called? | tool.called, tool.result |
| What was denied? | tool.denied, policy.denied |
| What files changed? | artifact.created, filesystem.write |
| Why did verification fail? | agent.response (verifier) |
| What artifacts were created? | artifact.created |
| How much did this cost? | budget.checked, agent.response |
| Who approved what? | policy.approval_granted |
| Was there an error? | agent.error, tool.error |

### 5.2 Ledger Queries
```python
# Get all tool invocations
tool_calls = ledger.query(event_type="tool.called")

# Get all denials
denials = ledger.query(event_type="policy.denied")

# Get timeline for a step
step_events = ledger.query(step_id="step_003")

# Get events by phase
phase_events = ledger.query(phase="EXECUTE_TASK")

# Get budget consumption
budget_events = ledger.query(event_type="budget.checked")

# Get all approvals
approvals = ledger.query(event_type="policy.approval_granted")
```

### 5.3 Trust Mechanism
The system does not ask users to trust it. It gives them the tools to verify:
- **Before a run:** Inspect the plan, check the context pack
- **During a run:** Watch state transitions, approve risky actions
- **After a run:** Read the full report, inspect every diff, check token usage
- **Across runs:** Compare ledgers, identify pattern changes

---

*End of 11_EVENT_AND_LEDGER_ARCHITECTURE.md*
