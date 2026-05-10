# 01 — SYSTEM VISION
## Target User Layers, Product Feel, and Progressive Disclosure Model

**Status:** DERIVED FROM 00_PROJECT_DOCTRINE
**Enforcement:** All interface and workflow decisions must align with this model.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. The Three-Layer Model

The same underlying system serves three distinct user layers without forking the codebase. Each layer sees a different surface of the same runtime. This is not three products. This is one product with progressive disclosure.

```
                    +------------------+
                    |   Beginner Layer  |
                    |  (Preset-driven)  |
                    +--------+---------+
                             | exposes
                    +--------v---------+
                    |  Power-User Layer |
                    | (Configurable)    |
                    +--------+---------+
                             | exposes
                    +--------v---------+
                    |   Developer Layer |
                    |  (Extensible)     |
                    +------------------+
                             |
                    +--------v---------+
                    |   Core Runtime    |
                    | (Generic Engine)  |
                    +------------------+
```

---

## 2. Beginner Layer

### 2.1 Target User
Non-technical users who do not know and do not need to know:
- MCP, vector database, provider registry
- Workflow DAG, policy engine, embedding model
- Context compiler, agent role, tool schema
- Provider adapter, capability registry, event sourcing

### 2.2 Interaction Model
The beginner sees a guided preset picker:

```
What do you want to automate?

1. Help me code in a project
2. Organize files in a folder
3. Chat with local documents
4. Research a topic and create a report
5. Monitor a folder and summarize changes
6. Maintain project documentation
7. Build a custom workflow
```

### 2.3 Required Inputs per Preset

| Preset | Required from User | NOT Required |
|--------|-------------------|--------------|
| Codebase Assistant | Folder path | Model selection, tool config, policy setup |
| Local Document Chat | Folder path, privacy mode | Vector DB backend, chunking strategy |
| Research Report | Topic, privacy mode | Search API config, summarizer model |
| File Organizer | Folder path | Analysis model, approval thresholds |
| Docs Maintainer | Folder path | Stale detection config, update strategy |
| GitHub Maintainer | (Optional) repo | Issue classifier, PR reviewer model |
| Command Assistant | Natural language intent | Shell safety config, command allowlist |
| Personal Workflow Builder | Goal description | Workflow schema, agent definitions |

### 2.4 Safety Defaults at Beginner Layer
- All destructive actions require explicit approval
- Preview of changes shown before application
- Plain language explanations of what will happen
- Default privacy mode: `local-preferred`
- Default approval behavior: `ask` for all non-read operations
- No network access without explicit opt-in per session

### 2.5 Beginner Layer FORBIDDEN Behaviors
No swarm agent may:
- Expose configuration for model roles, tool schemas, or policy rules
- Require the user to select a provider or model
- Present workflow DAGs, agent definitions, or capability registries
- Default to destructive operations without approval gates
- Show raw event logs or ledger entries

---

## 3. Power-User Layer

### 3.1 Target User
Users who understand configuration but do not want to build framework components. They want control without writing code.

### 3.2 Configurable Dimensions

| Dimension | Options | Default |
|-----------|---------|---------|
| Privacy mode | remote-allowed / local-preferred / local-only / strict-private | local-preferred |
| Model preference | Per-role model assignment, fallback chains | Auto-resolution |
| Approval behavior | auto-approve / always-ask / risk-based | risk-based |
| Folder permissions | Scoped read/write boundaries | Project root only |
| Verification | Custom verification commands, thresholds | Workflow default |
| Memory settings | Enable/disable cross-run memory, scope | Disabled |
| Provider fallback | Ordered fallback chain | Primary only |

### 3.3 Example Power-User Policy Expression
```yaml
privacy_mode: local-preferred
model_assignment:
  planner: claude-sonnet
  executor: local-qwen-coder
  verifier: local-qwen-fast
approval_behavior:
  read: auto
  write: ask
  delete: always_ask
  shell: always_ask
  network: ask
memory:
  enabled: true
  scope: project
provider_fallback: [ollama, openai-compatible]
```

### 3.4 Power-User Layer Interface Requirements
- All settings must be inspectable (show current values with explanations)
- Changes must be reversible (no destructive configuration changes)
- Configuration must be portable (exportable/importable as YAML/JSON)
- Invalid combinations must be rejected with explanations

---

## 4. Developer Layer

### 4.1 Target User
Engineers extending the platform: adding providers, tools, workflow packs, memory backends, and policy rules.

### 4.2 Extension Surface

| Extension Type | Interface | Location |
|---------------|-----------|----------|
| Provider adapter | Provider protocol implementation | `providers/<name>/` |
| Tool adapter | Tool protocol implementation | `tools/<category>/` |
| MCP integration | MCP client adapter | `tools/mcp/` |
| Workflow pack | Base workflow class + definitions | `workflows/<name>/` |
| Agent schema | Agent protocol + role definitions | Within workflow pack |
| Memory backend | Memory protocol implementation | `memory/backends/<name>/` |
| Policy rule | Policy engine rule registration | `core/policy/rules/` |
| CLI extension | Click/Typer command registration | `interfaces/cli/extensions/` |

### 4.3 Developer Layer Requirements
- All extensions must be typed (Python type hints required)
- All extensions must be testable (unit test fixtures provided)
- All extensions must follow the core invariant (no core modifications)
- All extensions must register through defined extension points
- All extensions must not leak core internals

### 4.4 Extension Contract
A valid extension:
1. Implements the relevant protocol interface
2. Registers itself through the capability registry
3. Declares its dependencies and conflicts
4. Provides metadata (name, version, author, description)
5. Includes test fixtures
6. Does not import from `core/` internals

---

## 5. Progressive Disclosure Enforcement

### 5.1 Disclosure Rules

| Layer | Visible Configuration | Hidden Internals |
|-------|----------------------|-----------------|
| Beginner | Preset picker, approval prompts, previews | All configuration |
| Power-user | Beginner surface + tunable settings | Protocol internals, schemas |
| Developer | All surfaces + extension APIs | Nothing — full access |

### 5.2 Disclosure Violations (Forbidden)
- A beginner interface that requires understanding agent roles
- A power-user setting that requires editing source code
- A developer extension that requires modifying core files
- A workflow pack that exposes its internal DAG to beginners
- A preset that assumes provider-specific knowledge

### 5.3 The Disclosure Test
For any feature or setting, ask: "At which layer does this belong?" If the answer is unclear, default to the higher layer (more hidden). It is always permissible to move a setting from a lower layer to a higher one based on user feedback. The reverse is a breaking change.

---

## 6. Product Feel Specifications

### 6.1 Beginner Feel
- **Guided:** Step-by-step preset execution with clear next actions
- **Preset-driven:** User picks intent, system handles implementation
- **Jargon-free:** No technical terminology without explanation
- **Safe:** Destructive actions always paused for approval
- **Trustworthy:** Every action explained before execution

### 6.2 Advanced Feel
- **Inspectable:** Full run history, model choices, tool calls visible
- **Configurable:** Granular settings with clear defaults
- **Precise:** Exact control over model assignment, approval thresholds
- **Overridable:** System suggestions can be overridden per-run

### 6.3 Developer Feel
- **Extensible:** New components added without core changes
- **Modular:** Clear interfaces between all subsystems
- **Schema-driven:** Type definitions and protocols are the contract
- **Testable:** Every component can be unit tested in isolation

### 6.4 The Feel Test
> "My mom can use it without knowing what an agent is. I can use it without feeling boxed in. Developers can extend it without forking the core."

Any feature that fails this test for its target layer is incorrectly positioned.

---

## 7. Interface Priority

At 70% completion, interfaces are prioritized as follows:

1. **CLI (primary)** — Always available. Beginner presets accessible. Power-user settings exposed via flags/config.
2. **Guided TUI** — Terminal-native preset picker and approval flow. Optional but recommended.
3. **Web UI** — Reserved for post-70% implementation.
4. **Desktop UI** — Reserved for post-70% implementation.
5. **API Server** — Reserved for post-70% implementation.

No interface may bypass the core runtime. All interfaces are thin layers over the same execution engine.

---

*End of 01_SYSTEM_VISION.md*
