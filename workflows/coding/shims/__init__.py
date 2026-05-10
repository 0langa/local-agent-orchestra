"""Workflow shims — adapters that expose canonical core API shapes.

These thin wrappers let the coding workflow call `tool_protocol.invoke()`,
`policy_engine.evaluate()`, `model_registry.resolve()`, and `run_ledger.append()`
without modifying core/.  During Phase 1 cleanup they can be promoted into
core/ and replaced by first-class implementations.
"""

from .model_registry import resolve as model_resolve
from .policy_engine import evaluate as policy_evaluate
from .run_ledger import append as ledger_append
from .tool_protocol import invoke as tool_invoke

__all__ = ["model_resolve", "policy_evaluate", "ledger_append", "tool_invoke"]
