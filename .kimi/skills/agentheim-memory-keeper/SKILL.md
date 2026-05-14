---
name: agentheim-memory-keeper
description: >
  Manage the project-specific memory knowledge graph stored at
  .kimi/memory.jsonl. Read, verify freshness, update, and prune
  memory entities to keep cross-session context accurate. Use when
  user says "update memory", "check memory", "refresh memory",
  "memory stale?", or after any significant task. Auto-triggers at
  session start to verify memory against live repository state.
---

# Agentheim Memory Keeper

Keep `.kimi/memory.jsonl` accurate. Memory = structured knowledge graph (entities + relations + observations). Stored via `@modelcontextprotocol/server-memory` MCP.

## Memory Location

File: `C:/Users/juliu/source/repos/local-agent-orchestra/.kimi/memory.jsonl`

Set via `MEMORY_FILE_PATH` env var in `~/.kimi/mcp.json`.

## When to Run

- User says: "update memory", "check memory", "refresh memory", "memory stale?"
- After significant task: code changes, architectural decisions, milestone completions, config updates
- At session start: verify stored state matches live repo
- Before long tasks: load relevant context from memory

## MCP Tools

Use these `memory` MCP tools:
- `read_graph` — dump all entities and relations
- `search_nodes` — find entities by name/type/observation content
- `open_nodes` — read specific entities with relations
- `create_entities` — add new entities with observations
- `create_relations` — link entities
- `add_observations` — append to existing entities
- `delete_entities` — remove stale entities
- `delete_relations` — remove stale relations
- `delete_observations` — remove stale observations

## Workflows

### 1. Freshness Check (Session Start)

```
1. Call read_graph → list all entities
2. Check key facts against live repo:
   - Test counts match? (read docs/DEV_TESTING.md or run pytest)
   - File paths still exist? (ls / grep)
   - Milestone statuses current? (read docs/AICTX_INTEGRATION_PLAN.md)
   - MCP config matches? (read ~/.kimi/mcp.json)
3. Flag discrepancies → queue updates
```

### 2. Update After Task

```
1. Identify what changed in this session:
   - New files/modules → create_entities
   - Modified behavior → add_observations to existing entities
   - New architecture decisions → create_entities + create_relations
   - Completed milestones → update milestone entity observations
   - Removed features → delete_entities or delete_observations
2. Append to docs/CHANGELOG.md (separate skill: agentheim-changelog)
3. Verify: open_nodes on updated entities → confirm stored
```

### 3. Load Context for Task

```
1. search_nodes for relevant keywords
2. open_nodes on highest-relevance entities
3. Summarize findings for user
```

### 4. Full Rebuild (if memory corrupt or very stale)

```
1. read_graph → inventory current memory
2. delete_entities on all existing (or delete_observations selectively)
3. Re-scan project:
   - AGENTS.md, docs/ARCHITECTURE.md, docs/DEV_TESTING.md
   - Core components, subsystems, interfaces
   - Recent changes from docs/CHANGELOG.md and git log
   - Rules, stop conditions, tech stack
4. create_entities + create_relations for clean baseline
```

## Entity Types to Maintain

| Type | Examples |
|------|----------|
| `project` | Agentheim |
| `subsystem` | Core Runtime, Providers, Tools, Workflows |
| `component` | WorkflowRunner, PolicyEngine, RunLedger |
| `initiative` | AICtx Integration |
| `doctrine` | Seven Immutable Laws |
| `rule` | Instruction Priority, Forbidden Behaviors |
| `file` | docs/ARCHITECTURE.md, AGENTS.md |
| `config` | MCP Servers Config |
| `history` | Recent Changes |
| `command` | Entry Points |
| `stack` | Tech Stack |

## Relation Types

| Type | Meaning |
|------|---------|
| `contains` | Parent subsystem → child component |
| `integrates with` | Project → external initiative |
| `governs` | Rule/doctrine → project |
| `references` | File → rule or other file |
| `validates` | Testing → project |
| `accesses` | Entry point → project |
| `builds` | Tech stack → project |
| `supports` | Config → project |
| `documents` | Doc file → project/subsystem |

## Key Entities to Keep Fresh

High-priority (check every session):
- Agentheim (stats, test counts, version)
- AICtx Integration (milestone status)
- Recent Changes (last few changelog entries)
- MCP Servers Config (active/removed servers)

Medium-priority (check after related tasks):
- Core Runtime components
- Subsystems (Providers, Tools, Workflows, Memory, Interfaces)
- Rules (Seven Immutable Laws, Forbidden Behaviors, Stop Conditions)

Low-priority (rarely change):
- Tech Stack
- Entry Points
- AGENTS.md / docs/ files

## Stop Conditions

- If memory file missing or unreadable: run Full Rebuild
- If entity count drops unexpectedly: verify before deleting
- If user says "stop updating memory": respect and note in memory
