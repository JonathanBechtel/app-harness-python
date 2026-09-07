---
name: commit
description: Stage and commit the current work as one logical unit with a conventional commit message. Use when asked to commit, or after finishing a slice of work.
allowed-tools: Bash
---

# Commit

1. `git status` and `git diff` to see what changed; `git log --oneline -5` for message style.
2. Stage only the files that belong to this logical unit. Split unrelated changes into separate commits.
3. Run the smallest relevant verification for the slice (at minimum `make lint typecheck test.unit`). Hooks run on commit; if they fail, fix and commit again — never `--no-verify`.
4. Commit with a HEREDOC message:

```bash
git commit -m "$(cat <<'MSG'
<type>(<scope>): <imperative summary under 72 chars>

<why, not what — one short paragraph if the diff does not explain itself>
MSG
)"
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.

## Rules
- Authorship is the local git identity. Never add Co-Authored-By or any AI attribution.
- Never commit `.env`, credentials, or generated artifacts.
- Never amend a pushed commit; never force-push.
