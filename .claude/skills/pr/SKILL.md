---
name: pr
description: Push the branch and open a pull request against main with gh. Use after committing when the work is ready for review.
allowed-tools: Bash
---

# Pull request

1. Confirm the tree is clean (`git status`) and the Definition of Done in CLAUDE.md has been run.
2. `git push -u origin HEAD` if the branch has no upstream.
3. `git log main..HEAD --oneline` and `git diff main...HEAD --stat` for scope.
4. Open the PR:

```bash
gh pr create --title "<imperative, under 72 chars>" --body "$(cat <<'MSG'
## Summary
- <what and why, 1-3 bullets>

## Verification
- [ ] `make checks` clean
- [ ] tests added/updated: <which>
- [ ] docs updated (CLAUDE.md / package CLAUDE.md / docs/) if behaviour or structure changed

## Risk
<what could break, how to roll back>
MSG
)"
```

Branch names: `feature/`, `fix/`, `bug/`, `refactor/`, `enhancement/`, `docs/` + short kebab-case description. No agent names, dates, or ticket metadata.
