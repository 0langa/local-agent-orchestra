# Setup Guide — local-agent-orchestra Roadmap

What you have: 28 files, ~6,700 lines. This guide tells you where they go and how to activate them.

---

## 1. Copy Files Into Your Repo

From this package into your `local-agent-orchestra` repository:

```
This package → Your repo
├── docs/roadmap/ → docs/roadmap/ (21 docs + pocket card)
├── .kimi/rules/ → .kimi/rules/ (5 rule files)
├── scripts/roadmap-check.py → scripts/roadmap-check.py
├── CONTRIBUTING.md → CONTRIBUTING.md
└── SETUP_GUIDE.md → (discard after reading)
```

Commands:
```bash
cd /path/to/local-agent-orchestra

# 1. Copy roadmap docs
cp -r /path/to/package/docs/roadmap docs/

# 2. Copy Kimi Code rules
cp -r /path/to/package/.kimi/rules .kimi/

# 3. Copy scripts
cp /path/to/package/scripts/roadmap-check.py scripts/
chmod +x scripts/roadmap-check.py

# 4. Copy contributing guide
cp /path/to/package/CONTRIBUTING.md .
```

---

## 2. Kimi Code Rules (Immediate Effect)

Kimi Code (VS Code extension) auto-reads `.kimi/rules/*.md`.

**What works now:**
- Open any file in your repo with Kimi Code
- The 5 rule files inject automatically into context
- Agent knows: 7 Laws, current phase, subsystem boundaries, forbidden patterns

**To update phase:**
Edit `.kimi/rules/01-phase-lock.md` — change `Current Phase: 0` to `1`, `2`, etc. Update the unlocked/locked lists from `docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md`.

**To update subsystem:**
Edit `.kimi/rules/02-subsystem-ownership.md` — change the owner assignments as team changes.

---

## 3. CI Enforcement (One-Time Setup)

### GitHub Actions

Create `.github/workflows/architecture.yml`:

```yaml
name: Architecture
on: [pull_request, push]
jobs:
  enforce:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: python scripts/roadmap-check.py --phase 0 --ci
```

### Pre-Commit Hook (Local)

```bash
# Install
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
python scripts/roadmap-check.py --phase 0
code=$?
if [ $code -ne 0 ]; then
    echo "Fix violations before committing"
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

---

## 4. Web UI Usage (Manual)

The web UI doesn't auto-read rules. Use this pattern:

1. **Create a Project** in Kimi web UI
2. **Upload these files** to the Project:
   - `docs/roadmap/AGENT_POCKET_CARD.md` (primary reference)
   - `docs/roadmap/00_PROJECT_DOCTRINE.md` (authority)
   - `docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md` (phases)
3. **At each conversation start**, paste from `AGENT_POCKET_CARD.md`:
   - The 7 Laws
   - Current phase status
   - Your assigned subsystem
4. **Reference specific docs** with `@filename.md`

---

## 5. Workflow Summary

| Step | Action | Frequency |
|------|--------|-----------|
| 1 | Copy files into repo | Once |
| 2 | Set up CI workflow | Once |
| 3 | Set up pre-commit hook | Once per clone |
| 4 | Update `01-phase-lock.md` when phase advances | Per phase |
| 5 | Run `scripts/roadmap-check.py` before commits | Every commit |
| 6 | Reference `AGENT_POCKET_CARD.md` in web UI | Every session |

---

## 6. What This Gives You

**Without enforcement:** Roadmap is a suggestion agents may ignore.
**With this setup:**
- Kimi Code agents know the laws automatically (`.kimi/rules/`)
- CI blocks merges that violate architecture (`roadmap-check.py --ci`)
- Local hooks catch violations before push (`pre-commit`)
- Human reviewers have clear authority chain (`CONTRIBUTING.md`)
- Quick reference exists for any session (`AGENT_POCKET_CARD.md`)

The rules are **advisory** (agents can theoretically ignore them). The CI is **binding** (merge is blocked). Use both.

---

## 7. Phase Advancement Protocol

When ALL exit gates for a phase pass:

1. Architecture Lead updates `docs/roadmap/06_PHASED_DEVELOPMENT_PLAN.md` — mark gates passed
2. Update `.kimi/rules/01-phase-lock.md` — new phase, new unlocked/locked lists
3. Update CI workflow — change `--phase N` to `--phase N+1`
4. Announce to team — which subsystems are now unlocked
5. Update `AGENT_POCKET_CARD.md` — new phase status (regenerate from source)

Do NOT advance a phase until ALL gates pass. Partial advancement is forbidden.

---

*End of SETUP_GUIDE.md*
*Discard this file after setup. The operational docs are the source of truth.*
