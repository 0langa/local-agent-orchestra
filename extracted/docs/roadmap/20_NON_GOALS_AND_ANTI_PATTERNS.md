# 20 — NON-GOALS AND ANTI-PATTERNS
## Explicit Non-Goals, Forbidden Behaviors, and Chaos Prevention

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE
**Enforcement:** These are binding constraints on all development.
**Violation Classification:** CONSTITUTIONAL VIOLATION (Level 4) for non-goals; BOUNDARY CONCERN (Level 2) for anti-patterns

---

## 1. Explicit Non-Goals

These are things the project explicitly does NOT do. They are not deferred features. They are excluded by design.

### 1.1 Cloud Hosting / SaaS
- **Reason:** Local-first is a core principle
- **Impact:** Cloud adds latency, cost, and privacy risk
- **Forbidden:** Any code that requires cloud infrastructure to function

### 1.2 Full Unsupervised Autonomy
- **Reason:** Human oversight is a safety requirement
- **Impact:** Unsupervised agents can cause damage
- **Forbidden:** Any code that removes approval gates or human oversight

### 1.3 AGI / General Intelligence
- **Reason:** Narrow, bounded tool with focused purpose
- **Impact:** Scope creep leads to unreliable systems
- **Forbidden:** Any claim or feature implying general intelligence

### 1.4 IDE Replacement
- **Reason:** Augments existing tools, does not replace them
- **Impact:** IDE integration is future work, not core product
- **Forbidden:** Any feature that replaces IDE functionality

### 1.5 Model Training
- **Reason:** Uses existing models via APIs
- **Impact:** Training requires expertise and infrastructure outside scope
- **Forbidden:** Any model training or fine-tuning code

### 1.6 Proprietary Lock-In
- **Reason:** No vendor-specific features
- **Impact:** Lock-in violates provider-agnostic principle
- **Forbidden:** Any feature that works with only one provider

### 1.7 Plugin Marketplace (Pre-Phase 6)
- **Reason:** Requires stable core and extension APIs
- **Impact:** Premature marketplace leads to broken extensions
- **Forbidden:** Any marketplace code before Phase 6

### 1.8 Distributed Workers (Pre-Phase 6)
- **Reason:** Requires mature single-node system first
- **Impact:** Premature distribution adds complexity without value
- **Forbidden:** Any distributed system code before Phase 6

---

## 2. Forbidden Implementation Behaviors

### 2.1 Absolute Prohibitions

| Behavior | Violation | Detection |
|----------|-----------|-----------|
| Provider-specific logic in core | Violates Law 1 | Static analysis |
| Workflow-specific logic in core | Violates Law 1 | Static analysis |
| Tool implementation imported into core | Violates Law 1 | Import linting |
| Mutable global state | Violates event-sourcing | Static analysis |
| Bypassing policy engine | Violates safety | Runtime validation |
| Modifying ledger events | Violates immutability | Ledger integrity check |
| Sending sensitive data in strict-private | Violates privacy | Runtime validation |
| Hardcoded model names | Violates provider-agnosticism | Code review |
| Skipping integration gates | Violates phase discipline | Process enforcement |
| Cross-module edits without approval | Violates ownership | Code review |

### 2.2 Conditional Prohibitions

| Behavior | Condition | Violation Level |
|----------|-----------|----------------|
| Adding new providers | Before provider registry stable | Level 2 |
| Adding workflow packs | Before workflow runtime stable | Level 2 |
| Adding memory backends | Before memory protocol stable | Level 2 |
| Adding UI interfaces | Before CLI stable | Level 2 |
| Modifying event schemas | Without migration plan | Level 2 |
| Changing phase machine | Without updating subsystems | Level 2 |
| Adding MCP integration | Before Phase 5 complete | Level 2 |
| Adding vector DB | Before basic memory stable | Level 2 |

---

## 3. Anti-Patterns

### 3.1 Architecture Anti-Patterns

| Anti-Pattern | Why Forbidden | Correct Approach |
|-------------|--------------|-----------------|
| Big Ball of Mud | Core becomes unmaintainable | Strict subsystem separation |
| God Object | Core knows everything | Core knows only protocols |
| Premature Abstraction | Complex indirection before need | Concrete first, extract later |
| Leaky Abstraction | Provider details leak to workflows | Capability-based resolution |
| Hidden Coupling | Dependencies not visible | Explicit dependency declaration |
| Speculative Generality | Abstractions for unneeded features | YAGNI — implement when needed |

### 3.2 Implementation Anti-Patterns

| Anti-Pattern | Why Forbidden | Correct Approach |
|-------------|--------------|-----------------|
| Copy-Paste Code | Maintenance burden | Refactor into shared components |
| Magic Numbers | Unclear intent | Named constants |
| Silent Failures | Undetected errors | Explicit error handling and logging |
| Hardcoded Paths | Not portable | Configurable paths |
| Secret in Code | Security risk | Environment variables |
| Untested Code | Unreliable | Test all code paths |

### 3.3 Swarm Anti-Patterns

| Anti-Pattern | Why Forbidden | Correct Approach |
|-------------|--------------|-----------------|
| Serial Collapse | Wastes parallel resources | Explicit parallelism markers |
| Infinite Replanning | Budget exhaustion | Bounded replanning |
| Worker Isolation Violation | Race conditions | No direct worker communication |
| Budget Ignorance | Runaway costs | Budget checks before every action |
| Context Bloat | Degraded performance | Token budget enforcement |
| Approval Fatigue | User ignores approvals | Smart approval batching |

---

## 4. Chaos Prevention Rules

### 4.1 For Swarm Agents
1. **No unassigned work:** Every agent has a defined subsystem
2. **No silent failures:** All errors logged and reported
3. **No budget surprises:** Budget checked before every action
4. **No cross-boundary edits:** Without explicit approval
5. **No premature implementation:** Of reserved systems
6. **No architecture shortcuts:** Even when under pressure

### 4.2 For Maintainers
1. **Review all cross-boundary changes:** With Architecture Lead
2. **Enforce import rules:** Via CI
3. **Monitor test coverage:** And require maintenance
4. **Document all decisions:** Via Architecture Decision Records
5. **Communicate changes:** To all affected teams
6. **Preserve invariants:** Even during refactoring

### 4.3 For the Project
1. **Core stability over features:** A stable core enables future features
2. **Safety over convenience:** Approval gates are not optional
3. **Clarity over cleverness:** Simple code is maintainable
4. **Tests over hope:** Untested code is broken code
5. **Documentation over memory:** Write it down
6. **Community over ego:** Decisions serve the project

---

## 5. Enforcement

### 5.1 Detection Mechanisms
- Static analysis for import violations
- CI checks for architecture compliance
- Code review for boundary violations
- Runtime validation for policy bypasses
- Ledger integrity checks for immutability

### 5.2 Consequences

| Violation | Consequence |
|-----------|-------------|
| Level 1 (Style) | Auto-corrected |
| Level 2 (Boundary) | Review required before merge |
| Level 3 (Architecture) | Blocks merge, triggers review |
| Level 4 (Constitutional) | Immediate revert, notification |

---

## 6. Culture

### 6.1 Architecture-First Culture
- Architecture is not a suggestion. It is binding.
- The project doctrine is the supreme authority.
- Invariants are preserved, not negotiated.

### 6.2 Safety-First Culture
- Safety is the default state.
- Approval gates are not friction; they are protection.
- Privacy is not a feature; it is a requirement.

### 6.3 Quality-First Culture
- Untested code is not shipped.
- Undocumented code is not complete.
- Unreviewed code is not merged.

---

*End of 20_NON_GOALS_AND_ANTI_PATTERNS.md*
*THIS DOCUMENT IS BINDING. IT IS NOT OPTIONAL GUIDANCE.*
