"""Unit tests for the per-agent env_var overlay proxy."""
from __future__ import annotations

import asyncio
import os

import pytest


pytestmark = pytest.mark.unit


def test_install_environ_proxy_is_idempotent():
    from services.environ_proxy import install_environ_proxy, _EnvironProxy

    install_environ_proxy()
    first = os.environ
    install_environ_proxy()
    assert os.environ is first
    assert isinstance(os.environ, _EnvironProxy)


def test_no_overlay_passes_through_to_real_environ(monkeypatch):
    from services.environ_proxy import install_environ_proxy

    install_environ_proxy()
    monkeypatch.setenv("ISSUE_008_TEST_KEY", "real-value")
    assert os.environ.get("ISSUE_008_TEST_KEY") == "real-value"


def test_overlay_takes_precedence_over_real():
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    os.environ["ISSUE_008_TEST_KEY"] = "real-value"
    try:
        with env_overlay({"ISSUE_008_TEST_KEY": "overlay-value"}):
            assert os.environ.get("ISSUE_008_TEST_KEY") == "overlay-value"
            assert "ISSUE_008_TEST_KEY" in os.environ
        # Outside the overlay, real value visible again.
        assert os.environ.get("ISSUE_008_TEST_KEY") == "real-value"
    finally:
        del os.environ["ISSUE_008_TEST_KEY"]


def test_overlay_missing_key_falls_back_to_real():
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    os.environ["ISSUE_008_FALLBACK_KEY"] = "real"
    try:
        with env_overlay({"OTHER_KEY": "other"}):
            assert os.environ.get("ISSUE_008_FALLBACK_KEY") == "real"
            assert os.environ.get("OTHER_KEY") == "other"
    finally:
        del os.environ["ISSUE_008_FALLBACK_KEY"]


def test_concurrent_overlays_are_isolated():
    """Two asyncio tasks see their own overlays — no cross-contamination."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    results: dict[str, str | None] = {}

    async def runner(label: str, val: str):
        with env_overlay({"ISO_TEST_KEY": val}):
            await asyncio.sleep(0)  # context-switch
            results[label] = os.environ.get("ISO_TEST_KEY")

    async def main():
        await asyncio.gather(runner("a", "alpha"), runner("b", "beta"))

    asyncio.run(main())
    assert results == {"a": "alpha", "b": "beta"}


def test_overlay_does_not_leak_after_exit():
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    with env_overlay({"NEW_OVERLAY_KEY": "x"}):
        assert "NEW_OVERLAY_KEY" in os.environ
    # Outside the overlay, the key shouldn't be reachable
    # (unless something else set it in the real environ — guard against that).
    assert os.environ.get("NEW_OVERLAY_KEY") is None


# ----- Overlay inheritance across nested agent calls -----
# env_overlay layers rather than replaces, so a callee agent inherits its
# caller's env_vars. Precedence: callee > caller > real environ.


def test_nested_overlay_inherits_parent_keys():
    """A key set only by the caller is visible inside the callee's overlay."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    with env_overlay({"PARENT_ONLY": "from-parent"}):
        with env_overlay({"CHILD_ONLY": "from-child"}):
            assert os.environ.get("PARENT_ONLY") == "from-parent"
            assert os.environ.get("CHILD_ONLY") == "from-child"


def test_nested_overlay_child_wins_on_conflict():
    """The callee's own value takes precedence over the caller's."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    with env_overlay({"SHARED_KEY": "parent-value"}):
        with env_overlay({"SHARED_KEY": "child-value"}):
            assert os.environ.get("SHARED_KEY") == "child-value"
        # Parent's value is restored once the child's block exits.
        assert os.environ.get("SHARED_KEY") == "parent-value"


def test_nested_overlay_inherits_transitively():
    """Grandchild sees a key set by the grandparent."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    with env_overlay({"GRANDPARENT_KEY": "gp"}):
        with env_overlay({"MIDDLE_KEY": "mid"}):
            with env_overlay({"LEAF_KEY": "leaf"}):
                assert os.environ.get("GRANDPARENT_KEY") == "gp"
                assert os.environ.get("MIDDLE_KEY") == "mid"
                assert os.environ.get("LEAF_KEY") == "leaf"


def test_nested_overlay_does_not_leak_upward():
    """A key introduced by the callee is gone after its block exits."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    with env_overlay({"PARENT_ONLY": "p"}):
        with env_overlay({"TRANSIENT_CHILD_KEY": "c"}):
            assert "TRANSIENT_CHILD_KEY" in os.environ
        assert os.environ.get("TRANSIENT_CHILD_KEY") is None
        assert os.environ.get("PARENT_ONLY") == "p"
    assert os.environ.get("PARENT_ONLY") is None


def test_nested_overlay_still_falls_back_to_real_environ():
    """Real environ remains the base layer under a nested overlay."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    os.environ["REAL_BASE_KEY"] = "real"
    try:
        with env_overlay({"PARENT_KEY": "p"}):
            with env_overlay({"CHILD_KEY": "c"}):
                assert os.environ.get("REAL_BASE_KEY") == "real"
    finally:
        del os.environ["REAL_BASE_KEY"]


def test_concurrent_nested_overlays_are_isolated():
    """Sibling tasks nesting under their own parents don't cross-contaminate."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    results: dict = {}

    async def child(label: str, val: str):
        with env_overlay({"CHILD_TIER": val}):
            await asyncio.sleep(0)
            results[label] = (
                os.environ.get("PARENT_TIER"),
                os.environ.get("CHILD_TIER"),
            )

    async def parent(label: str, pval: str, cval: str):
        with env_overlay({"PARENT_TIER": pval}):
            await asyncio.sleep(0)
            await child(label, cval)

    async def main():
        await asyncio.gather(
            parent("a", "p-alpha", "c-alpha"),
            parent("b", "p-beta", "c-beta"),
        )

    asyncio.run(main())
    assert results == {
        "a": ("p-alpha", "c-alpha"),
        "b": ("p-beta", "c-beta"),
    }


def test_iteration_includes_inherited_parent_keys():
    """__iter__/keys() surface inherited keys, not just the innermost overlay."""
    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()
    with env_overlay({"ITER_PARENT": "p"}):
        with env_overlay({"ITER_CHILD": "c"}):
            keys = os.environ.keys()
            assert "ITER_PARENT" in keys
            assert "ITER_CHILD" in keys
            snapshot = os.environ.copy()
            assert snapshot["ITER_PARENT"] == "p"
            assert snapshot["ITER_CHILD"] == "c"
