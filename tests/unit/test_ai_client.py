"""The client seam records usage on every call."""

from __future__ import annotations

import pytest

from app.ai.client import FakeModelClient


@pytest.mark.asyncio
async def test_fake_client_records_calls() -> None:
    """FakeModelClient returns the responder's text and appends a CallRecord per call."""
    client = FakeModelClient(responder=lambda p: p.upper())
    result = await client.complete(role="summarizer", system="sys", prompt="hello")
    assert result.text == "HELLO"
    assert len(client.calls) == 1
    assert client.calls[0].role == "summarizer"
