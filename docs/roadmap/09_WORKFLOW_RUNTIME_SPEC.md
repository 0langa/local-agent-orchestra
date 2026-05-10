# 09 — WORKFLOW RUNTIME SPEC
## DAG Execution, Workflow Packs, and Execution Patterns

**Status:** DERIVED FROM 03_EXECUTION_MODEL
**Enforcement:** All workflow implementations must conform.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. DAG-Based Execution Model

### 1.1 Graph Structure
The workflow engine treats task execution as a Directed Acyclic Graph (DAG) where:
- Nodes = tasks (work orders)
- Edges = dependencies (task B needs task A's output)
- The engine resolves dependencies and executes tasks in topological order
- Independent tasks execute in parallel where safe

### 1.2 DAG Properties
- **Acyclic by construction:** Cycles are detected at workflow load time
- **Deterministic ordering:** Same DAG produces same execution order every time
- **Partial re-execution:** Failed branches can be re-run without re-executing successful ones
- **Parallelizable:** Independent branches execute concurrently

### 1.3 DAG Definition

```python
class ExecutionDAG:
    steps: List[Step]

    def validate(self) -> None:
        # Check for cycles
        # Check for unreachable steps
        # Check for undefined dependencies
        # Check for parallel safety declarations
        pass

    def topological_order(self) -> List[Step]:
        # Return steps in dependency-resolved order
        pass

    def parallel_groups(self) -> List[List[Step]]:
        # Return groups of steps that can execute in parallel
        pass

    def critical_path(self) -> List[Step]:
        # Return the longest dependency chain
        pass
```

### 1.4 Step Definition

```python
class Step:
    id: str                          # Unique step identifier
    agent: str                       # Agent role responsible
    type: str                        # Step type (workflow-defined)
    depends_on: List[str]            # Step IDs that must complete first
    condition: Optional[str]         # Conditional execution (e.g., "verification_failed")
    max_iterations: int = 1          # Maximum repetitions (for loops)
    timeout: Optional[int] = None    # Step timeout in seconds
    budget: Optional[StepBudget] = None  # Token/time budget for this step
    parallel_safe: bool = False      # Whether this step can run in parallel
    workspace_isolation: bool = True # Whether this step needs isolated workspace
```

---

## 2. Execution Patterns

### 2.1 Sequential (Default)
- Tasks execute one at a time
- Safest, easiest to debug
- Used when tasks have strong dependencies or shared state
- No parallelism overhead

### 2.2 Parallel (Independent Branches)
- Tasks with no interdependencies execute concurrently
- Requires thread-safe workspace or isolated subdirectories
- Useful for: refactoring multiple unrelated files, running independent test suites
- Workflow pack must declare parallel_safe=true

### 2.3 Pipeline (Stream Processing)
- Output of task N feeds directly into task N+1
- Useful for: code generation → linting → testing → formatting
- Maintains ordering but allows overlap

### 2.4 Map-Reduce (Scatter-Gather)
- A task fans out to N parallel subtasks, then a reduce task combines results
- Useful for: update all API endpoints, analyze all files in directory
- Requires consistent output schema across subtasks

### 2.5 Pattern Selection
- Default: Sequential
- Workflow pack declares supported patterns
- Pattern selection is configuration, not runtime improvisation
- Orchestrator respects declared pattern constraints

---

## 3. Workflow Pack Lifecycle

### 3.1 Lifecycle States

```
REGISTERED → LOADED → CONFIGURED → READY → EXECUTING → COMPLETED | FAILED | CANCELLED
```

| State | Description | Transitions |
|-------|-------------|-------------|
| REGISTERED | Pack known to capability registry | → LOADED |
| LOADED | Pack class loaded, DAG validated | → CONFIGURED |
| CONFIGURED | Configuration applied, agents bound | → READY |
| READY | All prerequisites satisfied | → EXECUTING |
| EXECUTING | Currently running | → COMPLETED / FAILED / CANCELLED |
| COMPLETED | All steps finished successfully | (terminal) |
| FAILED | Step failed, no recovery possible | (terminal) |
| CANCELLED | User or system cancelled | (terminal) |

### 3.2 Lifecycle Transitions
All transitions are logged as events. Failed transitions trigger error classification.

---

## 4. Workflow Execution

### 4.1 Execution Flow

```
1. Workflow selected from preset or CLI
   |
   v
2. Workflow runner validates DAG
   |
   v
3. Context pack built (repository scan, file index)
   |
   v
4. Configuration loaded and validated
   |
   v
5. Agents resolved (role → model → provider)
   |
   v
6. Tools registered and policies applied
   |
   v
7. Phase machine initialized (INIT state)
   |
   v
8. For each step in topological order:
   a. Check budgets (step + run)
   b. Transition to step phase
   c. Resolve agent and model
   d. Build agent prompt with context
   e. Invoke agent
   f. Process agent response
   g. Execute any tool calls (through protocol)
   h. Validate results
   i. Log all events
   j. Check step completion criteria
   |
   v
9. Final verification (if workflow defines it)
   |
   v
10. Report generation
    |
    v
11. Artifact collection and storage
    |
    v
12. Phase machine transitions to DONE
```

### 4.2 Step Execution Detail

```python
async def execute_step(self, step: Step, context: StepContext) -> StepResult:
    # 1. Budget check
    self._budget.check_before_step(step)

    # 2. Phase transition
    self._phase_machine.transition(f"EXECUTE_{step.id.upper()}")

    # 3. Agent resolution
    agent = self._model_registry.resolve(step.agent)

    # 4. Prompt building
    prompt = self._build_prompt(step, context)

    # 5. Agent invocation
    response = await self._agent_protocol.invoke(agent, prompt, context.tools)

    # 6. Response processing
    result = self._process_response(step, response)

    # 7. Tool execution (if any)
    for tool_call in result.tool_calls:
        policy_decision = self._policy_engine.evaluate(tool_call)
        if policy_decision == "allow":
            tool_result = await self._tool_protocol.invoke(tool_call)
        elif policy_decision == "ask":
            approval = await self._request_approval(tool_call)
            if approval:
                tool_result = await self._tool_protocol.invoke(tool_call)
            else:
                tool_result = ToolResult(success=False, error="Denied by user")
        else:
            tool_result = ToolResult(success=False, error="Denied by policy")

    # 8. Validation
    validation = self._validate_step_result(step, result)

    # 9. Logging
    self._ledger.log_step(step, result, validation)

    # 10. Budget update
    self._budget.record_step_usage(step, result.token_usage)

    return StepResult(
        step_id=step.id,
        success=validation.passed,
        output=result.output,
        artifacts=result.artifacts,
    )
```

---

## 5. Workflow Pack Requirements

### 5.1 Minimal Workflow Pack
The smallest valid workflow pack:

```python
from workflows.base import Workflow, Step, ExecutionDAG, AgentRole

class MinimalWorkflow(Workflow):
    workflow_id = "minimal"

    required_agents = [
        AgentRole(id="worker", capabilities=["tool_use"]),
    ]

    required_tools = ["filesystem.read"]

    dag = ExecutionDAG(
        steps=[
            Step(id="do_work", agent="worker", type="simple_task"),
        ]
    )

    async def execute_step(self, step: Step, context: StepContext) -> StepResult:
        # Implementation
        pass
```

### 5.2 Required Methods
Every workflow pack MUST implement:
- `workflow_id` — Unique identifier
- `required_agents` — List of agent roles with capabilities
- `required_tools` — List of tool IDs
- `dag` — ExecutionDAG with steps
- `execute_step(step, context)` — Step execution logic

### 5.3 Optional Methods
Workflow packs MAY implement:
- `verify(result)` — Custom verification logic
- `on_step_complete(step, result)` — Post-step hook
- `on_run_complete(results)` — Post-run hook
- `build_context(pack)` — Custom context building
- `generate_report(results)` — Custom report generation

---

## 6. Workflow Pack Registry

### 6.1 Discovery
Workflow packs register themselves on import via the capability registry:

```python
# In workflows/coding/__init__.py
from core.capability_registry import register_workflow
from .workflow import CodingWorkflow

register_workflow(CodingWorkflow)
```

### 6.2 Loading
```python
# Load all registered workflows
workflows = capability_registry.list_workflows()

# Load specific workflow
workflow = capability_registry.get_workflow("coding")
```

### 6.3 Validation
All registered workflows are validated at startup:
- DAG is acyclic
- All step dependencies exist
- All agent roles have capability declarations
- All tool IDs are registered
- Required configuration is documented

---

*End of 09_WORKFLOW_RUNTIME_SPEC.md*
