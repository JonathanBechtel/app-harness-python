# app/cli — runtime jobs

- Entry point shape: `async def main() -> int` + `run_job("name", main)` from `_runner.py`. Exit code is the outcome.
- Invoked as `python -m app.cli.<module>` from a scheduler; never reference `scripts/`.
- Shared logic lives in `services/`, imported by both jobs and routes.
- Anything a human runs from a checkout (backfills, audits, one-off fixes) is a `scripts/` script, not a job.
