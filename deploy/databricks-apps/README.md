# Databricks Apps

Databricks Apps runs Python apps **from source**: it installs `requirements.txt` and runs the `command` in `app.yaml`, substituting `DATABRICKS_APP_PORT`. It does not consume the container image, so this adapter keeps parity a different way: CI ships the exact same commit, with `requirements.txt` exported from `pyproject.toml` at deploy time, and the same `alembic upgrade head && uvicorn ...` start sequence the image uses.

## Files

- `app.yaml` — the run command and non-secret env. Copied to the bundle root at deploy time.
- Secrets (`DATABASE_URL`, `SECRET_KEY`, provider keys) are declared in `app.yaml` with `valueFrom` pointing at Databricks secret scopes or app resources; never as literal values.

## Deploy

Actions → **Deploy (Databricks Apps)** → environment. Variables: `DATABRICKS_HOST`, `DATABRICKS_APP_NAME`, `DATABRICKS_WORKSPACE_PATH`; secret: `DATABRICKS_TOKEN` (a service principal token; swap for OIDC federation when the workspace supports it).

Manual equivalent from a checkout:

```bash
make requirements
databricks sync . /Workspace/Users/<you>/<app> --full
databricks apps deploy <app-name> --source-code-path /Workspace/Users/<you>/<app>
```

## Database

Lakebase (Databricks-managed Postgres) or Azure Database for PostgreSQL both work: the app only needs a `postgresql+asyncpg://` URL. Migrations run at start.

## Limits to know

Databricks Apps is Python-source only, single container, and the platform owns the process manager; `WEB_CONCURRENCY` is still honoured by uvicorn. Long-running scheduled work belongs in a Databricks Job invoking `python -m app.cli.<job>` from the same synced source.
