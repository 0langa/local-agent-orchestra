# 10 — TOOL AND POLICY SYSTEM
## Mediated Tool Invocation, Policy Engine, and Approval Gradient

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE, 07_SUBSYSTEM_DEFINITIONS
**Enforcement:** All tool implementations and policy decisions must conform.
**Violation Classification:** ARCHITECTURAL BREACH (Level 3) for bypass; BOUNDARY CONCERN (Level 2) for implementation

---

## 1. Mediated Tool Protocol

### 1.1 Core Principle
No agent directly executes arbitrary actions. All side effects go through named, policy-checked tools. The tool protocol is the ONLY path from agent decision to system action.

### 1.2 Tool Categories

| Category | Operations | Risk Level | Default Policy |
|----------|-----------|------------|---------------|
| filesystem.read | Read file contents | NONE | Auto-execute |
| filesystem.list | List directory | NONE | Auto-execute |
| filesystem.stat | File metadata | NONE | Auto-execute |
| filesystem.write | Write/create file | MEDIUM | Ask |
| filesystem.delete | Delete file | HIGH | Ask + reason |
| filesystem.move | Move/rename file | MEDIUM | Ask |
| shell.execute | Execute shell command | HIGH | Ask + classification |
| git.clone | Clone repository | MEDIUM | Ask |
| git.diff | Show diff | NONE | Auto-execute |
| git.commit | Commit changes | LOW | Auto-execute with log |
| git.push | Push to remote | HIGH | Ask |
| http.request | Outbound HTTP | HIGH | Ask |
| memory.read | Read from memory | NONE | Auto-execute |
| memory.write | Write to memory | LOW | Auto-execute with log |
| artifact.create | Create artifact | LOW | Auto-execute with log |

### 1.3 Tool Protocol Interface

```python
class ToolProtocol(Protocol):
    @property
    def tool_id(self) -> str:
        # Globally unique tool identifier
        # Format: "category.operation" (e.g., "filesystem.read")
        ...

    @property
    def schema(self) -> ToolSchema:
        # Tool description, parameters, return type
        ...

    @property
    def risk_level(self) -> RiskLevel:
        # NONE, LOW, MEDIUM, HIGH, CRITICAL
        ...

    async def invoke(self, params: Dict[str, Any],
                     context: ToolContext) -> ToolResult:
        # Execute the tool with validated parameters
        # Enforce boundaries from context
        # Return structured result
        ...
```

### 1.4 Tool Schema

```python
class ToolSchema:
    description: str              # Human-readable description
    parameters: Dict[str, ParamSchema]  # Parameter definitions
    returns: ReturnSchema         # Return value schema
    examples: List[ToolExample]   # Usage examples

class ParamSchema:
    type: str                     # JSON schema type
    description: str              # Parameter description
    required: bool = True         # Whether parameter is required
    default: Optional[Any] = None # Default value
    enum: Optional[List[str]] = None  # Allowed values

class ReturnSchema:
    type: str                     # JSON schema type
    description: str              # Return value description
```

### 1.5 Tool Context

```python
class ToolContext:
    run_id: str                   # Current run identifier
    step_id: str                  # Current step identifier
    agent_id: str                 # Calling agent identifier
    allowed_paths: List[str]      # Permitted filesystem paths
    denied_paths: List[str]       # Forbidden filesystem paths
    allowed_commands: List[str]   # Permitted shell commands
    denied_commands: List[str]    # Forbidden shell commands
    network_allowed: bool         # Whether network access permitted
    max_file_size: int            # Maximum file read size
    budget: ToolBudget            # Remaining budget for this tool
    workspace: Path               # Workspace directory
```

---

## 2. Policy Engine

### 2.1 Purpose
The policy engine is the gatekeeper for all tool invocations. It evaluates every tool call against configured policies and returns a decision.

### 2.2 Policy Decision Types

| Decision | Behavior | User Impact |
|----------|----------|-------------|
| `allow` | Proceed without interruption | None |
| `deny` | Block and log the attempt | Notification |
| `ask` | Pause and surface approval request | Must approve/deny |
| `path_boundary` | Restrict to declared scope | Silent enforcement |
| `command_allowlist` | Only permit listed commands | Silent enforcement |
| `command_denylist` | Block listed commands | Silent enforcement |
| `network_restriction` | Block/limit outbound HTTP | Silent enforcement |
| `delete_restriction` | Block delete operations | May prompt for override |
| `budget_limit` | Cap token/API cost per run | Halt when exceeded |
| `local_only` | Prevent remote model/network | Silent enforcement |
| `strict_private` | Block sensitive file upload | Silent enforcement |

### 2.3 Policy Evaluation Flow

```
Tool Call Received
    |
    v
Check local_only mode
    | (if local-only and tool requires network → deny)
    v
Check strict_private mode
    | (if strict-private and file is sensitive → deny upload)
    v
Check budget limits
    | (if budget exceeded → deny)
    v
Check path boundaries
    | (if path outside allowed → deny)
    v
Check command allowlist/denylist
    | (if command not allowed → deny)
    v
Check network restrictions
    | (if network not allowed → deny)
    v
Check delete restrictions
    | (if delete not allowed → ask or deny)
    v
Evaluate risk level
    | (NONE → allow, LOW → allow+log, MEDIUM → ask, HIGH → ask+reason, CRITICAL → deny)
    v
Return PolicyDecision
```

### 2.4 Policy Configuration

```yaml
policies:
  default:
    risk_level:
      none: allow
      low: allow
      medium: ask
      high: ask
      critical: deny
    path_boundaries:
      allowed: ["./workspace"]
      denied: ["./workspace/.git", "./workspace/secrets"]
    command_allowlist: ["git", "python", "pytest", "pip"]
    command_denylist: ["rm -rf /", "sudo", "chmod 777"]
    network:
      allowed: false
      allowed_hosts: []
    delete:
      allowed: false
      require_reason: true
    budget:
      max_tokens_per_run: 100000
      max_cost_per_run: 10.00
      max_wall_time: 3600
    privacy:
      mode: local-preferred
      sensitive_patterns: ["*.key", "*.pem", "*.env", "*secret*"]
```

### 2.5 Policy Decision Schema

```python
class PolicyDecision:
    decision: Literal["allow", "deny", "ask"]
    reason: str                       # Human-readable explanation
    policy_id: str                    # Which policy triggered this
    risk_level: RiskLevel
    suggested_approval: Optional[str] # For "ask" decisions
    override_possible: bool           # Whether user can override
```

---

## 3. Approval Gradient

### 3.1 Risk Levels and Behaviors

| Risk Level | Examples | Behavior |
|------------|----------|----------|
| NONE | Read files, run tests, git status | Auto-execute |
| LOW | Edit existing files, git commit | Auto-execute with ledger logging |
| MEDIUM | Create new files, install deps | Require confirmation |
| HIGH | Delete files, modify git history, network calls | Require explicit approval + reason |
| CRITICAL | System-wide installs, credential access, deploy | Require password/second factor |

### 3.2 Approval Workflow

```
Policy Decision: ask
    |
    v
Render approval prompt to user
    |
    v
User reviews:
  - What will happen
  - Why it was requested
  - Risk level
  - Alternatives (if any)
    |
    v
User decision:
  - Approve → Execute, log approval
  - Approve always → Execute, update policy
  - Deny → Skip, log denial
  - Deny always → Skip, update policy
    |
    v
Continue execution
```

### 3.3 Approval Prompt Requirements
Every approval prompt must include:
- **Action description:** Plain language of what will happen
- **Risk explanation:** Why this requires approval
- **Scope:** What files/directories are affected
- **Reversibility:** Whether the action can be undone
- **Alternatives:** Less risky alternatives if applicable
- **Policy reference:** Which policy triggered this approval

### 3.4 Beginner Default Behavior
All beginner presets default to `ask` for all non-read operations. The approval workflow is the primary safety mechanism for non-technical users.

---

## 4. Tool Registry

### 4.1 Registration
Tools register themselves on import:

```python
# In tools/filesystem/__init__.py
from core.capability_registry import register_tool
from .read import FilesystemReadTool
from .write import FilesystemWriteTool

register_tool(FilesystemReadTool())
register_tool(FilesystemWriteTool())
```

### 4.2 Discovery
```python
# List all available tools
tools = capability_registry.list_tools()

# Get specific tool
tool = capability_registry.get_tool("filesystem.read")

# Filter by category
tools = capability_registry.list_tools(category="filesystem")

# Filter by risk level
tools = capability_registry.list_tools(max_risk=RiskLevel.MEDIUM)
```

### 4.3 Validation
All registered tools are validated at startup:
- Tool ID is unique
- Schema is valid
- Risk level is declared
- Invoke method is implemented
- Required parameters are documented

---

## 5. Security Requirements

### 5.1 Path Confinement
- All file operations constrained to declared paths
- Path traversal attempts blocked (../../etc/passwd)
- Symlink resolution controlled
- Absolute paths validated against allowed paths

### 5.2 Command Classification
Every shell command classified as:
- `safe`: Read-only or low-risk (ls, cat, git status)
- `install`: Package installation (pip install, npm install)
- `destructive`: File deletion, history modification
- `deploy`: Production deployment

### 5.3 Secret Redaction
- Secrets redacted from all logs and artifacts
- Redaction happens before model context packing
- Secret patterns configurable (API keys, tokens, passwords)
- Redacted content replaced with `[REDACTED-<hash>]`

### 5.4 Audit Trail
- Every policy decision logged in ledger
- Approval/denial decisions preserved
- Policy overrides tracked
- Post-hoc suspicious pattern detection possible

---

*End of 10_TOOL_AND_POLICY_SYSTEM.md*
