# CLI Commands Reference

> Entry points:
> - installed script: `agentheim <command> [options]`
> - repo-local: `python -m interfaces.cli.cli <command> [options]`

The CLI is built with Typer. The lists below are derived from the current command registrations in `interfaces/cli/cli.py`, `interfaces/cli/product_commands.py`, `interfaces/cli/ctx_commands.py`, `interfaces/cli/provider_commands.py`, and `interfaces/cli/oci_commands.py`.

For the live, always-up-to-date command tree, run:

```bash
agentheim commands
agentheim commands --json
```

---

## Getting Started

| Command | Description | Key Options / Arguments |
| --- | --- | --- |
| `setup` | Configure one beginner provider, bind roles, and run readiness checks. | `--provider`, `--template`, `--model`, `--endpoint`, `--api-key`, `--profile`, `--local`, `--yes`, `--json`, `--dry-run`, `--privacy-mode` |
| `status` | Show provider readiness, integrations, recent runs, and next actions. | `--profile`, `--repo`, `--json`, `--debug-bundle` |
| `use` | Launch a task by plain-language goal or direct task ID. | `TASK_ID`, `--input key=value`, `--repo`, `--json`, `--yes`, `--watch` |
| `runs` | Inspect and recover runs. Calling without a subcommand lists all runs. | `--repo`, `--json` |
| `runs list` | List runs. | `--repo`, `--json` |
| `runs show` | Show a specific run. | `RUN_ID`, `--repo`, `--json`, `--watch` |
| `runs report` | Display the report for a run. | `RUN_ID`, `--repo`, `--json` |
| `runs resume` | Resume a run from its ledger. | `RUN_ID`, `--repo`, `--json` |
| `runs open-folder` | Open the artifact folder for a run. | `RUN_ID`, `--repo` |
| `open` | Open the local Agentheim UI on localhost. | `--port`, `--no-browser`, `--desktop`, `--json` |

---

## Root Commands

| Command | Description | Key Options / Arguments |
| --- | --- | --- |
| `config-dump` | Print loaded config as JSON. | `--redacted` / `--raw` |
| `ping-models` | Ping configured models with a deterministic request. | none |
| `inspect` | Inspect a repo and produce a compact context summary. | `--repo`, `--json`, `--write-ledger` |
| `plan` | Build a structured implementation plan without editing files. | `TASK_TEXT`, `--repo`, `--write-ledger`, `--out` |
| `run` | Plan and apply bounded work orders without auto-commit. | `TASK_TEXT`, `--repo`, `--mode`, `--allow-dirty`, `--max-fix-attempts`, `--max-diff-lines`, `--command-timeout`, `--no-tests` |
| `list-runs` | List persisted runs under the repository. | `--repo` |
| `report` | Emit canonical run summary JSON for a run. | `--repo`, `--run-id` |
| `resume` | Resume a run from its ledger. | `--repo`, `--run-id` |
| `presets` | List all available presets. | none |
| `start` | Run a preset with the given inputs. | `PRESET_ID`, `--input key=value` |
| `guided` | Launch the guided TUI preset picker. | none |
| `memory` | Interact with global memory. | `ACTION` = `get\|set\|history\|profile`, `--key`, `--value`, `--model-id` |
| `doctor` | Diagnose configuration and environment issues. | `--skip-connectivity`, `--oci` |
| `provider` | Manage provider profiles, secrets, templates, and role bindings. | subcommands |
| `ctx` | Run context operations and OCI artifact commands. | subcommands |
| `mcp-list` | List tools from configured MCP servers. | `--config` |
| `mcp-call` | Invoke an MCP tool directly. | `TOOL_NAME`, `--arg key=value`, `--config` |
| `desktop` | Launch the desktop UI wrapper. | `--port`, `--no-tray` |
| `copy` | Copy a file or directory within the workspace through the filesystem tool. | `SOURCE`, `DESTINATION` |
| `commands` | Print the full flattened command tree. | `--json` |

---

## Provider Commands

Use `agentheim commands` for a flattened cross-section of every provider and nested CLI path.

| Command | Description |
| --- | --- |
| `provider templates` | List provider setup templates. |
| `provider add` | Add a provider profile entry and initial role binding. |
| `provider list` | List providers and role bindings in a profile. |
| `provider profiles` | List profile names with default marker and counts. |
| `provider update` | Update endpoint, auth, headers, metadata, timeout, or secret for a provider. |
| `provider use` | Set the default profile or write the project profile pointer. |
| `provider assign` | Bind a team role to a provider/model. |
| `provider assign-all` | Bind every existing role in a profile to one provider/model. |
| `provider rotate-secret` | Rotate a provider secret. |
| `provider remove` | Remove a provider and its role bindings. |
| `provider delete-profile` | Delete an entire profile, optionally forcing removal of populated profiles. |
| `provider test` | Invoke the configured provider for a role with a small test request. |
| `provider import-env` | One-time migration from legacy environment variables. |

Notable options from current help:

- `provider add` supports `--template`, `--model`, `--role`, `--profile`, `--endpoint`, `--auth-mode`, `--api-key`, `--capability`
- `provider profiles` has no options
- `provider update` supports `PROVIDER_ID`, `--profile`, `--endpoint`, `--auth-mode`, repeated `--header`, repeated `--metadata`, `--timeout-seconds`, `--api-key`
- `provider assign` supports `ROLE`, `--provider`, `--model`, `--profile`, `--capability`
- `provider assign-all` supports `--provider`, `--model`, `--profile`, optional repeated `--capability`
- `provider delete-profile` supports `PROFILE`, optional `--force`
- `provider test` supports `--role`, `--profile`

### Profile Management

#### List profile names only

```bash
agentheim provider profiles
```

#### Inspect one profile in detail

```bash
agentheim provider list --profile azure-prod
```

#### Add a new profile

Profiles are created implicitly the first time you add a provider into a new profile name.

```bash
agentheim provider add azure-prod --template azure_foundry --model gpt-5.4 --role planner --profile azure-prod --endpoint https://YOUR-RESOURCE.openai.azure.com/openai/v1
```

Then add more role bindings as needed:

```bash
agentheim provider assign generator --provider azure-prod --model gpt-5.4 --profile azure-prod
agentheim provider assign reviewer --provider azure-prod --model gpt-5.4 --profile azure-prod
```

Or switch all existing roles in that profile at once:

```bash
agentheim provider assign-all --provider azure-prod --model gpt-4.1 --profile azure-prod
```

#### Edit an existing profile

Common edit operations are command-based:

- change the default active profile:

```bash
agentheim provider use azure-prod
```

- change the project-local profile pointer:

```bash
agentheim provider use azure-prod --project
```

- change one role binding:

```bash
agentheim provider assign planner --provider azure-prod --model gpt-4.1 --profile azure-prod
```

- change all current role bindings in a profile:

```bash
agentheim provider assign-all --provider azure-prod --model gpt-4.1 --profile azure-prod
```

- rotate the provider secret:

```bash
agentheim provider rotate-secret azure-prod --profile azure-prod
```

- update endpoint, auth, headers, or timeout:

```bash
agentheim provider update azure-prod --profile azure-prod --endpoint https://YOUR-RESOURCE.openai.azure.com/openai/v1 --timeout-seconds 90
agentheim provider update azure-prod --profile azure-prod --header api-version=2025-04-01-preview
agentheim provider update azure-prod --profile azure-prod --api-key NEW_SECRET_VALUE
```

#### Delete an existing profile

Delete an empty profile:

```bash
agentheim provider delete-profile azure-prod
```

Force-delete a populated profile and remove its saved provider secrets:

```bash
agentheim provider delete-profile azure-prod --force
```

---

## Context Commands

| Command | Description | Key Options |
| --- | --- | --- |
| `ctx init` | Initialize repo for context processing. | `--project` |
| `ctx scan` | Scan repository and print inventory summary. | `--project` |
| `ctx run` | Run the full context generation pipeline. | `--project`, `--scope`, `--write`, `--allow-dirty` |
| `ctx verify` | Verify context lock against repository state. | `--project`, `--strict` |
| `ctx status` | Show stale-context detection status. | `--project`, `--strict` |
| `ctx clean` | Remove generated run artifacts. | `--project`, `--run-id`, `--keep-runs` |
| `ctx public-docs impact` | Map source changes to impacted public docs. | `--project`, `--scope` |
| `ctx public-docs update` | Generate patches for impacted public docs. | `--project`, `--scope`, `--write` |

### OCI Subcommands

| Command | Description | Key Options |
| --- | --- | --- |
| `ctx oci doctor` | Run OCI readiness checks. | `--project` |
| `ctx oci snapshot create` | Create a deterministic repository snapshot. | `--project`, `--run-id` |
| `ctx oci snapshot verify` | Verify snapshot integrity. | `--project` |
| `ctx oci bundle create` | Create a result bundle for a run. | `--project`, `--run-id` |
| `ctx oci bundle verify` | Verify result bundle integrity. | `--project`, `--run-id` |

The `ctx oci` subtree is registered from `interfaces/cli/oci_commands.py`.

---

## Full Command Tree

For discovery, use:

```bash
agentheim commands
agentheim commands --json
```

`agentheim --help` stays compact and grouped by major area, while `agentheim commands` shows the full flattened command surface including nested branches.

### Current Grouping

- `Getting Started`
- `Setup & Configuration`
- `Repository Work`
- `Presets`
- `State & Integrations`
- `Context & Artifacts`

The flattened output is generated at runtime from the registered Typer command tree, so it stays aligned with the live CLI surface instead of relying on a manually maintained list.

---

## Run Modes

`agentheim run --mode` currently accepts:

| Mode | Meaning |
| --- | --- |
| `apply` | default path |
| `auto` | less interactive execution path |
| `ci` | non-interactive CI-oriented path |

The CLI validates only these three mode names.

---

## Privacy And Safety

Privacy modes are selectable from the beginner CLI surface.

```bash
agentheim setup --privacy-mode local_only
agentheim status --debug-bundle
```

Current user-visible safety behavior includes:

- selectable privacy modes (`standard`, `local_only`, `strict_private`, `encrypted`)
- policy-routed tool invocation
- approval prompts for medium-risk filesystem operations such as `copy`
- denial of high-risk operations through constrained interface paths
- secret redaction in debug bundles and ledger entries

See [Safety & Security](SAFETY.md) for full details.

---

## Artifacts

Runs write under `.ai-team/runs/<run-id>/`, but the exact artifact set depends on the workflow/runtime. Common files visible in the current repository include:

- `run.json`
- `ledger.jsonl`
- `ledger.hash`
- `tool_calls.jsonl`
- `state_transitions.jsonl`
- `final_report.md`
- `final_report.json`
- workflow-specific diagnostics or summary files

Do not assume every run produces the same artifact inventory.

---

## Quick Examples

```bash
# CLI help
python -m interfaces.cli.cli --help
python -m interfaces.cli.cli commands
python -m interfaces.cli.cli commands --json

# Interactive setup
agentheim setup

# Status and diagnostics
agentheim status
agentheim status --json
agentheim status --debug-bundle

# Run a task by goal
agentheim use code --input repo=. --input task="Refactor auth module"
agentheim use docs-chat --input repo=. --input query="Explain the routing logic"

# Inspect a repo
python -m interfaces.cli.cli inspect --repo .

# Plan work
python -m interfaces.cli.cli plan "Add rate limiting middleware" --repo .

# Run work
python -m interfaces.cli.cli run "Refactor auth module" --repo . --mode apply

# Provider setup
python -m interfaces.cli.cli provider templates
python -m interfaces.cli.cli provider profiles
python -m interfaces.cli.cli provider add openai --template openai_v1 --model gpt-4o-mini --role planner
python -m interfaces.cli.cli provider update azure-prod --profile azure-prod --timeout-seconds 90
python -m interfaces.cli.cli provider assign-all --provider azure-prod --model gpt-4.1 --profile azure-prod
python -m interfaces.cli.cli provider delete-profile scratch --force
python -m interfaces.cli.cli provider test --role planner

# Context operations
python -m interfaces.cli.cli ctx status --project . --strict
python -m interfaces.cli.cli ctx run --project . --scope changed --write patch
```
