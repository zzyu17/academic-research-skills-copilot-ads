"""Mutation tests for the Copilot mark/unmark CommandDefinition lint."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from tests.test_helpers import run_script


LINT = Path(__file__).parent / "check_v3_6_8_mark_read_commands.py"
REPO_ROOT = Path(__file__).parent.parent


def _fixture() -> tuple[TemporaryDirectory, Path]:
    temp = TemporaryDirectory()
    root = Path(temp.name)
    (root / "extension.mjs").write_text(
        (REPO_ROOT / "extension.mjs").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return temp, root


def _mutate(root: Path, old: str, new: str = "removed") -> None:
    path = root / "extension.mjs"
    source = path.read_text(encoding="utf-8")
    assert old in source
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def test_real_repo_passes() -> None:
    result = run_script(LINT, cwd=REPO_ROOT)
    assert result.returncode == 0, result.stderr


def test_missing_definition_fails() -> None:
    temp, root = _fixture()
    with temp:
        _mutate(root, 'name: "ars-mark-read"')
        result = run_script(LINT, cwd=root)
        assert result.returncode == 1
        assert "ars-mark-read" in result.stderr


def test_missing_validation_contract_fails() -> None:
    temp, root = _fixture()
    with temp:
        _mutate(root, "literature_corpus[]")
        result = run_script(LINT, cwd=root)
        assert result.returncode == 1
        assert "literature_corpus" in result.stderr


def test_missing_peer_file_contract_fails() -> None:
    temp, root = _fixture()
    with temp:
        _mutate(root, "human_read_log.yaml")
        result = run_script(LINT, cwd=root)
        assert result.returncode == 1
        assert "human_read_log" in result.stderr


def test_missing_execution_tier_routing_fails() -> None:
    temp, root = _fixture()
    with temp:
        _mutate(root, 'modelRoutingHint("execution")')
        result = run_script(LINT, cwd=root)
        assert result.returncode == 1
        assert "modelRoutingHint" in result.stderr
