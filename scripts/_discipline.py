"""The ``# discipline: <rule> <reason>`` waiver convention, defined once.

Every homegrown guard ships with an escape hatch, because a rule with no way out
gets bypassed wholesale the first time it is wrong. The reason is MANDATORY: a
bare marker is not a waiver. Exceptions are visible and argued in review rather
than silently accumulated. Third-party tools keep their own native ratchets
(ruff per-file-ignores, import-linter ignore_imports).
"""

from __future__ import annotations

import re
from functools import cache


@cache
def waiver_pattern(rule: str) -> re.Pattern[str]:
    """Compiled pattern for ``# discipline: <rule> <reason>``."""
    return re.compile(rf"#\s*discipline:\s*{re.escape(rule)}\b(?P<reason>.*)")


def line_has_reasoned_waiver(line: str, rule: str) -> bool:
    """True if ``line`` carries a waiver for ``rule`` with a non-empty reason."""
    match = waiver_pattern(rule).search(line)
    return bool(match and match.group("reason").strip())


def text_has_reasoned_waiver(text: str, rule: str) -> bool:
    """True if any line of ``text`` carries a justified waiver for ``rule``."""
    return any(line_has_reasoned_waiver(line, rule) for line in text.splitlines())


def statement_has_reasoned_waiver(lines: list[str], first: int, last: int, rule: str) -> bool:
    """Waiver on the statement's own lines or the contiguous comment block above it (1-indexed)."""
    for i in range(first, last + 1):
        if 1 <= i <= len(lines) and line_has_reasoned_waiver(lines[i - 1], rule):
            return True
    i = first - 1
    while 1 <= i <= len(lines) and lines[i - 1].strip().startswith("#"):
        if line_has_reasoned_waiver(lines[i - 1], rule):
            return True
        i -= 1
    return False
