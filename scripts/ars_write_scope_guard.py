#!/usr/bin/env python3
"""ARS write-scope guard — Copilot CLI onPreToolUse hook (#134 Slice 1).

Spec: docs/design/2026-06-01-ars-134-conductor-rescope-deterministic-write-guard-spec.md

Blocks out-of-scope file writes by the 23 Bucket A single-phase subagents, backed by
the machine-readable scope manifest at scripts/ars_phase_scope_manifest.json.

COVERAGE CLAIM — stated precisely, NOT over-promised (spec §3.3 / §7):
  * DETERMINISTIC for the structured editing tools (create / edit / write): a write
    outside the agent's declared scope is denied regardless of the agent's prompt. This is
    the load-bearing win.
  * Bash for Bucket A agents: DENIED WHOLESALE. A single-phase agent may not run any Bash;
    it uses the grep/glob tools to search and the create/edit tools to write. Six review
    rounds established WHY nothing finer is sound: neither "this Bash writes a file" (a
    denylist — `python -c`/`sh -c`/`make`/custom scripts all write, unenumerable) nor "this
    Bash is read-only" (an allowlist — `rg --pre`/`git grep -O`/`sort --compress-program`/
    `GIT_EXTERNAL_DIFF=…` all execute subprocesses, and "read-only" varies by flag, env, and
    binary version) can be decided reliably from a command string without a sandbox. All-deny
    is the only Bash policy that reaches ZERO fail-open by construction. The cost is a clean
    false-deny of ad-hoc read-only Bash, which the agent does not need (it has grep/glob).
  This is NOT "deterministic enforcement of all writes" — it is deterministic for the
  structured tools plus a clean wholesale Bash deny for fenced agents. The honest win is
  making the #133 shape (a helpful agent calling a write tool into a downstream phase dir)
  deterministically impossible, and closing the direct-shell-write path for Bucket A entirely.

The testable core is `evaluate_decision(payload, manifest, workspace_root, plugin_root)` — a pure
function. `main()` only wires stdin -> evaluate_decision -> stdout JSON.

PAYLOAD CONTRACT (stdin JSON):
  Required fields: tool_name, tool_input (dict), cwd.
  Copilot bridge field: plugin_root (str) — anchors protection to the installed ARS tree.
  Optional: agent_type (str) — the subagent frontmatter `name` (e.g. "bibliography_agent").
  Copilot CLI does not expose agent_type in hook inputs; when absent, Bucket A per-agent
  fencing is inactive but infrastructure self-protection (Step 2) still operates.

TOOL_INPUT SHAPES: create / edit / write each carry a top-level target path.
  Copilot CLI: {path, ...} — create: {path, file_text}; edit: {path, old_string, new_string}.
  The path-extraction below reads `path` and FAILS LOUD if a structured write tool ever
  lacks it — so a schema drift cannot silently fail the guard open.
"""

import fnmatch
import json
import os
import sys

MANIFEST_FILENAME = "ars_phase_scope_manifest.json"

# Structured editing tools: deterministic, single top-level target path. The 23 Bucket A
# agents emit markdown / yaml / bib / txt into their phase dir via these tools.
# Tool-name matching is case-insensitive (via _normalize_tool_name).
STRUCTURED_WRITE_TOOLS = {"write", "edit", "create"}

# Tools the guard inspects at all. Everything else -> allow (out of scope).
INSPECTED_TOOLS = STRUCTURED_WRITE_TOOLS | {"bash"}

# Step 2 infrastructure self-protection — normalized workspace-relative path patterns
# that NO agent (and not even the unconstrained main session) may write. These are the
# enforcement surface: tampering with them would fail the guard open.
INFRA_PROTECTED_GLOBS = [
    # Copilot CLI enforcement surface:
    "extension.mjs",                     # onPreToolUse hook wiring lives here
    "package.json",                      # plugin manifest
    "skills/ars-bootstrap/SKILL.md",
    "scripts/setup-copilot-extension.sh",
    # The hook script, its manifest, and the cross-check lint, protected by filename both
    # in any SUBDIR (`**/name`) AND at the workspace root (bare `name`). A deny-list
    # widening only protects MORE paths, so it is safe — unlike a per-agent allow-glob
    # widening, which would loosen scope. Covering both forms ensures a future directory
    # move can't fail the guard open. (`**/name` matches subdirs only, not root — see
    # _matches_any — so the bare entries are load-bearing for a root-level copy.)
    "**/ars_write_scope_guard.py",
    "ars_write_scope_guard.py",
    "**/ars_phase_scope_manifest.json",
    "ars_phase_scope_manifest.json",
    "**/check_v3_10_134_write_scope.py",  # the three-way name cross-check lint
    "check_v3_10_134_write_scope.py",
    # Agent definition files: the agent_type==name binding lives in their frontmatter;
    # renaming an agent out of the manifest would fail the guard open.
    "deep-research/agents/*.md",
    "academic-paper/agents/*.md",
    "academic-paper-reviewer/agents/*.md",
    "academic-pipeline/agents/*.md",
    "shared/agents/*.md",
    "agents/*.md",
]


def _normalize_target(raw_path, cwd, workspace_root):
    """Step 1 — resolve to a workspace-root-relative canonical path.

    Returns (rel_path, escaped_workspace). rel_path is None when the target escapes
    the workspace root (path traversal); escaped_workspace is True then.

    Resolves symlinks on the existing parent chain WITHOUT requiring the leaf to exist
    (the write may create it), so a path-traversal attempt is canonicalized to its real
    target BEFORE any deny-list / glob match runs.
    """
    if not os.path.isabs(raw_path):
        raw_path = os.path.join(cwd, raw_path)
    # CRITICAL: do NOT os.path.abspath() first — abspath collapses `..` LEXICALLY, which
    # would resolve `symlinked_dir/../x` to a sibling of symlinked_dir's *name* before the
    # symlink is followed, blinding the guard to the real target (caught in review). Instead
    # os.path.realpath() resolves symlinks AND `..` together in true filesystem order. It
    # tolerates a not-yet-created leaf (resolving the existing prefix and appending the
    # rest), so a brand-new file path still canonicalizes correctly.
    normalized = os.path.realpath(raw_path)

    real_ws = os.path.realpath(workspace_root)
    try:
        common = os.path.commonpath([normalized, real_ws])
    except ValueError:
        # Different drives / mixed abs-rel — treat as escape.
        return None, True
    if common != real_ws:
        return None, True
    rel = os.path.relpath(normalized, real_ws)
    # `commonpath(...) == real_ws` already proves the path did not escape; do NOT also
    # reject `rel.startswith("..")` — that would false-deny a legitimate root-level file
    # literally named `..foo` (caught in review). Only the workspace root itself (rel == ".")
    # is not a writable target.
    if rel == ".":
        return None, True
    return rel, False


def _match_segments(path_segs, pat_segs):
    """Path-segment-aware glob match. A `*` / `?` / `[...]` matches only WITHIN one
    segment (never across `/`); the literal segment `**` matches ONE OR MORE whole
    segments (a descendant — NOT zero, so `dir/**` covers files UNDER dir, not the bare
    dir node itself). This gives `dir/**` and `**/name` their intended PATH semantics —
    unlike bare fnmatch, whose `*` spans `/` and would let a root-level `phase2_x.md` match
    `phase2_*` (the false-open regression caught at review).

    ITERATIVE (NFA-style) matcher over (path_index, pattern_index) states — NOT recursive.
    A `**` previously recursed once per consumed segment, blowing Python's recursion limit
    (~1000) on a deep path and crashing the hook (caught in review). The worklist keeps a
    visited set so it is O(len(path) * len(pattern)) and cannot stack-overflow at any depth.
    """
    n, m = len(path_segs), len(pat_segs)
    # State = (i, j): path_segs[i:] still to match against pat_segs[j:].
    stack = [(0, 0)]
    seen = set()
    while stack:
        i, j = stack.pop()
        if (i, j) in seen:
            continue
        seen.add((i, j))
        if j == m:
            if i == n:
                return True
            continue  # pattern exhausted but path remains -> this branch fails
        head = pat_segs[j]
        if head == "**":
            # `**` consumes ONE OR MORE segments. So it requires >=1 remaining path segment,
            # then may consume just that one (advance both) or keep consuming (advance path
            # only). A trailing `**` (j == m-1) therefore needs >=1 remaining segment — so
            # `dir/**` matches a descendant, never the bare `dir` node; a leading `**/name`
            # matches name in any subdir but NOT at root (the bare INFRA pattern covers root).
            if i < n:
                stack.append((i + 1, j + 1))  # `**` ate exactly this segment
                stack.append((i + 1, j))      # `**` keeps eating
            continue
        # A literal segment pattern: needs a path segment that fnmatches it.
        if i < n and fnmatch.fnmatch(path_segs[i], head):
            stack.append((i + 1, j + 1))
    return False


def _matches_any(rel_path, globs):
    """Workspace-root-anchored glob match against the normalized relative path.

    Path-segment-aware (a `*` never crosses `/`). Conventions:
      * `dir/**`  — anything strictly UNDER `dir` (>=1 segment below). The bare `dir`
                    node is intentionally NOT matched: every real Bucket A write is to a
                    FILE inside its phase dir, and matching the bare single-segment path
                    would let a root file `phase2_x.md` masquerade as the `phase2_*` dir
                    (the false-open caught at review).
      * `**/name` — `name` in any subdirectory. For a file that may ALSO live at the
                    workspace root, the INFRA list carries both `**/name` and the bare
                    `name` (a deny-list, so widening is safe — see INFRA_PROTECTED_GLOBS).
    """
    # Patterns always use `/`. On Windows only, normalize the separator emitted by
    # os.path.relpath; on POSIX a backslash remains a legal filename character.
    if os.sep == "\\":
        rel_path = rel_path.replace("\\", "/")
    segs = [s for s in rel_path.split("/") if s not in ("", ".")]
    for g in globs:
        pat = [s for s in g.split("/") if s != ""]
        if _match_segments(segs, pat):
            return True
    return False


def _infra_protected_target(raw_path, cwd, plugin_root):
    """Return whether a target is ARS enforcement infrastructure.

    Infrastructure is anchored to the installed plugin root, not the user's project
    root. This protects the real extension/guard files without false-denying a user's
    unrelated file that happens to share a name such as ``extension.mjs``.
    """
    if not plugin_root:
        return False
    candidate = raw_path
    if not os.path.isabs(candidate):
        candidate = os.path.join(cwd, candidate)
    normalized = os.path.realpath(candidate)
    real_plugin = os.path.realpath(plugin_root)
    try:
        common = os.path.commonpath([normalized, real_plugin])
    except ValueError:
        return False
    if common != real_plugin:
        return False
    rel = os.path.relpath(normalized, real_plugin)
    if rel == ".":
        return False
    return _matches_any(rel, INFRA_PROTECTED_GLOBS)


def _allow_unconstrained(agent_type):
    """The decision for an actor that Slice 1 does not fence (main session / Bucket B/C/D).

    Single source for both the escaped-path allow (#302) and the Step-3 allow, so the two
    can't drift. A write tool firing with NO agent_type still surfaces a fail-loud advisory
    (spec §3.4) — do not silently no-op a possibly-regressed payload.
    """
    result = {"decision": "allow", "reason": ""}
    if not agent_type:
        result["absent_agent_type_advisory"] = True
    return result


def _normalize_tool_name(name):
    """Normalize tool name to lowercase for case-insensitive matching.

    Handles casing differences across platforms consistently.
    """
    return (name or "").strip().lower()


def _extract_structured_target(tool_input):
    """Single top-level target path for create/edit/write tools.

    Returns the path string, or None if absent (schema drift -> fail loud upstream).
    """
    if not isinstance(tool_input, dict):
        return None
    fp = tool_input.get("path")
    return fp if isinstance(fp, str) and fp else None


def evaluate_decision(payload, manifest, workspace_root, plugin_root=None):
    """Pure decision function implementing the spec §3.2 logic (Bash policy per §7).

    Returns a dict: {"decision": "allow"|"deny", "reason": str, ...advisory flags}.

    Two enforcement paths:
      * Structured tools (create/edit/write) — deterministic write-scope: normalize the
        single top-level target path FIRST, then infra self-protection, then Bucket A glob.
      * Bash — DENY ALL for a Bucket A agent. The agent uses the grep/glob tools for
        search and the structured tools for writes. Non-Bucket-A Bash passes through.
    """
    # The pure core defends itself too — not only main() — so a non-dict payload (`[]`,
    # null, a string) passed straight to evaluate_decision can't crash on `.get` (review).
    if not plugin_root:
        plugin_root = workspace_root
    if not isinstance(payload, dict):
        return {"decision": "allow", "reason": ""}
    tool_name = _normalize_tool_name(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):  # [] / null / str -> treat as empty (no crash)
        tool_input = {}
    cwd = payload.get("cwd") or workspace_root
    agent_type = payload.get("agent_type")
    agents = (manifest or {}).get("agents", {})
    is_bucket_a = bool(agent_type) and agent_type in agents

    # Tools we don't inspect (read, grep, web_fetch, ...) -> allow.
    if tool_name not in INSPECTED_TOOLS:
        return {"decision": "allow", "reason": ""}

    # --- Bash path: DENY ALL Bash for a Bucket A agent. Non-Bucket-A Bash passes through. ---
    if tool_name == "bash":
        if is_bucket_a:
            return {
                "decision": "deny",
                "reason": (f"ARS scope guard: {agent_type} (a single-phase agent) may not use "
                           "Bash. Use the grep/glob tools to search and the create/edit "
                           "tools to make file changes — those are scope-enforced deterministically. "
                           "Bash is denied wholesale because neither 'writes a file' nor 'is "
                           "read-only' is a property that can be decided reliably from a command "
                           "string (a tool can spawn a subprocess or be steered by an env var); "
                           "all-deny is the only policy that cannot fail open (spec §3.2/§3.3/§7)."),
                "bash_denied": True,
            }
        # Non-Bucket-A (main session / Bucket B/C/D) Bash -> pass through unconstrained.
        return {"decision": "allow", "reason": ""}

    # --- Structured tools: Step 1 extract + normalize the single top-level target path. ---
    raw = _extract_structured_target(tool_input)
    if raw is None:
        # Schema drift: a structured write tool with no target path. Do NOT
        # silently allow — fail loud (deny + advisory) so the guard cannot fail open.
        return {
            "decision": "deny",
            "reason": (f"ARS scope guard: {tool_name} payload carried no top-level "
                       "target path (unexpected schema) — denying to avoid silent "
                       "fail-open. Re-verify the tool_input shape."),
            "schema_drift_advisory": True,
        }
    # Step 2 is anchored to the ARS installation. It runs before workspace escape
    # handling because plugin files normally live outside the user's project root.
    if _infra_protected_target(raw, cwd, plugin_root):
        return {
            "decision": "deny",
            "reason": "ARS scope guard: target is part of the plugin enforcement "
                      "infrastructure and may not be written by any agent.",
        }

    rel, escaped = _normalize_target(raw, cwd, workspace_root)
    if escaped:
        # The escape / path-traversal deny is a BUCKET A FENCE, not a global one (#302).
        # Slice 1's stated scope (§3.3) is confining the 23 Bucket A single-phase agents to
        # their phase dir; the main session and Bucket B/C/D agents are unconstrained. A
        # main-session write to a sibling git worktree (a mainstream layout) resolves outside
        # the workspace root and MUST be allowed — fencing it here contradicted the Step-3
        # "unconstrained by Slice 1" gate below. So: only a Bucket A agent is denied for an
        # escape; a non-Bucket-A actor falls through to the Step-3 allow.
        #   Infra self-protection is intentionally NOT consulted on an escaped path: an escape
        # means the resolved real path is OUTSIDE the workspace, and every INFRA_PROTECTED_GLOB
        # is workspace-relative, so an escaped target can never be an infra target. (A symlink
        # that resolves back INTO the workspace yields escaped=False — see _normalize_target —
        # so infra protection still runs for it below.)
        if is_bucket_a:
            return {
                "decision": "deny",
                "reason": (f"ARS scope guard: {agent_type} write target {raw!r} escapes the "
                           "workspace root (path traversal) — denied."),
            }
        return _allow_unconstrained(agent_type)

    # --- Step 3: agent gating. ---
    if not is_bucket_a:
        # Main session or a Bucket B/C/D agent: unconstrained by Slice 1.
        return _allow_unconstrained(agent_type)

    # --- Step 4: Bucket A glob check (path already normalized in Step 1). ---
    allowed = agents[agent_type].get("allowed_write_globs", [])
    if not _matches_any(rel, allowed):
        return {
            "decision": "deny",
            "reason": (f"ARS scope guard: {agent_type} may not write {rel} "
                       f"(outside allowed_write_globs {allowed})."),
        }
    return {"decision": "allow", "reason": ""}


def render_output(decision):
    """Render the guard decision as Copilot-native stdout JSON.

    DENY -> {"blocked": true, "reason": "..."}
    ALLOW / pass-through -> {"blocked": false}
    """
    if decision.get("decision") == "deny":
        return json.dumps({
            "blocked": True,
            "reason": decision.get("reason", ""),
        })
    return json.dumps({"blocked": False})


def _load_manifest():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, MANIFEST_FILENAME)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed payload: do not block (avoid wedging the session); pass through.
        print(render_output({"decision": "allow", "reason": ""}))
        return 0

    # Valid JSON of the wrong SHAPE ([], null, a string) must not wedge the session either
    # — only a JSON object carries a tool call.
    if not isinstance(payload, dict):
        print(render_output({"decision": "allow", "reason": ""}))
        return 0

    # Hot-path early-exit: onPreToolUse fires on EVERY tool call (read, grep, web_fetch...),
    # not just writes. Bail before touching the manifest on disk for the common non-write
    # case.
    if _normalize_tool_name(payload.get("tool_name", "")) not in INSPECTED_TOOLS:
        print(render_output({"decision": "allow", "reason": ""}))
        return 0

    # Workspace root: prefer the payload cwd, else the process working directory.
    workspace_root = payload.get("cwd") or os.getcwd()

    try:
        manifest = _load_manifest()
    except (OSError, json.JSONDecodeError):
        # Manifest unreadable: fail loud to stderr (advisory) but do not wedge writes.
        sys.stderr.write("[ARS write-scope guard] manifest unreadable; passing through.\n")
        print(render_output({"decision": "allow", "reason": ""}))
        return 0

    # The extension supplies its resolved install root explicitly. The script-location
    # fallback keeps direct CLI tests and development invocations deterministic.
    plugin_root = payload.get("plugin_root") or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    decision = evaluate_decision(payload, manifest, workspace_root, plugin_root)

    # Surface fail-loud advisories to stderr (visible to the user/transcript), never silent.
    if decision.get("absent_agent_type_advisory"):
        sys.stderr.write("[ARS write-scope guard] write tool fired with no agent_type; "
                         "allowed (main session) but surfaced per no-silent-no-op rule.\n")
    if decision.get("schema_drift_advisory"):
        sys.stderr.write("[ARS write-scope guard] structured write tool lacked a top-level "
                         "target path; denied to avoid silent fail-open.\n")

    print(render_output(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
