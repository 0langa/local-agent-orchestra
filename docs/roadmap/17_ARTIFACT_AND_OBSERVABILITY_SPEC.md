# 17 — ARTIFACT AND OBSERVABILITY SPEC
## Run Artifacts, Inspectability, and Observability Requirements

**Status:** DERIVED FROM 11_EVENT_AND_LEDGER_ARCHITECTURE
**Enforcement:** All runs must produce artifacts. All artifacts must be inspectable.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. Run Artifact Schema

### 1.1 Artifact Directory Structure

```
runs/<run-id>/
    run.json                    # Run metadata
    timeline.jsonl              # Append-only event stream
    config.redacted.json        # Active config (secrets removed)
    context_bundle.md           # Human-readable context
    context_manifest.json       # Machine-readable context index
    plan.md                     # Generated plan (if applicable)
    tool_calls.jsonl            # Every tool invocation
    policy_decisions.jsonl      # Every policy evaluation
    patch.diff                  # File changes (if applicable)
    verification.json           # Verification result
    final_report.md             # Human-readable outcome
```

### 1.2 Artifact Descriptions

| Artifact | Format | Description | Always Produced |
|----------|--------|-------------|----------------|
| run.json | JSON | Run metadata: id, workflow, timestamps, status | Yes |
| timeline.jsonl | JSONL | Every event in order | Yes |
| config.redacted.json | JSON | Active config with secrets removed | Yes |
| context_bundle.md | Markdown | Human-readable context | Yes |
| context_manifest.json | JSON | Machine-readable context index | Yes |
| plan.md | Markdown | Generated execution plan | If workflow produces plan |
| tool_calls.jsonl | JSONL | Every tool call with input/output | Yes |
| policy_decisions.jsonl | JSONL | Every policy decision | Yes |
| patch.diff | Diff | File changes | If files changed |
| verification.json | JSON | Verification results | If verification performed |
| final_report.md | Markdown | Human-readable outcome | Yes |

### 1.3 Artifact Requirements
- All artifacts must be human-readable where possible
- All artifacts must be machine-parseable
- All artifacts must be portable (no absolute paths)
- All artifacts must have secrets redacted
- All artifacts must be preserved for audit

---

## 2. Observability Requirements

### 2.1 Questions a User Must Answer
From the artifacts alone, a user must be able to answer:

| Question | Source Artifacts |
|----------|-----------------|
| What happened? | timeline.jsonl, final_report.md |
| Which model was used? | timeline.jsonl (agent.invoked) |
| Which tools were called? | tool_calls.jsonl |
| What was denied? | policy_decisions.jsonl |
| What changed? | patch.diff, final_report.md |
| Why did verification pass/fail? | verification.json |
| What artifacts were created? | run.json, artifact events |
| How much did this cost? | timeline.jsonl (token usage) |
| How long did it take? | run.json, timeline.jsonl |
| What was the plan? | plan.md |
| What context was used? | context_bundle.md, context_manifest.json |

### 2.2 Transparency Requirements
- Every model message logged
- Every tool call logged with input and output
- Every policy decision logged with reason
- Every phase transition logged
- Every file change captured as diff
- Every approval/denial logged

### 2.3 Trust Mechanism
The system does not ask users to trust it. It gives them the tools to verify:
- Before a run: inspect the plan, check context pack
- During a run: watch state transitions, approve risky actions
- After a run: read full report, inspect every diff, check token usage
- Across runs: compare ledgers, identify pattern changes

---

## 3. Artifact Formats

### 3.1 run.json

```json
{
    "run_id": "run_550e8400-e29b-41d4-a716-446655440001",
    "workflow_id": "coding",
    "preset_id": "codebase_assistant",
    "status": "completed",
    "started_at": "2025-01-15T10:30:00Z",
    "completed_at": "2025-01-15T10:45:00Z",
    "duration_ms": 900000,
    "models_used": {
        "planner": "claude-sonnet",
        "executor": "qwen3-coder",
        "verifier": "gpt-4o-mini"
    },
    "token_usage": {
        "input": 10000,
        "output": 5000,
        "total": 15000
    },
    "tool_calls": 25,
    "phases_completed": 12,
    "artifacts_produced": 6
}
```

### 3.2 final_report.md

```markdown
# Run Report: coding

## Summary
- **Status:** Completed successfully
- **Duration:** 15 minutes
- **Models used:** claude-sonnet (planner), qwen3-coder (executor), gpt-4o-mini (verifier)

## What was done
1. Scanned repository: 150 files analyzed
2. Generated plan: 5 steps
3. Implemented changes: 3 files modified
4. Ran tests: 45/45 passed
5. Verified changes: All checks passed

## Files changed
- src/auth.py: Added login endpoint
- tests/test_auth.py: Added login tests
- docs/api.md: Updated API documentation

## Verification
- Unit tests: PASS (45/45)
- Type checking: PASS
- Linting: PASS

## Token usage
- Input: 10,000 tokens
- Output: 5,000 tokens
- Estimated cost: $0.15

## Artifacts
- plan.md: Execution plan
- patch.diff: Code changes
- test_results.json: Test results
- verification.json: Verification details
```

---

*End of 17_ARTIFACT_AND_OBSERVABILITY_SPEC.md*
