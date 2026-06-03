# ARS Copilot CLI Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port ARS v3.9.4.2 from Claude Code to Copilot CLI as a sibling distribution on the `copilot-main` branch.

**Architecture:** Remove 4 Claude-specific subsystems (`.claude/`, `commands/`, `hooks/`, `scripts/announce-ars-loaded.sh`). Create 5 new files: `extension.mjs` (13 CommandDefinitions + 4 hooks), `skills/ars-bootstrap/SKILL.md` (session-start bootstrap), `package.json`, `AGENTS.md` (contributor-only), `scripts/setup-copilot-extension.sh` (one-time extension registration + `.bootstrapped` marker). Adapt 4 SKILL.md files + remove `model: inherit` from 3 agent frontmatter. Rewrite documentation. Run 967 Python tests.

**Tech Stack:** Node.js (extension.mjs), Bash (setup script), Markdown (skills/agents/docs), Python (existing test suite)

**Design spec:** `docs/design/2026-05-28-ars-copilot-cli-port-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `extension.mjs` (new) | 13 slash commands via CommandDefinition, onSessionStart announce, onPostToolUse pipeline tracking, onErrorOccurred retry, reserved onPreToolUse |
| `skills/ars-bootstrap/SKILL.md` (new) | Session-start bootstrap: 4 skills overview, 25 modes, trigger keywords, model routing config, pipeline state machine, extension setup check with `.bootstrapped` silent gate |
| `package.json` (new) | Plugin metadata: name, version, type: module |
| `AGENTS.md` (new) | Contributor guidelines only (NOT loaded into user sessions) |
| `scripts/setup-copilot-extension.sh` (new) | One-time `ln -sf` extension.mjs to `~/.copilot/extensions/ars/` + `touch .bootstrapped` |
| `deep-research/SKILL.md` (modify) | Remove Claude-specific references, add task() dispatch hints |
| `academic-paper/SKILL.md` (modify) | Remove Claude-specific references, add task() dispatch hints |
| `academic-paper-reviewer/SKILL.md` (modify) | Remove Claude-specific references, add task() dispatch hints |
| `academic-pipeline/SKILL.md` (modify) | Remove Claude-specific references, add task() dispatch hints |
| `deep-research/agents/synthesis_agent.md` (modify) | Remove `model: inherit` from frontmatter (line 4) |
| `deep-research/agents/research_architect_agent.md` (modify) | Remove `model: inherit` from frontmatter (line 4) |
| `deep-research/agents/report_compiler_agent.md` (modify) | Remove `model: inherit` from frontmatter (line 4) |
| `README.md` (rewrite) | Copilot CLI audience: install via `/plugin marketplace add` + `/plugin install` |
| `README.zh-CN.md` (update) | Same |
| `README.zh-TW.md` (update) | Same |
| `README.ja-JP.md` (update) | Same |
| `QUICKSTART.md` (rewrite) | Copilot CLI install flow |
| `SETUP.md` (update) | Copilot CLI install instructions |
| `POSITIONING.md` (update) | Mention Copilot CLI sibling distribution |
| `CONTRIBUTING.md` (update) | Add sync policy, branch strategy |
| `CHANGELOG.md` (init/append) | Copilot-specific release notes |
| `.gitignore` (update) | Add Copilot-specific ignores |
| `.claude-plugin/plugin.json` (update) | Update name/description for Copilot CLI |
| `.claude-plugin/marketplace.json` (update) | Update for Copilot CLI marketplace |

---

## Task 0: Setup — Verify Branch and Baseline

**Files:** None (verification only)

- [ ] **Step 0.1: Confirm we're on copilot-main**

```bash
cd /home/zzyu/skills/academic-research-skills && git branch --show-current
```
Expected: `copilot-main`

- [ ] **Step 0.3: Run baseline test suite to confirm 967 pass before any changes**

```bash
cd /home/zzyu/skills/academic-research-skills && python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
```
Expected: `967 passed` (or close to it; 3 skipped acceptable)

> **Note:** this step confirms nothing is broken before we start. If tests fail, investigate before proceeding.

---

## Task 1: Remove Claude-Specific Infrastructure

**Files:** Remove `.claude/`, `commands/`, `hooks/`, `scripts/announce-ars-loaded.sh`

- [ ] **Step 1.1: Remove `.claude/` directory**

```bash
cd /home/zzyu/skills/academic-research-skills
rm -rf .claude/
```

- [ ] **Step 1.2: Remove `commands/` directory (13 slash command .md files)**

```bash
rm -rf commands/
```

- [ ] **Step 1.3: Remove `hooks/` directory (hooks.json)**

```bash
rm -rf hooks/
```

- [ ] **Step 1.4: Remove `scripts/announce-ars-loaded.sh`**

```bash
rm scripts/announce-ars-loaded.sh
```

---

## Task 2: Create `extension.mjs` — Copilot CLI Extension Entry Point

**Files:**
- Create: `extension.mjs`

**Purpose:** 13 slash commands via `CommandDefinition`, `onSessionStart` announce with source-aware behavior (`startup`/`clear` → full, `compact`/`resume` → minimal), `onPostToolUse` pipeline state tracking, `onErrorOccurred` retry logic, reserved `onPreToolUse` (no-op).

- [ ] **Step 2.1: Create the file with full implementation**

Create `extension.mjs` at repo root:

```javascript
// extension.mjs — ARS Copilot CLI Extension
// =============================================================================
// Slash commands (13) + lifecycle hooks (onSessionStart, onPostToolUse,
// onErrorOccurred). onPreToolUse is reserved for v3.10 parity.
// =============================================================================

import { joinSession } from "@github/copilot-cli/extensions";

// -----------------------------------------------------------------------------
// Model routing helpers
// -----------------------------------------------------------------------------

function getModelTier(tier) {
  // tier = "architect" | "execution"
  if (tier === "architect") return process.env.ARS_MODEL_ARCHITECT || null;
  if (tier === "execution") return process.env.ARS_MODEL_EXECUTION || null;
  return null;
}

function modelRoutingHint(tier) {
  const model = getModelTier(tier);
  if (model) {
    return `\n\n[Model routing: use task({model: "${model}"}) for subagent dispatches.]`;
  }
  return "";
}

function dispatchCommand(skill, mode, tier) {
  const routing = modelRoutingHint(tier);
  return {
    prompt: `[ARS] Activate skill: ${skill}, mode: ${mode}. Load ${skill}/SKILL.md and follow the ${mode} workflow.${routing}`,
  };
}

// -----------------------------------------------------------------------------
// Session announce (ported from announce-ars-loaded.sh)
// -----------------------------------------------------------------------------

function buildSessionAnnounce(source) {
  if (source === "compact" || source === "resume") {
    return `ARS plugin still loaded after ${source}. Slash commands: /ars-full /ars-plan /ars-outline /ars-revision /ars-revision-coach /ars-abstract /ars-lit-review /ars-reviewer /ars-format-convert /ars-citation-check /ars-disclosure /ars-mark-read /ars-unmark-read. Plugin agents: synthesis_agent, research_architect_agent, report_compiler_agent.`;
  }

  return `ARS (academic-research-skills) plugin loaded.

Slash commands (13):
  /ars-full              Full pipeline (research → write → review → revise → finalize)
  /ars-revision-coach    Parse reviewer comments → Revision Roadmap + Response Letter skeleton
  /ars-reviewer          academic-paper-reviewer full mode — simulated peer-review panel
  /ars-plan              Socratic chapter-by-chapter planning
  /ars-outline           Detailed outline + evidence map (no full draft)
  /ars-revision          Revised draft + R&R responses
  /ars-abstract          Bilingual abstract + keywords
  /ars-lit-review        Annotated bibliography in paper format
  /ars-format-convert    Convert paper between LaTeX / DOCX / PDF / Markdown
  /ars-citation-check    Citation error report
  /ars-disclosure        Venue-specific AI-usage disclosure statement
  /ars-mark-read         Record human-read signal for citation keys
  /ars-unmark-read       Rescind a prior human-read mark

Skills (4): deep-research (13 agents), academic-paper (12 agents),
           academic-paper-reviewer (7 agents), academic-pipeline (5 agents)

Model routing (optional):
  Set ARS_MODEL_ARCHITECT and/or ARS_MODEL_EXECUTION env vars for
  tiered model dispatch via task({model: "..."}).
  Without env vars, all dispatches use session default model.

Token budget reference: docs/PERFORMANCE.md.`;
}

// -----------------------------------------------------------------------------
// 13 Command Definitions
// -----------------------------------------------------------------------------

const commands = [
  {
    name: "ars-full",
    description: "Full pipeline — research → write → review → revise → finalize",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-pipeline", "full", "architect");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-revision-coach",
    description: "Parse reviewer comments → Revision Roadmap + Response Letter skeleton",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "revision-coach", "architect");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-reviewer",
    description: "academic-paper-reviewer full mode — simulated peer-review panel",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper-reviewer", "full", "architect");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-plan",
    description: "Socratic chapter-by-chapter planning",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "plan", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-outline",
    description: "Detailed outline + evidence map (no full draft)",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "outline-only", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-revision",
    description: "Revised draft + R&R responses",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "revision", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-abstract",
    description: "Bilingual abstract + keywords",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "abstract-only", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-lit-review",
    description: "Annotated bibliography in paper format",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "lit-review", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-format-convert",
    description: "Convert paper between LaTeX / DOCX / PDF / Markdown",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "format-convert", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-citation-check",
    description: "Citation error report",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "citation-check", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-disclosure",
    description: "Venue-specific AI-usage disclosure statement",
    handler: async (ctx) => {
      const { prompt } = dispatchCommand("academic-paper", "disclosure", "execution");
      await ctx.session.send({ prompt });
    },
  },
  {
    name: "ars-mark-read",
    description: "Record human-read signal for one or more citation keys",
    handler: async (ctx) => {
      await ctx.session.send({
        prompt: `[ARS] Record human-read signal for citation keys. Run: python3 scripts/ars_mark_read.py with the active Material Passport path. Per v3.6.8 §3.6, stores signal in <passport-stem>_human_read_log.yaml. literature_corpus[] is NEVER mutated.${process.env.ARS_MODEL_EXECUTION ? `\n\n[Model routing: use task({model: "${process.env.ARS_MODEL_EXECUTION}"}) for subagent dispatches.]` : ""}`,
      });
    },
  },
  {
    name: "ars-unmark-read",
    description: "Rescind a prior human-read mark for one or more citation keys",
    handler: async (ctx) => {
      await ctx.session.send({
        prompt: `[ARS] Rescind human-read signal for citation keys. Run: python3 scripts/ars_unmark_read.py with the active Material Passport path. Per v3.6.8 §3.6.${process.env.ARS_MODEL_EXECUTION ? `\n\n[Model routing: use task({model: "${process.env.ARS_MODEL_EXECUTION}"}) for subagent dispatches.]` : ""}`,
      });
    },
  },
];

// -----------------------------------------------------------------------------
// Export joinSession
// -----------------------------------------------------------------------------

export default joinSession({
  commands,

  hooks: {
    onSessionStart: async ({ session, source }) => {
      const announce = buildSessionAnnounce(source);

      // Build additionalContext: bootstrap summary for agent context
      const additionalContext = `ARS (Academic Research Skills) v3.9.4.2 loaded.
4 skills available: deep-research (13 agents, 7 modes), academic-paper (12 agents, 10 modes), academic-paper-reviewer (7 agents, 6 modes), academic-pipeline (5 agents, 1 pipeline).
Model routing: ${process.env.ARS_MODEL_ARCHITECT ? `architect tier → ${process.env.ARS_MODEL_ARCHITECT}` : "not configured"}${process.env.ARS_MODEL_EXECUTION ? `, execution tier → ${process.env.ARS_MODEL_EXECUTION}` : ""}. Without env vars, all dispatches use session default model.
See skills/ars-bootstrap/SKILL.md for routing rules, trigger keywords, and pipeline state machine.`;

      return {
        // session.log for user-visible timeline
        log: announce,
        // additionalContext injected into agent's first turn
        additionalContext,
      };
    },

    onPostToolUse: async ({ session, tool, toolInput, toolOutput }) => {
      // Pipeline state tracking — detect phase directory creation
      const phaseMatch = (toolInput?.file_path || toolInput?.path || "").match(
        /phase(\d+)[a-z]?_/
      );
      if (phaseMatch) {
        const phase = phaseMatch[1];
        // Log ephemeral deliverable creation for pipeline tracking
        // Reserved for future state-machine integration
      }
    },

    onErrorOccurred: async ({ session, error }) => {
      // Log error for diagnostics; retry logic is deferred to v3.10
      if (error?.type === "model_call" || error?.message?.includes("rate_limit")) {
        return { retry: true, maxRetries: 2 };
      }
      return { retry: false };
    },

    // Reserved for v3.10 active conductor (#134):
    // onPreToolUse: async ({ session, toolCall }) => {
    //   // Phase-boundary write blocking (e.g., Phase 3 agent cannot write to phase4_*/)
    //   // ARS_CLAIM_AUDIT HIGH-WARN annotation blocking
    //   // Formatter REFUSE rules 6-10 enforcement at tool level
    //   return { allow: true };
    // },
  },
});
```

- [ ] **Step 2.2: Verify the file has no syntax errors**

```bash
cd /home/zzyu/skills/academic-research-skills
node --check extension.mjs && echo "Syntax OK"
```
Expected: `Syntax OK`

---

## Task 3: Create `package.json`

**Files:**
- Create: `package.json`

- [ ] **Step 3.1: Create package.json**

```json
{
  "name": "academic-research-skills",
  "version": "3.9.4.2",
  "description": "Production-grade academic research pipeline for Copilot CLI: research → write → review → revise → finalize. 4 skills, 25+ modes, 42-agent ensemble, v3.7.3 + v3.8 L3 claim-faithfulness gate, v3.9.0 cross-index triangulation, v3.9.2 phase boundary fence.",
  "type": "module",
  "author": {
    "name": "Zhenyu Zhang",
    "url": "https://github.com/Imbad0202"
  },
  "homepage": "https://github.com/Imbad0202/academic-research-skills",
  "repository": "https://github.com/Imbad0202/academic-research-skills",
  "license": "CC-BY-NC-4.0",
  "keywords": [
    "academic",
    "research",
    "writing",
    "review",
    "deep-research",
    "literature-review",
    "systematic-review",
    "peer-review",
    "scholarly-publishing"
  ]
}
```

**How it works:**
- CommandDefinition handlers check `ARS_MODEL_ARCHITECT` / `ARS_MODEL_EXECUTION` env vars
- If set, the dispatch prompt includes `task({model: "<value>"})` for subagent dispatches
- If not set, all dispatches use the session default model (no routing)
- Model routing works within a single provider's model family (e.g., both opus and sonnet on Anthropic)
- Set `COPILOT_PROVIDER_BASE_URL`, `COPILOT_PROVIDER_TYPE`, `COPILOT_PROVIDER_API_KEY`, and `COPILOT_MODEL` for BYOK

## Pipeline State Machine

```
deep-research (socratic/full)
  → academic-paper (plan/full)
    → integrity check (Stage 2.5)
      → academic-paper-reviewer (full/guided)
        → academic-paper (revision)
          → academic-paper-reviewer (re-review, max 2 loops)
            → final integrity check (Stage 4.5)
              → academic-paper (format-convert → final output)
                → Process Summary + AI Self-Reflection Report
```

## Routing Discipline (v3.9.2)

**Routing precedence:** This section runs BEFORE Routing Rules 1-5. Once this section settles on a destination, Rules 1-5 apply within that destination's skill family.

**Step 0 — Escape hatch check (before any classification):** If the user's first message begins with `[direct-mode]` (case-insensitive byte-0 token, optionally preceded by whitespace/newlines that are stripped on parse), record this fact, strip the prefix and surrounding whitespace from the message, and skip directly to **Step 1 explicit-intent handling** on the stripped content. The literal `[direct-mode]` is NOT passed through to the dispatched agent. If the stripped message itself has no clear skill named, Step 1 falls through to Step 3 clarification (the escape hatch bypasses cross-phase clarification (Step 2), not all routing).

Otherwise, classify the user's input:

1. **Explicit clear intent** — user invokes a specific skill via `/ars-*` slash command, `/academic-research-skills:*` auto-command, or uses an unambiguous trigger keyword that maps to a single skill (e.g., "lit-review this", "review my paper", "draft an abstract"):
   → Route directly; no clarification, no orchestrator detour.

2. **Cross-phase materials detected** — user provides artifacts spanning ≥ 2 pipeline phases without naming a specific skill (e.g., pre-written abstract + pre-collected literature; full draft + reviewer comments + bibliography):
   → **Clarify**. Do NOT auto-route to a single-phase agent. List candidate workflows as a-d options in markdown body. See `shared/references/intent_clarification_protocol.md` for the message template.

3. **Ambiguous intent, no materials** — user provides no artifacts and no clear request:
   → Clarify per `shared/references/intent_clarification_protocol.md`.

**Anti-pattern:** Receiving ambiguous cross-phase materials and silently auto-routing to a single-phase agent based on which phase the materials "look closest to." This bypasses orchestrator-level reconciliation.

**Forward note (v3.10):** Active conductor (#134) will reframe this gate as structured intake with task envelope dispatch. v3.9.2 ships clarification-only as interim hot-fix.

## Routing Rules

1. **academic-pipeline vs individual skills**: academic-pipeline = full pipeline orchestrator (research → write → integrity → review → revise → final integrity → finalize). If the user only needs a single function (just research, just write, just review), trigger the corresponding skill directly without the pipeline.

2. **deep-research vs academic-paper**: Complementary. deep-research = upstream research engine (investigation + fact-checking), academic-paper = downstream publication engine (paper writing + bilingual abstracts). Recommended flow: deep-research → academic-paper.

3. **deep-research socratic vs full**: socratic = guided Socratic dialogue to help users clarify their research question. full = direct production of research report. When the user's research question is unclear, suggest socratic mode.

4. **academic-paper plan vs full**: plan = chapter-by-chapter guided planning via Socratic dialogue. full = direct paper production. When the user wants to think through their paper structure, suggest plan mode.

5. **academic-paper-reviewer guided vs full**: guided = Socratic review that engages the author in dialogue about issues. full = standard multi-perspective review report. When the user wants to learn from the review, suggest guided mode.

## Key Rules

- All claims must have citations
- Evidence hierarchy respected (meta-analyses > RCTs > cohort > case reports > expert opinion)
- Contradictions disclosed with evidence quality comparison
- AI disclosure in all reports
- Default output language matches user input (Traditional Chinese or English)
- **Agent dispatch:** Use `task({agent_type: "general-purpose", prompt: <agent template content>})` to dispatch sub-agents. Load agent templates from `deep-research/agents/`, `academic-paper/agents/`, `academic-paper-reviewer/agents/`, and `academic-pipeline/agents/` directories.

## Handoff Protocol

### deep-research → academic-paper
Materials: RQ Brief, Methodology Blueprint, Annotated Bibliography, Synthesis Report, INSIGHT Collection

### academic-paper → academic-paper-reviewer
Materials: Complete paper text. field_analyst_agent auto-detects domain and configures reviewers.

### academic-paper-reviewer → academic-paper (revision)
Materials: Editorial Decision Letter, Revision Roadmap, Per-reviewer detailed comments

## Version Info
- **Suite version**: 3.9.4.2-copilot
- **Last Updated**: 2026-05-28
- **Author**: Zhenyu Zhang
- **License**: CC-BY-NC 4.0
```

## Branch Strategy

- `claude-code-main` — tracks upstream `Imbad0202/academic-research-skills:main` (user-managed sync)
- `copilot-main` — Copilot CLI adaptations (maintained via merge from claude-code-main + Copilot-specific patches)

## Sync Workflow

1. Checkout `claude-code-main`: `git checkout claude-code-main`
2. Pull upstream: `git pull upstream main`
3. Resolve merge conflicts manually
4. Checkout `copilot-main`: `git checkout copilot-main`
5. Merge: `git merge claude-code-main`
6. Resolve conflicts in adapted files (SKILL.md, agent templates)
7. Re-apply `model: inherit` removal patch if needed
8. Run tests: `python3 -m pytest tests/ -q`

## Development

- **No `gh ext install`** — Copilot CLI uses `/plugin marketplace add` + `/plugin install`
- **Extension registration** — self-bootstrapping via `ars-bootstrap` skill + `scripts/setup-copilot-extension.sh`
- **Test in a separate Copilot CLI session** — this session is for development only
- **`onPreToolUse` enforcement** — deferred to v3.10 parity (same posture as upstream)
```

New:
```
> **Routing discipline (v3.9.2):** see `skills/ars-bootstrap/SKILL.md` "Routing Discipline (v3.9.2)" + `shared/references/intent_clarification_protocol.md` for cross-skill routing rules. This skill assumes routing has already settled — ambiguous cross-phase materials should have been clarified upstream.
```

**Change 2:** Find all instances of `Claude Code` → `Copilot CLI` (context-dependent; search first).

- [ ] **Step 7.2: Run grep to find Claude references in all 4 SKILL.md files**

```bash
cd /home/zzyu/skills/academic-research-skills
grep -rn -i "claude\|Claude Code\|\.claude/" skills/*/SKILL.md deep-research/SKILL.md academic-paper/SKILL.md academic-paper-reviewer/SKILL.md academic-pipeline/SKILL.md
```

Use the output to locate exact lines needing changes. Apply replacements accordingly.

- [ ] **Step 7.3: Add task() dispatch hints to each SKILL.md**

Add a "Copilot CLI Agent Dispatch" note at the end of each SKILL.md (before Version Info):

```markdown
## Copilot CLI Agent Dispatch

This skill uses sub-agents dispatched via `task()`:

```
task({agent_type: "general-purpose", prompt: <agent template content>})
```

Agent templates are loaded from `deep-research/agents/`, `academic-paper/agents/`, `academic-paper-reviewer/agents/`, and `academic-pipeline/agents/` directories. When `ARS_MODEL_ARCHITECT` or `ARS_MODEL_EXECUTION` env vars are set, include `model: "<value>"` in the `task()` call for tiered routing.
```

Expected: No output (no remaining `model:` lines).

- [ ] **Step 9.2: Update marketplace.json for Copilot CLI**

Edit `.claude-plugin/marketplace.json`:
- Update `description` to mention Copilot CLI
- Update `version` from `3.7.0` to `3.9.4.2`

---

## Task 11: Update `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 11.1: Add Copilot-specific ignores**

Add to `.gitignore`:
```
# Copilot CLI
.copilot/
```

Expected: `Syntax OK`

- [ ] **Step 12.3: Verify symlink integrity**

```bash
cd /home/zzyu/skills/academic-research-skills
for link in skills/deep-research skills/academic-paper skills/academic-paper-reviewer skills/academic-pipeline agents/synthesis_agent.md agents/research_architect_agent.md agents/report_compiler_agent.md; do
  if [ -L "$link" ]; then
    target=$(readlink "$link")
    echo "OK: $link -> $target"
  else
    echo "FAIL: $link is not a symlink"
  fi
done
```
Expected: All 7 symlinks report `OK`.

- [ ] **Step 12.4: Verify no model:inherit remains**

```bash
grep -rn "model: inherit" deep-research/agents/ academic-paper/agents/ academic-paper-reviewer/agents/ academic-pipeline/agents/
```
Expected: No output.

- [ ] **Step 12.5: Verify no .claude/ directory remains**

```bash
ls -d .claude/ 2>&1
```
Expected: `ls: cannot access '.claude/': No such file or directory`

- [ ] **Step 12.6: Verify no commands/ directory remains**

```bash
ls -d commands/ 2>&1
```
Expected: `ls: cannot access 'commands/': No such file or directory`

- [ ] **Step 12.7: Verify no hooks/ directory remains**

```bash
ls -d hooks/ 2>&1
```
Expected: `ls: cannot access 'hooks/': No such file or directory`

- [ ] **Step 12.8: Verify setup script is executable**

```bash
test -x scripts/setup-copilot-extension.sh && echo "OK: executable" || echo "FAIL: not executable"
```
Expected: `OK: executable`

- [ ] **Step 12.9: Final git status check**

```bash
cd /home/zzyu/skills/academic-research-skills && git status
```
Expected: Clean working tree (or only intentional untracked files).
