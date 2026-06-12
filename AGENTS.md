# Academic Research Skills — Contributor Guidelines

This file is for ARS maintainers and contributors. It is NOT loaded into Copilot CLI user sessions. End users receive their runtime instructions from the `ars-bootstrap` skill (`skills/ars-bootstrap/SKILL.md`) and the `onSessionStart` extension hook.

## Repository Structure

```
academic-research-skills/
├── copilot-main          ← Copilot CLI adaptations (this branch)
├── claude-code-main      ← Tracks upstream Imbad0202/academic-research-skills:main
├── extension.mjs         ← Copilot CLI extension (13 slash commands + hooks)
├── package.json          ← Plugin metadata
├── skills/
│   ├── ars-bootstrap/    ← Session-start bootstrap (replaces .claude/CLAUDE.md)
│   ├── deep-research/    ← 13-agent research team skill
│   ├── academic-paper/   ← 12-agent paper writing skill
│   ├── academic-paper-reviewer/ ← 7-agent peer review skill
│   └── academic-pipeline/ ← 5-agent pipeline orchestrator
├── agents/               ← 3 symlinks to deep-research/agents/
├── shared/               ← Shared references, contracts, templates
├── scripts/              ← Python scripts + setup-copilot-extension.sh
└── tests/                ← 4 Python tests
```

## Branch Strategy

- `claude-code-main` — tracks upstream `Imbad0202/academic-research-skills:main` (user-managed sync)
- `copilot-main` — Copilot CLI adaptations (maintained via merge from claude-code-main + Copilot-specific patches)
- `copilot-ads` — ADS edition (astronomy/astrophysics ADS + arXiv integration, distributed via `zzyu17/academic-research-skills-copilot-ads`)

## Development

- **No `gh ext install`** — Copilot CLI uses `/plugin marketplace add` + `/plugin install`
- **Extension registration** — self-bootstrapping via `ars-bootstrap` skill + `scripts/setup-copilot-extension.sh`
- **Test in a separate Copilot CLI session** — this session is for development only
- **`onPreToolUse` enforcement** — deferred to v3.10 parity (same posture as upstream)
