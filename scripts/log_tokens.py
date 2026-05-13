#!/usr/bin/env python3
"""Token usage aggregator for Agentheim dev testing.

Reads ``.ai-team/tokens.jsonl`` and prints a clean cost breakdown.

Usage::

    python scripts/log_tokens.py
    python scripts/log_tokens.py --today
    python scripts/log_tokens.py --run 20260514-013416-plan

Pricing defaults (per 1M tokens)::

    gpt-oss-120b:  $0.1545 input / $0.6180 output
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path


# Pricing table — dollars per 1_000_000 tokens
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "openai.gpt-oss-120b-1:0": {"input": 0.1545, "output": 0.6180},
    "openai.gpt-oss-120b": {"input": 0.1545, "output": 0.6180},
    "gpt-oss-120b": {"input": 0.1545, "output": 0.6180},
}


def load_records(log_path: Path, *, today_only: bool = False, run_id: str | None = None) -> list[dict]:
    records: list[dict] = []
    if not log_path.exists():
        return records

    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue

        if today_only:
            ts = rec.get("ts", "")
            try:
                rec_date = datetime.fromisoformat(ts).date()
            except ValueError:
                continue
            if rec_date != date.today():
                continue

        if run_id and rec.get("metadata", {}).get("run_id") != run_id:
            continue

        records.append(rec)

    return records


def format_usd(cents: float) -> str:
    if cents >= 1.0:
        return f"${cents:.4f}"
    if cents >= 0.01:
        return f"${cents:.6f}"
    return f"${cents:.8f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Agentheim token usage")
    parser.add_argument("--today", action="store_true", help="Only show today's usage")
    parser.add_argument("--run", dest="run_id", help="Filter by run ID")
    parser.add_argument("--log", default=".ai-team/tokens.jsonl", help="Path to token log")
    args = parser.parse_args()

    log_path = Path(args.log)
    records = load_records(log_path, today_only=args.today, run_id=args.run_id)

    if not records:
        print("No token records found.")
        return

    # Aggregate by model
    by_model: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0, "total": 0, "calls": 0})
    by_role: dict[str, dict[str, int]] = defaultdict(lambda: {"input": 0, "output": 0, "total": 0})

    for rec in records:
        model = rec.get("model", "unknown")
        role = rec.get("role", "unknown")
        inp = rec.get("input_tokens", 0)
        out = rec.get("output_tokens", 0)
        total = rec.get("total_tokens", inp + out)

        by_model[model]["input"] += inp
        by_model[model]["output"] += out
        by_model[model]["total"] += total
        by_model[model]["calls"] += 1

        by_role[role]["input"] += inp
        by_role[role]["output"] += out
        by_role[role]["total"] += total

    print("=" * 70)
    print("  Agentheim Token Usage Report")
    if args.today:
        print(f"  Date: {date.today().isoformat()}")
    print(f"  Records: {len(records)}")
    print("=" * 70)

    grand_input = 0
    grand_output = 0
    grand_cost = 0.0

    for model, stats in sorted(by_model.items()):
        pricing = DEFAULT_PRICING.get(model, {"input": 0.0, "output": 0.0})
        inp_cost = (stats["input"] / 1_000_000) * pricing["input"]
        out_cost = (stats["output"] / 1_000_000) * pricing["output"]
        total_cost = inp_cost + out_cost

        grand_input += stats["input"]
        grand_output += stats["output"]
        grand_cost += total_cost

        print(f"\n  Model: {model}")
        print(f"    Calls:     {stats['calls']}")
        print(f"    Input:     {stats['input']:>10,} tokens")
        print(f"    Output:    {stats['output']:>10,} tokens")
        print(f"    Total:     {stats['total']:>10,} tokens")
        print(f"    Cost:      {format_usd(total_cost)}")
        if pricing["input"]:
            print(f"    Rate:      ${pricing['input']}/1M in, ${pricing['output']}/1M out")

    print("\n" + "-" * 70)
    print("  BY ROLE")
    print("-" * 70)
    for role, stats in sorted(by_role.items()):
        print(f"    {role:12}  in={stats['input']:>8,}  out={stats['output']:>8,}  total={stats['total']:>9,}")

    print("\n" + "=" * 70)
    print(f"  GRAND TOTAL")
    print(f"    Input:     {grand_input:>10,} tokens")
    print(f"    Output:    {grand_output:>10,} tokens")
    print(f"    Combined:  {grand_input + grand_output:>10,} tokens")
    print(f"    Est. Cost: {format_usd(grand_cost)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
