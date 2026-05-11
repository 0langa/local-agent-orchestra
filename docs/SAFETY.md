# Safety & Security

> Privacy, security, and safety features of Agentheim — plus how to report vulnerabilities.

---

## Table of Contents

- [Security Philosophy](#security-philosophy)
- [Privacy Modes](#privacy-modes)
- [Approval Gates](#approval-gates)
- [Policy Engine](#policy-engine)
- [Secret Redaction](#secret-redaction)
- [Path Confinement](#path-confinement)
- [Security Features Summary](#security-features-summary)
- [Known Limitations](#known-limitations)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [Supported Versions](#supported-versions)

---

## Security Philosophy

Agentheim is designed with **security as a core principle**, not an afterthought. The system follows a **defense-in-depth** approach:

1. **Local-first by default** — no data leaves your machine unless you explicitly allow it
2. **Policies are code, not prompts** — safety restrictions are enforced at the engine level, not delegated to model behavior
3. **Defense in depth** — multiple independent enforcement layers: privacy enforcer, policy engine, path confinement, secret redaction
4. **Auditability** — every action is recorded in an append-only event ledger with SHA-256 hash chain verification

---

## Privacy Modes

Privacy is enforced at the **policy engine level**, not merely advisory. The current code exposes these structured `PrivacyMode` values:

| Mode | Behavior | Use Case |
|------|----------|----------|
| `standard` | Baseline mode with no extra privacy restrictions | Default local development |
| `local_only` | Blocks network-oriented tools such as HTTP requests and push/clone operations | Sensitive codebases, air-gapped environments |
| `strict_private` | Adds sensitive-path blocking on top of privacy enforcement | High-sensitivity local work |
| `encrypted` | Applies strict-private-style blocking and redacts all audited params | Maximum auditing caution |

These values are implemented in `core/privacy_enforcer.py`. The public CLI in this checkout does **not** yet expose a dedicated top-level privacy-mode flag, so privacy selection currently depends on the calling runtime and policy configuration rather than a documented `agentheim --privacy ...` command.

The privacy mode is evaluated by `PrivacyEnforcer` (`core/privacy_enforcer.py`), which checks every tool invocation and can block or redact based on the active mode.

---

## Approval Gates

All side-effecting operations are mediated by the `PolicyEngine` (`core/policy_engine.py`). Tools declare their risk level, and the engine evaluates allow/deny/ask decisions at runtime.

### Approval Levels

| Level | Behavior |
|-------|----------|
| `auto-approve` | Read-only ops run automatically |
| `always-ask` | Every non-read operation pauses for approval |
| `risk-based` (default) | LOW auto-runs, MEDIUM asks, HIGH blocks |

### Tool Risk Levels

| Level | Examples | Default Behavior |
|-------|----------|-----------------|
| `LOW` | Read file, list directory | Auto-approved |
| `MEDIUM` | Write file, execute safe command | Requires confirmation |
| `HIGH` | Delete files, install packages | Blocked by default |
| `CRITICAL` | System-level operations | Always blocked |

### How Approval Works

When a tool invocation requires approval:

1. An `APPROVAL_REQUESTED` event is emitted to the ledger with 6-field disclosure: `tool_id`, `action`, `target`, `risk_level`, `justification`, `params_redacted`
2. The system pauses execution and waits for a decision
3. The user can `grant` or `deny` the request
4. The decision is recorded as an `APPROVAL_GRANTED` or `APPROVAL_DENIED` event

---

## Policy Engine

The `PolicyEngine` is the central safety gate for all tool invocations. Every tool call flows through:

```
Tool Call Request
    ↓
PrivacyEnforcer — checks privacy mode compliance
    ↓
PolicyEngine.evaluate() — determines allow/deny/ask
    ↓
BudgetEnforcer — checks token/time/iteration budgets
    ↓
Tool Execution (if allowed)
    ↓
Event emitted to ledger
```

The engine:
- Emits `POLICY_EVALUATED` events for every evaluation
- Respects step budgets (tokens, time, tool calls, agent invocations)
- Integrates with the approval workflow for manual decisions
- Classifies commands via `CommandPolicy` (`core/policies.py`) for shell safety

---

## Secret Redaction

API keys, tokens, and other secrets are automatically redacted from:
- All log output
- Ledger events and artifacts
- Context bundles and manifests
- Configuration dumps

Redaction is handled by `core/redaction.py` and applied consistently across the system.

---

## Path Confinement

All filesystem operations are scoped to the workspace:
- Patch paths cannot escape the repository root
- Read/write operations validate relative paths
- The `PatchApplier` class enforces confinement in `core/patching.py`

---

## Security Features Summary

| Feature | Implementation | Enforced By |
|---------|---------------|-------------|
| Privacy modes | `PrivacyEnforcer` with 4 modes | Policy engine |
| Approval gates | `ApprovalWorkflow` with ledger events | Policy engine |
| Risk-based tool control | Tool risk levels (LOW→CRITICAL) | Policy engine |
| Secret redaction | Automated on all output | `redaction.py` |
| Path confinement | Workspace-root-scoped | `patching.py` |
| Audit trail | Append-only ledger with hash chain | `ledger.py` |
| Command classification | Allowlist/denylist for shell | `policies.py` |
| Budget enforcement | Token/time/call limits | `step_budget.py` |
| Tamper detection | SHA-256 hash chain on events | `ledger.py` |
| Safe defaults | All destructive ops blocked by default | Policy engine |

---

## Known Limitations

- The shell tool allowlist is a safety net, not a sandbox. Running Agentheim on untrusted codebases is not recommended.
- Network policies are advisory at the tool level; a compromised host could bypass them.
- The plugin marketplace (Phase 6 scaffold) does not yet have cryptographic signature verification.

---

## Reporting a Vulnerability

If you discover a security vulnerability in Agentheim, please report it responsibly.

**Do NOT open a public issue.**

Instead, please send an email to the maintainer with:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within **48 hours** and provide a timeline for a fix.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| Older releases | ❌ |

Agentheim is currently in active development. Only the latest commit on `main` receives security updates.

---

## See Also

- [User Guide](USER_GUIDE.md) — privacy mode usage in daily operation
- [Architecture](ARCHITECTURE.md) — policy engine and enforcement details
- [Roadmap: Safety & Permission Model](roadmap/18_SAFETY_AND_PERMISSION_MODEL.md) — design specification
