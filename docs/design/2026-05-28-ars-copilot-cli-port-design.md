# ARS Copilot CLI Port — Design Spec

**Date:** 2026-05-28
**Issue:** Copilot CLI sibling distribution of Academic Research Skills
**Target release:** v3.9.4.2-copilot (parity with upstream v3.9.4.2)
**Design phase:** v1 initial
**Upstream baseline:** `Imbad0202/academic-research-skills` @ commit `85bf5256d3` (v3.9.4.2)
**Sibling references:** `Imbad0202/academic-research-skills-codex` (existing Codex CLI port)
**Related:** v3.7.0 plugin packaging roadmap, v3.10 active conductor (#134)

**Doc revision history:**
- v1 (2026-05-28): initial — complete Copilot CLI port design
- v2 (2026-05-28): corrected — keep symlinks, auto slash commands via plugin namespace, self-bootstrapping extension setup via script
- v3 (2026-05-28): refined — `.bootstrapped` marker file for silent no-op after setup; plugin install via `/plugin marketplace add` + `/plugin install`; self-bootstrapping vs. installation script comparison (§5.4)

---

## 1. Summary

Port Academic Research Skills (ARS) v3.9.4.2 from Claude Code to GitHub Copilot CLI as a sibling distribution (`academic-research-skills-copilot`). The port uses Copilot CLI's plugin system (`/plugin install`), native slash commands (`CommandDefinition`), skill auto-triggering (`SKILL.md` frontmatter), extension hooks (`onSessionStart` announce, `onPreToolUse` enforcement reserve), and configurable model routing via environment variables.

Two git branches in the sibling repo:
- `claude-code-main` — stays in sync with upstream `Imbad0202/academic-research-skills:main` (user-managed)
- `copilot-main` — Copilot-specific adaptations (copilot-assistant-maintained)

---

## 2. Design Philosophy

1. **Vendor upstream unmodified where possible.** `shared/`, `tests/`, `docs/`, Python `scripts/` are direct copies.
2. **Adapt where necessary.** `SKILL.md` frontmatter, agent prompt templates, instruction files.
3. **Replace where platform-specific.** Claude plugin hooks → Copilot extension hooks, slash commands → `CommandDefinition`, `CLAUDE.md` → `ars-bootstrap` skill + `AGENTS.md` (contributor-only).
4. **Keep Codex audit infrastructure.** All `scripts/run_codex_audit.sh`, `shared/contracts/audit/` schemas, and `codex_audit_multifile_template.md` remain unchanged for cross-model audit use and upstream consistency.
5. **Defer enforcement hooks.** `onPreToolUse` phase-boundary enforcement is reserved for v3.10 parity (same posture as upstream).
6. **Model routing is opt-in.** Default: session model for all dispatches. Users configure `ARS_MODEL_ARCHITECT` / `ARS_MODEL_EXECUTION` env vars when using BYOK providers.

---

## 3. 1:1 Feature Mapping

### 3.1 Plugin Packaging

| # | Claude Code Feature | Copilot CLI Equivalent | Status |
|---|-------------------|----------------------|--------|
| P1 | `.claude-plugin/plugin.json` | `.claude-plugin/plugin.json` (same schema) | ✅ Direct port |
| P2 | `.claude-plugin/marketplace.json` | `.claude-plugin/marketplace.json` | ✅ Direct port |
| P3 | Install via `/plugin marketplace add` + `/plugin install` | Same commands | ✅ Identical |
| P4 | `package.json` | `package.json` (added; Copilot CLI uses `"type": "module"`) | 🆕 New |

### 3.2 Slash Commands — Dual System

ARS provides slash commands through two complementary mechanisms:

**A. Auto-generated plugin namespace commands (zero setup, always available):**

When a plugin is installed via `/plugin install`, Copilot CLI automatically creates slash commands for every skill using the pattern `/<plugin-name>:<skill-name>`. These trigger the skill's default mode:

| Auto Command | Skill Triggered | Default Behavior |
|---|---|---|
| `/academic-research-skills:deep-research` | deep-research | Socratic guided research dialogue |
| `/academic-research-skills:academic-paper` | academic-paper | Full paper writing pipeline |
| `/academic-research-skills:academic-paper-reviewer` | academic-paper-reviewer | Multi-perspective peer review |
| `/academic-research-skills:academic-pipeline` | academic-pipeline | 10-stage end-to-end pipeline |
| `/academic-research-skills:ars-bootstrap` | ars-bootstrap | Session-start instruction injection |

**B. Mode-specific slash commands (via extension, self-bootstrapping):**

After the extension is registered (§8), 13 mode-specific commands become available via Copilot CLI's native `CommandDefinition` API in `extension.mjs`. Model routing moves from YAML frontmatter to env vars.

| # | Claude Code Command | Copilot CLI CommandDefinition | Model Tier |
|---|-------------------|------------------------------|------------|
| C1 | `/ars-full` (model: opus) | `ars-full` → `session.send({prompt...})` | architect |
| C2 | `/ars-revision-coach` (model: opus) | `ars-revision-coach` | architect |
| C3 | `/ars-reviewer` (model: opus) | `ars-reviewer` | architect |
| C4 | `/ars-plan` (model: sonnet) | `ars-plan` | execution |
| C5 | `/ars-outline` (model: sonnet) | `ars-outline` | execution |
| C6 | `/ars-revision` (model: sonnet) | `ars-revision` | execution |
| C7 | `/ars-abstract` (model: sonnet) | `ars-abstract` | execution |
| C8 | `/ars-lit-review` (model: sonnet) | `ars-lit-review` | execution |
| C9 | `/ars-format-convert` (model: sonnet) | `ars-format-convert` | execution |
| C10 | `/ars-citation-check` (model: sonnet) | `ars-citation-check` | execution |
| C11 | `/ars-disclosure` (model: sonnet) | `ars-disclosure` | execution |
| C12 | `/ars-mark-read` (model: sonnet) | `ars-mark-read` | execution |
| C13 | `/ars-unmark-read` (model: sonnet) | `ars-unmark-read` | execution |

**Model tier routing:** Each command's handler checks `ARS_MODEL_ARCHITECT` (architect tier) or `ARS_MODEL_EXECUTION` (execution tier) env vars. If set, the dispatch prompt instructs the agent to use `task({model: "<value>"})` for subagent dispatches. If not set, the session default model is used — no routing.

### 3.3 Instruction Delivery (Bootstrap)

| # | Claude Code Feature | Copilot CLI Equivalent | Status |
|---|-------------------|----------------------|--------|
| I1 | `.claude/CLAUDE.md` — loaded from plugin root, contains skill overview, routing rules, trigger keywords | `skills/ars-bootstrap/SKILL.md` — auto-triggered at session start via `description` frontmatter. Contains: all 4 skills overview, 25 modes, trigger keywords, model routing config docs, pipeline state machine, integrity gate instructions | 🔄 New bootstrap skill |
| I2 | `hooks/hooks.json` — SessionStart bash hook injecting `additionalContext` via `${CLAUDE_PLUGIN_ROOT}` | `extension.mjs` → `onSessionStart` hook — builds announce string (13 slash commands, 4 skills, env var hints), emits via `session.log()` (user-visible) + `additionalContext` (agent-context) | 🔄 Reimplemented |
| I3 | `scripts/announce-ars-loaded.sh` | Logic inlined in `extension.mjs` `buildSessionAnnounce()`. Handles `startup`/`clear` (full announce) vs `compact`/`resume` (minimal announce) — same behavior. | 🔄 Logic ported to JS |
| I4 | Plugin `AGENTS.md` | `AGENTS.md` — **contributor guidelines only** (like superpowers' `CLAUDE.md`). Not loaded into user sessions — users get instructions from `ars-bootstrap` skill. | 🔄 Contributor-only |

**Why `ars-bootstrap` skill instead of `AGENTS.md`:** In Copilot CLI, `AGENTS.md` is loaded from the **project git root** (the user's working directory), NOT from a plugin directory. A plugin's `AGENTS.md` is only read when the user is working inside the plugin repo itself (i.e., ARS maintainers). End users get their runtime instructions from skill SKILL.md files (auto-triggered via `description` frontmatter) and extension `onSessionStart` `additionalContext`.

This is the same pattern as superpowers: `using-superpowers` SKILL.md is the bootstrap skill, and superpowers' `CLAUDE.md` contains contributor guidelines only.

### 3.4 Plugin Subagents → Copilot CLI task() Dispatch

All 42 agent prompt templates remain in their original `*/agents/` directories with the existing symlink structure preserved. The `agents/` symlink directory at the plugin root (pointing to `deep-research/agents/` for the 3 plugin-shipped agents) is also kept.

| # | Claude Code Feature | Copilot CLI Equivalent | Status |
|---|-------------------|----------------------|--------|
| A1 | 3 plugin-shipped agents (`agents/` → symlinks) with `model: inherit` frontmatter | Symlinks kept. `model: inherit` removed from frontmatter. Dispatched via `task({agent_type: "general-purpose", model: <from-env-or-default>, prompt: <agent template>})` per `ars-bootstrap` SKILL.md instructions. | 🔄 Frontmatter adapted; dispatch mechanism adapted |
| A2 | 38 in-skill agent prompt templates (`*/agents/*.md`) with `model: inherit` / phase-boundary blocks | Kept in original directories. `model: inherit` frontmatter removed (not applicable). Phase-boundary blocks kept (prompt-level enforcement). Copilot CLI `onPreToolUse` enforcement reserved for v3.10. | 🔄 Port content; remove `model: inherit` |

**Why keep symlinks:** The existing symlink structure (`skills/` → top-level dirs, `agents/` → `deep-research/agents/`) is transparent to Copilot CLI's filesystem operations and makes upstream sync automatic. When upstream modifies an agent template, the symlink resolves to the updated content without manual intervention. Flattening would require manually syncing every change.

**Agent dispatch pattern:**
```markdown
<!-- In ars-bootstrap SKILL.md: -->
When dispatching a subagent from any ARS skill:
- Use the `task()` tool with `agent_type: "general-purpose"`
- Load the agent prompt from the appropriate path:
  - Plugin-shipped agents: agents/<agent_name>.md
  - Skill-specific agents: <skill>/agents/<agent_name>.md
- Model selection:
  - If ARS_MODEL_ARCHITECT is set AND current mode is architect-tier: use model="${ARS_MODEL_ARCHITECT}"
  - If ARS_MODEL_EXECUTION is set AND current mode is execution-tier: use model="${ARS_MODEL_EXECUTION}"
  - Otherwise: omit the model parameter (use session default)
```

### 3.5 Hooks

| # | Claude Code Feature | Copilot CLI Equivalent | Status |
|---|-------------------|----------------------|--------|
| H1 | `hooks/hooks.json` — SessionStart bash hook | `extension.mjs` `onSessionStart` — JS handler | 🔄 Reimplemented |
| H2 | `${CLAUDE_PLUGIN_ROOT}` env var in hooks | `import.meta.url` in extension for plugin root path resolution | 🔄 Reimplemented |
| H3 | `PreToolUse` hook (planned v3.10) | `onPreToolUse` in extension — **reserved, not implemented** for v1.0. Will be activated when upstream ships v3.10 active conductor. | 🔮 Reserved |
| H4 | `SubagentStop` hook (scoped out v3.7.0) | Not applicable. Copilot CLI subagents complete and return naturally. | ❌ Not needed |

### 3.6 Shared References & Contracts

All `shared/` content (43 files) is vendored unmodified:
- `shared/references/` — glossaries, protocols, hedging rules, word count conventions
- `shared/contracts/` — audit schemas (including Codex-specific JSONL/sidecar — kept for upstream consistency), passport schemas, sprint contract schema
- `shared/templates/` — cross-model audit template (kept as-is; "codex" in name is historical)
- `shared/collaboration_depth_rubric.md`, `cross_model_verification.md`, `style_calibration_protocol.md`

### 3.7 Python Scripts

| Category | Count | Verdict |
|---|---|---|
| API clients (crossref, openalex, semantic_scholar) | 3 | ✅ Keep — platform-agnostic |
| Claim audit pipeline & finalizer | 3 | ✅ Keep — generic Python, not Codex-specific |
| Codex audit wrapper | 1 (`run_codex_audit.sh`) | ✅ Keep — upstream consistency |
| Static lint scripts (`check_*.py`) | ~20 | ✅ Keep — useful for CI |
| Test files (`test_*.py`) | ~50 | ✅ Keep — 967 test suite |
| Literature corpus adapters | ~5 | ✅ Keep — platform-agnostic |
| End-to-end audit tests | ~5 | ✅ Keep — includes Codex-specific tests, kept for consistency |
| `announce-ars-loaded.sh` | 1 | ❌ Remove — replaced by extension JS |

**Note:** All Codex-related scripts and schemas (`run_codex_audit.sh`, `audit_jsonl.schema.json`, `audit_sidecar.schema.json`, `test_run_codex_audit_e2e.py`) are kept unchanged for consistency with upstream. They do not affect Copilot CLI functionality.

### 3.8 Tests & CI

| # | Item | Status |
|---|------|--------|
| T1 | `tests/` (292 files) | ✅ Vendored unmodified |
| T2 | `.github/workflows/` (CI) | ✅ Vendored — GitHub Actions are platform-agnostic |
| T3 | `conftest.py`, `requirements-dev.txt` | ✅ Vendored |
| T4 | 967 tests (current pass baseline) | ✅ Expected to pass (no logic changes in Python code) |

### 3.9 Optional Feature Flags

`ARS_PASSPORT_RESET` behavior remains governed by
`academic-pipeline/references/passport_as_reset_boundary.md`; the Copilot
adapter changes only how the flag is read and dispatched.

| # | Flag | Copilot CLI Support | Status |
|---|------|-------------------|--------|
| F1 | `ARS_PASSPORT_RESET=1` | Read from `process.env` in extension and in skill instructions. Identical behavior: FULL checkpoints promote to context-reset boundaries. | ✅ Identical |
| F2 | `ARS_CLAIM_AUDIT=1` | Read from `process.env`. Enables L3 claim-faithfulness audit gate at Stage 4→5 transition. The `claim_ref_alignment_audit_agent` prompt template and Python audit pipeline are platform-agnostic. | ✅ Identical |
| F3 | `ARS_CROSS_MODEL` | Read from `process.env`. Enables cross-model Devil's Advocate critique during review. Since Copilot CLI BYOK can use Anthropic models, cross-model audit remains viable. | ✅ Identical |
| F4 | `ARS_MODEL_ARCHITECT` | Copilot CLI only. Sets the model ID for architect-tier commands (`/ars-full`, `/ars-revision-coach`, `/ars-reviewer`) and socratic/plan modes. | 🆕 New |
| F5 | `ARS_MODEL_EXECUTION` | Copilot CLI only. Sets the model ID for execution-tier commands (all other `/ars-*`). | 🆕 New |

### 3.10 Known Limitations (vs Claude Code Version)

| # | Feature | Copilot CLI Gap | Mitigation |
|---|---------|----------------|------------|
| L1 | No `model: inherit` frontmatter | Agent prompt templates cannot self-declare model inheritance | Configured via `ars-bootstrap` SKILL.md instructions + env vars |
| L2 | No `SubagentStop` lifecycle control | Cannot programmatically stop subagents at phase boundaries | Not needed — Copilot CLI subagents complete and return naturally; prompt-level phase boundary enforcement is primary |
| L3 | No automatic cross-session context injection | Plugin agents lack persistent context between sessions | `ARS_PASSPORT_RESET=1` + `onSessionStart` resume path handles this |
| L4 | Single BYOK provider at a time | Cannot simultaneously use Anthropic for architecture and OpenAI for execution (only one `COPILOT_PROVIDER_*` config) | Documented limitation; model routing works within a single provider's model family |
| L5 | `onPreToolUse` enforcement deferred | No `PreToolUse` hook enforcement for phase boundaries or audit gates until v3.10 | Prompt-level enforcement only (matching upstream's current posture) |

---

## 4. Plugin Directory Structure

The existing directory structure is **largely preserved** from upstream to minimize sync conflicts. Only new files are added and Claude-specific files are removed.

```
academic-research-skills-copilot/
│
├── .claude-plugin/                 # Plugin manifest (same format, Copilot CLI compatible)
│   ├── plugin.json                 # name: "academic-research-skills-copilot", version
│   └── marketplace.json            # Marketplace listing entry
│
├── .github/                        # GitHub Actions CI (vendored)
│   ├── workflows/                  # spec-consistency.yml, harness-retirement-monthly.yml, post-squash-review.yml
│   └── FUNDING.yml
│
├── extension.mjs                   # ★ NEW: Copilot CLI extension entry point
│                                   #   - 13 slash commands (CommandDefinition)
│                                   #   - onSessionStart (announce + additionalContext)
│                                   #   - onPreToolUse (reserved for v3.10)
│                                   #   - onPostToolUse (pipeline state tracking)
│                                   #   - onErrorOccurred (retry logic)
│
├── package.json                    # ★ NEW: Copilot CLI plugin metadata
│
├── AGENTS.md                       # ★ NEW: Contributor guidelines only (like superpowers' CLAUDE.md)
│                                   #   NOT loaded into user sessions.
│
├── skills/                         # ✅ Kept: symlinks to top-level skill dirs + 1 new bootstrap skill
│   ├── ars-bootstrap/              # ★ NEW: replaces .claude/CLAUDE.md
│   │   └── SKILL.md                #   Auto-triggered at session start
│   ├── deep-research -> ../deep-research/          # ✅ Symlink (kept)
│   ├── academic-paper -> ../academic-paper/        # ✅ Symlink (kept)
│   ├── academic-paper-reviewer -> ../academic-paper-reviewer/  # ✅ Symlink (kept)
│   └── academic-pipeline -> ../academic-pipeline/  # ✅ Symlink (kept)
│
├── deep-research/                  # ✅ Vendored unmodified (skill + 13 agents)
│   ├── SKILL.md
│   ├── agents/
│   │   ├── bibliography_agent.md
│   │   ├── synthesis_agent.md       # ← Remove "model: inherit" frontmatter
│   │   ├── research_architect_agent.md  # ← Remove "model: inherit"
│   │   ├── report_compiler_agent.md     # ← Remove "model: inherit"
│   │   └── ... (10 more agents)
│   └── references/
│
├── academic-paper/                 # ✅ Vendored (skill + 12 agents)
│   ├── SKILL.md
│   ├── agents/
│   │   └── ... (12 agents)
│   └── references/
│
├── academic-paper-reviewer/        # ✅ Vendored (skill + 7 agents)
│   ├── SKILL.md
│   ├── agents/
│   │   └── ... (7 agents)
│   └── references/
│
├── academic-pipeline/              # ✅ Vendored (skill + 5 agents)
│   ├── SKILL.md
│   ├── agents/
│   │   ├── pipeline_orchestrator_agent.md
│   │   └── ... (4 more agents)
│   └── references/
│
├── agents/                         # ✅ Kept: 3 symlinks to deep-research/agents/
│   ├── synthesis_agent.md -> ../deep-research/agents/synthesis_agent.md
│   ├── research_architect_agent.md -> ../deep-research/agents/research_architect_agent.md
│   └── report_compiler_agent.md -> ../deep-research/agents/report_compiler_agent.md
│
├── shared/                         # ★ Vendored unmodified from upstream (43 files)
│   ├── references/
│   ├── contracts/
│   ├── templates/
│   └── ...
│
├── scripts/                        # Python scripts (vendored; announce-ars-loaded.sh removed)
│   ├── setup-copilot-extension.sh  # ★ NEW: one-time automatic extension registration
│   ├── announce-ars-loaded.sh      # ❌ Removed (replaced by extension JS)
│   ├── run_codex_audit.sh          # ✅ Kept (upstream consistency)
│   ├── crossref_client.py          # ✅ Vendored
│   ├── openalex_client.py          # ✅ Vendored
│   ├── ... (all other scripts vendored unmodified)
│   └── _ci_pytest_manifest.toml
│
├── commands/                       # ❌ Removed (replaced by extension.mjs CommandDefinitions)
│
├── hooks/                          # ❌ Removed (replaced by extension.mjs hooks)
│
├── .claude/                        # ❌ Removed (replaced by ars-bootstrap skill + AGENTS.md)
│
├── tests/                          # ★ Vendored unmodified from upstream (292 files)
├── docs/                           # ★ Vendored + new design doc
│   ├── ARCHITECTURE.md
│   ├── SETUP.md                    # ← Updated for Copilot CLI install flow
│   ├── design/
│   │   ├── 2026-05-28-ars-copilot-cli-port-design.md  # ← This document
│   │   └── ... (all existing design docs)
│   └── migration/
│
├── README.md                       # ★ Rewritten for Copilot CLI audience
├── README.zh-CN.md                 # ★ Updated
├── README.zh-TW.md                 # ★ Updated
├── README.ja-JP.md                 # ★ Updated
├── QUICKSTART.md                   # ★ Updated: Copilot CLI install flow
├── CHANGELOG.md                    # ★ Copilot-specific changelog (appends)
├── CONTRIBUTING.md                 # ★ Updated
├── POSITIONING.md                  # ★ Updated with Copilot CLI context
├── MODE_REGISTRY.md                # ✅ Vendored unmodified
├── LICENSE                         # ✅ Vendored (CC BY-NC 4.0)
├── SECURITY.md                     # ✅ Vendored
├── NOTICE.md                       # ✅ Vendored
├── .gitignore                      # ★ Updated
├── conftest.py                     # ✅ Vendored
└── requirements-dev.txt            # ✅ Vendored
```

**Key structural changes from upstream:**

| Element | Claude Version | Copilot Version |
|---------|---------------|-----------------|
| `skills/` | Symlinks to top-level dirs | **Kept** as-is + 1 new real subdirectory (`ars-bootstrap/`) |
| `agents/` (top-level) | 3 symlinks to `deep-research/agents/` | **Kept** as-is |
| 4 top-level skill dirs | Real directories with SKILL.md + agents/ | **Kept** as-is (vendored unmodified) |
| `commands/` (13 files) | YAML frontmatter `.md` files | **Removed.** Functionality → `extension.mjs` `CommandDefinition` |
| `hooks/` | `hooks.json` + bash scripts | **Removed.** Functionality → `extension.mjs` hooks |
| `.claude/` | `CLAUDE.md` (runtime) + `CHANGELOG.md` | **Removed.** Runtime instructions → `ars-bootstrap` skill |
| `extension.mjs` | Not present | **New.** At repo root |
| `ars-bootstrap` skill | Not present | **New.** `skills/ars-bootstrap/` |
| `scripts/setup-copilot-extension.sh` | Not present | **New.** Self-bootstrapping script |
| `scripts/announce-ars-loaded.sh` | Bash hook script | **Removed.** Logic in `extension.mjs` |

---

## 5. Self-Bootstrapping Extension Registration

The mode-specific slash commands (`/ars-full`, `/ars-plan`, etc.) and lifecycle hooks (`onSessionStart` announce) require `extension.mjs` to be loaded by Copilot CLI. Extensions are discovered from `~/.copilot/extensions/<name>/extension.mjs` — a different location from plugins (`~/.copilot/installed-plugins/`). A one-time automatic setup bridges this gap.

### 5.1 Setup Script

`scripts/setup-copilot-extension.sh` — idempotent, safe to run multiple times:

```bash
#!/usr/bin/env bash
# One-time setup: registers the ARS extension for slash commands & hooks.
# Idempotent — safe to run multiple times.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
EXT_DIR="${HOME}/.copilot/extensions/ars"

mkdir -p "$EXT_DIR"
ln -sf "${PLUGIN_DIR}/extension.mjs" "${EXT_DIR}/extension.mjs"

# Marker file: suppresses repeated bootstrap prompts after setup is complete.
# ars-bootstrap checks for this file and exits silently when it exists.
touch "${EXT_DIR}/.bootstrapped"

echo "ARS extension registered at ${EXT_DIR}"
echo "Slash commands will be activated after extension reload"
```

### 5.2 Bootstrap Skill Detection

The `ars-bootstrap` SKILL.md includes an extension setup check:

```markdown
#### Extension Setup Check (run once, idempotent)

**Step 0 — Silent exit gate (prevents repeated prompts):**

Check: does ~/.copilot/extensions/ars/.bootstrapped exist?
  If YES → extension was previously registered. Exit silently — do NOT display
  any of the setup instructions below. The bootstrap skill still loads so that
  the routing rules, skill overview, and trigger keywords are injected into
  agent context, but no user-facing setup message is shown.

  If NO → proceed to Step 1 below for first-time setup.

**Step 1 — First-time setup (only when .bootstrapped is missing):**

On first invocation, verify the ARS extension is registered:

Check: does ~/.copilot/extensions/ars/extension.mjs exist?
  (use `test -L ~/.copilot/extensions/ars/extension.mjs` or equivalent)

If the file does NOT exist:
  1. Resolve the plugin install directory from the location of this SKILL.md:
     PLUGIN_DIR=$(dirname $(dirname $(readlink -f skills/ars-bootstrap/SKILL.md)))
  2. Run the setup script:
     bash "${PLUGIN_DIR}/scripts/setup-copilot-extension.sh"
  3. The setup script creates the symlink AND the .bootstrapped marker.
  4. Tell the user: "ARS extension registered. Slash commands will be activated after extension reload."
     Copilot CLI to activate slash commands (/ars-full, /ars-plan, etc.)."

If the file EXISTS but .bootstrapped is missing (edge case: manual symlink):
  Create the marker: touch ~/.copilot/extensions/ars/.bootstrapped
  Then exit silently.

After setup is complete and .bootstrapped exists, the bootstrap skill runs
silently on every subsequent session — routing rules are injected into agent
context without any user-facing prompt.
```

### 5.3 User Flow

```
Session 1 (first ARS use):
  1. User installs plugin: /plugin marketplace add <repo>
                            /plugin install academic-research-skills-copilot
  2. 5 auto slash commands available immediately:
     /academic-research-skills:deep-research
     /academic-research-skills:academic-paper
     /academic-research-skills:academic-paper-reviewer
     /academic-research-skills:academic-pipeline
     /academic-research-skills:ars-bootstrap
  3. ars-bootstrap auto-triggers at session start
  4. Bootstrap checks .bootstrapped → missing → displays setup instructions
  5. Bootstrap agent runs setup-copilot-extension.sh
     → User approves one bash permission
     → Symlink created + .bootstrapped marker written

Session 2+ (all subsequent sessions):
  1. Extension auto-loads from ~/.copilot/extensions/ars/
  2. onSessionStart fires → full ARS announce displayed
  3. All 13 /ars-* slash commands available via CommandDefinition
  4. 5 /academic-research-skills:* auto commands still available
  5. ars-bootstrap auto-triggers → checks .bootstrapped → EXISTS → exits silently
     (routing rules, skill overview, and trigger keywords are injected into
      agent context without any user-facing setup message)
```

### 5.4 Why Self-Bootstrapping (Not an Install Script)

Two approaches were considered for bridging the plugin/extension gap:

| Dimension | A: Self-Bootstrapping (chosen) | B: Standalone Install Script |
|---|---|---|
| **Plugin install** | `/plugin marketplace add` + `/plugin install` (native) | `curl \| bash` script bypassing native commands |
| **Extension registration** | Bootstrap skill → one-time prompt → script → `.bootstrapped` marker → silent thereafter | Script does everything at once |
| **User steps** | 2 steps (install plugin, then approve one bash execution in next session) | 1 step (run script) |
| **Follows Copilot CLI standard?** | ✅ Uses native plugin commands | ❌ Duplicates/reinvents plugin installation |
| **Transparency** | High — each step is visible and understandable | Low — script is a black box |
| **Security** | Bash execution requires per-command user approval | Pipe-to-bash has no per-step review |
| **External dependencies** | None | Requires a hosted script URL |
| **Maintenance burden** | Low — just `setup-copilot-extension.sh` + bootstrap SKILL.md logic | Medium — independent script must handle idempotency, upgrades, uninstall, edge cases |
| **Matches superpowers pattern?** | ✅ Superpowers also plugin-only, no install script | ❌ Different pattern than superpowers |
| **Repeated prompting?** | ❌ No — `.bootstrapped` marker silences after setup | ❌ No (but for different reasons) |

**Decision: Self-bootstrapping (A).** Three primary reasons:

1. **Doesn't reinvent plugin installation.** Copilot CLI already has `/plugin marketplace add` and `/plugin install` — a standalone install script would either duplicate that logic or bypass it, creating confusion about canonical installation paths.

2. **Progressive disclosure of complexity.** Users get skill functionality immediately after `/plugin install` (via auto-generated namespace commands). The extension registration (for richer slash commands + hooks) is exposed only when the bootstrap skill detects it's missing — users who don't need `/ars-full` don't have to set it up.

3. **Consistent with superpowers.** The most popular Copilot CLI plugin uses the same pattern: install via `/plugin install`, bootstrap via a `using-superpowers` SKILL.md. ARS follows this established convention.

---

## 6. `extension.mjs` Design

### 6.1 Architecture

```
┌─────────────────────────────────────────────────┐
│                  extension.mjs                   │
│                                                  │
│  joinSession({                                   │
│    commands: [13 CommandDefinitions],             │
│    hooks: {                                      │
│      onSessionStart   → announce + bootstrap     │
│      onPreToolUse     → (reserved v3.10)         │
│      onPostToolUse    → pipeline state tracking  │
│      onErrorOccurred  → retry logic              │
│    }                                             │
│  })                                              │
└─────────────────────────────────────────────────┘
```

### 6.2 Slash Command Dispatch

Each of the 13 commands follows this pattern:

```
User types: /ars-full
  → CommandDefinition handler fires
  → Checks ARS_MODEL_ARCHITECT env var
  → If set: prompt includes "use task({model: ARS_MODEL_ARCHITECT})"
  → If not: prompt uses session default (no model param)
  → session.send({prompt: "[ARS] Activate skill: academic-pipeline, mode: full..."})
  → Agent receives full dispatch prompt
  → Agent reads ars-bootstrap skill for routing rules
  → Agent reads academic-pipeline/SKILL.md for pipeline instructions
  → Pipeline executes with 10-stage workflow
```

### 6.3 `onSessionStart` Hook

```
Session starts (source: startup | resume | new | clear | compact)
  → buildSessionAnnounce(source):
      startup/clear → full announce (all 13 commands, 4 skills, env var hints)
      compact/resume → minimal announce (commands only, no docs)
  → session.log(announce) — user-visible in timeline
  → return { additionalContext: "<bootstrap summary>" } — injected into agent context
```

### 6.4 `onPostToolUse` Hook

```
After create/edit operations:
  → Detects phase directory pattern (phase<N>_*/)
  → Logs ephemeral deliverable creation
  → Injects anti-fake-audit reminder when synthesis/report agents produce output
```

### 6.5 `onErrorOccurred` Hook

```
On recoverable model_call errors:
  → Retry up to 2 times
On non-recoverable errors:
  → Abort with user notification containing error details
```

### 6.6 `onPreToolUse` Hook (Reserved)

```
Implemented as no-op for v1.0.
v3.10 upstream will ship PreToolUse enforcement for:
  - Phase-boundary write blocking (Phase 3 agent cannot write to phase4_*/)
  - ARS_CLAIM_AUDIT HIGH-WARN annotation blocking
  - Formatter REFUSE rules 6-10 enforcement at tool level
When upstream ships v3.10, activate this hook in Copilot port.
```

---

## 7. `ars-bootstrap` SKILL.md Design

### 7.1 Purpose

Replaces `.claude/CLAUDE.md` as the session-start instruction injection point. Auto-triggered by Copilot CLI's skill system when the session starts, because its `description` frontmatter signals it should be used at conversation start.

### 7.2 Structure

```markdown
---
name: ars-bootstrap
description: "Academic Research Skills bootstrap. Loaded at session start. 
  Establishes 4 skills (deep-research, academic-paper, academic-paper-reviewer, 
  academic-pipeline), 25 modes, trigger keyword auto-detection, model routing 
  configuration, pipeline state machine, and integrity gates."
---

# Academic Research Skills — Copilot CLI

```markdown
## Skills Overview
[Table: 4 skills, modes, purpose — same as upstream CLAUDE.md]

## Trigger Auto-Detection
[Keyword lists: English + zh-TW — same as upstream CLAUDE.md]

## Model Routing (Optional)
[ARS_MODEL_ARCHITECT / ARS_MODEL_EXECUTION env var documentation]

## Pipeline State Machine
[10-stage workflow, integrity gates, revision loops]

## Routing Rules
[Same 5 rules as upstream CLAUDE.md]

## Key Rules
[3 rules: skill tool invocation, agent dispatch via task(), pipeline orchestrator coordination]
```

### 7.3 Auto-Trigger Mechanism

The `description` frontmatter contains the signal phrases Copilot CLI uses for skill auto-discovery. When a session starts and `ars-bootstrap` is the first skill triggered, it establishes the full ARS context for the session. Subsequent user prompts then auto-trigger the appropriate ARS skill (deep-research, academic-paper, etc.) based on their `description` frontmatter keyword matching.

This mirrors superpowers' `using-superpowers` skill: it auto-triggers at session start and teaches the agent about all other superpowers skills.

---

## 8. Agent Prompt Template Migration

### 8.1 What Changes in Each Agent Template

Agent templates remain in their original `*/agents/` directories. The existing symlink structure (`skills/` → top-level dirs, `agents/` → `deep-research/agents/`) is preserved for upstream sync compatibility.

For the 3 agent templates with `model: inherit` frontmatter (`synthesis_agent.md`, `research_architect_agent.md`, `report_compiler_agent.md`):

| Change | Detail |
|---|---|
| **Remove** `model: inherit` | YAML frontmatter line. Copilot CLI has no concept of model inheritance. |
| **Keep** phase-boundary blocks | "Phase Boundary (v3.9.2)" sections stay. Prompt-level enforcement is primary. |
| **Keep** PATTERN PROTECTION blocks | "PATTERN PROTECTION (v3.6.7)" sections stay. |
| **Keep** Three-Layer Citation Emission blocks | "Three-Layer Citation Emission (v3.7.3)" sections stay. |
| **Keep** all agent-specific instructions | Role definition, core principles, output format, etc. |

All other 39 agent templates require no changes — they have no `model: inherit` frontmatter and contain no Claude-specific references.

### 8.2 Why Keep Symlinks

The existing symlink structure is preserved because:

1. **Upstream sync is automatic.** When upstream modifies `deep-research/agents/synthesis_agent.md`, the symlink `agents/synthesis_agent.md → ../deep-research/agents/synthesis_agent.md` resolves to the updated content without any manual intervention.
2. **Copilot CLI follows symlinks.** Symlinks are transparent to Node.js filesystem operations (`readFileSync`, `opendir`). Copilot CLI's skill and agent discovery follows them normally — the same way it resolves `skills/deep-research/SKILL.md` through the symlink to `../deep-research/SKILL.md`.
3. **Flattening creates drift risk.** If we copy agent files into a flat `agents/` directory, every upstream change to the original files requires manual sync to the copies. The Claude Code port's `codex_audit` pipeline validates agent template consistency — flattening would break this audit.

---

## 9. Model Routing — Full Mechanism

### 9.1 Default (No Env Vars)

```
All subagent dispatches use the session default model.
task({agent_type: "general-purpose", prompt: <agent template>})
// No model parameter → inherits session model
```

### 9.2 Single-Provider BYOK (e.g., Anthropic)

```bash
export COPILOT_PROVIDER_TYPE=anthropic
export COPILOT_PROVIDER_BASE_URL=https://api.anthropic.com
export COPILOT_PROVIDER_API_KEY=sk-ant-...
export COPILOT_MODEL=claude-sonnet-4-5
export ARS_MODEL_ARCHITECT=claude-opus-4-5
export ARS_MODEL_EXECUTION=claude-sonnet-4-5
```

```
Architect-tier dispatch:
  task({agent_type: "general-purpose", model: "claude-opus-4-5", prompt: ...})

Execution-tier dispatch:
  task({agent_type: "general-purpose", model: "claude-sonnet-4-5", prompt: ...})
```

Both models are served by the same Anthropic endpoint. The `model` parameter in `task()` routes to different models on the same provider.

### 9.3 DeepSeek Provider (Current User Setup)

```bash
export COPILOT_PROVIDER_BASE_URL=https://api.deepseek.com
export COPILOT_PROVIDER_API_KEY=sk-...
export COPILOT_MODEL=deepseek-v4-pro
# No ARS_MODEL_* set → all dispatches use deepseek-v4-pro
```

### 9.4 Copilot-Managed Models (No BYOK)

When using Copilot-managed models (GitHub plan, no `COPILOT_PROVIDER_*` vars), the available model list depends on the plan. `task({model: "..."})` uses whatever models are available:

```
# Example with Copilot plan that includes Claude:
export ARS_MODEL_ARCHITECT=claude-opus-4-5
export ARS_MODEL_EXECUTION=claude-sonnet-4-5
# task() model parameter resolved against Copilot-managed model list
```

---

## 10. Upstream Sync Strategy

### 10.1 Branch Architecture

```
claude-code-main          ←--- tracks upstream Imbad0202/academic-research-skills:main
       │                        (user pulls updates, resolves merge conflicts)
       │
       ▼
copilot-main              ←--- Copilot-specific adaptations
       │                        (assistant applies adaptations, commits)
       │
       ├── extension.mjs        (new — no upstream equivalent)
       ├── skills/ars-bootstrap/ (new)
       ├── skills/*/SKILL.md    (adapted from upstream)
       ├── agents/*.md           (adapted from upstream)
       ├── README.md etc.        (rewritten)
       ├── shared/               (vendored unmodified → no diff)
       ├── scripts/              (vendored, minus announce-ars-loaded.sh)
       ├── tests/                (vendored unmodified)
       └── docs/                 (vendored + new design doc)
```

### 10.2 Sync Workflow

```
1. User: git checkout claude-code-main
2. User: git pull upstream main
3. User: resolves any merge conflicts
4. User: git checkout copilot-main
5. User: git merge claude-code-main
6. Copilot Assistant: resolves conflicts in adapted files
7. Copilot Assistant: applies new adaptations for upstream changes
8. Copilot Assistant: runs test suite (967 tests)
9. Copilot Assistant: commits with message:
   "sync: merge upstream vX.Y.Z into copilot-main [commit hash]"
```

### 10.3 Conflict-Prone Files

| File | Conflict risk | Resolution strategy |
|---|---|---|
| `skills/*/SKILL.md` (4 files) | **High** — upstream modifies these actively | Manual merge; keep Copilot adaptations (task() dispatch instructions, removed Claude refs) |
| `agents/*.md` (42 files) | **Medium** — upstream adds agents, modifies prompts | Accept upstream content; re-apply "model: inherit" removal patch |
| `shared/` (43 files) | **Low** — vendored unmodified | Accept upstream always |
| `scripts/` (~130 files) | **Low** — vendored, minus one removal | Accept upstream; ensure announce-ars-loaded.sh stays removed |
| `tests/` (292 files) | **Low** — vendored unmodified | Accept upstream always |
| `docs/` | **Low** — vendored + one new design doc | Accept upstream; keep Copilot design doc |

---

## 11. Implementation Scope

### 11.1 Phase 1: Remove Claude-Specific Infrastructure

- [ ] Remove `.claude/` directory (CLAUDE.md replaced by ars-bootstrap skill)
- [ ] Remove `commands/` directory (13 slash commands moved to extension.mjs)
- [ ] Remove `hooks/` directory (hooks moved to extension.mjs)
- [ ] Remove `scripts/announce-ars-loaded.sh` (logic moved to extension.mjs)

### 11.2 Phase 2: Create New Files

- [ ] Create `extension.mjs` at repo root — 13 CommandDefinitions + 5 hooks (§6)
- [ ] Create `package.json` — Copilot plugin metadata (`"type": "module"`)
- [ ] Create `skills/ars-bootstrap/SKILL.md` — session-start bootstrap (§7)
- [ ] Create `AGENTS.md` — contributor guidelines only
- [ ] Create `scripts/setup-copilot-extension.sh` — self-bootstrapping extension registration (§5.1), creates symlink + `.bootstrapped` marker
- [ ] Update `.claude-plugin/plugin.json` — name, description for Copilot CLI marketplace

### 11.3 Phase 3: Adapt Existing Files (Minimal Changes)

- [ ] Remove `model: inherit` from 3 agent frontmatters:
  - `deep-research/agents/synthesis_agent.md`
  - `deep-research/agents/research_architect_agent.md`
  - `deep-research/agents/report_compiler_agent.md`
- [ ] Adapt 4 `SKILL.md` files (remove Claude-only references, add task() dispatch hints):
  - `deep-research/SKILL.md`
  - `academic-paper/SKILL.md`
  - `academic-paper-reviewer/SKILL.md`
  - `academic-pipeline/SKILL.md`
- [ ] Update `.gitignore` for Copilot-specific files

### 11.4 Phase 4: Documentation

- [ ] Rewrite `README.md` for Copilot CLI audience (install via `/plugin marketplace add`)
- [ ] Update `README.zh-CN.md`, `README.zh-TW.md`, `README.ja-JP.md`
- [ ] Rewrite `QUICKSTART.md` — Copilot CLI install flow
- [ ] Update `SETUP.md` — `/plugin install` instructions
- [ ] Update `POSITIONING.md` — mention Copilot CLI sibling distribution
- [ ] Update `CONTRIBUTING.md` — add sync policy, branch strategy
- [ ] Initialize `CHANGELOG.md` — Copilot-specific release notes

### 11.5 Phase 5: Verification

- [ ] Run Python test suite (967 tests expected to pass — no Python code changed)
- [ ] Verify `extension.mjs` loads without syntax errors
- [ ] Verify `skills/ars-bootstrap/SKILL.md` frontmatter is valid
- [ ] Verify `scripts/setup-copilot-extension.sh` is idempotent
- [ ] Verify symlink integrity (all symlinks resolve correctly)
- [ ] Test plugin installation in a separate Copilot CLI session
- [ ] Test slash command registration after extension setup
- [ ] Test skill auto-triggering via `description` frontmatter

---

## 12. Files Summary

| Category | New | Modified (in-place) | Vendored Unmodified | Removed |
|---|---|---|---|---|
| Extension & config | 5 (`extension.mjs`, `package.json`, `AGENTS.md`, `skills/ars-bootstrap/SKILL.md`, `scripts/setup-copilot-extension.sh`) | 2 (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`) | 0 | 0 |
| Skills (SKILL.md) | 1 (ars-bootstrap) | 4 (deep-research, academic-paper, academic-paper-reviewer, academic-pipeline) | 0 | 0 |
| Agent templates | 0 | 3 (remove `model: inherit` from synthesis, research_architect, report_compiler) | 39 | 0 |
| Shared | 0 | 0 | 43 | 0 |
| Scripts | 1 (setup-copilot-extension.sh) | 0 | ~130 | 1 (`announce-ars-loaded.sh`) |
| Tests | 0 | 0 | 292 | 0 |
| Docs | 1 (this design doc) | 6 (READMEs ×4, QUICKSTART, SETUP, POSITIONING, CONTRIBUTING) | 27 (design docs) | 0 |
| Top-level | 1 (`CHANGELOG.md`) | 1 (`.gitignore`) | 7 (LICENSE, SECURITY, NOTICE, MODE_REGISTRY, conftest.py, requirements-dev.txt, README already counted) | 3 (`.claude/`, `commands/`, `hooks/`) |
| Plugin manifest | 0 | 2 | 0 | 0 |
| **Total** | **~9** | **~18** | **~530** | **~17** |

---

## 13. Acceptance Criteria

1. **Install works:** `/plugin marketplace add <repo>` + `/plugin install academic-research-skills-copilot` succeeds
2. **Self-bootstrapping (once, then silent):** `ars-bootstrap` skill detects missing extension → triggers `setup-copilot-extension.sh` → creates symlink + `.bootstrapped` marker → on all subsequent sessions, bootstrap detects `.bootstrapped` and exits silently
3. **Announce displays:** On subsequent session start, full ARS announce appears with 13 slash commands
4. **Slash commands work:** `/ars-full` dispatches pipeline orchestrator; all 13 commands trigger correct skill+mode
5. **Bootstrap loads:** `ars-bootstrap` skill auto-triggers at session start, agent learns all routing rules
6. **No model routing without env vars:** Default behavior uses session model for all dispatches (no breakage)
7. **Model routing with env vars:** Setting `ARS_MODEL_ARCHITECT` / `ARS_MODEL_EXECUTION` causes `task({model: "..."})` in dispatch prompt
8. **Agent dispatch works:** 42 agent templates loadable via `task()` with correct prompt content
9. **Feature flags work:** `ARS_PASSPORT_RESET=1`, `ARS_CLAIM_AUDIT=1`, `ARS_CROSS_MODEL` recognized by extension
10. **Tests pass:** 967 Python tests pass (no logic changes in vendored scripts)
11. **Upstream sync viable:** `claude-code-main` branch tracks upstream cleanly; merge into `copilot-main` produces manageable conflicts
