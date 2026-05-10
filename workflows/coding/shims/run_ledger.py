"""Shim: run_ledger.append(ledger, name, payload)

Delegates to core.ledger.RunLedger.append_jsonl until core/ exposes a
generic `append()` method.
"""

from __future__ import annotations

from typing import Any

from core.ledger import RunLedger


def append(ledger: RunLedger, name: str, payload: dict[str, Any]) -> None:
    """Append a payload to a JSON-lines artifact."""
    ledger.append_jsonl(name, payload)
