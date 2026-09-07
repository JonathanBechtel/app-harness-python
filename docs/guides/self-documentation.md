# Self-documentation: keeping the agent docs true

The documentation in this repo is written for the next agent. Its value is entirely in being *accurate about this application*; a template description left in place is worse than no description because it is confidently wrong.

## What the harness does about it

`scripts/check_docs_freshness.py` (`make lint.docs`, pre-commit, CI) fails when:

- **D1** a package under `app/` has no `CLAUDE.md`, or `app/CLAUDE.md`'s table has no row for it;
- **D2** real application code exists (any module not in the template's own list) while `<!-- template:placeholder -->` markers remain in `CLAUDE.md` or `docs/architecture/overview.md`;
- **D3** `CLAUDE.md` names a task that `tasks.py` does not define, or a guard script is missing from the discipline catalog.

## What agents are asked to do

`CLAUDE.md` § "Your obligations to the next agent" states it; the `/update-docs` skill is the procedure. In short: docs change in the same PR as the code they describe; decisions get an ADR; `make lint.docs` before finishing.

## What humans should do

Treat a stale `CLAUDE.md` as a bug with the same priority as a failing test. In review, ask "would the next agent learn something wrong from the docs after this PR?" If yes, request the doc change before merge.

## Extending the template itself

If you improve the harness (a new guard, a new package in the skeleton), update `TEMPLATE_MODULES` in `scripts/check_docs_freshness.py` so the new skeleton module does not count as "real code" and prematurely trip D2 in fresh projects.
