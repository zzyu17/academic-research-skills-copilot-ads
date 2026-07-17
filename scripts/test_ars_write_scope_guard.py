"""Copilot-specific write-scope guard regression tests."""

from __future__ import annotations

import tempfile
import os
from pathlib import Path

import pytest

from scripts.ars_write_scope_guard import evaluate_decision, render_output


MANIFEST = {"agents": {}}
BUCKET_MANIFEST = {
    "agents": {
        "bibliography_agent": {
            "allowed_write_globs": ["phase2_*/**"],
        }
    }
}


def _payload(path: Path) -> dict:
    return {
        "tool_name": "edit",
        "tool_input": {"path": str(path)},
    }


def test_plugin_infrastructure_is_protected_outside_the_user_workspace() -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as plugin:
        target = Path(plugin) / "extension.mjs"
        decision = evaluate_decision(
            _payload(target), MANIFEST, workspace, plugin_root=plugin
        )
        assert decision["decision"] == "deny"
        assert "infrastructure" in decision["reason"]


def test_same_named_user_file_is_not_mistaken_for_plugin_infrastructure() -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as plugin:
        target = Path(workspace) / "extension.mjs"
        decision = evaluate_decision(
            _payload(target), MANIFEST, workspace, plugin_root=plugin
        )
        assert decision["decision"] == "allow"


def test_materialized_top_level_agent_mirror_is_protected() -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as plugin:
        target = Path(plugin) / "agents" / "synthesis_agent.md"
        decision = evaluate_decision(
            _payload(target), MANIFEST, workspace, plugin_root=plugin
        )
        assert decision["decision"] == "deny"


def test_copilot_tool_name_matching_is_case_insensitive() -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as plugin:
        payload = _payload(Path(plugin) / "package.json")
        payload["tool_name"] = "Edit"
        decision = evaluate_decision(payload, MANIFEST, workspace, plugin_root=plugin)
        assert decision["decision"] == "deny"


@pytest.mark.parametrize(
    "relative",
    [
        "extension.mjs",
        "package.json",
        "skills/ars-bootstrap/SKILL.md",
        "scripts/setup-copilot-extension.sh",
        "scripts/ars_write_scope_guard.py",
        "scripts/ars_phase_scope_manifest.json",
        "deep-research/agents/bibliography_agent.md",
        "agents/synthesis_agent.md",
    ],
)
def test_every_copilot_enforcement_surface_is_protected(relative: str) -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as plugin:
        target = Path(plugin) / relative
        decision = evaluate_decision(_payload(target), MANIFEST, workspace, plugin_root=plugin)
        assert decision["decision"] == "deny"


def test_relative_traversal_into_plugin_infrastructure_is_denied() -> None:
    with tempfile.TemporaryDirectory() as root:
        workspace = Path(root) / "workspace"
        plugin = Path(root) / "plugin"
        workspace.mkdir()
        plugin.mkdir()
        payload = {"tool_name": "edit", "tool_input": {"path": "../plugin/extension.mjs"}}
        decision = evaluate_decision(payload, MANIFEST, workspace, plugin_root=plugin)
        assert decision["decision"] == "deny"


def test_symlink_into_plugin_infrastructure_is_denied() -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as plugin:
        link = Path(workspace) / "linked-plugin"
        try:
            os.symlink(plugin, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"symlink unavailable: {exc}")
        decision = evaluate_decision(
            _payload(link / "extension.mjs"), MANIFEST, workspace, plugin_root=plugin
        )
        assert decision["decision"] == "deny"


def test_structured_write_without_path_fails_closed() -> None:
    decision = evaluate_decision(
        {"tool_name": "edit", "tool_input": {"old_string": "a"}},
        MANIFEST,
        "/work",
        plugin_root="/plugin",
    )
    assert decision["decision"] == "deny"
    assert decision["schema_drift_advisory"] is True


@pytest.mark.parametrize("payload", [None, [], "write"])
def test_non_object_payload_does_not_crash(payload) -> None:
    assert evaluate_decision(payload, MANIFEST, "/work", plugin_root="/plugin")["decision"] == "allow"


def test_uninspected_tool_passes_through() -> None:
    decision = evaluate_decision(
        {"tool_name": "grep", "tool_input": {"path": "/plugin/extension.mjs"}},
        MANIFEST,
        "/work",
        plugin_root="/plugin",
    )
    assert decision["decision"] == "allow"


def test_bucket_a_copilot_write_path_is_scope_checked() -> None:
    with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as plugin:
        allowed = Path(workspace) / "phase2_research" / "notes.md"
        denied = Path(workspace) / "phase3_writing" / "draft.md"
        allowed.parent.mkdir()
        denied.parent.mkdir()
        base = {"tool_name": "edit", "agent_type": "bibliography_agent"}
        allow_decision = evaluate_decision(
            {**base, "tool_input": {"path": str(allowed)}},
            BUCKET_MANIFEST,
            workspace,
            plugin_root=plugin,
        )
        deny_decision = evaluate_decision(
            {**base, "tool_input": {"path": str(denied)}},
            BUCKET_MANIFEST,
            workspace,
            plugin_root=plugin,
        )
        assert allow_decision["decision"] == "allow"
        assert deny_decision["decision"] == "deny"


def test_bucket_a_bash_is_denied_when_identity_is_available() -> None:
    decision = evaluate_decision(
        {
            "tool_name": "bash",
            "tool_input": {"command": "grep x paper.md"},
            "agent_type": "bibliography_agent",
        },
        BUCKET_MANIFEST,
        "/work",
        plugin_root="/plugin",
    )
    assert decision["decision"] == "deny"
    assert decision["bash_denied"] is True


def test_render_output_uses_copilot_blocked_contract() -> None:
    assert render_output({"decision": "allow", "reason": ""}) == '{"blocked": false}'
    assert render_output({"decision": "deny", "reason": "protected"}) == (
        '{"blocked": true, "reason": "protected"}'
    )
