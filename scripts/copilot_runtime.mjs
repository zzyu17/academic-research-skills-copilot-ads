import { spawnSync } from "node:child_process";
import path from "node:path";

const PYTHON_MARKER = "ARS_PY_OK";
const VALID_MODEL_TIERING = new Set(["economy", "quality-boost"]);

function buildModelRoutingHint(commandTier, env, includeInvalidWarning) {
  const rawTiering = (env.ARS_MODEL_TIERING || "").trim();
  if (VALID_MODEL_TIERING.has(rawTiering)) {
    return `\n\n[Model tiering: ARS_MODEL_TIERING=${rawTiering}. Load shared/model_tiering.md and scripts/model_tiering_manifest.json, then apply the canonical relative per-agent tiering at dispatch time. Do not use the legacy blanket command-tier model overrides while this switch is active.]`;
  }

  const warning = rawTiering && includeInvalidWarning
    ? `[MODEL-TIERING: invalid ARS_MODEL_TIERING=${rawTiering} — treated as absent.]\n`
    : "";
  const legacyModel = commandTier === "architect"
    ? env.ARS_MODEL_ARCHITECT
    : commandTier === "execution"
      ? env.ARS_MODEL_EXECUTION
      : null;
  const legacy = legacyModel
    ? `[Model routing: use task({model: "${legacyModel}"}) for subagent dispatches.]`
    : "";
  return warning || legacy ? `\n\n${warning}${legacy}` : "";
}

export function modelRoutingHint(commandTier, env = process.env) {
  return buildModelRoutingHint(commandTier, env, true);
}

export function createModelRoutingHint(envProvider = () => process.env) {
  let invalidWarningEmitted = false;
  return (commandTier) => {
    const env = envProvider();
    const rawTiering = (env.ARS_MODEL_TIERING || "").trim();
    const invalid = Boolean(rawTiering) && !VALID_MODEL_TIERING.has(rawTiering);
    const hint = buildModelRoutingHint(commandTier, env, !invalidWarningEmitted);
    if (invalid) invalidWarningEmitted = true;
    return hint;
  };
}

export function buildGuardPayload(input, pluginRoot) {
  return {
    tool_name: input.toolName,
    tool_input: input.toolArgs || {},
    cwd: input.cwd || process.cwd(),
    plugin_root: pluginRoot,
  };
}

function pythonCandidates(platform) {
  return platform === "win32"
    ? [["py", "-3"], ["python3"], ["python"]]
    : [["python3"], ["python"]];
}

export function findRealPython(
  spawnSyncImpl = spawnSync,
  platform = process.platform,
) {
  for (const [command, ...prefixArgs] of pythonCandidates(platform)) {
    const result = spawnSyncImpl(
      command,
      [...prefixArgs, "-c", `import sys; sys.stdout.write('${PYTHON_MARKER}')`],
      {
        encoding: "utf8",
        timeout: 1500,
        windowsHide: true,
      },
    );
    if (!result?.error && result?.status === 0 && result?.stdout === PYTHON_MARKER) {
      return [command, ...prefixArgs];
    }
  }
  return null;
}

export function runGuard(input, options = {}) {
  const {
    platform = process.platform,
    pluginRoot,
    scriptPath = path.join(pluginRoot || "", "scripts", "ars_write_scope_guard.py"),
    spawnSyncImpl = spawnSync,
  } = options;
  const python = findRealPython(spawnSyncImpl, platform);
  if (!python) return {};

  const [command, ...prefixArgs] = python;
  const result = spawnSyncImpl(command, [...prefixArgs, scriptPath], {
    input: JSON.stringify(buildGuardPayload(input, pluginRoot)),
    timeout: 5000,
    encoding: "utf8",
    maxBuffer: 64 * 1024,
    windowsHide: true,
  });
  if (result?.error || result?.status !== 0) return {};

  try {
    const parsed = JSON.parse((result.stdout || "").trim());
    if (parsed?.blocked) {
      return {
        permissionDecision: "deny",
        permissionDecisionReason: parsed.reason || "Write blocked by ARS scope guard",
      };
    }
  } catch {
    // A broken guard must not wedge the Copilot hot path.
  }
  return {};
}
