# 0006 — One repo, one stack, every use case

**Status:** accepted · **Date:** 2026-09-07

## Context
Some internal apps are APIs, some have a UI, some call LLMs, some do all three. Separate templates per shape would fork the harness and drift.

## Decision
Every project starts from this single template with the full stack present: API, optional server-rendered web layer (`app/web`, Jinja + static, no build step), optional LLM plumbing (`app/ai`, `evals/`), runtime jobs (`app/cli`). Unused layers stay in place and cost nothing; they are not deleted from the template.

## Consequences
One set of guards, one CI, one deploy contract to maintain. A project that never adds a template route still carries `app/web`, which is a few files. A richer frontend (a bundler, a SPA) would be a superseding ADR, not an ad-hoc addition.
