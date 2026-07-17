# ARS Update-and-Port Workflow

For ARS maintainers porting new `claude-code-main` releases into `copilot-main`.

---

## 1. Overview

The update-and-port workflow transfers features from the upstream Claude Code version of ARS
(`claude-code-main` branch) into the Copilot CLI adaptation (`copilot-main` branch).

**When to run:** After upstream `claude-code-main` releases a new version.

**Core principle:** Port by dependency-ordered subsystem with a three-way comparison,
not by blindly merging or replaying every upstream commit. Use
`claude-code-main-base` to distinguish upstream changes from Copilot adaptations. Portable
content follows upstream; divergent runtime and distribution surfaces are merged or adapted
explicitly. For a small release, feature-level checkout may still be the clearest execution
method, but it is not a requirement.

---

## 2. Pre-Flight

### 2.1 Branch state check

```bash
cd /home/zzyu/skills/academic-research-skills
git fetch --all
git checkout copilot-main
git status --porcelain | wc -l   # Expected: 0 (clean working tree)
```

Confirm all three branches exist and are in expected state:

```bash
git log --oneline -1 claude-code-main
git log --oneline -1 claude-code-main-base
git log --oneline -1 copilot-main
```

### 2.2 Verify merge base and compute diff

```bash
git merge-base claude-code-main claude-code-main-base
# Should match claude-code-main-base HEAD (the version last ported)

git diff --stat claude-code-main-base..claude-code-main
# Shows all new commits since the last port
git log --oneline claude-code-main-base..claude-code-main
```

### 2.3 Inventory new commits/features since last port

Scan the diff for new files, modified files, and deleted files:

```bash
git diff --name-status --diff-filter=A claude-code-main-base..claude-code-main  # Added
git diff --name-status --diff-filter=M claude-code-main-base..claude-code-main  # Modified
git diff --name-status --diff-filter=D claude-code-main-base..claude-code-main  # Deleted
```

Group changes into logical features. Each feature should map to a set of related file
changes with a clear purpose (e.g., "Citation Integrity System", "Firm Rules").

### 2.4 Tooling prerequisites

Required for every port:

| Tool | Purpose | Install |
|------|---------|---------|
| `python3` | Python syntax checks, schema validation | `command -v python3 && python3 --version` |
| `node` | `extension.mjs` syntax check | `node --version` |

Additional tools may be needed per-port (e.g., `jq` for jq filter validation in v3.11.1).
Determine from the feature inventory before starting execution.

---

## 3. Feature Classification

Classify every feature into one of the following three categories:

### 3.1 Directly portable ✅

Model-agnostic content with no Copilot-specific changes needed:
- Python scripts and linters
- JSON/YAML schemas and contracts
- Markdown documentation and reference files
- Agent prompt text (`.md` files under `*/agents/`)
- GitHub Actions workflows

### 3.2 Needs Copilot adaptation ⚠️

Portable content that requires Copilot-specific wiring:
- Routing references that point to `.claude/CLAUDE.md` → must revert to `skills/ars-bootstrap/SKILL.md`
- Claude Code hook patterns → must rewire in `extension.mjs` hook handlers
- New slash commands added in Claude Code version (`commands/*.md`) → must add CommandDefinitions in `extension.mjs`

### 3.3 Skipped or behavior-mapped ❌ / ⚠️

Claude Code-only infrastructure with no Copilot equivalent:
- `scripts/announce-ars-loaded.sh` — do not copy the shell hook; map user-relevant bootstrap
  content to `ars-bootstrap` / `onSessionStart`
- Claude Code hook configuration — do not copy `hooks/hooks.json`; map applicable behavior
  to `extension.mjs` and document any Copilot interface gap
- `.claude/` directory files — do not copy as runtime infrastructure; map current routing,
  version, and CI authority to the bootstrap

### 3.4 Output: Feature mapping table

Produce a table like:

| # | Feature | Version | Portability | Notes |
|---|---------|---------|-------------|-------|
| F1 | Feature name | vX.Y.Z | ✅ / ⚠️ / ❌ | Adaptation detail if ⚠️ |

---

## 4. Design & Planning

### 4.1 Write design spec

Save under `docs/superpowers/specs/YYYY-MM-DD-ars-vX.Y.Z-copilot-port-design.md`.

Must include:
- Summary (versions, merge base, strategy)
- Feature inventory table (§3.4 above)
- Copilot-specific adaptation points with affected files
- Phased execution plan overview
- File preservation rules
- Risk assessment

### 4.2 Write implementation plan

Save under `docs/superpowers/plans/YYYY-MM-DD-ars-vX.Y.Z-copilot-port-plan.md`.

Must include:
- Goal and architecture summary
- Pre-flight setup steps
- Per-task breakdown: exact files, exact commands, expected output
- Verification gate per phase
- Post-port checklist

### 4.3 Define adaptation points — WITH ISOLATED SPECS

**CRITICAL — Each ⚠️ adaptation point must have an isolated, comprehensive adaptation spec before any code is touched.**

#### 4.3.1 Adaptation spec template

For each ⚠️ feature, create a spec covering these sections **before touching any code**:

**A. Claude Code behavior — thorough inspection**
- Read every source file the feature touches (hook config, Python scripts, manifests, agent prompts)
- Trace the full execution flow: what triggers it, what data flows in, what decisions are made, what output is produced
- Identify ALL Claude-specific conventions embedded in the feature (env vars like `CLAUDE_PROJECT_DIR`, paths like `.claude/CLAUDE.md`, tool names like `Write`/`MultiEdit`, payload fields like `file_path`, output formats like `hookSpecificOutput`)

**B. Copilot CLI interface — 1:1 mapping**
- For each Claude interface, find the exact Copilot equivalent (e.g., `PreToolUse` hook → `onPreToolUse` hook)
- Map every Claude-specific field to its Copilot counterpart using the installed Copilot SDK
  types or current official interface (e.g., `tool_name` → `toolName`; current
  `PreToolUseHookInput.cwd` remains `cwd`, not `workingDirectory`)
- Document any fields that have NO Copilot equivalent (e.g., `agent_type` in hook inputs) — these are gaps

**C. Adaptation strategy — concrete changes**
- List every file that needs modification with the exact changes
- For each change, specify: which lines, what old content, what new content
- If a Python script needs changes, specify: new functions, modified functions, changed constants, updated docstrings
- If `extension.mjs` needs changes, specify: which hook, input/output mapping, payload construction

**D. Purge checklist**
- List every Claude-specific string that must be removed from the live Copilot execution
  path: tool names (`MultiEdit`), env vars (`CLAUDE_PROJECT_DIR`), hook paths
  (`hooks/hooks.json`), and output wrappers (`hookSpecificOutput`). Do not mechanically purge
  packaging files such as `.claude-plugin/` when the Copilot marketplace still consumes them.
- After execution, grep for each string to confirm zero remain

**E. Verification plan**
- Smoke tests for the adaptation: what payloads to test, what expected output
- Cross-check lints that must still pass
- Syntax checks (`python3 -c "import ast; ..."`, `node --check extension.mjs`)

#### 4.3.2 Adaptation spec location

Save under `docs/superpowers/specs/YYYY-MM-DD-ars-vX.Y.Z-copilot-port-design.md` as a sub-section of the design spec, or as a standalone companion file referenced from the design spec.

#### 4.3.3 Mandatory pre-execution gate

Before starting any ⚠️ feature port, verify the adaptation spec is complete:
- [ ] Claude Code behavior fully traced (all source files read)
- [ ] 1:1 interface mapping complete (no "assumed equivalent" fields)
- [ ] Adaptation strategy concrete (line-level changes specified)
- [ ] Purge checklist exhaustive (every Claude string catalogued)
- [ ] Verification plan ready (smoke tests defined)

---

## 5. Phased Execution

### 5.1 Phase ordering principle

Phases must be dependency-ordered:
1. **Foundation** — features with no dependencies on other new features
2. **Domain features** — grouped by subsystem (e.g., citation, cross-model, tooling, etc.)
3. **Content/agent updates** — prompt text and `SKILL.md` bumps (may depend on feature files)
4. **Copilot finalization** — `extension.mjs` updates, bootstrap trigger expansion, final verification

### 5.2 Per-phase pattern

Each phase follows the same pattern:

1. **Mark the phase in progress in the active task plan.**

2. **Port new files:**
   ```bash
   git checkout claude-code-main -- <file1> <file2> ...
   ```

3. **Port modified files:**
   ```bash
   git checkout claude-code-main -- <file1> <file2> ...
   ```

4. **Apply Copilot-specific adaptations inline** (e.g., routing fixes, hook wiring, etc.)

5. **Run verification gate** (see §6.1)

6. **Mark phase done and commit it automatically after its verification gate:**
   ```
   Copilot: port v<version> - phase <N>

   <phase summary line — lowercase, ~1 line describing features ported>
   ```

   Do not add `Co-authored-by`, generator, or AI attribution trailers. Continue directly to
   the next approved phase without asking for per-phase approval. Ask the user for inspection
   and approval only after all execution phases and final verification are complete.

This automatic-commit policy applies only after the maintainer has approved the port plan.
It does not authorize pushing, tagging, advancing `claude-code-main-base`, rebasing a sibling
branch, or publishing a release.

### 5.3 File porting methods

Do not limit the transfer to `git diff claude-code-main-base..claude-code-main` paths.
That delta omits files which upstream left unchanged but a previous Copilot port deleted or
adapted. For each portable subsystem, also compare the complete current source tree against
`copilot-main` and restore every upstream-tracked file unless it is an explicit platform
exception. Use null-delimited path handling when filenames may contain non-ASCII characters.

```bash
git ls-tree -rz --name-only claude-code-main <portable-roots...> \
  | rg --null-data -v '<exact-platform-exclusion-regex>' \
  | xargs -0 -r git checkout claude-code-main --
```

**New files** (added in `claude-code-main`, don't exist in `copilot-main`):
```bash
git checkout claude-code-main -- path/to/new/file
```

**Modified files** (exist in both branches, `claude-code-main` has updates):
```bash
git checkout claude-code-main -- path/to/modified/file
```

**Copilot-only files must NOT be bulk-checked-out.** These are edited inline with
surgical edits:
- `extension.mjs`
- `skills/ars-bootstrap/SKILL.md`
- `scripts/setup-copilot-extension.sh`
- `package.json`

**Claude Code-inert files** (`.claude/`, `commands/`, `hooks/`) are not copied as runtime
infrastructure. Their behavior must still be inventoried: relevant routing, commands, guards,
and CI assertions are mapped to `ars-bootstrap` and `extension.mjs`; truly Claude-only pieces
are documented as skipped.

---

## 6. Verification Gates

### 6.0 Adapt live-authority lints before using them as gates

Do not interpret a Claude-layout failure as a product-runtime failure. At the start of every
port, search current and incoming checks for assumptions about `.claude/CLAUDE.md`,
`commands/`, `hooks/hooks.json`, or the announce script. In the Copilot branch:

- version/routing checks validate `skills/ars-bootstrap/SKILL.md`;
- command checks validate the `CommandDefinition` inventory and dispatch prompts in
  `extension.mjs`;
- hook checks validate `onSessionStart` / `onPreToolUse` wiring in `extension.mjs`;
- release-tag checks accept the `vX.Y.Z-copilot` convention.

Until those checks are adapted in the runtime/finalization phase, record their failures as
explicitly deferred and exclude only those named tests from earlier phase gates. Never weaken
the final gate: the adapted tests must pass before the completed port is presented.

### 6.1 Per-phase

Minimum checks after each phase:

```bash
# Python syntax (all new/modified .py files in scripts/)
python3 -c "import ast; ast.parse(open('<file>').read())"

# JSON schema validity (all new/modified .json files in shared/contracts/)
python3 -c "import json; json.load(open('<file>'))"

# extension.mjs syntax (if modified)
node --check extension.mjs

# Additional per-port tools (e.g., jq filter syntax)
jq -n -f scripts/cross_model_verification/<filter>.jq > /dev/null
```

### 6.2 Cross-phase

After all feature phases but before Copilot finalization:

```bash
# All agents in sync with claude-code-main
for f in $(find skills -path '*/agents/*.md' ! -path '*/docs/*' | sort); do
  if ! git diff --quiet claude-code-main -- "$f" 2>/dev/null; then
    echo "DRIFT: $f"
  fi
done
# Expected: no output (zero drift)
```

### 6.3 Final

After all phases complete:

```bash
# No newly-introduced Claude/Claude Code/CLAUDE.md refs in SKILL.md or docs
# Pre-existing refs that were already in copilot-main before this port are acceptable
grep -rn 'CLAUDE\.md\|Claude Code' skills/*/SKILL.md docs/*.md QUICKSTART.md README*.md

# All Claude Code version slash commands ported to extension.mjs
# Compare the upstream command filenames with extension definitions
git ls-tree -r --name-only claude-code-main commands/ | sed 's|commands/||; s|\.md$||' | sort
grep -o 'name: "ars-[^"]*"' extension.mjs | sed 's/name: "//; s/"//' | sort
grep -c "name: \"ars-" extension.mjs                 # should be >= N

# All copilot-specific files present
test -f extension.mjs
test -f skills/ars-bootstrap/SKILL.md
test -f scripts/setup-copilot-extension.sh
test -f package.json

# All Python files parse
find scripts -name '*.py' ! -path '*/tests/*' -exec python3 -c \
  "import ast; ast.parse(open('{}').read())" \;

# All JSON schemas load
find shared/contracts -name '*.json' -exec python3 -c \
  "import json; json.load(open('{}'))" \;
```

---

## 7. Post-Port

### 7.1 Run test

Run all tests in `scripts/tests/` and ensure they pass without errors.
```bash
python3 -m pytest scripts/
```

### 7.2 Bump distribution version

After all feature phases are committed, bump the version in every
distribution-identifying file from the previous port version to the new
source version (e.g., `3.9.4.2` → `3.11.1`).

#### 7.2.1 Discover and bump current version surfaces

Do not rely on a historical fixed file count. First discover every live distribution surface,
including newly added translations:

```bash
rg -l 'v?<old-version>|releases/tag/v<old-version>' \
  package.json .claude-plugin skills/ars-bootstrap README* MODE_REGISTRY.md \
  docs/ARCHITECTURE.md CITATION.cff
```

Classify matches as current markers or historical examples before editing. The common current
patterns are:

**Pattern 1 — JSON version fields:**

```bash
NEW="3.17.0"  # replace with actual new version

for f in package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json; do
  sed -i 's|"version": "[0-9.]*"|"version": "'"$NEW"'"|' "$f"
done
```

**Pattern 2 — README badges and current references (all present translations):**

```bash
OLD_SHORT="3.9.4.2"  # replace with actual old version
for f in README.md README.zh-CN.md README.zh-TW.md README.ja-JP.md README.ko-KR.md; do
  sed -i "s|version-v${OLD_SHORT}-blue|version-v${NEW}-blue|g" "$f"
  sed -i "s|releases/tag/v${OLD_SHORT}|releases/tag/v${NEW}|g" "$f"
  sed -i "s|\`academic-pipeline\` v${OLD_SHORT}|\`academic-pipeline\` v${NEW}|g" "$f"
  sed -i "s|v[0-9.]* – v${OLD_SHORT}|v[0-9.]* – v${NEW}|g" "$f"
done
```

**Pattern 3 — ars-bootstrap SKILL.md (1 file):**

```bash
sed -i "s|v${OLD_SHORT}|v${NEW}|g" skills/ars-bootstrap/SKILL.md
# Then fix the suite version suffix:
sed -i "s|Suite version\*\*: ${NEW}|**Suite version**: ${NEW}-copilot|" skills/ars-bootstrap/SKILL.md
```

**Pattern 4 — MODE_REGISTRY.md (1 file):**

```bash
TODAY=$(date +%F)
sed -i "s|Last updated: v${OLD_SHORT} (.*)|Last updated: v${NEW} (${TODAY})|" MODE_REGISTRY.md
```

Copilot release links and tags use `v${NEW}-copilot`, not the upstream plain tag. Preserve
plain `v${NEW}` only where a source/upstream version is intentionally named.

#### 7.2.2 Verify

```bash
# All distribution files must be clean
for f in package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json \
         README.md README.zh-CN.md README.zh-TW.md README.ja-JP.md README.ko-KR.md \
         skills/ars-bootstrap/SKILL.md MODE_REGISTRY.md; do
  grep -q "$OLD_SHORT" "$f" && echo "STALE: $f still has $OLD_SHORT" || true
done
# Expected: no output
```

#### 7.2.3 Files NOT bumped

These contain historical references to the old version in changelogs, design docs,
test fixtures, or CI comments — they are intentionally preserved:

- `CHANGELOG.md` — historical release entries
- `docs/design/` — historical design documents
- `docs/ARCHITECTURE.md` — version history table
- `docs/UPDATE-AND-PORT-WORKFLOW.md` — past ports log
- `scripts/check_spec_consistency.py` — lint expects specific changelog headers
- `scripts/test_check_*.py` — test fixtures use old version as example data
- `.github/workflows/` — inline comments referencing past commits

### 7.3 Sync documentation translations

If documentation files with translated versions were modified, ensure their translations are updated as well. These include:
- `REAMDE.md` → `README.zh-CN.md`, `README.zh-TW.md`, `README.ja-JP.md`
- `docs/PERFORMANCE.md` → `docs/PERFORMANCE.zh-TW.md`
- `docs/SETUP.md` → `docs/SETUP.zh-TW.md`

### 7.4 Update `claude-code-main-base` (separate authorization required)

After all phases are committed and reviewed, the maintainer may separately authorize
advancing the reference branch so the next port starts from the current
`claude-code-main` HEAD. Port-plan approval alone does not authorize this mutation.

```bash
git checkout claude-code-main-base
git merge --ff-only claude-code-main
git checkout copilot-main
```

After this, `git merge-base claude-code-main claude-code-main-base` will return the new
HEAD, and `git diff claude-code-main-base..claude-code-main` will be empty until the
next upstream release.

### 7.5 Update `copilot-ads` branch (separate authorization required)

The `copilot-ads` branch is the ADS (Astrophysics Data System) Edition of Copilot ARS.
It carries the same Copilot port as `copilot-main` plus native SAO/NASA ADS integration.
After each update-and-port, it can be rebased onto the updated `copilot-main` to keep
the two branches in sync, but only after the maintainer separately authorizes the rebase.

```bash
# Step 1: Rebase copilot-ads onto the updated copilot-main
git checkout copilot-ads
git rebase copilot-main

# Step 2: Verify copilot-ads version fields match copilot-main
git diff copilot-main..copilot-ads -- \
  package.json \
  .claude-plugin/plugin.json \
  .claude-plugin/marketplace.json \
  skills/ars-bootstrap/SKILL.md \
  MODE_REGISTRY.md

# If the diff shows only ADS-specific additions, the rebase is clean.
# If version fields are stale (e.g., copilot-ads still shows an old version),
# bump them to match copilot-main using the same commands as §7.2.

# Step 3: Return to copilot-main
git checkout copilot-main
```

The rebase should be a clean fast-forward of ADS-specific commits on top of
`copilot-main`. If conflicts arise:
- **Conflict in distribution-identifying files** (e.g., `package.json`): Accept
  `copilot-main`'s version, then re-apply any ADS-specific metadata additions.
- **Conflict in source files**: Re-apply ADS changes on top of the updated base,
  preserving both the upstream port and the ADS integration.

### 7.6 User-managed

- Review full diff: `git diff <last-commit-before-port>..HEAD`
- Commit remaining changes if any
- Test plugin update: `/plugin update academic-research-skills@academic-research-skills` then `/restart`
- Verify all slash commands appear
- Trigger ARS via natural language to verify skill dispatch
- Run a full pipeline smoke test with a simple research topic

### 7.7 Out of scope

- **Plugin Test execution** — user will run plugin test in a separate session
- **Plugin marketplace publishing** — user will handle the plugin distribution

---

## 8. Adaptation Point Patterns

These patterns recur across port cycles. Not every port uses all of them, but every
port should check for them.

**REMEMBER:** Before executing any of these patterns, complete the isolated adaptation
spec per §4.3. The spec must trace the full Claude Code behavior, map every interface
1:1 to Copilot CLI, catalogue every Claude-specific string for purging, and define
smoke tests. Do not touch code until the spec is complete.

### 8.1 Routing Reference Reversal

**Problem:** Claude Code routes skill dispatch through `.claude/CLAUDE.md`. Copilot
CLI routes through `skills/ars-bootstrap/SKILL.md`. When `claude-code-main` introduces
or updates routing references, they must be reverted in `copilot-main`.

**Fix:** After porting `SKILL.md` files from `claude-code-main`, run:

```bash
for f in academic-paper/SKILL.md academic-paper-reviewer/SKILL.md \
         academic-pipeline/SKILL.md deep-research/SKILL.md; do
  sed -i 's|\.claude/CLAUDE\.md|skills/ars-bootstrap/SKILL.md|g' "$f"
  sed -i 's|Claude Code session|Copilot CLI session|g' "$f"
done
```

**Verify:**

```bash
# No newly-introduced Claude Code refs (pre-existing copilot-main refs are OK)
grep -rn 'CLAUDE\.md' skills/*/SKILL.md
```

### 8.2 Extension Hook Wiring

**Problem:** Claude Code uses `hooks/hooks.json` with specific events (e.g., `PreToolUse`).
Copilot CLI uses `extension.mjs` with equivalent lifecycle hooks (e.g., `onPreToolUse`).
New Claude Code hooks need Copilot equivalents.

**Fix:** Port the underlying logic (Python scripts, guard rules) as-is, then wire them
into the appropriate `extension.mjs` hook handler per the adaptation spec.

### 8.3 Copilot-Specific File Preservation

These files exist only in `copilot-main` and must never be overwritten by a bulk
`git checkout claude-code-main --`:

| File | Purpose | How to modify |
|------|---------|---------------|
| `extension.mjs` | Slash commands + lifecycle hooks | Edit inline |
| `skills/ars-bootstrap/SKILL.md` | Self-bootstrapping entry point | Edit inline |
| `scripts/setup-copilot-extension.sh` | One-time extension registration | Edit inline |
| `package.json` | Copilot CLI `"type": "module"` | Edit inline |

---

## 9. Past Ports Log

| # | Source Version | Target Branch | Merge Base Start | Merge Base End | Phases | Features Ported |
|---|---------------|---------------|------------------|----------------|--------|-----------------|
| 1 | v3.9.4.2 | copilot-main | — (initial) | — | — | Initial Copilot CLI port |
| 2 | v3.11.1 | copilot-main | `121f904` | `7e124c7` | 6 phases | 20 of 21 (1 skipped: `announce-ars-loaded.sh`) |
