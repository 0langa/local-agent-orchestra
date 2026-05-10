# 15 — PARALLEL EXECUTION PROTOCOL
## Parallel Safety, Concurrency Rules, and Task Decomposition

**Status:** DERIVED FROM 04_SWARM_GOVERNANCE, 09_WORKFLOW_RUNTIME_SPEC
**Enforcement:** All parallel execution must conform.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. Parallel Safety Model

### 1.1 Parallel Safety Levels

| Level | Description | Concurrent Execution |
|-------|-------------|---------------------|
| PARALLEL_SAFE | Step can execute concurrently with any other step | Allowed |
| PARALLEL_ISOLATED | Step can execute concurrently with steps in different workspaces | Allowed with isolation |
| PARALLEL_READ_ONLY | Step only reads; can execute concurrently with other read-only steps | Allowed with read-only |
| SEQUENTIAL_REQUIRED | Step must execute alone | Forbidden |
| DEPENDENCY_BOUND | Step can execute concurrently only with non-dependent steps | Allowed per DAG |

### 1.2 Parallel Safety Declaration
Workflow packs declare parallel safety per step:

```python
Step(
    id="refactor_file",
    agent="executor",
    type="refactoring",
    parallel_safe=True,           # This step can run in parallel
    workspace_isolation=True,     # Needs isolated workspace
)
```

### 1.3 Parallel Execution Rules
1. Steps with `SEQUENTIAL_REQUIRED` never execute concurrently
2. Steps with `PARALLEL_SAFE` execute concurrently when possible
3. Steps with `PARALLEL_ISOLATED` execute concurrently with workspace isolation
4. Read-only steps can execute concurrently with other read-only steps
5. Steps with shared dependencies execute sequentially
6. File write operations require exclusive file locks

---

## 2. Concurrency Controls

### 2.1 Maximum Concurrency

| Resource | Default Limit | Configurable |
|----------|--------------|--------------|
| Concurrent agents | 5 | Yes (per-workflow) |
| Concurrent tool calls | 10 | Yes (per-run) |
| File write operations | 1 (exclusive) | No |
| Network requests | 5 | Yes (per-provider) |
| Memory operations | Unlimited (reads), 1 (writes) | No |

### 2.2 Resource Locking

```python
class ResourceLock:
    async def acquire_file_lock(self, path: str, 
                                 mode: Literal["read", "write"]) -> bool:
        # Write locks are exclusive
        # Read locks are shared
        # Returns True if lock acquired
        pass

    async def release_file_lock(self, path: str) -> None:
        pass

    async def acquire_workspace(self, agent_id: str) -> Path:
        # Allocate isolated workspace for agent
        pass

    async def release_workspace(self, agent_id: str) -> None:
        pass
```

### 2.3 Workspace Isolation
Parallel agents receive isolated workspaces:
```
workspace/
    shared/           # Read-only shared files
        (symlinks to original files)
    agent_001/        # Agent 1's workspace
        (isolated, writable)
    agent_002/        # Agent 2's workspace
        (isolated, writable)
```

---

## 3. Task Decomposition for Parallelism

### 3.1 Decomposition Rules

Valid parallel decomposition:
- Independent file operations (different files)
- Independent analysis tasks (different components)
- Batch processing (same operation on different items)
- Parallel research (different queries)

Invalid parallel decomposition:
- Operations on the same file
- Tasks with data dependencies
- Sequential algorithm steps
- Tasks requiring shared mutable state

### 3.2 Decomposition Process

```
1. Analyze task for parallelism opportunities
   |
   v
2. Identify independent subtasks
   |
   v
3. Check for resource conflicts
   |
   v
4. Allocate workspaces
   |
   v
5. Execute subtasks in parallel
   |
   v
6. Collect results
   |
   v
7. Merge results (if needed)
   |
   v
8. Validate merged results
```

### 3.3 Merge Requirements
When parallel subtasks produce results that must be merged:
- Merge must be deterministic
- Merge must handle conflicts (log and escalate)
- Merge must preserve all subtask outputs
- Merge must be validated

---

## 4. Parallel Execution Monitoring

### 4.1 Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Parallelism ratio | Concurrent agents / Total agents | > 0.5 |
| Resource contention | Lock wait time / Total time | < 0.1 |
| Speedup | Sequential time / Parallel time | > 1.5 |
| Overhead | Coordination time / Total time | < 0.2 |
| Conflict rate | Conflicts / Total parallel tasks | < 0.05 |

### 4.2 Monitoring
- Track parallelism ratio per run
- Alert on serial collapse (ratio < 0.3)
- Log resource contention events
- Report speedup in final artifacts

---

*End of 15_PARALLEL_EXECUTION_PROTOCOL.md*
