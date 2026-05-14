---
name: agentheim-test-subset
description: >
  Select the minimal relevant test subset for Agentheim changes. Avoid running the
  full 695-test suite when only a small area changed. Use when running tests,
  before committing, or when user asks "what tests should I run", "run tests",
  or "validate this change". Auto-triggers when pytest is invoked or when
  validating code changes.
---

# Agentheim Test Subset

Run only tests relevant to the changed code. Full suite = ~100s. Targeted subset = ~10-30s.

## Decision Tree

### 1. What files changed?

Map file patterns to test commands:

| Changed Files | Run These Tests |
|--------------|-----------------|
| `core/workflow_runner.py` | `pytest tests/core/test_workflow_runner.py tests/core/test_workflow_runner_parallel.py tests/smoke/test_workflow_execution.py` |
| `core/ledger.py` | `pytest tests/core/test_ledger_*.py` |
| `core/policy_engine.py` | `pytest tests/core/test_policy_engine.py tests/core/test_policy_audit.py` |
| `core/model_registry.py` | `pytest tests/core/test_model_registry.py tests/test_provider_lazy_loading.py` |
| `core/tool_protocol.py` | `pytest tests/test_tool_protocol.py tests/test_local_db_tool.py tests/test_browser_tool.py` |
| `core/capability_registry.py` | `pytest tests/core/test_capability_registry.py tests/smoke/test_presets.py` |
| `core/events.py` | `pytest tests/test_events.py` |
| `core/artifact_store.py` | `pytest tests/test_artifact_store.py` |
| `core/context_packer.py` | `pytest tests/test_context_packer.py` |
| `core/retry_engine.py` | `pytest tests/test_retry_engine.py` |
| `core/run_executor.py` | `pytest tests/test_run_executor.py` |
| `core/state_machine.py` | `pytest tests/test_state_machine.py` |
| `core/schemas*.py` | `pytest tests/core/test_schemas.py` |
| `providers/*.py` | `pytest tests/test_provider_lazy_loading.py tests/core/test_model_registry.py` |
| `tools/browser/*.py` | `pytest tests/test_browser_tool.py tests/test_browser_e2e.py -m e2e` |
| `tools/mcp/*.py` | `pytest tests/test_mcp.py tests/test_mcp_pool.py` |
| `tools/filesystem/*.py` | `pytest tests/test_local_db_tool.py` |
| `workflows/coding/*.py` | `pytest tests/smoke/test_workflow_execution.py tests/smoke/test_presets.py` |
| `workflows/research/*.py` | `pytest tests/smoke/test_workflow_execution.py` |
| `interfaces/cli/*.py` | `pytest tests/smoke/test_cli.py` |
| `interfaces/api_server/*.py` | `pytest tests/test_api_server.py` |
| `memory/*.py` | `pytest tests/memory/` |
| `presets/*.py` | `pytest tests/smoke/test_presets.py` |
| `agentheim/vendor/aictx/**/*.py` | `pytest agentheim/vendor/aictx/tests/` |

### 2. Cross-cutting changes?

If multiple areas touched:
```bash
# Combine relevant subsets
pytest tests/core/test_model_registry.py tests/smoke/test_cli.py tests/smoke/test_presets.py
```

### 3. Smoke validation

Always include smoke if public behavior changed:
```bash
pytest tests/smoke/test_cli.py tests/smoke/test_presets.py tests/smoke/test_workflow_execution.py
```

### 4. Quick sanity

For trivial changes (docs, comments, formatting):
```bash
pytest tests/core/test_schemas.py -q  # fastest meaningful check
```

## E2E Tests

Browser E2E tests are slow (~12s) and need network. Only run when browser tool changed:
```bash
pytest tests/test_browser_e2e.py -m e2e -v
```

## Full Suite

Run full suite only when:
- Refactoring core abstractions
- Changing pytest config or conftest
- Pre-release validation
- User explicitly requests

```bash
pytest tests/ -q --ignore=tests/test_browser_e2e.py
```
