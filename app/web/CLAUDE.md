# app/web — optional server-rendered pages

Present in every project; used only by projects that need a UI. API-only services leave it alone (the placeholder `/` route is harmless) or delete `routes.py` and the `include_router` line in `app/main.py`.

- Jinja templates in `app/templates/`, extending `base.html`. Static assets in `app/static/`; **no build step**, plain CSS + vanilla JS.
- Shared UI primitives (buttons, cards, pagination) live once in `static/css/main.css`; page-specific styles in their own kebab-case file loaded via `{% block extra_css %}`. Extend a component with a modifier class rather than re-declaring it.
- `TemplateResponse` context must include `request` (route-conventions R4).
- Custom Jinja filters register in `templating.py` so tests rendering a partial see the same environment.
- Verify UI changes visually: `make test.e2e` drives a real browser against a running server and saves screenshots under `tests/e2e/screenshots/`; read them.
