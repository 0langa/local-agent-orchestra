# FORBIDDEN BEHAVIORS — AUTOMATIC REJECTION

## Level 4: Constitutional Violations (Immediate Revert)
- Introducing provider-specific logic into `core/`
- Skipping policy engine for tool calls
- Modifying ledger events after append
- Sending sensitive data to remote in strict-private mode
- Implementing Phase 6 (RESERVED) systems

## Level 3: Architectural Breaches (Blocks Merge)
- Importing concrete implementations into `core/`
- Workflow-specific logic in `core/`
- Direct tool execution outside `tools/` protocol
- Mutable global state
- Modifying roadmap documents without approval

## Level 2: Boundary Concerns (Requires Review)
- Adding providers before provider registry is stable
- Adding workflow packs before workflow runtime is stable
- Modifying event schemas without migration plan
- Changing phase machine without updating subsystems
- Adding UI interfaces before CLI is stable

## Anti-Patterns I Must Avoid
| Anti-Pattern | Correct Approach |
|-------------|-----------------|
| "I'll just put this provider check in core for now" | Route through provider_registry |
| "This workflow needs a special core hook" | Workflow packs extend base class |
| "I'll import the tool directly to save time" | Always use tool_protocol.invoke() |
| "Global config is easier than passing context" | Explicit dependency injection |
| "I'll add the vector DB since I'm here anyway" | Phase 5 only — deferred |
| "MCP would make this easier" | Phase 6 only — reserved |

## Self-Check Before Every Change
1. Does this touch only my assigned subsystem? (If no → approval needed)
2. Does this implement a future-phase system? (If yes → STOP)
3. Does this introduce provider/workflow/tool specifics into core? (If yes → STOP)
4. Does this bypass policy_engine or tool_protocol? (If yes → STOP)
5. Does this have tests? (If no → write tests)
