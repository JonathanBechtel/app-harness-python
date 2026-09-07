# app/ai — LLM plumbing (no product logic)

- Call sites name a **role**; `registry.resolve(role)` returns the (provider, model). Model ids live only in `app/config.py` and per-role env vars. A model id anywhere else under `app/` fails `tests/unit/test_model_centralization.py`.
- Every provider call goes through a `ModelClient` implementation (`client.py`); tests use `FakeModelClient`. Vendor SDK imports are confined to client implementations.
- Record a `CallRecord` (tokens, latency) for every call; that is what evals, cost tracking, and incident triage read.
- Prompts are versioned modules under `prompts/<family>/vN.py` with `VERSION`, `TEMPLATE`, `render()`; bump the version when the contract changes.
- Provider guidance (model choice, thinking, streaming, caching): `docs/guides/llm-features.md`.
