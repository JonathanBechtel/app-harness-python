"""The client seam: one protocol every LLM call goes through.

Provider SDK calls belong in a concrete implementation of ``ModelClient`` in
this module family, never in a service. Tests substitute ``FakeModelClient``;
nothing above this layer ever imports a vendor SDK, which is what keeps the
whole test suite runnable without credentials.

The template ships no vendor implementation on purpose (no application logic).
When adding one, follow docs/guides/llm-features.md: pin the model id in
config, prefer adaptive thinking and streaming for long outputs, record usage
(input/output/cache tokens) on every call via ``CallRecord``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class CallRecord:
    """Usage and identity of one model call, for cost attribution and evals."""

    role: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    latency_ms: int = 0


@dataclass(frozen=True)
class Completion:
    """The text a model returned plus the usage record behind it."""

    text: str
    record: CallRecord


class ModelClient(Protocol):
    """Minimal surface a provider adapter must implement."""

    async def complete(self, *, role: str, system: str, prompt: str) -> Completion:
        """Return the model's reply to ``prompt`` under ``system`` for ``role``."""
        ...


@dataclass
class FakeModelClient:
    """Deterministic stand-in for tests and evals: replies via ``responder``."""

    responder: Callable[[str], str] = lambda prompt: f"echo: {prompt}"
    calls: list[CallRecord] = field(default_factory=list)

    async def complete(self, *, role: str, system: str, prompt: str) -> Completion:
        """Produce a canned reply and record a zero-cost call."""
        text = self.responder(prompt)
        record = CallRecord(
            role=role,
            provider="fake",
            model="fake",
            input_tokens=len(prompt),
            output_tokens=len(text),
        )
        self.calls.append(record)
        return Completion(text=text, record=record)
