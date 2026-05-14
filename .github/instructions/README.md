# Agentheim Instructions Index

This directory contains binding instructions for agents working on Agentheim.

## Instruction Classes

| File | Class | Purpose |
| --- | --- | --- |
| `00-instruction-priority.md` | always-read, always-enforced | Precedence, conflict handling, and required reads |
| `01-doctrine.md` | always-read, always-enforced | Project identity and immutable architecture laws |
| `02-forbidden-behaviors.md` | always-read, always-enforced | Rejection-level anti-patterns and stop conditions |
| `03-traceability.md` | always-read, always-enforced | Evidence, reporting, changelog, and artifact expectations |
| `04-AICtx-integration.md` | always-read, contextual-enforced | AICtx integration rules and hard boundaries |
| `05-documentation-integrity.md` | always-read, always-enforced | Documentation accuracy, link, example, and GitHub rendering rules |
| `06-tooling-and-verification.md` | always-read, always-enforced | Canonical local validation, AI live-test limits, and legacy roadmap status |
| `07-chat-output.md` | always-read, always-enforced | rules for how to interact with user in input/output interface talking with you |

## AICtx Rule

All agents must read `04-AICtx-integration.md`.

Its integration workflow rules apply when work touches AICtx, repository context generation, `docs/AIprojectcontext/**`, `context.lock.json`, public-doc impact mapping, context verification, or migration from the AICtx workspace project at `../AICtx`.

Its hard boundaries always apply, including using the editable AICtx install from `../AICtx` rather than vendored or copied source.
