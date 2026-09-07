# LLM features

The template ships plumbing, not product logic: `app/ai/registry.py` (role → provider/model from config), `app/ai/client.py` (the `ModelClient` seam and `FakeModelClient`), `app/ai/prompts/` (versioned prompt modules), and `evals/`.

## Rules

1. **Roles, not models.** Code calls `resolve("summarizer")`; configuration decides the provider and model (`AI_DEFAULT_*`, `AI_<ROLE>_*`). A literal model id anywhere else under `app/` fails `tests/unit/test_model_centralization.py`. Default: provider `anthropic`, model `claude-opus-5`; pin exact ids, never `-latest` or preview aliases.
2. **One seam.** Vendor SDK calls live in a `ModelClient` implementation only. Services receive a client (injected) so tests and evals can substitute `FakeModelClient` without credentials.
3. **Record every call.** Return a `CallRecord` (tokens in/out, cache reads, latency) and persist or log it; cost questions and incident triage read that, not vendor dashboards.
4. **Version prompts.** `app/ai/prompts/<family>/vN.py` with `VERSION`, `TEMPLATE`, `render()`. Bump when tools, output format, or response contract change; edit in place for wording. Pin with `PROMPT_<FAMILY>_VERSION`.
5. **No network inside a transaction.** Provider calls are network I/O; do them before `db.begin()`. The runtime guard raises outside prod.
6. **Evals before shipping a prompt or model change.** `make evals`; paste the score in the PR. Questions are stationary (absolute dates); ground truth comes from data, not from the model's narrative.

## Anthropic specifics (when the provider is Anthropic)

Use the official `anthropic` SDK inside the client implementation. Current-generation models take adaptive thinking (`thinking={"type": "adaptive"}`) and `output_config={"effort": ...}` rather than `budget_tokens`; stream anything with long input or output and read `get_final_message()`; check `stop_reason` (a `refusal` carries `stop_details`) before reading content; parse tool inputs with `json.loads`, never string matching; keep stable content (system prompt, tool list) first so prompt caching hits, and verify with `usage.cache_read_input_tokens`. Consult the `claude-api` skill or the official docs for the exact current surface before writing SDK code — the API changes faster than any doc in this repo.

## Adding an eval dataset

1. Pick the tool/endpoint and 5–8 dimensions worth measuring.
2. Write `evals/datasets/<name>.py`: `QUESTIONS` (stationary, grounded), `score(answer, expected)`.
3. Capture ground truth from the data source, not from a model run.
4. Add it to a suite with a weight; run 3 repetitions; commit the result JSON path in the PR description.
