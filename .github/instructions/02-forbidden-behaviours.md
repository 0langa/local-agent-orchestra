> This file is a compatibility alias for `02-forbidden-behaviors.md` (the canonical file).  
> Both spellings are required by check-agent-instructions.py. Content is identical.

# Forbidden Behaviors

These behaviors are automatic rejection unless the user explicitly asks for a controlled migration that includes tests, docs, and rollback reasoning.

## Level 4: Constitutional Violations

- Introducing provider-specific logic into `core/`
- Introducing workflow-specific logic into `core/`
- Introducing AICtx-specific implementation logic into `core/`
- Skipping the policy engine for tool calls
- Mutating ledger events after append
- Sending secrets, sensitive files, or strict-private data to remote services without explicit policy approval
- Weakening authentication, authorization, redaction, path confinement, approval, or safety defaults without explicit user intent
- Committing gitignored local reference repositories, including `AICtx/`

## Level 3: Architectural Breaches

- Importing concrete provider, workflow, tool, or interface implementations into `core/`
- Direct tool execution outside the maintained tool protocol
- Adding hidden mutable global state for runtime behavior
- Creating a second provider registry, second policy path, or second ledger system instead of using Agentheim primitives
- Adding public commands, APIs, or workflow behavior without updating docs and tests
- Silently swallowing production errors where callers need actionable failure information

## Level 2: Boundary Concerns

- Changing event schemas without a compatibility or migration plan
- Changing artifact layout without updating docs, tests, and consumers
- Adding workflow packs without registration and smoke coverage
- Adding provider adapters without lazy-loading and capability coverage
- Adding generated files without ignore/update rules
- Touching multiple subsystems without explaining the cross-boundary impact

## Common Anti-Patterns

| Anti-Pattern | Required Approach |
| --- | --- |
| "Put this provider check in core for now." | Route through provider configuration, descriptors, and registry boundaries. |
| "This workflow needs a special core hook." | Extend workflow contracts or workflow pack behavior without hard-coding the workflow in core. |
| "Import the tool directly to save time." | Use the maintained tool protocol and policy path. |
| "Use a global singleton because passing context is noisy." | Prefer explicit dependencies and existing runtime context objects. |
| "Docs can be fixed later." | Fix docs in the same change when behavior, paths, commands, or guarantees change. |
| "Copy AICtx wholesale into Agentheim internals." | Import or adapt through the approved integration boundary and preserve Agentheim ownership. |

## Stop Conditions

Stop and ask for direction if:

- The task requires violating any immutable law.
- The requested change conflicts with `.github/instructions/*.md`.
- The worktree contains user changes that directly conflict with the required edit.
- Verification shows a real defect outside the requested scope that must be fixed before proceeding safely.

