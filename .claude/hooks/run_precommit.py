#!/usr/bin/env python3
"""Claude Code Stop hook: a turn may not end with the tree failing pre-commit.

Reads the hook payload on stdin. Exit 2 blocks the stop and feeds the output
back as instructions; exit 0 lets the turn end. Cross-platform (no shell).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    if payload.get("stop_hook_active"):
        return 0  # already retrying under this hook; do not loop
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False
    )
    if not dirty.stdout.strip():
        return 0  # nothing changed, nothing to check
    candidates = [
        root / ".venv" / ("Scripts/pre-commit.exe" if os.name == "nt" else "bin/pre-commit")
    ]
    exe = next((str(c) for c in candidates if c.exists()), shutil.which("pre-commit"))
    if not exe:
        print("pre-commit not installed; run python scripts/bootstrap_env.py", file=sys.stderr)
        return 0
    result = subprocess.run(
        [exe, "run", "--all-files"], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode == 0:
        return 0
    tail = "\n".join((result.stdout + result.stderr).splitlines()[-60:])
    print(
        "pre-commit failed. Fix these before finishing (CLAUDE.md Definition of Done):\n" + tail,
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
