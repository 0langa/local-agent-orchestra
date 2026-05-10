# AGENT POCKET CARD
## One-Page Reference for Autonomous Agents

**Fold this into your context window. Everything else is in the roadmap docs.**

---

## The 7 Laws (NEVER Violate)

| # | Law | One-Line Rule |
|---|-----|---------------|
| 1 | Core Ignorance | `core/` knows NO provider, workflow, tool, or model names |
| 2 | Pack Autonomy | Workflow packs don't import providers or mutate core state |
| 3 | Provider Swap | All providers are lazy-loaded, interchangeable adapters |
| 4 | Disclosure | Beginner gets presets. Power-user gets config. Dev gets APIs. |
| 5 | Event Truth | All state from append-only ledger. No mutable run state. |
| 6 | Local-First | Zero external services by default. Privacy modes enforced. |
| 7 | Safety Default | All destructive ops require approval. Policies are code. |

---

## Current Phase: **0 — FOUNDATION**

### I May Work On
`core/` (refactor only), `providers/<name>/`, `workflows/coding/`, `tools/base.py`, `providers/base.py`, directory structure, import linting, CI

### I Must NOT Touch
`workflows/documents/`, `workflows/research/`, `memory/vector_retrieval.py`, `interfaces/guided_tui/`, `interfaces/web_ui/`, `tools/mcp/`, `tools/browser/`, `presets/` — all LOCKED or RESERVED

### Phase 0 Exit Gates (ALL must pass)
G0.1 No provider logic in core | G0.2 No workflow logic in core | G0.3 Canonical dirs | G0.4 CI enforces | G0.5 Import lint passes | G0.6 Generic ModelRegistry

---

## My Subsystem Check

Before editing ANY file, confirm its owner:

| Directory | Owner | Ask Before Modifying? |
|-----------|-------|----------------------|
| `core/` | Runtime | If not assigned to runtime |
| `providers/` | Provider | If not assigned to provider |
| `tools/` | Tool | If not assigned to tool |
| `workflows/` | Workflow | If not assigned to workflow |
| `memory/` | Memory | If not assigned to memory |
| `interfaces/` | Interface | If not assigned to interface |
| `presets/` | Product | If not assigned to product |
| `docs/roadmap/` | Architecture Lead | **ALWAYS — frozen** |

---

## Self-Check (Before Every Change)

```
[ ] I only touch files in my assigned subsystem
[ ] I do NOT implement future-phase systems
[ ] I do NOT put provider/workflow/tool names in core/
[ ] I do NOT bypass policy_engine or tool_protocol
[ ] I do NOT use mutable global state
[ ] I write tests for my changes
[ ] I update docs for user-facing changes
[ ] I add CHANGELOG entries
```

---

## Import Rules

**Core may import:** `core.*`, `providers.base`, `tools.base`, `workflows.base`, `memory.base`

**Core may NOT import:** `providers.openai`, `tools.filesystem`, `workflows.coding`, any concrete implementation

**Workflows may import:** `workflows.base`, `core.types`, `core.schemas`, `tools.registry` (discovery only)

**Workflows may NOT import:** `core.provider_registry`, any provider implementation

---

## Quick Fixes

| If I see... | I should... |
|-------------|-------------|
| Provider name in `core/` | Move to `providers/<name>/` |
| `subprocess.run()` outside `tools/shell/` | Route through `tool_protocol.invoke()` |
| Workflow role name in `core/` | Move to `workflows/<name>/` |
| Global variable for run state | Use `run_ledger.append()` |
| Direct file write without policy check | Add `policy_engine.evaluate()` |
| Import from concrete implementation | Import from `*.base` protocol instead |

---

## Run Artifact Checklist (Every Run Must Produce)

- `run.json` — metadata
- `timeline.jsonl` — all events
- `config.redacted.json` — config (no secrets)
- `context_bundle.md` — human-readable context
- `tool_calls.jsonl` — every tool call
- `policy_decisions.jsonl` — every policy decision
- `final_report.md` — human-readable outcome

---

## Authority Chain

```
Question about Laws? → 00_PROJECT_DOCTRINE.md
Question about structure? → 02_CORE_ARCHITECTURE_PRINCIPLES.md
Question about phase? → 06_PHASED_DEVELOPMENT_PLAN.md
Question about boundaries? → 05_REPOSITORY_BOUNDARIES.md
Question about my subsystem? → 07_SUBSYSTEM_DEFINITIONS.md
Cross-boundary change? → Architecture Lead approval required
Want to modify roadmap? → Architecture Lead approval required
```

---

## Forbidden One-Liners

- "I'll just put this in core for now" → **NO. Use the protocol.**
- "This workflow needs a core hook" → **NO. Extend the base class.**
- "I'll import the tool directly" → **NO. Use tool_protocol.**
- "Global config is easier" → **NO. Explicit injection.**
- "I'll add the vector DB" → **NO. Phase 5.**
- "MCP would help here" → **NO. Phase 6 RESERVED.**

---

*This card is derived from docs/roadmap/00-20. If this card conflicts with the roadmap, the roadmap wins.*
*Last updated: Phase 0 activation.*
