"""Lint Copilot CommandDefinitions for /ars-mark-read and /ars-unmark-read.

Copilot CLI does not load ``commands/*.md``. The live command authority is
``extension.mjs``; this check pins the same v3.6.8 user-visible contract there.
"""

from __future__ import annotations

import sys
from pathlib import Path


COMMANDS = {
    "ars-mark-read": "ars_mark_read.py",
    "ars-unmark-read": "ars_unmark_read.py",
}
REQUIRED_TOKENS = ("literature_corpus", "human_read_log", 'modelRoutingHint("execution")')


def _definition_block(source: str, command: str) -> str | None:
    marker = f'name: "{command}"'
    start = source.find(marker)
    if start < 0:
        return None
    next_definition = source.find("\n    {\n      name:", start + len(marker))
    return source[start:] if next_definition < 0 else source[start:next_definition]


def check(root: Path) -> list[str]:
    extension = root / "extension.mjs"
    if not extension.is_file():
        return ["extension.mjs: missing Copilot command authority"]
    source = extension.read_text(encoding="utf-8")
    errors: list[str] = []
    for command, script in COMMANDS.items():
        block = _definition_block(source, command)
        if block is None:
            errors.append(f"extension.mjs: missing CommandDefinition {command!r}")
            continue
        for token in (*REQUIRED_TOKENS, script):
            if token not in block:
                errors.append(
                    f"extension.mjs: {command!r} missing required token {token!r}"
                )
    return errors


def main() -> int:
    errors = check(Path.cwd())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("[v3.6.8 mark-read commands lint] PASSED (2 Copilot definitions scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
