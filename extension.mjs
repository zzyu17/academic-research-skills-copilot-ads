// extension.mjs — ARS Copilot CLI Extension
// =============================================================================
// Slash commands (13) + lifecycle hooks (onSessionStart, onPostToolUse,
// onErrorOccurred). onPreToolUse is reserved for v3.10 parity.
//
// Uses Copilot CLI SDK: import { joinSession } from "@github/copilot-sdk/extension"
// SDK is auto-resolved by the Copilot CLI extension bootstrap — no install needed.
// =============================================================================

import { joinSession } from "@github/copilot-sdk/extension";

// -----------------------------------------------------------------------------
// Model routing helpers
// -----------------------------------------------------------------------------

function getModelTier(tier) {
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
  const base = `/${context.command}`;
  const trimmed = userPrompt?.trim();
  return trimmed ? `${base} ${trimmed}` : base;
}

function buildDispatchContext(skill, mode, tier) {
  const routing = modelRoutingHint(tier);
  return `[ARS] Activate skill: ${skill}, mode: ${mode}. Load ${skill}/SKILL.md and follow the ${mode} workflow.${routing}`;
}

async function dispatchSkillCommand(context, skill, mode, tier) {
  const userPrompt = resolveUserPrompt(context, true);
  pendingDispatchContext = buildDispatchContext(skill, mode, tier);
  await session.send({
    prompt: userPrompt || context.command,
    displayPrompt: buildVisibleSlashPrompt(context, userPrompt),
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
        pendingDispatchContext = `[ARS] Record human-read signal for citation keys. Run: python3 scripts/ars_mark_read.py with the active Material Passport path. Per v3.6.8 §3.6, stores signal in <passport-stem>_human_read_log.yaml. literature_corpus[] is NEVER mutated.${routing}`;
        await session.send({
          prompt: userPrompt || context.command,
          displayPrompt: buildVisibleSlashPrompt(context, userPrompt),
        });
      },
    },
    {
      name: "ars-unmark-read",
      description: "Rescind a prior human-read mark for one or more citation keys",
      handler: async (context) => {
        const routing = modelRoutingHint("execution");
        const userPrompt = resolveUserPrompt(context, false);
        pendingDispatchContext = `[ARS] Rescind human-read signal for citation keys. Run: python3 scripts/ars_unmark_read.py with the active Material Passport path. Per v3.6.8 §3.6.${routing}`;
        await session.send({
          prompt: userPrompt || context.command,
          displayPrompt: buildVisibleSlashPrompt(context, userPrompt),
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

    onPostToolUse: async (input) => {
      // Pipeline state tracking — detect phase directory creation
      const inputPath = input.toolArgs?.file_path || input.toolArgs?.path || "";
      if (/phase\d+[a-z]?_/.test(inputPath)) {
        // Reserved for future state-machine integration
      }
    },

    onErrorOccurred: async (input) => {
      // input.error, input.errorContext, input.recoverable
      if (input.errorContext === "model_call" || input.error?.includes("rate_limit")) {
        return { errorHandling: "retry", retryCount: 2 };
      }
      return {};
    },

    // Reserved for v3.10 active conductor (#134):
    // onPreToolUse: async (input) => {
    //   // input.toolName, input.toolArgs
    //   // Phase-boundary write blocking
    //   // ARS_CLAIM_AUDIT HIGH-WARN annotation blocking
    //   // Formatter REFUSE rules 6-10 enforcement at tool level
    //   return { permissionDecision: "allow" };
    // },
  },
});
