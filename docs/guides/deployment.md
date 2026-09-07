# Deployment

See `deploy/README.md` for the contract and per-target setup. This page is the operating procedure.

## Flow

1. Merge to `main` → **CI** (checks, tests, image build proof) → **Build image** publishes `sha-<12>` to GHCR (+ ACR when configured).
2. **Deploy (Azure Container Apps)** → pick `stage`; the workflow updates the revision and waits until `/health` reports the commit's `release_sha`.
3. Verify stage: `/health/db`, logs (JSON, filter by `request_id`), the e2e smoke against the stage URL if there is a UI.
4. **Deploy** → `prod` with the same tag. Never build a new image for prod; promote the tested one.
5. **Deploy (Databricks Apps)** ships the same commit from source when that target is in use.

## Migrations

Run at container start (`alembic upgrade head`) before uvicorn binds. Because migrations are lock-safe (concurrent indexes, `lock_timeout`, one transaction per revision), a contended migration fails the start quickly and the previous revision keeps serving. A failed start is a deploy problem, never a user-facing outage.

Breaking schema changes (drop/rename a column in use) are two deploys: expand, migrate data, then contract.

## Rollback

`az containerapp revision activate` the previous revision, or redeploy the previous `sha-` tag. Migrations are forward-only in production; write the compensating migration rather than downgrading.

## Drift

`deploy-freshness.yml` runs on weekday mornings when `DEPLOY_URL` is set and goes red if the deployment is more than 72 hours behind `main` or `/health/db` fails. It observes; it never deploys.

## Secrets

Platform secret stores only (ACA secrets / Databricks secret scopes). CI authenticates to Azure via OIDC; no cloud credentials live in GitHub secrets. Rotate anything that ever appears in a log or a ticket.
