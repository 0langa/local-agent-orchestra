"""Shim: policy_engine.evaluate(command, context)

Delegates to core.policies until core/ grows a first-class PolicyEngine class.
"""

from __future__ import annotations

from core.policies import CommandPolicy, classify_command


def evaluate(command: list[str], context: dict | None = None) -> dict:
    """Evaluate a command against the policy engine.

    Returns a dict matching the canonical PolicyDecision shape:
        {
            "decision": "allow" | "block" | "prompt",
            "policy": "safe" | "install" | "destructive" | "deploy",
            "reason": "...",
        }
    """
    policy = classify_command(command)
    if policy == CommandPolicy.SAFE:
        return {
            "decision": "allow",
            "policy": policy.value,
            "reason": "Command classified as safe for automatic execution.",
        }
    if policy == CommandPolicy.INSTALL:
        return {
            "decision": "prompt",
            "policy": policy.value,
            "reason": "Installation command requires user confirmation.",
        }
    if policy in {CommandPolicy.DESTRUCTIVE, CommandPolicy.DEPLOY}:
        return {
            "decision": "block",
            "policy": policy.value,
            "reason": f"Command classified as {policy.value}; blocked by safety policy.",
        }
    return {
        "decision": "block",
        "policy": policy.value,
        "reason": "Unknown policy classification; blocked by default.",
    }
