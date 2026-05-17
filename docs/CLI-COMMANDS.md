# CLI Commands Reference

> Entry points:
> - installed script: `agentheim <command> [options]`
> - repo-local: `python -m interfaces.cli.cli <command> [options]`

The CLI is built with Typer. The lists below are derived from the current command registrations in `interfaces/cli/cli.py`, `interfaces/cli/ctx_commands.py`, `interfaces/cli/provider_commands.py`, and `interfaces/cli/oci_commands.py`.

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
| `memory` | Interact with global memory. | `ACTION` = `get|set|history|profile`, `--key`, `--value`, `--model-id` |
| `doctor` | Diagnose configuration and environment issues. | `--skip-connectivity`, `--oci` |
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
agentheim provider list --profile azure-real
```

#### Add a new profile

Profiles are created implicitly the first time you add a provider into a new profile name.

```bash
agentheim provider add azure-real --template azure_foundry --model gpt-5.4 --role planner --profile azure-real --endpoint https://YOUR-RESOURCE.openai.azure.com/openai/v1
```

Then add more role bindings as needed:

```bash
agentheim provider assign generator --provider azure-real --model gpt-5.4 --profile azure-real
agentheim provider assign reviewer --provider azure-real --model gpt-5.4 --profile azure-real
```

Or switch all existing roles in that profile at once:

```bash
agentheim provider assign-all --provider azure-real --model gpt-4.1 --profile azure-real
```

#### Edit an existing profile

Common edit operations are command-based:

- change the default active profile:

```bash
agentheim provider use azure-real
```

- change the project-local profile pointer:

```bash
agentheim provider use azure-real --project
```

- change one role binding:

```bash
agentheim provider assign planner --provider azure-real --model gpt-4.1 --profile azure-real
```

- change all current role bindings in a profile:

```bash
agentheim provider assign-all --provider azure-real --model gpt-4.1 --profile azure-real
```

- rotate the provider secret:

```bash
agentheim provider rotate-secret azure-real --profile azure-real
```

To edit provider endpoint/auth metadata, there is currently no dedicated `provider update` command. The supported path today is:

Use `provider update` directly:

```bash
agentheim provider update azure-real --profile azure-real --endpoint https://YOUR-RESOURCE.openai.azure.com/openai/v1 --timeout-seconds 90
agentheim provider update azure-real --profile azure-real --header api-version=2025-04-01-preview
agentheim provider update azure-real --profile azure-real --api-key NEW_SECRET_VALUE
```

#### Delete an existing profile

Delete an empty profile:

```bash
agentheim provider delete-profile azure-real
```

Force-delete a populated profile and remove its saved provider secrets:

```bash
agentheim provider delete-profile azure-real --force
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

Privacy and policy concepts exist in code, but the public CLI in this checkout does not expose a top-level privacy-mode selector.

Current user-visible safety behavior includes:

- policy-routed tool invocation
- approval prompts for medium-risk filesystem operations such as `copy`
- denial of high-risk operations through constrained interface paths

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
python -m interfaces.cli.cli provider update azure-real --profile azure-real --timeout-seconds 90
python -m interfaces.cli.cli provider assign-all --provider azure-real --model gpt-4.1 --profile azure-real
python -m interfaces.cli.cli provider delete-profile scratch --force
python -m interfaces.cli.cli provider test --role planner

# Context operations
python -m interfaces.cli.cli ctx status --project . --strict
python -m interfaces.cli.cli ctx run --project . --scope changed --write patch
```
