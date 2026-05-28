#!/usr/bin/env bash
# setup-copilot-extension.sh — One-time ARS extension registration
# =============================================================================
# Registers the ARS extension for Copilot CLI slash commands & hooks.
# Idempotent — safe to run multiple times.
# Creates: ~/.copilot/extensions/ars/extension.mjs (symlink)
#           ~/.copilot/extensions/ars/.bootstrapped (marker)
# =============================================================================

set -euo pipefail

# Resolve script directory robustly (works even when sourced)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
EXT_DIR="${HOME}/.copilot/extensions/ars"
EXT_FILE="${PLUGIN_DIR}/extension.mjs"

# Validate that extension.mjs exists in the plugin directory
if [[ ! -f "$EXT_FILE" ]]; then
  echo "ERROR: extension.mjs not found at ${EXT_FILE}" >&2
  echo "Plugin directory structure may have changed. Expected: <plugin>/extension.mjs" >&2
  exit 1
fi

mkdir -p "$EXT_DIR"
ln -sf "$EXT_FILE" "${EXT_DIR}/extension.mjs"

# Marker file: suppresses repeated bootstrap prompts after setup is complete.
# ars-bootstrap checks for this file and exits silently when it exists.
touch "${EXT_DIR}/.bootstrapped"

echo "ARS extension registered at ${EXT_DIR}"
echo "→ Symlink: ${EXT_DIR}/extension.mjs → ${EXT_FILE}"
echo "Slash commands will be activated after extension reload"
