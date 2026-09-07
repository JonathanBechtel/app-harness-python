# Evals

```bash
make evals SUITE=core          # runs evals/suites/core.py with the FakeModelClient responder
python -m evals.runner --suite core --repetitions 5 --responder app.some_module:responder
```

A responder is any `async def responder(question: str) -> str` importable as `module:attr`. The default uses `FakeModelClient` so the harness runs without credentials; a real project points it at its own entry point (e.g. the function behind the chat endpoint).

Results: `evals/results/<suite>-<timestamp>.json` with per-dataset accuracy, consistency, and gate verdicts. Compare runs over time rather than reading one in isolation.
