# TRACEABILITY — EVERY CHANGE LEAVES EVIDENCE

## Artifact Requirements
Every implementation task MUST produce:

1. **Code** — the implementation itself
2. **Tests** — unit tests with >80% coverage
3. **Documentation** — docstrings + relevant doc updates
4. **CHANGELOG entry** — what changed and why

## Per-Run Artifact Requirements
Every workflow execution MUST produce:

```
runs/<run-id>/
    run.json                 # Run metadata
    timeline.jsonl           # Complete event log
    config.redacted.json     # Config with secrets removed
    context_bundle.md        # Human-readable context
    context_manifest.json    # Machine-readable context
    plan.md                  # Execution plan (if applicable)
    tool_calls.jsonl         # Every tool invocation
    policy_decisions.jsonl   # Every policy evaluation
    patch.diff               # File changes (if applicable)
    verification.json        # Verification results
    final_report.md          # Human-readable outcome
```

## What I Must Log
- Every file modified (path, before/after hash)
- Every subsystem touched
- Every test added or modified
- Every policy decision (if implementing policy-related code)
- Every event type added (if implementing event-related code)

## Traceability Test
Can a reviewer answer these questions from my output alone?
- [ ] What was changed?
- [ ] Why was it changed?
- [ ] Which subsystem was affected?
- [ ] Does it preserve all 7 Laws?
- [ ] Are there tests?
- [ ] Is there documentation?

If any answer is "no" or "unclear," the task is not complete.
