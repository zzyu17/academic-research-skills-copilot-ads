"""Copilot-specific write-scope guard regression tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from scripts.ars_write_scope_guard import evaluate_decision


MANIFEST = {"agents": {}}


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
