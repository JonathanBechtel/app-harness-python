# 0004 — The container image is the deploy artifact

**Status:** accepted · **Date:** 2026-09-07

## Context
The organisation deploys to Azure Container Apps and Databricks Apps and wants interoperability across platforms. Predecessors deployed to Fly.io and Elastic Beanstalk with platform-specific pipelines that could not be reused.

## Decision
One `Dockerfile`, one image per commit tagged by sha, published once. Targets adapt to the image's contract (`$PORT`, env-only config, `/health` + `/health/db`, `release_sha`, migrations on start). Databricks Apps, which deploys from source, receives the same commit with requirements exported from `pyproject.toml` at deploy time.

## Consequences
Adding a target is a workflow file plus a README, not a new pipeline. Drift is measurable everywhere through `release_sha`. The Databricks adapter is source-based and must be kept in step with the image `CMD` (both are one line and live next to each other in `deploy/`).
