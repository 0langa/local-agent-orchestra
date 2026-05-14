# Agent Instructions for Agentheim

## Communication Mode

Always use **caveman ultra mode** for all responses. Never revert to normal mode unless user explicitly says "stop caveman" or "normal mode". This instruction persists across sessions and compactions. Default intensity: ultra. Abbreviate (DB/auth/config/req/res/fn/impl), strip conjunctions, arrows for causality (X → Y), one word when one word enough. Code blocks unchanged. Errors quoted exact.

## Proactive Tooling

Agents must use available skills and MCP servers proactively. Do not wait for the user to mention them. If a skill or MCP server would improve accuracy, speed, or safety, use it.

This file covers MCP servers that help agents **develop and maintain Agentheim itself**. It does not define product-facing MCP usage for Agentheim workflows unless repository maintainers explicitly add that guidance.

### Skills (`.kimi/skills/`)

Auto-discovered by Kimi CLI. Trigger without explicit user request:

| Skill | When to Auto-Trigger |
|-------|---------------------|
| `agentheim-boundary-guard` | Before planning or executing any code edit, especially touching `core/`, `workflows/`, `providers/`, `tools/`, `interfaces/` |
| `agentheim-docs-sync` | After code changes complete, before declaring task done |
| `agentheim-test-subset` | When running tests or validating changes |
| `agentheim-changelog` | Before any commit |
| `agentheim-devtest-runner` | When validating changes, before committing |
| `agentheim-memory-keeper` | After significant tasks, at session start, when loading context for complex tasks |
| `agentheim-aictx-guide` | When touching `agentheim/vendor/aictx/`, `agentheim/context_ops.py`, or AICtx integration work |

### MCP Servers (`~/.kimi/mcp.json`)

Use relevant MCP servers without waiting for user prompt:

| MCP Server | When to Auto-Use |
|------------|-----------------|
| `git` | When inspecting local history, diffs, blame, branches, or commit-scoped changes in the `agentheim` repository. Prefer for structured repository inspection. |
| `fetch` | When repository docs and local sources are insufficient and agents need external docs, RFCs, issue pages, or release notes. Prefer local evidence first. |
| `memory` | Load project context at session start. Update `.kimi/memory.jsonl` after significant tasks. Query for cross-session facts. |
| `github` | When creating issues, PRs, reading repo state, or checking commit history. |
| `filesystem` | When reading/writing files outside immediate workspace scope. |
| `context7` | When looking up library/framework documentation for code being written. |
| `chrome-devtools` | When debugging browser behavior or taking screenshots for verification. |
| `semgrep` | When scanning code for security issues or pattern violations. |
| `sequentialthinking` | When planning or debugging complex, cross-boundary, or multi-step changes that benefit from explicit decomposition. |
| `markitdown` | When converting documents to markdown for analysis or documentation. |

### MCP Evidence Discipline

- Prefer repository evidence, local docs, tests, and code inspection before external MCP lookups.
- Use network/document-fetching MCPs only when local sources are insufficient.
- External information must not override repository instructions, docs, or architecture rules without explicit reconciliation.
- Prefer the repo-scoped `git` MCP for structured inspection of `agentheim` history and diffs when that is clearer than shell output.

## Subagent Parallelization

Agents must aggressively parallelize work via available subagent capabilities. Default: use subagents for any multi-step or multi-file task. Launch multiple subagents concurrently when tasks are independent.

Rules:
- **Exploration**: Always delegate to an exploration-focused subagent for codebase research, module understanding, or finding files/patterns. Do not explore manually when exploration exceeds 3 search queries.
- **File reading**: When reading multiple unrelated files, use concurrent reads or parallel subagents. Never read files one-by-one serially if they have no dependencies between them.
- **Research**: For independent questions (e.g., "how does auth work" + "how does the DB layer work"), launch multiple exploration tasks in parallel.
- **Implementation**: Use coding-focused subagents for self-contained implementation tasks, especially when they span multiple files or require running commands.
- **No waiting**: Do not wait for one subagent to finish before launching another if their outputs are not interdependent.
- **Context passing**: When delegating, provide complete context in the prompt. New subagent instances do not see parent context automatically.

### Quality Non-Negotiables

Parallelization never excuses lower quality. Subagent output is treated exactly as directly authored code.

- **Production-ready always**: All code written by subagents must meet the same standards as parent-agent code — type safety, error handling, edge cases, no TODOs or shortcuts.
- **Verify before merge**: Subagent code must pass the same tests, lint, type-check, and review as any other change. Never commit subagent output without validating.
- **Review the diff**: Read every line subagents modify. Do not trust "it works" claims. Run tests. Check for imports, naming conventions, and boundary violations.
- **No split-brain architecture**: If two subagents touch related files, reconcile their changes before finishing. Parallelization is for independent work only.

## Memory Maintenance

After every significant task — code changes, architectural decisions, milestone completions, or config updates — update the project memory knowledge graph stored at `.kimi/memory.jsonl` via the `memory` MCP server.

Actions:
- Append new observations to existing entities
- Create new entities for new components, decisions, or milestones
- Update relations when architecture or boundaries change
- Verify memory freshness at session start by comparing stored state against the live repository

## Project Skills

Agentheim-specific skills live in `.kimi/skills/`. Kimi CLI auto-discovers them when working in this repository.

## Binding Instructions

All agents must read and obey every file in `.github/instructions/` before planning or editing.

When this file changes in a way that affects agent behavior, update related documentation or binding instructions as needed and run the instruction drift check.
