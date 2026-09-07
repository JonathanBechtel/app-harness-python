---
name: review
description: Read-only code review of uncommitted changes (or a commit range / files) for convention alignment against the nearest CLAUDE.md, simplicity, and redundancy with existing code. Use after significant implementation work or when asked to review.
allowed-tools: Bash, Read, Grep, Glob, Task
---

# Review

Scope: no args → `git diff` + `git diff --cached`; `--commit <ref|range>`; `--files <paths>`.

Spawn a read-only sub-agent with this brief:

> For each changed file (skip deletions), walk up the directory tree and read the nearest `CLAUDE.md`. Review for: (1) convention alignment with that file — layering, naming, typing, docstrings, transaction ownership; (2) simplicity — parallel abstractions, redundant logic, unnecessary indirection; (3) redundancy — does this duplicate something nearby that should be reused? (4) tests — do new tests assert behaviour (status codes, rows, payload shapes) rather than implementation? (5) docs — if a package, route, job, or convention changed, did its CLAUDE.md / docs change with it? Report grouped by file with line references. Do not modify files.

Present findings as discretionary items. Do not apply changes unless asked.
