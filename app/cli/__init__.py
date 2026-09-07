"""Shipped runtime jobs: entrypoints that run INSIDE the deployed image.

Invoked as ``python -m app.cli.<module>`` by a scheduler (Azure Container Apps
jobs, a Databricks job, cron). Operator tooling that runs from a checkout lives
in ``scripts/`` instead; ``scripts/check_runtime_entrypoints.py`` enforces the
split. Wrap every job in ``run_job`` so it is logged and correlated like a request.
"""
