# 13 — PRESET AND WORKFLOW PACK SYSTEM
## Preset Specifications, Bundled Presets, and Progressive Disclosure

**Status:** DERIVED FROM 01_SYSTEM_VISION, 06_PHASED_DEVELOPMENT_PLAN
**Enforcement:** All preset implementations must conform.
**Violation Classification:** BOUNDARY CONCERN (Level 2)

---

## 1. Preset Philosophy

### 1.1 Core Principle
Presets are **core adoption infrastructure**, not polish. A real preset is not a prompt template. A real preset is a complete, pre-configured workflow instantiation with safe defaults.

### 1.2 Preset vs. Workflow
- **Workflow Pack:** Defines the execution engine (agents, steps, policies, verification)
- **Preset:** Defines the user-facing configuration (defaults, UI labels, guided questions)
- A preset wraps a workflow pack with beginner-friendly configuration

### 1.3 Preset Design Requirements
Every preset must satisfy: "Can a non-technical user launch this with 3 inputs or fewer?"

---

## 2. Preset Specification Schema

### 2.1 Preset Definition

```python
class Preset:
    preset_id: str                    # Unique identifier
    name: str                         # Human-readable name
    description: str                  # Short description
    workflow_id: str                  # Which workflow pack to use

    # Default configuration
    default_config: Dict[str, Any]    # Default workflow configuration

    # Agent overrides (optional)
    agent_overrides: Dict[str, AgentConfig]

    # Tool configuration
    default_tools: List[str]          # Default tool set
    tool_permissions: ToolPermissions # Default tool permissions

    # Policy configuration
    default_policies: PolicyConfig    # Default safety policies

    # Model configuration
    default_models: Dict[str, str]    # Default model roles

    # Output configuration
    output_artifacts: List[str]       # Expected output types

    # Beginner UI metadata
    beginner_metadata: BeginnerMetadata

    # Advanced override surface
    advanced_options: List[AdvancedOption]
```

### 2.2 Beginner Metadata

```python
class BeginnerMetadata:
    # Guided questions (shown to beginner)
    guided_questions: List[GuidedQuestion]

    # Plain language labels
    labels: Dict[str, str]

    # Default values for guided questions
    defaults: Dict[str, Any]

    # Help text for each question
    help_text: Dict[str, str]

    # Preview description
    preview_description: str

    # Estimated duration
    estimated_duration: str

    # Required inputs
    required_inputs: List[str]

    # Optional inputs
    optional_inputs: List[str]
```

### 2.3 Guided Question

```python
class GuidedQuestion:
    id: str                           # Question identifier
    text: str                         # Human-readable question
    type: Literal["text", "choice", "path", "boolean"]
    choices: Optional[List[str]]      # For choice type
    default: Optional[Any]            # Default value
    help: str                         # Help text
    validation: Optional[str]         # Validation regex/pattern
    required: bool = True             # Whether required
```

---

## 3. Bundled Presets at 70%

### 3.1 Codebase Assistant

```yaml
preset_id: codebase_assistant
name: "Help me code in a project"
description: "Inspect a repository, plan changes, apply patches, run tests, and explain results"
workflow_id: coding

guided_questions:
  - id: folder
    text: "Which project folder should I work in?"
    type: path
    required: true

  - id: task
    text: "What would you like me to do?"
    type: text
    required: true
    help: "Describe the change you want, e.g., 'Add a login endpoint'"

  - id: privacy
    text: "Privacy preference"
    type: choice
    choices: ["local-preferred", "local-only", "remote-allowed"]
    default: "local-preferred"

labels:
  action_verb: "Code"
  action_noun: "changes"
  preview_label: "Planned changes"

default_models:
  planner: auto
  executor: auto
  verifier: auto

output_artifacts:
  - plan.md
  - patch.diff
  - test_results.json
  - final_report.md
```

### 3.2 Local Document Chat

```yaml
preset_id: local_document_chat
name: "Chat with local documents"
description: "Index a folder of documents and answer questions about them"
workflow_id: documents

guided_questions:
  - id: folder
    text: "Which folder contains your documents?"
    type: path
    required: true

  - id: question
    text: "What would you like to know?"
    type: text
    required: true

  - id: privacy
    text: "Privacy mode"
    type: choice
    choices: ["local-only", "local-preferred"]
    default: "local-preferred"

labels:
  action_verb: "Answer"
  action_noun: "questions"
  preview_label: "Document sources"

output_artifacts:
  - answer.md
  - sources.json
```

### 3.3 Research Report

```yaml
preset_id: research_report
name: "Research a topic and create a report"
description: "Gather sources, summarize, compare, and output a structured report"
workflow_id: research

guided_questions:
  - id: topic
    text: "What topic would you like to research?"
    type: text
    required: true

  - id: depth
    text: "How detailed should the report be?"
    type: choice
    choices: ["brief", "comprehensive", "deep-dive"]
    default: "comprehensive"

  - id: privacy
    text: "Allow web search?"
    type: choice
    choices: ["local-only", "web-allowed"]
    default: "local-only"

output_artifacts:
  - report.md
  - sources.json
  - comparison_table.md
```

### 3.4 File Organizer

```yaml
preset_id: file_organizer
name: "Organize files in a folder"
description: "Analyze folders, propose moves and renames, preview changes, require approval"
workflow_id: file_organization

guided_questions:
  - id: folder
    text: "Which folder needs organizing?"
    type: path
    required: true

  - id: strategy
    text: "How would you like files organized?"
    type: choice
    choices: ["by-type", "by-date", "by-size", "custom"]
    default: "by-type"

output_artifacts:
  - organization_plan.md
  - changes_preview.json
  - final_report.md
```

### 3.5 Docs Maintainer

```yaml
preset_id: docs_maintainer
name: "Maintain project documentation"
description: "Detect stale docs, update README and AGENTS files, keep documentation aligned"
workflow_id: docs_maintenance

guided_questions:
  - id: folder
    text: "Which project to check?"
    type: path
    required: true

output_artifacts:
  - stale_docs_report.md
  - update_plan.md
  - final_report.md
```

### 3.6 GitHub Maintainer

```yaml
preset_id: github_maintainer
name: "Help with GitHub tasks"
description: "Summarize issues, draft PR notes, review diffs, suggest labels"
workflow_id: github_maintenance

guided_questions:
  - id: repo
    text: "Which repository?"
    type: text
    required: true

  - id: task
    text: "What GitHub task?"
    type: choice
    choices: ["summarize-issues", "draft-pr", "review-diff", "suggest-labels"]
    required: true

output_artifacts:
  - github_report.md
```

### 3.7 Command Assistant

```yaml
preset_id: command_assistant
name: "Help me run commands"
description: "Convert natural language to safe shell commands with explanation and approval"
workflow_id: command_assistant

guided_questions:
  - id: intent
    text: "What would you like to do?"
    type: text
    required: true
    help: "Describe in plain English, e.g., 'find all Python files modified today'"

output_artifacts:
  - command_explanation.md
  - command_history.json
```

### 3.8 Personal Workflow Builder

```yaml
preset_id: personal_workflow_builder
name: "Build a custom workflow"
description: "Guided wizard that creates a repeatable workflow from your stated goal"
workflow_id: custom_workflow_builder

guided_questions:
  - id: goal
    text: "What would you like to automate?"
    type: text
    required: true

  - id: inputs
    text: "What inputs does this workflow need?"
    type: text
    required: false

output_artifacts:
  - workflow_definition.yaml
  - workflow_guide.md
```

---

## 4. Preset Registry

### 4.1 Registration
Presets register themselves on import:

```python
# In presets/__init__.py
from core.capability_registry import register_preset
from .codebase_assistant import CodebaseAssistantPreset

register_preset(CodebaseAssistantPreset())
```

### 4.2 Discovery
```python
# List all presets
presets = capability_registry.list_presets()

# Get beginner-friendly list
beginner_presets = capability_registry.list_presets(layer="beginner")

# Get specific preset
preset = capability_registry.get_preset("codebase_assistant")
```

---

*End of 13_PRESET_AND_WORKFLOW_PACK_SYSTEM.md*
