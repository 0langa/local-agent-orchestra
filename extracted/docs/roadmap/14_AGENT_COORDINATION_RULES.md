# 14 — AGENT COORDINATION RULES
## Agent Roles, Model Classes, and Capability Matrix

**Status:** DERIVED FROM 03_EXECUTION_MODEL, 08_PROVIDER_AND_MODEL_ARCHITECTURE
**Enforcement:** All agent definitions must conform.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. Agent Roles

### 1.1 Role Definition
An agent role is a logical capability requirement, not a model name. The runtime resolves roles to configured models via the capability registry.

### 1.2 Standard Roles

| Role | Capabilities | Responsibility | Model Class |
|------|-------------|----------------|-------------|
| orchestrator | reasoning, instruction-following | Decompose intent, plan execution, manage dependencies | Reasoning-heavy |
| planner | reasoning, long-context | Generate detailed execution plans | Reasoning-heavy |
| executor | code-generation, tool-use | Implement work orders, edit files, run tests | Code-optimized |
| verifier | critique, structured-output | Evaluate correctness against criteria | Fast/cheap |
| summarizer | compression, extraction | Summarize content, extract key points | Fast/cheap |
| classifier | labeling, routing | Classify tasks, route to appropriate handlers | Fast/cheap |
| researcher | web-search, synthesis | Gather information, compare sources | Long-context |
| critic | evaluation, analysis | Evaluate plans, identify risks | Reasoning-heavy |

### 1.3 Custom Roles
Workflow packs may define custom roles. Custom roles must declare:
- Role ID (unique within workflow)
- Required capabilities (from capability registry)
- Optional: Recommended model class
- Optional: Fallback capabilities

---

## 2. Model Classes

### 2.1 Model Classification

| Class | Strengths | Weaknesses | Best Role |
|-------|-----------|------------|-----------|
| Reasoning Models | Complex planning, debugging, architecture | Slower, expensive, may overthink | orchestrator, planner, critic |
| Code-Optimized | Code generation, refactoring, patterns | May miss big-picture context | executor |
| Fast/Cheap | Verification, simple edits, high-volume | Limited reasoning depth | verifier, summarizer, classifier |
| Long-Context | Large codebase understanding | Expensive, not always needed | researcher, context analysis |
| Local Models | Zero latency, zero cost, privacy | Lower capability ceiling | verifier, simple refactors |

### 2.2 Model Class Selection
The orchestrator selects model class based on task characteristics:

| Task Characteristic | Model Class |
|-------------------|-------------|
| Requires multi-step reasoning | Reasoning |
| Requires code generation | Code-optimized |
| Requires simple evaluation | Fast/cheap |
| Requires large input processing | Long-context |
| Requires low latency | Local |
| Requires privacy | Local |

---

## 3. Agent Protocol

### 3.1 Message Schema

```python
class AgentMessage:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[ToolResult]] = None
    metadata: Optional[Dict[str, Any]] = None

class AgentRequest:
    messages: List[AgentMessage]
    tools: Optional[List[ToolSchema]] = None
    model_config: Optional[ModelConfig] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

class AgentResponse:
    content: str
    tool_calls: List[ToolCall]
    token_usage: TokenUsage
    model_used: str
    provider_used: str
    finish_reason: str
    latency_ms: int
```

### 3.2 Agent Invocation Flow

```
1. Workflow requests agent for step
   |
   v
2. Runtime resolves role to model
   |
   v
3. Runtime builds context (context pack + step context)
   |
   v
4. Runtime formats agent prompt
   |
   v
5. Runtime invokes model via provider adapter
   |
   v
6. Model generates response
   |
   v
7. Runtime parses response
   |
   v
8. Runtime extracts tool calls (if any)
   |
   v
9. Runtime returns response to workflow
```

### 3.3 Agent Context

```python
class AgentContext:
    run_id: str
    step_id: str
    workflow_id: str
    agent_role: str
    model_binding: ModelBinding
    context_pack: ContextPack
    previous_results: List[StepResult]
    available_tools: List[ToolSchema]
    budget_remaining: BudgetStatus
    memory_access: Optional[MemoryQuery]
```

---

## 4. Multi-Agent Coordination

### 4.1 Coordinator Pattern
The orchestrator coordinates multiple agents:
1. Planner generates execution plan
2. Executor implements plan steps
3. Verifier evaluates results
4. Orchestrator decides next action based on verification

### 4.2 Handoff Rules
- Agent handoffs are logged as events
- Each agent receives full context of previous agents' work
- Agents do not share mutable state
- Context is passed through the context pack

### 4.3 Conflict Resolution
When agents disagree:
1. Log the conflict with full context
2. Escalate to orchestrator
3. Orchestrator may: replan, retry, or request user input
4. User has final authority

### 4.4 Agent Independence
- Agents are stateless between invocations
- Agents do not communicate directly with each other
- All communication goes through the orchestrator
- Agents do not retain memory between steps (memory is explicit)

---

## 5. Capability-Based Resolution

### 5.1 Resolution Process

```
Workflow requests: role=executor, capabilities=[code-generation, python]
    |
    v
ModelRegistry queries capability registry
    |
    v
Filter: Models that support code-generation AND python
    |
    v
Score: Match quality, cost, latency, availability
    |
    v
Select: Best matching model
    |
    v
Return: ModelBinding(provider=ollama, model=qwen3-coder:32b)
```

### 5.2 Resolution Constraints
- Must respect privacy mode (local-only → only local models)
- Must respect budget (prefer cheaper models when budget low)
- Must respect user preferences (preferred models)
- Must handle provider unavailability (fallback chain)
- Must cache resolution results per run

---

*End of 14_AGENT_COORDINATION_RULES.md*
