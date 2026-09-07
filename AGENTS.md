# Agent instructions

**Read [`CLAUDE.md`](CLAUDE.md). It is the single source of project instructions for every agent runtime (Claude Code, Codex, Gemini, Cursor, and whatever comes next).**

This file is a pointer, not a copy. Two files obliged to say the same thing drift within a release cycle, and they drift on exactly the rules that were hardest won. An invariant maintained by hand, with no guard, is not an invariant; a pointer satisfies the parity requirement structurally because there is no second copy to keep in step. (`docs/decisions/0001-single-source-of-agent-instructions.md`)

Repo-local skills live in `.claude/skills/` and are exposed to other runtimes through symlinks in `.agents/skills/`.
