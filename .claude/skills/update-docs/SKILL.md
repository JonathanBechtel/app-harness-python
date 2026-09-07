---
name: update-docs
description: Bring the agent documentation (CLAUDE.md, per-package CLAUDE.md, docs/architecture/overview.md, .env.example) back in line with what the application actually does. Use after adding a package, route, job, integration, or convention, when `make lint.docs` fails, or when starting a new project from this template.
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Update the docs to match the code

The docs are for the NEXT agent. They must describe this application, not the template it came from. Procedure:

1. Run `make lint.docs`. Fix every D1/D2/D3 finding it reports.
2. Read `CLAUDE.md`. For every section marked `<!-- template:placeholder -->`, replace the placeholder text with the truth about this app (purpose, users, domain vocabulary, external systems, deploy targets), then delete the marker. Do the same in `docs/architecture/overview.md`.
3. For every package under `app/`, read its `CLAUDE.md` and compare with the code: new modules, changed conventions, retired patterns. Update it; keep it short and imperative.
4. Compare `app/config.py` with `.env.example`; document every setting.
5. If a design decision was made (a library chosen, a boundary drawn, a convention adopted), add `docs/decisions/NNNN-<slug>.md` from `docs/decisions/template.md`.
6. If the Definition of Done changed (new check, new make target), update CLAUDE.md and `tasks.py` together.
7. Run `make lint.docs` again and `make checks`; commit docs with the code change they describe, not separately.
