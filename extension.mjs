// extension.mjs — ARS Copilot CLI Extension
// =============================================================================
// Slash commands (16) + lifecycle hooks (onSessionStart, onPreToolUse,
// onErrorOccurred). onPreToolUse hosts the scoped-write guard.
//
// Uses Copilot CLI SDK: import { joinSession } from "@github/copilot-sdk/extension"
// SDK is auto-resolved by the Copilot CLI extension bootstrap — no install needed.
// =============================================================================

import { joinSession } from "@github/copilot-sdk/extension";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { createModelRoutingHint, runGuard } from "./scripts/copilot_runtime.mjs";

const pluginRoot = dirname(fileURLToPath(import.meta.url));
const modelRoutingHint = createModelRoutingHint();

// -----------------------------------------------------------------------------
// Model routing helpers
// -----------------------------------------------------------------------------

const RECENT_PROMPT_WINDOW_MS = 5000;
let lastUserPrompt = "";
let lastUserPromptAt = 0;
let pendingDispatchContext = "";

function shouldCaptureUserPrompt(prompt) {
  if (!prompt) return false;
  const trimmed = prompt.trim();
  if (!trimmed) return false;
  if (trimmed.startsWith("/")) return false;
  if (trimmed.startsWith("[ARS]")) return false;
  return true;
}

function captureUserPrompt(prompt) {
  if (!shouldCaptureUserPrompt(prompt)) return;
  lastUserPrompt = prompt;
  lastUserPromptAt = Date.now();
}

function consumeRecentUserPrompt() {
  if (!lastUserPrompt) return "";
  if (Date.now() - lastUserPromptAt > RECENT_PROMPT_WINDOW_MS) return "";
  const prompt = lastUserPrompt;
  lastUserPrompt = "";
  lastUserPromptAt = 0;
  return prompt;
}

function resolveUserPrompt(context, allowRecentFallback) {
  const args = context?.args?.trim();
  if (args) return args;
  if (!allowRecentFallback) return "";
  return consumeRecentUserPrompt();
}

function buildVisibleSlashPrompt(context, userPrompt) {
  const commandName = (context?.commandName || "").replace(/^\//, "").trim();
  const base = commandName ? `/${commandName}` : (context?.command || "").trim();
  const trimmed = userPrompt?.trim();
  return trimmed ? `${base} ${trimmed}` : base;
}

function buildDispatchContext(skill, mode, tier) {
  const routing = modelRoutingHint(tier);
  return `[ARS] Activate skill: ${skill}, mode: ${mode}. Load ${skill}/SKILL.md and follow the ${mode} workflow.${routing}`;
}

async function dispatchSkillCommand(context, skill, mode, tier) {
  const userPrompt = resolveUserPrompt(context, true);
  const visiblePrompt = buildVisibleSlashPrompt(context, userPrompt);
  pendingDispatchContext = buildDispatchContext(skill, mode, tier);
  await session.send({
    prompt: visiblePrompt,
  });
}

// -----------------------------------------------------------------------------
// Join session — register commands + hooks via Copilot CLI SDK
// -----------------------------------------------------------------------------

const session = await joinSession({
  commands: [
    {
      name: "ars-full",
      description: "Full pipeline — research → write → review → revise → finalize",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-pipeline", "full", "architect");
      },
    },
    {
      name: "ars-revision-coach",
      description: "Parse reviewer comments → Revision Roadmap + Response Letter skeleton",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "revision-coach", "architect");
      },
    },
    {
      name: "ars-reviewer",
      description: "academic-paper-reviewer full mode — simulated peer-review panel",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper-reviewer", "full", "architect");
      },
    },
    {
      name: "ars-plan",
      description: "Socratic chapter-by-chapter planning",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "plan", "execution");
      },
    },
    {
      name: "ars-outline",
      description: "Detailed outline + evidence map (no full draft)",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "outline-only", "execution");
      },
    },
    {
      name: "ars-revision",
      description: "Revised draft + R&R responses",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "revision", "execution");
      },
    },
    {
      name: "ars-abstract",
      description: "Bilingual abstract + keywords",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "abstract-only", "execution");
      },
    },
    {
      name: "ars-lit-review",
      description: "Annotated bibliography in paper format",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "lit-review", "execution");
      },
    },
    {
      name: "ars-3w",
      description: "WHY / HOW / WHAT paper comparison plus cross-paper synthesis",
      handler: async (context) => {
        await dispatchSkillCommand(context, "deep-research", "three-way-scan", "execution");
      },
    },
    {
      name: "ars-rebuttal-audit",
      description: "QA an existing rebuttal draft against reviewer comments",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "rebuttal-audit", "execution");
      },
    },
    {
      name: "ars-format-convert",
      description: "Convert paper between LaTeX / DOCX / PDF / Markdown",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "format-convert", "execution");
      },
    },
    {
      name: "ars-citation-check",
      description: "Citation error report",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "citation-check", "execution");
      },
    },
    {
      name: "ars-disclosure",
      description: "Venue-specific AI-usage disclosure statement",
      handler: async (context) => {
        await dispatchSkillCommand(context, "academic-paper", "disclosure", "execution");
      },
    },
    {
      name: "ars-mark-read",
      description: "Record human-read signal for one or more citation keys",
      handler: async (context) => {
        const routing = modelRoutingHint("execution");
        const userPrompt = resolveUserPrompt(context, false);
        const visiblePrompt = buildVisibleSlashPrompt(context, userPrompt);
        pendingDispatchContext = `[ARS] Record human-read signal for citation keys. Run: python3 scripts/ars_mark_read.py with the active Material Passport path. Per v3.6.8 §3.6, stores signal in <passport-stem>_human_read_log.yaml. literature_corpus[] is NEVER mutated.${routing}`;
        await session.send({
          prompt: visiblePrompt,
        });
      },
    },
    {
      name: "ars-unmark-read",
      description: "Rescind a prior human-read mark for one or more citation keys",
      handler: async (context) => {
        const routing = modelRoutingHint("execution");
        const userPrompt = resolveUserPrompt(context, false);
        const visiblePrompt = buildVisibleSlashPrompt(context, userPrompt);
        pendingDispatchContext = `[ARS] Rescind human-read signal for citation keys after validating every citation_key against literature_corpus[]. Run: python3 scripts/ars_unmark_read.py with the active Material Passport path. Per v3.6.8 §3.6, updates <passport-stem>_human_read_log.yaml and NEVER mutates literature_corpus[].${routing}`;
        await session.send({
          prompt: visiblePrompt,
        });
      },
    },
    {
      name: "ars-cache-invalidate",
      description: "Invalidate the ARS cache for a specific cache key or scope",
      handler: async (context) => {
        const routing = modelRoutingHint("execution");
        const userPrompt = resolveUserPrompt(context, false);
        const visiblePrompt = buildVisibleSlashPrompt(context, userPrompt);
        pendingDispatchContext = `[ARS] Cache Invalidate — use python3 scripts/ars_cache_invalidate.py to invalidate cache entries. Per v3.11.1 §3.6.${routing}`;
        await session.send({
          prompt: visiblePrompt,
        });
      },
    },
  ],

  hooks: {
    onSessionStart: async (input) => {
      // Silent: no session.log() spam, no additionalContext that
      // replaces the user prompt. All ARS routing/context is provided
      // by ars-bootstrap/SKILL.md when the skill is actually invoked.
      return {};
    },

    onUserPromptSubmitted: async (input) => {
      captureUserPrompt(input.prompt);
      if (pendingDispatchContext) {
        const additionalContext = pendingDispatchContext;
        pendingDispatchContext = "";
        return { additionalContext };
      }
    },

    onPreToolUse: async (input) => {
      // -------------------------------------------------------------------
      // Scoped-Write Guard — pre-execution write blocking.
      //
      // Inspects create/edit/bash tool calls. Calls ars_write_scope_guard.py
      // via stdin JSON. Maps the guard output ({blocked, reason}) to
      // Copilot CLI's onPreToolUse return format (permissionDecision).
      //
      // Platform gap: Copilot CLI hooks do not expose agent_type/subagent
      // context. The guard's Bucket A per-agent fencing is therefore inactive;
      // infrastructure self-protection (Step 2 — deny writes to guard scripts,
      // agent definitions, extension.mjs, etc.) still operates. Bucket A Bash
      // denial also requires agent identity and is therefore unavailable here.
      // -------------------------------------------------------------------
      const writeTools = ['create', 'edit', 'bash', 'write'];
      if (!writeTools.includes((input.toolName || '').toLowerCase())) return {};

      // agent_type is deliberately omitted — Copilot CLI hooks lack subagent
      // context. The guard enforces plugin infrastructure self-protection; the
      // per-agent Bucket A fence remains unavailable at this hook boundary.
      return runGuard(input, { pluginRoot });
    },

    onErrorOccurred: async (input) => {
      // input.error, input.errorContext, input.recoverable
      if (input.errorContext === "model_call" || input.error?.includes("rate_limit")) {
        return { errorHandling: "retry", retryCount: 2 };
      }
      return {};
    },
  },
});
