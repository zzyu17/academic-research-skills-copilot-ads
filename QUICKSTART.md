# Quick Start — Copilot CLI

Get from zero to your first AI-assisted research in 3 steps.

## Step 1: Install

In your Copilot CLI session:

```text
/plugin marketplace add zzyu17/academic-research-skills-copilot-ads
/plugin install academic-research-skills-ads@academic-research-skills-ads
```

## Step 2: Set up the extension (first session only)

When you start your next Copilot CLI session with an academic prompt, the `ars-bootstrap` skill auto-triggers. It will:

1. Detect that the ARS extension is not yet registered
2. Ask you to approve running `scripts/setup-copilot-extension.sh` (one bash permission)
3. Create the extension symlink and `.bootstrapped` marker
4. Reload extensions automatically — 16 slash commands (`/ars-full`, `/ars-plan`, etc.) are activated immediately within the same session

On all subsequent sessions, the bootstrap skill exits silently — routing rules are injected into agent context without any user-facing prompt.

> **After plugin update:** If you run `/plugin update academic-research-skills-ads@academic-research-skills-ads`, the extension symlink auto-follows the updated source files.
To activate the updated `extension.mjs`, run `/restart` or start a new session with `/clear`.

## Step 3: Start researching

Tell Copilot what you want to do. It will automatically pick the right skill and mode.

### Example: Guided research (Socratic mode)

```
You: "I have a vague idea about AI's impact on higher education quality assurance,
      but I'm not sure how to frame the research question. Can you guide me?"
```

Copilot enters Socratic mode — asking questions to help you clarify your thinking. After 5-15 rounds, you'll have a focused research question.

### Example: Write a paper

```
You: "Help me write a paper about the impact of declining birth rates
      on private universities in Taiwan"
```

### Example: Review an existing paper

```
You: "Review this paper" (then paste or attach the paper)
```

### Example: Full pipeline

```
You: "I want to produce a complete research paper about how agentic AI
      is reshaping student learning outcome measurement"

Or use the slash command:
/ars-full
```

This triggers the full 10-stage pipeline. Budget ~$4-6 in API costs and 2-4 hours of collaborative work.

## Which mode should I use?

| I want to... | Use this |
|-------------|----------|
| Explore a vague idea | `/academic-research-skills-ads:deep-research` socratic mode |
| Get a quick literature summary | `/academic-research-skills-ads:deep-research` quick mode |
| Do a systematic review (PRISMA) | `/academic-research-skills-ads:deep-research` systematic-review mode |
| Write a paper from scratch | `/ars-full` or `/academic-research-skills-ads:academic-paper` full mode |
| Plan a paper chapter by chapter | `/ars-plan` |
| Get my paper reviewed | `/ars-reviewer` |
| Do everything end-to-end | `/ars-full` |

## Slash commands

**Mode-specific and utilities** (16, requires extension setup):
`/ars-full`, `/ars-plan`, `/ars-outline`, `/ars-revision`, `/ars-revision-coach`, `/ars-abstract`, `/ars-lit-review`, `/ars-reviewer`, `/ars-format-convert`, `/ars-citation-check`, `/ars-disclosure`, `/ars-mark-read`, `/ars-unmark-read`, `/ars-cache-invalidate`, `/ars-3w`, `/ars-rebuttal-audit`

**Skill entry points** (5, available immediately after plugin install):
`/academic-research-skills-ads:deep-research`, `/academic-research-skills-ads:academic-paper`, `/academic-research-skills-ads:academic-paper-reviewer`, `/academic-research-skills-ads:academic-pipeline`, `/academic-research-skills-ads:ars-bootstrap`

## Model routing (optional)

ARS uses the session model by default. Opt in to the v3.16 model-tiering policy with:

```bash
export ARS_MODEL_TIERING="economy"        # execution roles step down one tier
# or: export ARS_MODEL_TIERING="quality-boost"  # judgment roles use the frontier tier
```

Without the variable, all dispatches use the session model. See [`shared/model_tiering.md`](shared/model_tiering.md) for role classifications and precedence.

## What's next?

- [Full README](README.md) — all features, modes, and changelog
- [中文版](README.zh-TW.md) — Traditional Chinese version
- [한국어](README.ko-KR.md) — Korean version
- [Pipeline showcase](examples/showcase/) — real artifacts from a complete pipeline run
