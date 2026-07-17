---
name: ars-bootstrap
description: "Academic Research Skills — unified entry point for research, writing, reviewing, and publishing academic papers. Coordinates 4 skills: deep-research (13-agent research team), academic-paper (12-agent writing pipeline), academic-paper-reviewer (peer review panel), and academic-pipeline (full orchestrator). Triggers on: research, literature review, three-way scan, write paper, revise paper, rebuttal audit, peer review, academic pipeline, full workflow, end-to-end, citation check, format convert, cache invalidate, commitment ledger, version reconcile, domain evidence, firm rules. 研究, 文獻回顧, 論文寫作, 學術論文, 修改論文, 完整流程, 引用檢查, 格式轉換, 연구, 문헌 검토, 논문 작성, 논문 수정, 동료 평가."
metadata:
  version: "1.0.0"
  last_updated: "2026-07-17"
  status: active
  task_type: bootstrap
---

# Academic Research Skills — Copilot CLI

A suite of Copilot CLI skills for rigorous academic research, paper writing, peer review, and pipeline orchestration.

## Extension Setup Check (run once, idempotent)

**Step 0 — Silent exit gate (prevents repeated prompts):**

Check: does `~/.copilot/extensions/ars/.bootstrapped` exist?

- If YES → extension was previously registered. Exit silently — do NOT display any of the setup instructions below. The rest of this bootstrap skill (skills overview, routing rules, trigger keywords) should still be loaded into agent context, but no user-facing setup message is shown.
- If NO → proceed to Step 1 below for first-time setup.

**Step 1 — First-time setup (only when .bootstrapped is missing):**

On first invocation, verify the ARS extension is registered:

Check: does `~/.copilot/extensions/ars/extension.mjs` exist?
  (use `test -L ~/.copilot/extensions/ars/extension.mjs` or equivalent)

If the file does NOT exist:
  1. Resolve the plugin install directory from the location of this SKILL.md:
     `PLUGIN_DIR=$(dirname $(dirname $(readlink -f skills/ars-bootstrap/SKILL.md)))`
  2. Run the setup script:
     `bash "${PLUGIN_DIR}/scripts/setup-copilot-extension.sh"`
  3. The setup script creates the symlink AND the `.bootstrapped` marker.
  4. Call `extensions_reload({})` to reload extensions. The 16 slash commands are activated immediately within the same session.

If the file EXISTS but `.bootstrapped` is missing (edge case: manual symlink):
  1. Create the marker: `touch ~/.copilot/extensions/ars/.bootstrapped`
  2. Then exit silently.

After setup is complete and `.bootstrapped` exists, the bootstrap skill runs silently on every subsequent session — routing rules are injected into agent context without any user-facing prompt.

## Skills Overview

| Skill | Purpose | Key Modes |
|-------|---------|-----------|
| `deep-research` v2.11.0 | 13-agent research team | full, quick, socratic, review, lit-review, three-way-scan, fact-check, systematic-review |
| `academic-paper` v3.2.0 | 12-agent paper writing | full, plan, outline-only, revision, revision-coach, abstract-only, lit-review, format-convert, citation-check, disclosure, rebuttal-audit |
| `academic-paper-reviewer` v1.10.0 | Multi-perspective paper review (5 reviewers + optional cross-model DA critique) | full, re-review, quick, methodology-focus, guided, calibration |
| `academic-pipeline` v3.17.0 | Full pipeline orchestrator | (coordinates all above) |

## v3.17 Key Additions

- Canonical cross-model handoff envelopes move external transport to the dispatching layer.
- Stage 5/6 boundary semantics and terminal acknowledgement are pinned by deterministic locks.
- The executable panel checker validates reviewer and synthesis decisions mechanically.
- Plugin-agent tool allowlists and materialized top-level mirrors enforce least privilege.
- The degradation registry and transport fixtures make graceful fallback auditable.

## Trigger Auto-Detection

**English keywords:**
- Research: research, literature review, systematic review, fact-check, research proposition
- Writing: write my paper, academic paper, revise my paper, format conversion, abstract
- Reviewing: peer review, manuscript review, referee report, critique paper
- Pipeline: full pipeline, end-to-end, research to publication, complete workflow

**中文關鍵詞:**
- 研究: 研究, 深度研究, 文獻回顧, 事實查核, 研究方向
- 寫作: 論文寫作, 學術論文, 期刊論文, 修改論文, 寫摘要
- 審核: 審查意見, 審稿回覆, 模擬審查
- 流程: 完整流程, 從頭到尾, 研究到論文

**한국어 키워드:**
- 연구: 연구, 심층 연구, 문헌 검토, 체계적 문헌고찰, 팩트체크
- 작성: 논문 작성, 학술 논문, 논문 수정, 초록 작성
- 검토: 동료 평가, 논문 심사, 심사 의견, 반박문 감사
- 파이프라인: 전체 파이프라인, 처음부터 끝까지, 연구에서 출판까지

## Model Routing (Optional)

ARS supports the canonical relative model-tiering switch:

```bash
export ARS_MODEL_TIERING="economy"        # execution agents one tier down, with floor
export ARS_MODEL_TIERING="quality-boost"  # judgment gates up to the frontier tier
```

Load `shared/model_tiering.md` and `scripts/model_tiering_manifest.json` when the switch is
active. Unset preserves the session model everywhere. An invalid value is warned and treated
as absent. The older explicit Copilot overrides remain supported when the switch is unset:

```bash
# Architect tier (complex reasoning: full pipeline, revision-coach, reviewer)
export ARS_MODEL_ARCHITECT="claude-opus-4-5"

# Execution tier (focused tasks: plan, outline, revision, abstract, etc.)
export ARS_MODEL_EXECUTION="claude-sonnet-4-5"
```

**How it works:**
- A valid `ARS_MODEL_TIERING` value takes precedence and suppresses blanket command-tier overrides
- Tier positions are relative to the current model family; ARS does not hard-pin ids for this mechanism
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

6. **rebuttal-audit vs revision-coach (input-shape gate)**: Route to `academic-paper rebuttal-audit` only when the user supplies BOTH reviewer comments and an existing rebuttal/response draft to evaluate. If only reviewer comments are present, route to `revision-coach`. If the input shape is unclear, clarify. `rebuttal-audit` is standalone/advisory and does not emit Schema 11 or verified status.

## Key Rules

- All claims must have citations
- Evidence hierarchy respected (meta-analyses > RCTs > cohort > case reports > expert opinion)
- Contradictions disclosed with evidence quality comparison
- AI disclosure in all reports
- Default output language matches user input (including English, Chinese, Korean, or Japanese)
- **Agent dispatch:** Use `task({agent_type: "general-purpose", prompt: <agent template content>})` to dispatch sub-agents. Load agent templates from `deep-research/agents/`, `academic-paper/agents/`, `academic-paper-reviewer/agents/`, and `academic-pipeline/agents/` directories.

## Handoff Protocol

### deep-research → academic-paper
Materials: RQ Brief, Methodology Blueprint, Annotated Bibliography, Synthesis Report, INSIGHT Collection

### academic-paper → academic-paper-reviewer
Materials: Complete paper text. field_analyst_agent auto-detects domain and configures reviewers.

### academic-paper-reviewer → academic-paper (revision)
Materials: Editorial Decision Letter, Revision Roadmap, Per-reviewer detailed comments

## Version Info
- **Suite version**: 3.17.0-copilot
- **Last Updated**: 2026-07-17
- **Author**: Zhenyu Zhang
- **License**: CC-BY-NC 4.0
