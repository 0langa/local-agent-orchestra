# 18 — SAFETY AND PERMISSION MODEL
## Threat Model, Defense in Depth, Privacy Modes

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE, 10_TOOL_AND_POLICY_SYSTEM
**Enforcement:** All safety mechanisms must conform.
**Violation Classification:** CONSTITUTIONAL VIOLATION (Level 4)

---

## 1. Threat Model

### 1.1 Threat Assumptions
An autonomous coding agent with system access is a powerful tool that can cause powerful damage. The threat model assumes:
- The agent may misinterpret instructions
- The agent may be confused by ambiguous prompts
- External code (dependencies, cloned repos) may be malicious
- Model outputs may contain hidden instructions (prompt injection)
- The user may accidentally approve destructive operations

### 1.2 Threat Scenarios

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Agent deletes wrong files | Data loss | Path confinement, delete restrictions, approval gates |
| Agent exposes secrets | Data breach | Secret redaction, strict-private mode |
| Agent runs malicious code | System compromise | Command allowlist, sandboxing |
| Agent sends data externally | Privacy violation | Network restrictions, local-only mode |
| Agent modifies git history | Code loss | Git policy restrictions |
| Agent installs malware | System compromise | Install approval, path confinement |
| Prompt injection | Unauthorized actions | Input validation, policy enforcement |
| Model hallucination | Incorrect changes | Verification, human-in-the-loop |

---

## 2. Defense in Depth

### 2.1 Layer 1: Static Policy Enforcement
- Command classification: every shell command classified as safe/install/destructive/deploy
- Only safe commands auto-execute
- Install/destructive/deploy commands require explicit approval
- Policy is defined in code, not by the model
- Policy is immutable even if the model is compromised

### 2.2 Layer 2: Path Confinement
- All file operations constrained to declared paths
- Path traversal attempts blocked (../../etc/passwd)
- Symlink resolution controlled
- Workspace isolation for parallel agents

### 2.3 Layer 3: Network Confinement
- By default, agents have no network access
- Network access policy-gated
- GitHub operations through official gh CLI
- Outbound HTTP requires explicit approval

### 2.4 Layer 4: Secret Redaction
- Secrets redacted from all logs and artifacts
- Redaction before model context packing
- Prevents accidental exfiltration via model logs
- Secret patterns configurable

### 2.5 Layer 5: Ledger-Based Auditability
- Every action logged before execution
- Ledger is append-only and tamper-evident
- Suspicious patterns detected post-hoc
- Full execution trajectory preserved

---

## 3. Privacy Modes

### 3.1 Mode Definitions

| Mode | Behavior | Use Case |
|------|----------|----------|
| remote-allowed | Remote API models may be used freely | Maximum capability |
| local-preferred | Local models preferred; remote fallback allowed | Balance of capability and privacy |
| local-only | No remote model or network calls permitted | Maximum privacy |
| strict-private | Sensitive files never sent to remote providers | Maximum data protection |

### 3.2 Mode Enforcement

```python
class PrivacyMode(Enum):
    REMOTE_ALLOWED = "remote-allowed"
    LOCAL_PREFERRED = "local-preferred"
    LOCAL_ONLY = "local-only"
    STRICT_PRIVATE = "strict-private"

class PrivacyEnforcer:
    def __init__(self, mode: PrivacyMode):
        self.mode = mode

    def can_use_remote_model(self) -> bool:
        return self.mode in [PrivacyMode.REMOTE_ALLOWED, PrivacyMode.LOCAL_PREFERRED]

    def can_use_remote_fallback(self) -> bool:
        return self.mode == PrivacyMode.LOCAL_PREFERRED

    def can_make_network_request(self) -> bool:
        return self.mode in [PrivacyMode.REMOTE_ALLOWED, PrivacyMode.LOCAL_PREFERRED]

    def can_upload_file(self, file_path: str) -> bool:
        if self.mode == PrivacyMode.STRICT_PRIVATE:
            return not self._is_sensitive_file(file_path)
        return self.can_use_remote_model()

    def _is_sensitive_file(self, file_path: str) -> bool:
        sensitive_patterns = [
            r".*\.key$", r".*\.pem$", r".*\.env$",
            r".*secret.*", r".*password.*", r".*token.*",
            r".*credential.*", r".*private.*",
        ]
        return any(re.match(pattern, file_path) for pattern in sensitive_patterns)
```

### 3.3 Mode Configuration

```yaml
privacy:
    mode: local-preferred
    sensitive_patterns:
        - "*.key"
        - "*.pem"
        - "*.env"
        - "*secret*"
        - "*password*"
        - "*token*"
        - "*credential*"
        - "*private*"
```

---

## 4. Approval Gradient

### 4.1 Risk Levels

| Level | Examples | Behavior |
|-------|----------|----------|
| NONE | Read files, run tests, git status | Auto-execute |
| LOW | Edit existing files, git commit | Auto-execute with logging |
| MEDIUM | Create new files, install deps | Require confirmation |
| HIGH | Delete files, modify git history, network | Require explicit approval + reason |
| CRITICAL | System-wide installs, credential access | Require password/second factor |

### 4.2 Approval Requirements

| Requirement | Description |
|-------------|-------------|
| What will happen | Plain language description |
| Why it was requested | Explanation of the need |
| Risk level | Classification of risk |
| Scope | Affected files/directories |
| Reversibility | Whether action can be undone |
| Alternatives | Less risky alternatives |
| Policy reference | Which policy triggered approval |

---

## 5. Human-in-the-Loop Design

### 5.1 Supervised Autonomy
- The Orchestrator plans, but the user approves the plan
- The Executor executes, but destructive actions pause for confirmation
- The Verifier validates, but the user can override its judgment
- The Ledger preserves everything for post-hoc review

### 5.2 Augmented Development
The goal is augmented development, not replaced development. The human provides judgment and context; the agent provides execution capability.

---

*End of 18_SAFETY_AND_PERMISSION_MODEL.md*
