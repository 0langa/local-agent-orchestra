# Instruction Priority — BINDING

## Priority Order

When instructions overlap, apply them in this order:

1. Current user request
2. Repository `AGENTS.md`
3. `.github/instructions/*.md`
4. `.github/agents/*.agent.md`
5. Repository documentation in `docs/`
6. Project skills in `skills/`

Higher-priority instructions override lower-priority instructions.

## Conflict Handling

If a request or instruction conflicts with a higher-priority rule:

- Stop before editing.
- Cite the exact conflicting files and rules.
- Explain the smallest viable path forward.
- Ask for direction when the conflict cannot be resolved from repository evidence.

Do not silently choose one side of a conflict.

## Always-Read Rule

Before planning or editing, read:

- `AGENTS.md`
- `.github/instructions/README.md`
- Every non-empty `.github/instructions/*.md`

## Scope Rule

Instructions in `.github/instructions/` are binding even when they are not repeated in the main agent file. The main agent file may summarize them, but it cannot weaken them.
