# Receiving harness updates

The template is a living thing: guards get sharper, CI gets faster, agent docs get clearer. Projects created from it should receive those changes the way they receive dependency updates — as a reviewed pull request, not a manual diff. `.github/workflows/template-sync.yml` does that: every Monday (and on demand from the Actions tab) it merges the template's `main` into a branch and opens a PR labelled `harness-sync`.

## One-time setup in a new project

1. **Let Actions open PRs.** Repository → Settings → Actions → General → *Workflow permissions*: enable "Allow GitHub Actions to create and approve pull requests". Without it the sync run fails at the PR step.
2. **Optional but recommended: a token so CI runs on the sync PR.** GitHub does not trigger workflows on a PR opened with the default `GITHUB_TOKEN`. Add a fine-grained PAT (or GitHub App token) with `contents: write` and `pull-requests: write` on this repo as the secret `TEMPLATE_SYNC_TOKEN`; the workflow prefers it when present. Without it, push an empty commit to the sync branch (or close and reopen the PR) to start CI.
3. **Expect a large first PR.** A repository created with "Use this template" has no shared history with the template, so the first sync merges unrelated histories. Files already identical merge silently; anything the project renamed on day one (see `docs/guides/new-project-checklist.md`) shows as a conflict once, and the merge base is established from then on.

## What syncs and what does not

Everything is harness unless `.templatesyncignore` says otherwise. The ignore file lists what a project owns: its README and `CLAUDE.md`, product code under `app/`, migrations, budgets and baselines, ADRs and plans, `pyproject.toml`, and deploy config that names its resources. Infrastructure under `app/` that projects rarely touch (`observability/`, `utils/network_guard.py`, `cli/_runner.py`) is deliberately synced so fixes arrive; a project that has edited one of those sees a conflict, which is the right amount of friction.

To keep a harness file frozen for this project, add its path to `.templatesyncignore` in the same PR that diverges it, and say why in the commit body. Prefer a `# discipline: <rule> <reason>` waiver over freezing a guard.

## Reviewing a sync PR

1. Read the diff as you would a dependency bump: what changed in the guards, CI, hooks, docs?
2. Resolve conflicts by taking the template's side unless the local change was deliberate; when keeping both, make the guards agree (`make checks` will tell you).
3. Run the Definition of Done in `CLAUDE.md`. The sync is not trusted; the gate is.
4. If a new guard fails on existing code, baseline or waive with a reason in the same PR — never by weakening the guard.
5. Merge. The next sync starts from here.

## Keeping the siblings in step

This harness has a TypeScript sibling, [`app-harness-typescript`](https://github.com/JonathanBechtel/app-harness-typescript). The sync flows from each template to its own projects only; a change to one harness must be mirrored into the other by hand. When you change this template, ask whether the change is a Python detail or a harness property, and open the matching change in the sibling for the latter.
