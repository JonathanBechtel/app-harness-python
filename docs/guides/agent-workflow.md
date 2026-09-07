# Agent workflow

How a feature travels from idea to landed code with AI agents doing most of the typing and the harness doing the policing.

```
idea ─► /create-product-pitch ─► tech spec (docs/plans/) ─► /create-qa-checklist
     ─► /create-project (tickets with dependency metadata) ─► /orchestrate (parallel agents)
     ─► /ship (commit, PR, address CI + review, merge) ─► deploy workflows
```

- **Pitch** — the *why*: problem, audience, hypothesis, scope boundaries, success signal. Optional for mechanical work, required for anything novel.
- **Spec** — the *what*: data model deltas (checked against `docs/architecture/north-star.md` review questions), API surface, migration plan, observability, test plan.
- **QA checklist** — observable behaviours a human or the `verdict-qa` agent can refute.
- **Tickets** — one PR-sized unit each, classified agent-executable or not, with `depends-on`. Template: `.github/ISSUE_TEMPLATE/ticket.md`; per-repo overrides: `docs/plans/ai-orchestrator-ticket-spec.md`.
- **Orchestrate** — agents work tickets in dependency order in worktrees; every PR still passes the full CI gate — the harness is the trust boundary, not the agent.
- **Ship** — the PR skill; CI and bot review feedback are addressed within a fix budget, then squash-merge.

## Ground rules for agents

1. Read the nearest `CLAUDE.md` before editing. Run the Definition of Done before declaring done.
2. Plan when asked to plan; build when asked to build. Do not start editing on an "assess" request.
3. Escape hatches need reasons. Never bypass a hook.
4. Update the docs in the same PR (`/update-docs`).
5. When something cannot be verified in the current environment (no DB, no browser, no credentials), say so; do not report the step as passed.
6. Use the `verdict-qa` agent as a fresh-eyes gate on UI or user-visible changes; it tries to refute your claims from the evidence.

## Cloud / remote sessions

`python scripts/bootstrap_env.py` reaches CI parity on any box with Python 3.12 and Docker. What it cannot provide: provider credentials, deploy auth, a human to look at screenshots. Scope remote work to what is runnable.
