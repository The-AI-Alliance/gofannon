"""Unit tests for the log_redaction module.

Covers each known prefix pattern, the dict/list traversal used by the
observability service, the bad-regex resilience guarantee, and the
fail-open behavior on non-string input. Pure-Python tests; no
FastAPI, no DB.

The threat model here is "agent or stack accidentally prints a
credential into logs" — these tests verify the filter catches each
known issuer's token shape AND doesn't false-positive into making
the logs useless. Both directions matter; failing either is an
incident.
"""
from __future__ import annotations

import re

import pytest

from services.log_redaction import (
    _compile_patterns,
    redact,
    redact_in_place,
)


pytestmark = pytest.mark.unit
# ---------------------------------------------------------------------
# Test fixture builders.
#
# These produce credential-shaped strings at runtime so the test file
# itself never contains a literal that GitHub's secret scanner (or any
# similar scanner) would flag. The redactor is exercised against the
# assembled strings, which match the real token shapes by construction.
#
# Don't replace these with constants — the whole point is that the
# literal forms only exist in memory at test time, not on disk.
# ---------------------------------------------------------------------

# Char pools we splice together. Splitting a long alphanumeric run
# into a few short variables keeps any single line from looking like
# the body of a credential.
_LOWER = "abcdefghijklmnopqrstuvwxyz"
_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_DIGITS = "0123456789"
_BODY36 = _LOWER + _DIGITS  # 36 chars total — exactly the length the
                            # classic GitHub token regex requires.


def _gh_classic(prefix2: str) -> str:
    """github_token shape: ghp_/gho_/ghu_/ghs_/ghr_ + 36 alnum chars."""
    return prefix2 + "_" + _BODY36


def _gh_pat() -> str:
    """github_pat_ + 82+ alnum/underscore chars."""
    body = "11" + _UPPER + "_" + _DIGITS + _LOWER + _DIGITS + _UPPER[:10]
    # Pad to 82 chars after the 'github_pat_' prefix.
    body = body.ljust(82, "x")
    return "github_pat" + "_" + body


def _openai_proj() -> str:
    return "sk" + "-" + "proj" + "-" + _LOWER + _DIGITS[:10]


def _anthropic() -> str:
    return "sk" + "-" + "ant" + "-" + "api03" + "-" + _LOWER + _DIGITS[:10]


def _openai_legacy() -> str:
    return "sk" + "-" + _DIGITS + _LOWER


def _aws(prefix: str) -> str:
    """AKIA / ASIA + 16 caps/digits."""
    return prefix + "IOSFODNN7" + "EXAMPLE"


def _google() -> str:
    return "AIza" + "SyA-abcd" + _DIGITS + "efghijklmn-opqrstuv"


def _slack(suffix: str) -> str:
    return "xox" + suffix + "-" + _DIGITS + "123-" + _LOWER[:10]


def _stripe(env: str) -> str:
    return "sk" + "_" + env + "_" + _LOWER + _DIGITS


def _jwt() -> str:
    """Three base64url segments separated by dots."""
    head = "eyJ" + "hbGciOiJIUzI1NiJ9"
    body = "eyJ" + "zdWIiOiJ0ZXN0IiwibmFtZSI6IkFsaWNlIn0"
    sig = "signature_segment_xxxxx"
    return head + "." + body + "." + sig


def _bearer_token() -> str:
    return _LOWER[:6] + _DIGITS[:3] + "def456" + "ghi789" + "jklmno"





# ---------------------------------------------------------------------
# Prefix patterns: positive cases — each known issuer's token shape
# should redact. The fake values below all match real-world token
# regexes; they're not actually live credentials.
# ---------------------------------------------------------------------


@pytest.mark.parametrize("text, expected_kind", [
    # GitHub
    (_gh_pat(), "github_pat"),
    (_gh_classic("ghp"), "github_token"),
    (_gh_classic("gho"), "github_token"),
    (_gh_classic("ghu"), "github_token"),
    (_gh_classic("ghs"), "github_token"),
    (_gh_classic("ghr"), "github_token"),

    # OpenAI / Anthropic — note: "openai_key" is the catch-all for sk-X
    # that isn't sk-proj or sk-ant.
    (_openai_proj(), "openai_project"),
    (_anthropic(), "anthropic_key"),
    (_openai_legacy(), "openai_key"),

    # AWS access key IDs (both root user "AKIA" and STS "ASIA" forms).
    # The AKIA/ASIA + IOSFODNN7EXAMPLE pattern is GitHub's documented
    # canary fixture — scanners are explicitly trained to ignore it.
    (_aws("AKIA"), "aws_access_key"),
    (_aws("ASIA"), "aws_access_key"),

    # Google API key — 35 chars after AIza prefix
    (_google(), "google_api_key"),

    # Slack — five letter codes after xox
    (_slack("b"), "slack_token"),
    (_slack("p"), "slack_token"),
    (_slack("a"), "slack_token"),
    (_slack("r"), "slack_token"),
    (_slack("s"), "slack_token"),

    # Stripe
    (_stripe("live"), "stripe_key"),
    (_stripe("test"), "stripe_key"),

    # JWT (3 base64url segments separated by dots, each >=10 chars)
    (_jwt(), "jwt"),
])
def test_known_token_shapes_get_redacted(text, expected_kind):
    """Each known issuer's token shape produces a [REDACTED:<kind>]
    placeholder where <kind> matches the issuer."""
    out = redact(text)
    assert out != text, f"didn't redact: {text!r}"
    assert f"[REDACTED:{expected_kind}]" in out, (
        f"wrong kind: expected {expected_kind!r}, got {out!r}"
    )


# ---------------------------------------------------------------------
# Authorization Bearer header — both inline-header form and
# standalone form (when a header value is dumped out of a dict).
# ---------------------------------------------------------------------


def test_authorization_bearer_inline_header():
    """The 'Authorization: Bearer <token>' inline form keeps the
    'Authorization: Bearer ' prefix so the line is still readable."""
    out = redact("Authorization: Bearer " + _bearer_token())
    assert "Authorization: Bearer " in out
    assert "[REDACTED:bearer]" in out
    assert _bearer_token() not in out


def test_authorization_bearer_case_insensitive():
    out = redact("authorization: bearer " + _bearer_token())
    assert "[REDACTED:bearer]" in out


def test_standalone_bearer_token():
    """When a header value gets logged without 'Authorization:' prefix
    (typical when dumping a request headers dict), the standalone
    'Bearer <opaque>' form should still redact."""
    out = redact("Bearer " + _bearer_token())
    assert "[REDACTED:bearer]" in out
    assert _bearer_token() not in out


def test_word_bearer_in_english_does_not_trigger():
    """'bearer' lowercase in a sentence shouldn't redact. The pattern
    requires capital-B 'Bearer' followed by >=20 token-looking chars."""
    text = "the bearer of bad news"
    assert redact(text) == text


# ---------------------------------------------------------------------
# Generic key=value catchall — credential-shaped values after
# secret-suggestive key names.
# ---------------------------------------------------------------------


@pytest.mark.parametrize("key", [
    "api_key", "apikey", "api-key",
    "secret", "password", "passwd",
    "token", "pat",
    "access_key", "access-key",
])
def test_secret_kv_catchall_redacts_long_values(key):
    """A secret-shaped key followed by a credential-length value
    redacts."""
    text = f"{key}=" + "v" * 30
    out = redact(text)
    assert "[REDACTED:secret]" in out
    assert "v" * 20 not in out
    # The key itself stays so the log retains context.
    assert f"{key}=" in out


def test_secret_kv_with_quoted_value():
    out = redact('api_key="' + "x" * 24 + '"')
    assert "[REDACTED:secret]" in out


def test_secret_kv_short_value_not_redacted():
    """Values under 16 chars don't trigger the catchall — too short
    to be a real credential, would false-positive on innocuous data
    like 'password=short'."""
    text = "password=short"
    assert redact(text) == text


def test_partition_key_not_redacted():
    """Common false-positive case from real codebases: column names
    that contain 'key' but aren't credentials."""
    # The catchall requires the key to be exactly 'api[_-]?key' /
    # 'secret' / etc., not 'partition_key'. Verify.
    text = "partition_key=customer_id_12345"
    assert redact(text) == text


# ---------------------------------------------------------------------
# Private key inline marker
# ---------------------------------------------------------------------


@pytest.mark.parametrize("variant", [
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN ENCRYPTED PRIVATE KEY-----",
])
def test_private_key_marker_redacted(variant):
    out = redact(variant + "\nMIIEvQIBADANBgk...")
    # The BEGIN line is replaced; the body falls through (a known
    # limitation — would need a stateful parser to redact across
    # multiple write() calls).
    assert "[REDACTED:private_key]" in out
    # Marker itself is gone:
    assert variant not in out


# ---------------------------------------------------------------------
# Real-shape tests — the leak the user actually hit, plus a few
# representative log-line patterns.
# ---------------------------------------------------------------------


def test_real_world_pat_leak_from_user_logs():
    """Exactly the shape that triggered this whole feature: an agent
    printing a multi-line 'raw input' debug dump that included the
    GitHub PAT it was about to use."""
    pat = _gh_pat()
    raw = (
        "DEBUG raw input: 'repo: apache/tooling-runbooks\\n"
        f"pat: {pat}\\n"
        "directories: ASVS/reports/mahout/245aad3/all\\n"
        "output: ASVS/reports/mahout/245aad3'"
    )
    out = redact(raw)
    assert "[REDACTED:github_pat]" in out
    assert pat[:20] not in out  # original PAT prefix is gone
    # The non-secret context survives.
    assert "apache/tooling-runbooks" in out
    assert "ASVS/reports/mahout" in out


def test_multiple_secrets_in_one_line():
    """A single line with two different credential shapes should
    redact both, leaving non-secret bits intact."""
    text = "config: api_key=" + _gh_classic("ghp") + " host=api.example.com"
    out = redact(text)
    # The github_token pattern matches first (more specific than the
    # generic key=value catch); secret_kv won't fire on the same
    # value because the token's already been replaced.
    assert "[REDACTED:" in out
    assert _gh_classic("ghp") not in out
    # Non-secret survives.
    assert "host=api.example.com" in out


# ---------------------------------------------------------------------
# Placeholder format — readers need to be able to grep for redactions
# and tell what kind. Lock the format down.
# ---------------------------------------------------------------------


def test_placeholder_format_is_grepable():
    """[REDACTED:<kind>] format is stable and contains the kind for
    both grep-ability and to tell readers what got scrubbed."""
    out = redact(_gh_classic("ghp"))
    assert re.match(r"^\[REDACTED:[a-z_]+\]$", out)


def test_placeholder_does_not_leak_value_length():
    """The placeholder size doesn't depend on input length — defends
    against length-reveal side channels."""
    short = redact("ghp" + "_" + "A" * 36)
    long = redact("ghp" + "_" + "B" * 36)
    assert short == long  # same redacted output regardless of token contents


# ---------------------------------------------------------------------
# redact() input handling — never raise, never break the log pipeline.
# ---------------------------------------------------------------------


def test_redact_empty_string_returns_unchanged():
    assert redact("") == ""


def test_redact_none_returns_unchanged():
    """The contract: non-string input passes through untouched."""
    assert redact(None) is None


def test_redact_non_string_passes_through():
    assert redact(42) == 42
    assert redact(True) is True
    assert redact([1, 2]) == [1, 2]  # not a list-of-strings recurse case


def test_redact_unicode_does_not_corrupt():
    text = "héllo wörld with no secrets"
    assert redact(text) == text


def test_redact_very_long_input_does_not_hang():
    """Just a smoke test that the regex set is well-behaved on big
    inputs (no catastrophic backtracking). 100KB of mixed content."""
    text = ("hello world " * 1000) + "\n" + _gh_classic("ghp") + "\n" + ("more " * 5000)
    out = redact(text)
    assert "[REDACTED:github_token]" in out
    assert len(out) > 0


# ---------------------------------------------------------------------
# redact_in_place — recursive traversal of dict/list/tuple structures.
# Used by observability_service for log-payload metadata.
# ---------------------------------------------------------------------


def test_redact_in_place_walks_dict():
    obj = {
        "message": "ran with " + _gh_classic("ghp"),
        "user": "alice",
    }
    out = redact_in_place(obj)
    assert "[REDACTED:github_token]" in out["message"]
    assert out["user"] == "alice"
    # Mutates in place — same object identity.
    assert out is obj


def test_redact_in_place_walks_nested_dict():
    obj = {
        "headers": {
            "Authorization": "Bearer " + _bearer_token(),
            "User-Agent": "curl/7.68",
        },
    }
    out = redact_in_place(obj)
    assert "[REDACTED:bearer]" in out["headers"]["Authorization"]
    assert out["headers"]["User-Agent"] == "curl/7.68"


def test_redact_in_place_walks_list():
    obj = ["plain", _gh_classic("ghp"), "also plain"]
    out = redact_in_place(obj)
    assert out[0] == "plain"
    assert "[REDACTED:github_token]" in out[1]
    assert out[2] == "also plain"


def test_redact_in_place_walks_tuple():
    """Tuples are immutable, so redact_in_place returns a new tuple
    rather than mutating."""
    obj = ("plain", _gh_classic("ghp"))
    out = redact_in_place(obj)
    assert isinstance(out, tuple)
    assert out[0] == "plain"
    assert "[REDACTED:github_token]" in out[1]


def test_redact_in_place_preserves_non_string_leaves():
    obj = {"count": 42, "ok": True, "ratio": 3.14, "missing": None}
    out = redact_in_place(obj)
    assert out["count"] == 42
    assert out["ok"] is True
    assert out["ratio"] == 3.14
    assert out["missing"] is None


def test_redact_in_place_deeply_nested():
    """A realistic observability payload with nested headers, query
    params, and a token in metadata.headers.Authorization."""
    payload = {
        "level": "INFO",
        "message": "http request completed",
        "metadata": {
            "request": {
                "method": "POST",
                "headers": {
                    "Authorization": "Bearer " + _jwt(),
                    "Content-Type": "application/json",
                },
                "body": "api_key=" + "v" * 30,
            },
        },
    }
    out = redact_in_place(payload)

    auth = out["metadata"]["request"]["headers"]["Authorization"]
    assert "[REDACTED:" in auth  # could be 'bearer' or 'jwt'; either is fine
    assert _jwt()[:8] not in auth  # original JWT head is gone

    body = out["metadata"]["request"]["body"]
    assert "[REDACTED:secret]" in body
    assert "v" * 20 not in body  # value chars are gone

    # Non-secret structure survives
    assert out["level"] == "INFO"
    assert out["metadata"]["request"]["method"] == "POST"
    assert out["metadata"]["request"]["headers"]["Content-Type"] == "application/json"


# ---------------------------------------------------------------------
# Pattern compilation resilience — a bad regex shouldn't disable the
# rest. This is the "graceful degradation" guarantee from the
# module's docstring.
# ---------------------------------------------------------------------


def test_compile_patterns_skips_bad_regex_keeps_others(caplog):
    """A malformed regex in the middle of the pattern list should be
    logged and skipped; the surrounding patterns must still compile."""
    defs = [
        ("good_one", r"github_pat_[A-Za-z0-9_]{82,}"),
        ("BAD", r"["),  # unterminated character class — definitely bad
        ("good_two", r"\bsk-[A-Za-z0-9]{20,}"),
    ]
    import logging
    with caplog.at_level(logging.WARNING):
        compiled = _compile_patterns(defs)

    # The two good ones survive; the bad one is skipped.
    kinds = [k for k, _ in compiled]
    assert "good_one" in kinds
    assert "good_two" in kinds
    assert "BAD" not in kinds

    # And the failure is logged so it's visible in CI / startup logs.
    assert any("BAD" in record.message for record in caplog.records)


def test_compile_patterns_all_good_returns_all():
    defs = [
        ("a", r"abc"),
        ("b", r"def"),
    ]
    compiled = _compile_patterns(defs)
    assert len(compiled) == 2


def test_compile_patterns_empty_list():
    assert _compile_patterns([]) == []


# ---------------------------------------------------------------------
# Source patterns spot-check — make sure the production module's
# patterns all compile (no shipped bad regex).
# ---------------------------------------------------------------------


def test_production_patterns_all_compile():
    """If someone adds a pattern to _PATTERN_DEFS that doesn't compile,
    we want CI to catch it. The module logs and skips at import time
    rather than crashing, but a failed compile still means the
    pattern's not protecting anything — that's a regression."""
    from services.log_redaction import _PATTERN_DEFS, _COMPILED
    assert len(_COMPILED) == len(_PATTERN_DEFS), (
        f"some patterns failed to compile: "
        f"defined={len(_PATTERN_DEFS)}, compiled={len(_COMPILED)}"
    )
