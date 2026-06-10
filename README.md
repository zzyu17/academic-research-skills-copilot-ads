# Academic Research Skills for Copilot CLI

[![Version](https://img.shields.io/badge/version-v3.11.1-blue)](https://github.com/Imbad0202/academic-research-skills/releases/tag/v3.11.1)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](https://creativecommons.org/licenses/by-nc/4.0/)

[简体中文版](README.zh-CN.md) | [繁體中文版](README.zh-TW.md) | [日本語版](README.ja-JP.md)

A comprehensive suite of Copilot CLI skills for academic research — 4 skills, 25+ modes, 42-agent ensemble covering the full pipeline from research to publication.

> **This is the Copilot CLI sibling distribution.** For the reference Claude Code distribution, see [the upstream README](https://github.com/Imbad0202/academic-research-skills). Feature documentation, version history, design specs, and architecture details live in the upstream docs and this repo's `docs/` directory. This README covers Copilot CLI-specific installation and usage only.

---

## Install

In your Copilot CLI session:

```text
/plugin marketplace add zzyu17/academic-research-skills-copilot
/plugin install academic-research-skills@academic-research-skills
```

**First session only — extension registration:**

The `ars-bootstrap` skill auto-triggers on academic keywords. It detects the missing extension, asks you to approve `setup-copilot-extension.sh` (one bash permission), creates the symlink, and reloads extensions automatically. 13 slash commands (`/ars-full`, `/ars-plan`, etc.) are activated immediately within the same session.

On all subsequent sessions, the bootstrap exits silently — no repeated prompts.

> **After plugin update:** If you run `/plugin update academic-research-skills@academic-research-skills`, the extension symlink auto-follows the updated source files.
To activate the updated `extension.mjs`, run `/restart` or start a new session with `/clear`.

See [QUICKSTART.md](QUICKSTART.md) for the full walkthrough.

---

## Slash commands

| Slash command | What it does |
|---|---|
| `/ars-full` | Full pipeline — research → write → review → revise → finalize |
| `/ars-plan` | Socratic chapter-by-chapter planning |
| `/ars-outline` | Detailed outline + evidence map |
| `/ars-revision` | Revised draft + R&R responses |
| `/ars-revision-coach` | Parse reviewer comments → Revision Roadmap |
| `/ars-reviewer` | Multi-perspective simulated peer review |
| `/ars-abstract` | Bilingual abstract + keywords |
| `/ars-lit-review` | Annotated bibliography |
| `/ars-format-convert` | Convert between LaTeX / DOCX / PDF / Markdown |
| `/ars-citation-check` | Citation error report |
| `/ars-disclosure` | Venue-specific AI-usage disclosure |
| `/ars-mark-read` | Record human-read signal for citations |
| `/ars-unmark-read` | Rescind a prior human-read mark |

**Auto-generated skill commands** (available immediately after plugin install, no extension needed):

`/academic-research-skills:deep-research`, `/academic-research-skills:academic-paper`, `/academic-research-skills:academic-paper-reviewer`, `/academic-research-skills:academic-pipeline`, `/academic-research-skills:ars-bootstrap`

---

## Model routing (optional)

For tiered model dispatch via environment variables:

```bash
export ARS_MODEL_ARCHITECT="claude-opus-4-5"    # architect tier (full pipeline, revision-coach, reviewer)
export ARS_MODEL_EXECUTION="claude-sonnet-4-5"   # execution tier (plan, outline, revision, abstract, etc.)
```

Without env vars, all sub-agent dispatches use the session default model. Both tiers must be served by the same provider endpoint (`COPILOT_PROVIDER_BASE_URL`) (BYOK mode) or available in your Copilot subscription.

---

## Skills at a glance

| Skill | Purpose |
|-------|---------|
| `deep-research` v2.9.4 | 13-agent research team — 7 modes |
| `academic-paper` v3.1.2 | 12-agent paper writing — 10 modes |
| `academic-paper-reviewer` v1.9.1 | Multi-perspective peer review — 6 modes |
| `academic-pipeline` v3.11.1 | Full 10-stage pipeline orchestrator |

---

## Further reading

- **[Upstream README](https://github.com/Imbad0202/academic-research-skills)** — full feature documentation, architecture, version history, design philosophy
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — pipeline flow, stage matrix, quality gates
- **[docs/design/](docs/design/)** — all design specs (v3.6.2 – v3.11.1 + Copilot port)
- **[QUICKSTART.md](QUICKSTART.md)** — step-by-step Copilot CLI setup
- **[POSITIONING.md](POSITIONING.md)** — what ARS is and isn't
- **[CHANGELOG.md](CHANGELOG.md)** — release history (Copilot port at top)

## License

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
