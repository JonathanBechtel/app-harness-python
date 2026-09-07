# app/observability — ops plane

Correlation context (`bind`, `bind_job_run`), JSON/console formatters, and secret scrubbing. Imports nothing from the rest of the app. Add a credential to `app/config.py` → add it to `SECRET_SETTING_FIELDS` in `scrubbing.py` (a test enforces this).
