"""Generic litellm model registration and the prompt-caching gate.

Some providers expose a model under a name litellm's model map does not
know. Every lookup on that name misses: capability probes report False,
cost tracking reads zero, and parameters the model does support are
silently dropped. Models can therefore declare a litellm_registration
block that copies (and optionally overrides) an entry litellm already
ships, applied once at import time by _register_litellm_models.

These tests cover that loop and the prompt-caching gate that reads the
same config, using synthetic entries rather than any one model.
"""

from __future__ import annotations

import litellm
import pytest
from config.provider_config import PROVIDER_CONFIG
from services import llm_service

pytestmark = pytest.mark.unit




def _declared_registration_names(config):
    """Every model string that declares a litellm_registration block."""
    return [
        name
        for provider in config.values()
        for name, spec in (provider.get("models") or {}).items()
        if isinstance(spec, dict) and spec.get("litellm_registration")
    ]


class TestRegisterLitellmModels:
    """The generic loop that applies litellm_registration blocks."""

    def test_registration_does_not_crash_without_the_source(self, monkeypatch, capsys):
        """A litellm upgrade that renames the source entry must not break
        startup. The entry is skipped with a warning instead."""
        fake_map = {k: v for k, v in litellm.model_cost.items() if k != "some-source"}
        monkeypatch.setattr(litellm, "model_cost", fake_map)
        cfg = {"p": {"models": {"m": {"litellm_registration": {"copy_from": "some-source"}}}}}
        assert llm_service._register_litellm_models(cfg) == []
        assert "no 'some-source' to copy from" in capsys.readouterr().out

    def test_copy_from_merges_overrides_and_registers_aliases(self, monkeypatch):
        registered = {}
        monkeypatch.setattr(litellm, "model_cost", {"src": {"a": 1, "litellm_provider": "x"}})
        monkeypatch.setattr(litellm, "register_model", lambda d: registered.update(d))
        cfg = {"p": {"models": {"m": {"litellm_registration": {
            "copy_from": "src",
            "overrides": {"litellm_provider": "anthropic"},
            "aliases": ["m-alias"],
        }}}}}
        assert llm_service._register_litellm_models(cfg) == ["m", "m-alias"]
        assert registered == {
            "m": {"a": 1, "litellm_provider": "anthropic"},
            "m-alias": {"a": 1, "litellm_provider": "anthropic"},
        }

    def test_literal_entry_without_copy_from(self, monkeypatch):
        registered = {}
        monkeypatch.setattr(litellm, "register_model", lambda d: registered.update(d))
        cfg = {"p": {"models": {"m": {"litellm_registration": {"overrides": {"mode": "chat"}}}}}}
        assert llm_service._register_litellm_models(cfg) == ["m"]
        assert registered == {"m": {"mode": "chat"}}

    def test_registration_is_idempotent(self):
        """A second import or config reload must not change the map: entries
        are keyed by model string and overwritten, never stacked."""
        import copy
        before = copy.deepcopy(litellm.model_cost)
        llm_service._register_litellm_models(PROVIDER_CONFIG)
        llm_service._register_litellm_models(PROVIDER_CONFIG)
        assert litellm.model_cost.keys() == before.keys()
        for name in _declared_registration_names(PROVIDER_CONFIG):
            assert litellm.model_cost.get(name) == before.get(name)

    def test_models_without_registration_are_ignored(self, monkeypatch):
        monkeypatch.setattr(litellm, "register_model", lambda d: pytest.fail("should not register"))
        assert llm_service._register_litellm_models({"p": {"models": {"m": {}}}}) == []


class TestPromptCachingGate:
    def test_non_claude_models_are_excluded(self):
        assert llm_service._supports_prompt_caching("selfhosted", "gemma4-26b") is False
        assert llm_service._supports_prompt_caching("openai", "gpt-5.2") is False

    def test_declared_models_still_follow_the_litellm_map(self):
        """A model that DECLARES the capability and that litellm agrees about.

        The map remains a second gate, but it is no longer the first: the
        config decides whether a model is a candidate at all. This asserts
        the two together -- declared here, supported there.
        """
        declared = [
            name
            for name, cfg in PROVIDER_CONFIG.get("bedrock", {}).get("models", {}).items()
            if cfg.get("supports_prompt_caching")
            and litellm.model_cost.get(name, {}).get("supports_prompt_caching") is not False
        ]
        if not declared:
            pytest.skip("no bedrock model both declares caching and is supported by litellm's map")
        assert llm_service._supports_prompt_caching("bedrock", declared[0]) is True


    def test_undeclared_model_does_not_support_caching(self):
        """A model the config does not declare gets no cache_control marker.

        This inverts the previous assertion, deliberately. The gate used to
        be `"claude" in model.lower()`, so any Claude-ish string defaulted to
        enabled -- including models that do not exist. That is how a name
        match came to decide a capability, and the same function returned
        False for every self-hosted model, whose cache_prefix llm_service
        then silently discarded rather than delivering another way.

        An undeclared model now takes the prepend path instead: the same
        bytes reach the model, without a marker and without a cache
        discount. Nothing is lost that was not already absent.
        """
        assert llm_service._supports_prompt_caching("bedrock", "us.anthropic.claude-not-a-real-model-v9") is False

    def test_the_name_no_longer_decides_anything(self):
        """A declared model and an undeclared one differing only in case.

        Replaces a test that asserted the name match was case-insensitive.
        There is no name match now -- the point is that the string has
        stopped carrying meaning, so a case variant that is not a config key
        is simply an unknown model.
        """
        assert llm_service._supports_prompt_caching("bedrock", "CLAUDE-OPUS-5") is False
