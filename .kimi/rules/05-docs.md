# Documentation Integrity — BINDING

Documentation drift is a defect. Documentation must describe the current repository unless it is explicitly historical, speculative, or marked as a plan.

## Binding Rules

- Root GitHub-facing files must remain useful and render correctly: `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `AGENTS.md`.
- `docs/` is the canonical home for long-form documentation.
- `docs/CHANGELOG.md` is the canonical changelog.
- Historical entries in `docs/CHANGELOG.md` must not be rewritten only to remove old references.
- Examples must be executable against the current repository or clearly marked conceptual.
- Local Markdown links in active docs must resolve.
- Active docs must not link to deleted `docs/roadmap/` files.
- Public behavior, commands, paths, configuration keys, endpoints, provider names, workflow IDs, and test commands must be verified before being documented.

## Required Checks

Run `python scripts/check-agent-instructions.py` after changing:

- root GitHub-facing docs
- any file under `docs/`
- `.github/agents/*.agent.md`
- `.github/instructions/*.md`
- GitHub issue or PR templates
- devtest command documentation

If the check fails, fix the docs or instruction drift in the same change.
