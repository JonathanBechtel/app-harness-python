# System overview

<!-- template:placeholder -->
> **Template placeholder.** Replace this whole file with a description of the actual application: what it does, who uses it, the domain vocabulary, the external systems it talks to, its data model at a glance, and how requests and jobs flow through the packages in `app/`. Keep the diagram. Delete this note when done — `make lint.docs` fails while placeholders remain once real code exists.

## Purpose

_What problem this application solves and for whom._

## Shape

```
clients ──► app/api (+ app/web) ──► app/services ──► app/repositories ──► Postgres
                                          │
scheduler ─► app/cli.<job> ───────────────┘        app/ai (LLM roles) ─► provider
```

## Data model

_Canonical entities, what is evidence vs cache (north-star P2), key indexes._

## External systems

_Each integration, its adapter module, auth model, and failure behaviour._

## Runtime

_Deploy targets (see `deploy/README.md`), environments, scheduled jobs, observability entry points._
