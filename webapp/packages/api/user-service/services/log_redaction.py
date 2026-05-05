"""Secret redaction for log output.

Used by ``services.agent_trace`` to scrub secrets from agent-side
``print()`` and ``logging`` output before it reaches the trace's event
list (and from there the streaming SSE channel and the final response
payload). Also used by ``services.observability_service`` to scrub
framework-side log lines on their way to stdout/the log providers.

Strategy: a list of compiled regexes targeting known issuer-prefixed
token shapes (GitHub PATs, OpenAI/Anthropic API keys, AWS access keys,
Google API keys, Slack tokens, Stripe keys, JWT triplets, generic
"key=value" pairs where the key looks secret-shaped, and inline
private-key markers). Each match becomes a stable placeholder
``[REDACTED:<kind>]`` so the log line keeps its shape — readers can
see something was redacted, what type, and where it sat in the
sentence — without leaking the value or even its length.

Failure modes:

  * If a single regex fails to compile (someone added a bad pattern in
    code review), we log a warning at module-load time and skip just
    that pattern. The remaining patterns still apply. We never want
    one broken regex to disable redaction wholesale or to crash the
    log pipeline.

  * The redactor must never raise from inside ``redact()``. Errors at
    apply-time (e.g. malformed input that confuses ``re.sub``)
    fall through to returning the original input unchanged. That's a
    deliberate fail-open in the *availability* sense (logs always
    flow) at the cost of fail-closed in the *security* sense (a
    secret could in principle survive a redactor crash). The
    alternative — dropping log lines entirely on redactor failure —
    is worse for debuggability and creates an attractive
    denial-of-logging vector.

The function is pure (no I/O, no global state beyond the compiled
patterns), so it's safe to call from any context.
"""
from __future__ import annotations

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


# Each entry: (kind, pattern_str). The "kind" is what shows up in the
# placeholder so a reader can tell what was scrubbed. Order matters
# slightly — more specific patterns come first so a generic catch-all
# doesn't preempt a tighter, well-known shape. Currently no two
# patterns can match the same string in conflicting ways, but ordering
# them this way is cheap insurance.
_PATTERN_DEFS: List[Tuple[str, str]] = [
    # Inline private-key block markers. We don't try to scrub the body
    # of the key (that would require multi-line stateful parsing); we
    # just nuke the line that contains the BEGIN/END marker. The agent
    # is unlikely to print key bodies inline anyway — they're typically
    # in files. If they do show up we'd still want this header line
    # gone so the marker doesn't tip off scanners.
    ("private_key", r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),

    # GitHub.
    # Fine-grained PAT — long, fixed prefix.
    ("github_pat", r"github_pat_[A-Za-z0-9_]{82,}"),
    # Classic PAT and OAuth/app variants — same length, different prefix.
    ("github_token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b"),

    # OpenAI. Project keys are prefixed sk-proj-; legacy/user keys are
    # bare sk-. Both have varying lengths in practice; require >=20
    # alphanumeric/underscore/dash chars after the prefix to avoid
    # false-positives on things like "sk-test" in unrelated contexts.
    ("openai_project", r"\bsk-proj-[A-Za-z0-9_-]{20,}"),
    ("anthropic_key",  r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    ("openai_key",     r"\bsk-[A-Za-z0-9]{20,}"),

    # AWS access key IDs. Secret access keys are 40 base64-ish chars
    # without a distinctive prefix — too generic to match safely on
    # their own. We only catch the access key ID; the more sensitive
    # secret access key would fall through unless caught by the
    # generic `key=value` pattern below.
    ("aws_access_key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),

    # Google API keys. Fixed prefix + 35+ charset chars.
    ("google_api_key", r"AIza[0-9A-Za-z_\-]{35,}"),

    # Slack tokens. xoxb (bot), xoxp (user), xoxa (workspace), xoxr
    # (refresh), xoxs (legacy).
    ("slack_token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),

    # Stripe. sk_live_… or sk_test_…
    ("stripe_key", r"\bsk_(?:live|test)_[A-Za-z0-9]{24,}\b"),

    # JWTs. Three base64url segments separated by dots, each at least 10
    # chars. Some JWTs are intentionally non-secret; we redact them
    # anyway because telling them apart from the secret kind requires
    # parsing claims — too much work for a defensive filter.
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),

    # Authorization: Bearer <opaque>. Catches the inline-header form.
    # Using IGNORECASE so authorization/Authorization both match.
    ("bearer", r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._\-+/=]+"),

    # Standalone "Bearer <opaque>" — when a header value is logged
    # without the "Authorization:" prefix (typical when dumping a
    # dict where Authorization was a key, not part of a string).
    # The capital B and the >= 20-char body keep this from flagging
    # English sentences with "bearer" in them.
    ("bearer", r"\bBearer\s+[A-Za-z0-9._\-+/=]{20,}"),

    # Generic "key=value" or "key: value" where the key name suggests
    # it's secret-shaped and the value looks credential-shaped (>=16
    # chars, no spaces, mixed alphanumeric with optional underscores
    # /dashes/dots/slashes/equals). Keeps the key= prefix so context
    # isn't lost. Last in the list so the more specific patterns above
    # catch their cases first.
    ("secret_kv", r"(?i)\b(api[_-]?key|secret|password|passwd|token|pat|access[_-]?key)\s*[=:]\s*['\"]?([A-Za-z0-9_\-./=+]{16,})['\"]?"),
]


def _compile_patterns(defs: List[Tuple[str, str]]) -> List[Tuple[str, "re.Pattern[str]"]]:
    """Compile each pattern, skipping any that fail.

    A bad regex anywhere in the list shouldn't disable the rest. We
    log a warning and continue.
    """
    compiled: List[Tuple[str, re.Pattern[str]]] = []
    for kind, pattern in defs:
        try:
            compiled.append((kind, re.compile(pattern)))
        except re.error as exc:
            logger.warning(
                "log_redaction: failed to compile pattern %r (%s); skipping. "
                "Remaining patterns will still apply.",
                kind, exc,
            )
    return compiled


_COMPILED = _compile_patterns(_PATTERN_DEFS)


def _placeholder(kind: str) -> str:
    """Stable placeholder that's grep-friendly and obviously synthetic."""
    return f"[REDACTED:{kind}]"


def _sub_for(kind: str, match: re.Match) -> str:
    """How to replace a match. Most patterns get a flat placeholder,
    but a couple keep a context prefix so the line stays readable.
    """
    if kind == "bearer":
        # First bearer pattern captures the "authorization: bearer "
        # prefix as group 1; second pattern has no groups, so group(1)
        # raises IndexError. Detect by trying group(1) and falling back
        # to a static "Bearer " prefix.
        try:
            prefix = match.group(1)
        except IndexError:
            prefix = "Bearer "
        return f"{prefix}{_placeholder(kind)}"
    if kind == "secret_kv":
        # Group 1 is the key name (api_key, secret, etc.); rebuild
        # "key=[REDACTED:secret]" so the log keeps the key.
        return f"{match.group(1)}={_placeholder('secret')}"
    if kind == "private_key":
        # Replace the whole BEGIN-marker line with one placeholder.
        return _placeholder(kind)
    return _placeholder(kind)


def redact(text: str) -> str:
    """Scrub known secret shapes from `text`, returning the redacted version.

    Returns the original text unchanged if anything goes wrong inside —
    the contract is "never break the log pipeline." Returns the input
    unchanged for non-string inputs and empty strings.
    """
    if not text or not isinstance(text, str):
        return text
    try:
        result = text
        for kind, pattern in _COMPILED:
            # functools.partial would also work; closure is simpler.
            result = pattern.sub(lambda m, _kind=kind: _sub_for(_kind, m), result)
        return result
    except Exception as exc:  # pragma: no cover — defensive only
        logger.warning("log_redaction: redact() raised %s; passing input through", exc)
        return text


def redact_in_place(obj):
    """Recursively redact strings inside a dict/list/tuple structure.

    Used by observability_service to scrub log payloads' metadata
    fields before serialization. Mutates dicts and lists in place;
    returns the (possibly transformed) object so it can also be used
    as a pure function for non-mutable inputs.
    """
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = redact_in_place(v)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = redact_in_place(v)
        return obj
    if isinstance(obj, tuple):
        return tuple(redact_in_place(v) for v in obj)
    return obj
