"""How cache_prefix reaches the model.

cache_prefix is a guaranteed-delivered input: a cache_control block on models
that declare supports_prompt_caching, prepended text on everything else. It
is never dropped -- it used to be, on every non-Claude model, which is how
asvs_audit ran its HEAVY analysis with no system prompt on self-hosted models.

Callers pass the stable text ONLY as cache_prefix and keep only the variable
text in the message. The prepend path guards against a caller that inlines it
too; the cache-block path does not, and would send it twice. The ASVS agents
are written to that contract, so it is pinned here.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from services import llm_service

pytestmark = pytest.mark.unit

PREFIX = "STABLE SYSTEM PROMPT AND INVENTORY"


class TestPrependPath:
    P = staticmethod(llm_service._prepend_prefix_to_message)

    def test_prefix_leads_joined_by_blank_line(self):
        out = self.P([{"role": "user", "content": "FILES"}], PREFIX)
        assert out[0]["content"] == f"{PREFIX}\n\nFILES"

    def test_prefix_leads_so_vllm_can_prefix_match(self):
        a = self.P([{"role": "user", "content": "batch one"}], PREFIX)[0]["content"]
        b = self.P([{"role": "user", "content": "batch two"}], PREFIX)[0]["content"]
        assert a.startswith(PREFIX) and b.startswith(PREFIX)

    def test_guard_does_not_double_an_inlined_prefix(self):
        msg = f"{PREFIX}\n\nFILES"
        out = self.P([{"role": "user", "content": msg}], PREFIX)
        assert out[0]["content"] == msg

    def test_block_content_gets_a_leading_text_block(self):
        out = self.P([{"role": "user", "content": [{"type": "text", "text": "FILES"}]}], PREFIX)
        assert out[0]["content"][0] == {"type": "text", "text": PREFIX}

    def test_empty_messages(self):
        assert self.P([], PREFIX) == [{"role": "user", "content": PREFIX}]

    def test_caller_list_is_not_mutated(self):
        msgs = [{"role": "user", "content": "FILES"}]
        self.P(msgs, PREFIX)
        assert msgs == [{"role": "user", "content": "FILES"}]


class TestCacheBlockPath:
    I = staticmethod(llm_service._inject_cache_prefix)

    def test_prefix_is_a_marked_first_block(self):
        out = self.I([{"role": "user", "content": "FILES"}], PREFIX)
        first, second = out[0]["content"]
        assert first == {"type": "text", "text": PREFIX, "cache_control": {"type": "ephemeral"}}
        assert second == {"type": "text", "text": "FILES"}

    def test_marker_carries_no_ttl(self):
        """Bedrock rejects ttl (litellm #17250 / #15880)."""
        block = self.I([{"role": "user", "content": "x"}], PREFIX)[0]["content"][0]
        assert block["cache_control"] == {"type": "ephemeral"}

    def test_does_not_dedupe_an_inlined_prefix(self):
        """Pinned deliberately. Unlike the prepend path, this one sends an
        inlined prefix twice -- once cached, once in the message. Callers must
        not inline. If this ever changes, the agents' convention can relax."""
        out = self.I([{"role": "user", "content": f"{PREFIX}\n\nFILES"}], PREFIX)
        texts = [b["text"] for b in out[0]["content"]]
        assert sum(t.startswith(PREFIX) for t in texts) == 2


@pytest.fixture
def captured(monkeypatch):
    seen = {}

    async def fake_acompletion(**kwargs):
        seen.clear()
        seen.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))],
            usage=SimpleNamespace(total_cost=0.0),
        )

    monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
    return seen


@pytest.mark.asyncio
async def test_non_caching_model_receives_the_prefix(captured, monkeypatch):
    """The original bug: this used to arrive with the prefix silently dropped."""
    monkeypatch.setenv("SELFHOSTED_API_BASE", "https://llm.example.com/v1")
    monkeypatch.setenv("SELFHOSTED_API_KEY", "sk-test")
    await llm_service.call_llm(
        provider="selfhosted", model="gemma4-26b",
        messages=[{"role": "user", "content": "FILES"}], parameters={},
        user_service=Mock(), user_id="u", cache_prefix=PREFIX,
    )
    assert captured["messages"][0]["content"] == f"{PREFIX}\n\nFILES"


@pytest.mark.asyncio
async def test_caching_model_receives_a_cache_block(captured, monkeypatch):
    model = "us.anthropic.claude-sonnet-4-6"
    monkeypatch.setattr(llm_service, "_supports_prompt_caching", lambda p, m: True)
    await llm_service.call_llm(
        provider="bedrock", model=model,
        messages=[{"role": "user", "content": "FILES"}], parameters={},
        user_service=Mock(), user_id="u", cache_prefix=PREFIX,
    )
    first = captured["messages"][0]["content"][0]
    assert first["text"] == PREFIX and first["cache_control"] == {"type": "ephemeral"}
