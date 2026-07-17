import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  buildGuardPayload,
  createModelRoutingHint,
  findRealPython,
  modelRoutingHint,
  runGuard,
} from "../scripts/copilot_runtime.mjs";

test("extension registers every upstream ARS command", () => {
  const extension = readFileSync(new URL("../extension.mjs", import.meta.url), "utf8");
  const names = [...extension.matchAll(/name:\s*"(ars-[^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(names.sort(), [
    "ars-3w",
    "ars-abstract",
    "ars-cache-invalidate",
    "ars-citation-check",
    "ars-disclosure",
    "ars-format-convert",
    "ars-full",
    "ars-lit-review",
    "ars-mark-read",
    "ars-outline",
    "ars-plan",
    "ars-rebuttal-audit",
    "ars-reviewer",
    "ars-revision",
    "ars-revision-coach",
    "ars-unmark-read",
  ]);
});

test("guard payload uses Copilot cwd and records the plugin root", () => {
  assert.deepEqual(
    buildGuardPayload(
      { cwd: "/work/project", toolName: "edit", toolArgs: { path: "paper.md" } },
      "/plugins/ars",
    ),
    {
      cwd: "/work/project",
      plugin_root: "/plugins/ars",
      tool_input: { path: "paper.md" },
      tool_name: "edit",
    },
  );
});

test("valid ARS_MODEL_TIERING suppresses legacy blanket model ids", () => {
  const hint = modelRoutingHint("architect", {
    ARS_MODEL_TIERING: "economy",
    ARS_MODEL_ARCHITECT: "hard-pinned-model",
  });
  assert.match(hint, /ARS_MODEL_TIERING=economy/);
  assert.match(hint, /shared\/model_tiering\.md/);
  assert.doesNotMatch(hint, /hard-pinned-model/);
});

test("unset tiering preserves legacy explicit model routing", () => {
  const hint = modelRoutingHint("execution", { ARS_MODEL_EXECUTION: "chosen-model" });
  assert.match(hint, /chosen-model/);
});

test("invalid tiering warns and otherwise behaves as absent", () => {
  const hint = modelRoutingHint("architect", {
    ARS_MODEL_TIERING: "fastest",
    ARS_MODEL_ARCHITECT: "chosen-model",
  });
  assert.match(hint, /invalid ARS_MODEL_TIERING=fastest/);
  assert.match(hint, /chosen-model/);
});

test("session model-routing wrapper warns only once for an invalid value", () => {
  const hintFor = createModelRoutingHint(() => ({
    ARS_MODEL_TIERING: "fastest",
    ARS_MODEL_ARCHITECT: "chosen-model",
  }));
  assert.match(hintFor("architect"), /invalid ARS_MODEL_TIERING=fastest/);
  const second = hintFor("architect");
  assert.doesNotMatch(second, /invalid ARS_MODEL_TIERING/);
  assert.match(second, /chosen-model/);
});

test("python discovery rejects a successful stub without the marker", () => {
  const calls = [];
  const fakeSpawn = (command, args) => {
    calls.push([command, ...args]);
    if (command === "python3") return { status: 0, stdout: "", stderr: "" };
    if (command === "python") return { status: 0, stdout: "ARS_PY_OK", stderr: "" };
    return { status: 1, stdout: "", stderr: "" };
  };
  assert.deepEqual(findRealPython(fakeSpawn, "linux"), ["python"]);
  assert.equal(calls[0][0], "python3");
});

test("broken or unavailable guard fails open without logging", () => {
  const fakeSpawn = () => ({ status: 1, stdout: "", stderr: "noisy stub" });
  const originalError = console.error;
  let logged = false;
  console.error = () => { logged = true; };
  try {
    assert.deepEqual(runGuard(
      { cwd: "/work", toolName: "edit", toolArgs: { path: "paper.md" } },
      { pluginRoot: "/plugins/ars", spawnSyncImpl: fakeSpawn, platform: "linux" },
    ), {});
  } finally {
    console.error = originalError;
  }
  assert.equal(logged, false);
});
