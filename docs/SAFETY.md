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
- [Security Fixes — Resolved Limitations](#security-fixes--resolved-limitations)
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
| `NONE` | Filesystem read, list, stat | Auto-approved |
| `LOW` | Read file, list directory | Auto-approved |
| `MEDIUM` | Filesystem write/copy, execute safe command | Requires confirmation |
| `HIGH` | Shell execute, delete files, install packages | Blocked by default |
| `CRITICAL` | System-level operations | Always blocked |

Operation-level risk resolution adjusts the effective risk within a tool. For example, `filesystem` read/list/stat resolve to `NONE`, while `filesystem` write/copy resolve to `MEDIUM`.

### How Approval Works

When a tool invocation requires approval:

1. An `APPROVAL_REQUESTED` event is emitted to the ledger with 6-field disclosure: `tool_id`, `action`, `target`, `risk_level`, `justification`, `params_redacted`
2. The system pauses execution and waits for a decision
3. The user can `grant` or `deny` the request
4. The decision is recorded as an `APPROVAL_GRANTED` or `APPROVAL_DENIED` event

#### Interface Behavior

- **CLI**: Medium-risk operations prompt interactively (`Grant approval? [y/N]`). If granted, the request is re-invoked with the approved decision.
- **API / Web UI**: Medium-risk operations return an approval-required payload (HTTP 409) without executing. The caller must explicitly grant or deny the request through the approval continuation routes before the tool runs or is cancelled.
- **Workflow internal**: Coding and other workflows evaluate policy through their own agent adapters, which remain autonomous but must respect the same `PolicyEngine` rules.

---

## Policy Engine

The `PolicyEngine` is the central safety gate for all tool invocations. Interface-facing tool calls flow through `ToolInvoker` (`core/tool_invocation.py`), which ensures a single policy-gated, ledger-audited path:

```
Tool Call Request
    ↓
ToolInvoker.lookup — resolves tool and operation-level risk
    ↓
PrivacyEnforcer — checks privacy mode compliance
    ↓
PolicyEngine.evaluate() — determines allow/deny/ask
    ↓
BudgetEnforcer — checks token/time/iteration budgets
    ↓
Tool Execution (if allowed)
    ↓
POLICY_EVALUATED + TOOL_CALLED + TOOL_RESULT_RECEIVED events emitted to ledger
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
| **Shell process sandbox** | `ShellSandbox` with env filtering, injection prevention, path confinement | `tools/shell/sandbox.py` |
| **Network host enforcement** | `NetworkEnforcer` with IP range / host / DNS validation | `tools/http/__init__.py` via `tools/network/__init__.py` |
| **Plugin crypto signatures** | Ed25519 signature verification with trusted key registry | `marketplace/signing.py` + `marketplace/manager.py` |

---

## Security Fixes — Resolved Limitations

The following previously documented limitations have been fully resolved:

### Shell Tool Sandbox (Resolved)

The shell tool no longer relies on a safety-net allowlist.  Every command runs through a
process-level ``ShellSandbox`` that provides:

- **Strict command prefix allowlist** — only explicitly permitted commands may execute
- **Shell metacharacter injection prevention** — blocks `\``, `$()`, `;`, `|`, `&&`, shell redirects
- **Path traversal blocking** — prevents `../` escape from the workspace
- **Environment variable filtering** — only inherits a curated allowlist of env vars
- **Process group isolation** — enables reliable cleanup on timeout or cancellation
- **Working directory confinement** — commands cannot escape the repository root
- **Output size limits** — prevents memory exhaustion from large output

| Capability | Implementation | Enforced By |
|-----------|---------------|-------------|
| Command allowlist | `SandboxConfig.allowed_commands` | `ShellSandbox._validate()` |
| Shell injection prevention | Metacharacter detection | `ShellSandbox._validate_arg()` |
| Path traversal blocking | `..` detection in args | `ShellSandbox._validate_arg()` |
| Env filtering | `SandboxConfig.allowed_env_vars` | `ShellSandbox._build_env()` |
| Process isolation | Process group / `start_new_session` | `ShellSandbox.execute()` |
| Output limits | `SandboxConfig.max_output_bytes` | `ShellSandbox.execute()` |

### Network Policy Enforcement (Resolved)

Network policies are enforced at the tool implementation level, not merely advisory.
The ``NetworkEnforcer`` validates every outbound request against:

- **Global network access flag** — denies all outbound traffic when disabled
- **URL scheme validation** — defaults to HTTPS-only
- **Host allow/deny lists** — glob-pattern matching prevents access to internal services
- **Private IP range blocking** — denies RFC 1918 (10.x, 172.16-31.x, 192.168.x), loopback (127.x), and IPv6 unique-local (fc00::/7)
- **Link-local blocking** — denies 169.254.x.x and fe80::/10
- **Cloud metadata service protection** — blocks metadata.google.internal and similar
- **DNS-level resolution checks** — resolves hostnames to detect rebinding attacks

| Capability | Implementation | Enforced By |
|-----------|---------------|-------------|
| Network access gate | `NetworkPolicy.allowed` | `NetworkEnforcer.validate()` |
| URL scheme restriction | `NetworkPolicy.allowed_schemes` | `NetworkEnforcer.validate()` |
| Host allow/deny lists | Glob pattern matching | `NetworkEnforcer.validate()` |
| Private IP blocking | CIDR range checks | `NetworkEnforcer._check_ip_ranges()` |
| Link-local blocking | CIDR range checks | `NetworkEnforcer._check_ip_ranges()` |
| DNS resolution | `socket.getaddrinfo()` | `NetworkEnforcer._check_ip_ranges()` |

### Plugin Marketplace Cryptographic Signatures (Resolved)

Plugin packages are verified using **Ed25519** public-key cryptography at load time.
The non-cryptographic SHA-256 hash has been replaced with a proper signature scheme:

- **Ed25519 key generation** — ``PluginSigner.generate_keypair()`` creates a PEM-encoded key pair
- **Package signing** — ``PluginSigner.sign_package()`` signs all package files with the private key, storing the base64-encoded signature in ``manifest.json``
- **Trusted key registry** — public keys are stored in ``~/.agentheim/trusted-keys/`` or ``.agentheim/trusted-keys/`` and referenced by ``trusted_key_id`` in the manifest
- **Mandatory verification** — unsigned plugins are rejected with a clear error message
- **Canonical signing message** — all files in the plugin directory are hashed in sorted order, excluding the signature field itself, ensuring deterministic verification

| Capability | Implementation | Enforced By |
|-----------|---------------|-------------|
| Key generation | `PluginSigner.generate_keypair()` | Ed25519 (`cryptography`) |
| Package signing | `PluginSigner.sign_package()` | Ed25519 (`cryptography`) |
| Signature verification | `PluginSigner.verify_package()` | Ed25519 (`cryptography`) |
| Trusted key resolution | `PluginManager._resolve_public_key()` | Searches `trusted_key_dirs` |
| Mandatory signing | Rejection in `PluginManager.load()` | Production policy |

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
- [Forbidden Behaviors](../.github/instructions/02-forbidden-behaviors.md) — safety-related rejection rules
