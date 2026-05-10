# 16 — INTEGRATION AND VALIDATION GATES
## Phase Gates, Test Requirements, and Validation Checkpoints

**Status:** DERIVED FROM 06_PHASED_DEVELOPMENT_PLAN
**Enforcement:** No phase advances without passing all gates.
**Violation Classification:** ARCHITECTURAL BREACH (Level 3)

---

## 1. Gate Philosophy

### 1.1 Purpose
Phase gates prevent premature advancement. A phase is only complete when ALL its gates pass. No exceptions.

### 1.2 Gate Types

| Type | Description | Who Approves |
|------|-------------|-------------|
| Technical | Code quality, test coverage, performance | Automated + Primary Owner |
| Integration | Cross-subsystem compatibility | Integration Team |
| Architecture | Invariant preservation | Architecture Lead |
| Security | Security review | Security Team |
| UX | User experience validation | Product Team |

### 1.3 Gate Classification

| Level | Description | Action on Failure |
|-------|-------------|-------------------|
| REQUIRED | Must pass to advance | Block advancement |
| RECOMMENDED | Should pass to advance | Warning, may advance with approval |
| INFORMATIONAL | Nice to have | Log only |

All gates in this document are REQUIRED unless otherwise specified.

---

## 2. Phase 0 Gates: FOUNDATION

### GATE 0.1: Provider Logic Removed from Core
- **Criteria:** `grep -r "grok\|openai\|ollama" core/` returns only imports from `providers.base`
- **Validation:** Static analysis + manual review
- **Approver:** Architecture Lead

### GATE 0.2: Workflow Logic Removed from Core
- **Criteria:** `grep -r "coding\|planner\|executor\|verifier" core/` returns only generic references
- **Validation:** Static analysis + manual review
- **Approver:** Architecture Lead

### GATE 0.3: Canonical Directory Structure
- **Criteria:** `tree` output matches 02_CORE_ARCHITECTURE_PRINCIPLES exactly
- **Validation:** Automated directory structure check
- **Approver:** Automated

### GATE 0.4: CI Architecture Enforcement
- **Criteria:** CI pipeline fails on import violations
- **Validation:** CI test with intentional violation
- **Approver:** Platform Team

### GATE 0.5: Import Linting
- **Criteria:** All imports conform to 02_CORE_ARCHITECTURE_PRINCIPLES
- **Validation:** Import linting passes on all modules
- **Approver:** Automated

### GATE 0.6: Generic ModelRegistry
- **Criteria:** ModelRegistry loops over configured models generically
- **Validation:** Unit test with multiple providers
- **Approver:** Provider Team

---

## 3. Phase 1 Gates: CORE RUNTIME

### GATE 1.1: Unit Test Coverage
- **Criteria:** All core subsystems >80% line coverage
- **Validation:** Coverage report
- **Approver:** Automated

### GATE 1.2: Integration Tests
- **Criteria:** All core subsystem interactions tested
- **Validation:** Integration test suite passes
- **Approver:** Automated

### GATE 1.3: Phase Machine
- **Criteria:** Full lifecycle executes without errors
- **Validation:** End-to-end phase machine test
- **Approver:** Runtime Team

### GATE 1.4: Ledger Replay
- **Criteria:** Replay produces identical state
- **Validation:** Deterministic replay test
- **Approver:** Runtime Team

### GATE 1.5: Policy Engine
- **Criteria:** All decision types evaluate correctly
- **Validation:** Policy engine test matrix
- **Approver:** Security Team

### GATE 1.6: Lazy Provider Loading
- **Criteria:** Providers loaded only when configured
- **Validation:** Startup time + import analysis
- **Approver:** Provider Team

### GATE 1.7: Model Resolution
- **Criteria:** Capability-based resolution works
- **Validation:** Resolution test with multiple providers
- **Approver:** Provider Team

### GATE 1.8: Budget Enforcement
- **Criteria:** Runs halt cleanly on budget exhaustion
- **Validation:** Budget exhaustion test
- **Approver:** Runtime Team

---

## 4. Phase 2 Gates: FIRST WORKFLOW PACK

### GATE 2.1: End-to-End Execution
- **Criteria:** Coding workflow executes without core modifications
- **Validation:** E2E test
- **Approver:** Workflow Team

### GATE 2.2: Core API Compliance
- **Criteria:** Workflow uses only public core APIs
- **Validation:** API boundary test
- **Approver:** Architecture Lead

### GATE 2.3: Artifact Generation
- **Criteria:** All workflow artifacts generated correctly
- **Validation:** Artifact inspection
- **Approver:** Workflow Team

### GATE 2.4: Policy Enforcement
- **Criteria:** Workflow-specific policies enforced
- **Validation:** Policy test suite
- **Approver:** Security Team

### GATE 2.5: Verification
- **Criteria:** Verifier correctly evaluates code changes
- **Validation:** Verification test suite
- **Approver:** Workflow Team

### GATE 2.6: Replayability
- **Criteria:** Coding run is fully replayable
- **Validation:** Replay test
- **Approver:** Runtime Team

### GATE 2.7: Core Stability
- **Criteria:** Zero core code changes due to workflow integration
- **Validation:** Git diff analysis
- **Approver:** Architecture Lead

---

## 5. Phase 3 Gates: TOOL & SAFETY SYSTEM

### GATE 3.1: Tool Policy Enforcement
- **Criteria:** All tool calls go through policy engine
- **Validation:** Tool invocation test with policy checks
- **Approver:** Security Team

### GATE 3.2: Path Confinement
- **Criteria:** Path traversal blocked
- **Validation:** Path escape attempt test
- **Approver:** Security Team

### GATE 3.3: Command Classification
- **Criteria:** Shell commands classified correctly
- **Validation:** Command classification test matrix
- **Approver:** Security Team

### GATE 3.4: Approval Workflow
- **Criteria:** Approval workflow functions for all risk levels
- **Validation:** Approval test suite
- **Approver:** Security Team

### GATE 3.5: Secret Redaction
- **Criteria:** Secrets removed from artifacts
- **Validation:** Secret detection test
- **Approver:** Security Team

### GATE 3.6: Network Policy
- **Criteria:** Unauthorized requests blocked
- **Validation:** Network policy test
- **Approver:** Security Team

### GATE 3.7: Tool Registry
- **Criteria:** All tools discovered and registered
- **Validation:** Tool registry test
- **Approver:** Tool Team

---

## 6. Phase 4 Gates: PRESET SYSTEM & CLI

### GATE 4.1: Beginner Accessibility
- **Criteria:** Beginner can launch preset with 3 inputs
- **Validation:** User test with non-technical user
- **Approver:** Product Team

### GATE 4.2: Power-User Overrides
- **Criteria:** Power-user can override all settings via CLI
- **Validation:** CLI flag test
- **Approver:** Interface Team

### GATE 4.3: Doctor Script
- **Criteria:** Doctor diagnoses common issues
- **Validation:** Doctor test suite
- **Approver:** Platform Team

### GATE 4.4: Artifact Completeness
- **Criteria:** All presets produce complete artifacts
- **Validation:** Artifact inspection per preset
- **Approver:** Product Team

### GATE 4.5: Configuration Portability
- **Criteria:** Config export/import works
- **Validation:** Portability test
- **Approver:** Interface Team

---

## 7. Phase 5 Gates: EXPANSION

### GATE 5.1: Workflow Pack Count
- **Criteria:** At least 3 additional workflow packs functional
- **Validation:** E2E test per workflow
- **Approver:** Workflow Team

### GATE 5.2: TUI Functionality
- **Criteria:** Guided TUI provides beginner experience
- **Validation:** TUI user test
- **Approver:** Interface Team

### GATE 5.3: Memory Backends
- **Criteria:** At least 2 memory backends functional
- **Validation:** Memory backend test suite
- **Approver:** Memory Team

### GATE 5.4: Workflow Artifacts
- **Criteria:** All workflow packs produce complete artifacts
- **Validation:** Artifact inspection
- **Approver:** Workflow Team

### GATE 5.5: Beginner Usability
- **Criteria:** Platform usable by non-technical users
- **Criteria:** 70% of beginners complete task without help
- **Validation:** User study
- **Approver:** Product Team

---

## 8. Test Requirements

### 8.1 Unit Tests
- Coverage target: >80% for all subsystems
- All public methods tested
- Boundary conditions tested
- Error cases tested

### 8.2 Integration Tests
- All cross-subsystem interactions tested
- Provider integration tested (with mocks)
- Tool integration tested
- Workflow integration tested

### 8.3 End-to-End Tests
- Full workflow execution tested
- Error recovery tested
- Budget enforcement tested
- Ledger replay tested

### 8.4 Security Tests
- Path traversal prevention tested
- Command injection prevention tested
- Secret redaction tested
- Policy enforcement tested

---

*End of 16_INTEGRATION_AND_VALIDATION_GATES.md*
