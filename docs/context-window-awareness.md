# Context Window Awareness

This guide explains how Gofannon gives generated agent code full visibility into model context window limits, enabling reliable batch processing of large datasets without token overflows.

## Table of Contents

- [Overview](#overview)
- [Problem](#problem)
- [Architecture](#architecture)
- [Provider Configuration](#provider-configuration)
- [Runtime API](#runtime-api)
- [Batch Processing Guidance](#batch-processing-guidance)
- [Error Handling](#error-handling)
- [Adding a New Model](#adding-a-new-model)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Overview

Every LLM has a maximum input size (context window). When an agent processes large datasets — scanning hundreds of files for a security audit, for example — the generated code needs to split work into batches that fit within these limits and consolidate results without overflowing during the merge step.

Gofannon addresses this with three layers:

1. **`context_window` metadata** on every model in the provider config
2. **`get_context_window(provider, model)`** available in the agent sandbox at runtime
3. **Batch processing guidance** in the code generation prompt, teaching generated code how to estimate tokens, create batches, and consolidate hierarchically

## Problem

Without context window awareness, agents processing non-trivial workloads hit a cascade of failures:

- **Token overflow on consolidation** — batch results joined into a single prompt exceed the model's limit
- **Character-based token estimation undercounts by 30–50%** — code tokens are denser than prose; naive `len(text) / 4` consistently underestimates
- **No runtime visibility into model limits** — generated code has no way to look up context window sizes, so developers hardcode guesses
- **Static assets waste tokens** — CSS, minified JS, lock files, and images get processed as if they were code
- **Infinite recursion on single-line files** — minified files with ≤2 lines cause line-based splitters to loop forever

## Architecture

```
┌─────────────────────────┐
│   Provider Configs      │   config/{anthropic,openai,...}/__init__.py
│   context_window: N     │   ← Verified against provider docs
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   agent_factory/        │   Surfaces context_window in the code
│   __init__.py           │   generation prompt for each model
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   dependencies.py       │   get_context_window(provider, model)
│   (agent sandbox)       │   injected into exec_globals
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   prompts.py            │   Batch processing guidance with
│   (how_to_use_llm)      │   estimate_tokens(), create_batches(),
│                         │   hierarchical consolidation pattern
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   llm_service.py        │   Catches overflow errors, re-raises
│   (error handling)      │   with context window size + advice
└─────────────────────────┘
```

## Provider Configuration

Every model in the cloud provider configs (`openai`, `anthropic`, `gemini`, `perplexity`, `bedrock`) includes a `context_window` field specifying the maximum input tokens. Values are verified against provider documentation.

```python
# config/anthropic/__init__.py
"claude-opus-4-6": {
    "context_window": 200000,
    "returns_thoughts": False,
    "parameters": { ... }
}
```

### Current Coverage

| Provider    | Models | Coverage |
|-------------|--------|----------|
| OpenAI      | 58     | 100%     |
| Anthropic   | 12     | 100%     |
| Bedrock     | 41     | 100%     |
| Gemini      | 4      | 100%     |
| Perplexity  | 6      | 100%     |
| Ollama      | 2      | N/A (local models, user-defined) |

### Notable Context Windows

| Model Family | Context Window |
|---|---|
| Claude 4.x (Anthropic/Bedrock) | 200,000 tokens |
| GPT-5 / GPT-5-mini (OpenAI) | 400,000 tokens |
| GPT-4.1 family (OpenAI) | 1,047,576 tokens |
| Gemini 3.0 Pro | 1,048,576 tokens |
| Llama 4 Scout (Bedrock) | 3,538,944 tokens |
| Llama 4 Maverick (Bedrock) | 1,048,576 tokens |

## Runtime API

### `get_context_window(provider, model)`

Available in the agent sandbox alongside `call_llm()`. Returns the context window size in tokens.

```python
# Inside generated agent code:
ctx = get_context_window("anthropic", "claude-opus-4-6")  # 200000
ctx = get_context_window("openai", "gpt-4.1")             # 1047576
ctx = get_context_window("unknown", "unknown")             # 128000 (safe default)
```

### `count_tokens(text, provider, model)` / `count_message_tokens(messages, provider, model)`

Exact token counting via litellm's tokenizer. Also available in the agent sandbox. Use these instead of character-based estimation (`len(text)/N` undercounts by 30–50% for code).

```python
tokens = count_tokens(file_content, provider, model)
total = count_message_tokens(messages, provider, model)
```

**Location:** Defined inside `_execute_agent_code()` in `dependencies.py` and injected into `exec_globals`.

**Default behavior:** Returns 128,000 if the provider or model is not found. This is a conservative default that works safely with most models.

### Context Window in Code Generation Prompts

When the agent factory generates code, each model's documentation section includes its context window:

```
### `anthropic/claude-opus-4-6`
**Configured Parameters:** {"temperature": 1.0}
**Context Window:** 200,000 tokens (maximum input size — prompts exceeding this will fail)
```

This gives the LLM generating agent code explicit knowledge of the limit so it can compute budgets accordingly.

## Batch Processing Guidance

The prompt guidance in `prompts.py` (`how_to_use_llm`) teaches generated agent code the following patterns. These are documented as code examples that the code-generating LLM can adapt.

### Token Counting

The guidance uses **exact token counting** via litellm's tokenizer rather than character-based estimation (which undercounts by 30–50% for code):

```python
# Exact token counts — available in the agent sandbox
count_tokens(text, provider, model)
count_message_tokens(messages, provider, model)
```

### Safe Input Limits

The guidance recommends using **40% of the context window** for batch content, reserving the remaining 60% for system prompts, user message templates, instructions, response tokens, and estimation error margin:

```python
CONTEXT_WINDOW = get_context_window(provider, model)
SAFE_INPUT_LIMIT = int(CONTEXT_WINDOW * 0.40)
```

### Token-Aware Batching

`create_batches()` splits items into groups that fit within the token budget. Items that exceed the budget individually get their own batch for further splitting.

### Hierarchical Consolidation

The most critical pattern. Instead of joining all batch results into a single consolidation prompt (which overflows for any non-trivial workload), the guidance teaches a tree-style merge:

1. Group batch results by token budget
2. Consolidate each group with a separate LLM call
3. Repeat until one final result remains

This is explicitly called out with a **"NEVER do this"** warning against naive consolidation.

### Pre-Flight Checks

Before every `call_llm` invocation, generated code should verify that the assembled prompt fits within 80% of the context window:

```python
def preflight_check(messages, provider, model):
    """Verify assembled prompt fits within context window. Returns token count."""
    total = count_message_tokens(messages, provider, model)
    limit = int(get_context_window(provider, model) * 0.80)
    if total > limit:
        raise ValueError(f"Prompt too large: {total} tokens > {limit} limit (80% of context window)")
    return total
```

### Skip Lists

Guidance includes patterns for filtering non-code files before batching: skip directories (`node_modules`, `vendor`, `dist`), skip files (`package-lock.json`, `uv.lock`), and skip extensions (`.min.js`, `.map`, `.css`, `.woff`, `.png`).

## Error Handling

### LLM Service Overflow Detection

`llm_service.py` catches context window overflow errors from provider APIs and re-raises them with an enriched message that includes the model name, context window size, and remediation advice.

Detected error patterns:

- `"prompt is too long"` (Anthropic)
- `"context_length_exceeded"` (OpenAI)
- `"maximum context length"` (various providers)

Example enriched error:

```
Prompt exceeded claude-opus-4-6's context window of 200000 tokens.
Use hierarchical consolidation to process data in smaller groups.
```

These errors are also logged via the observability service with `event_type: "context_window_exceeded"` and metadata including the provider, model, and context window size.

> **Note:** The overflow error detection uses string matching against provider error messages. This is a pragmatic approach that works across providers today. A TODO exists to refactor this to use LiteLLM's error taxonomy when it stabilizes. See the reviewer comment on PR #567 for context.

## Adding a New Model

When adding a model to any provider config:

1. **Look up the context window** in the provider's official documentation
2. **Add `context_window`** to the model's config dict:
   ```python
   "new-model-name": {
       "context_window": 256000,  # verified against provider docs
       "returns_thoughts": False,
       "parameters": { ... }
   }
   ```
3. **Run the tests** — `test_context_window.py::TestProviderContextWindowMetadata` will fail if any cloud provider model is missing the field
4. **Consider adding a spot-check** to `test_known_context_window_values` for flagship models

## Testing

Tests are in `tests/unit/test_context_window.py` and cover six areas:

| Test Class | What It Covers |
|---|---|
| `TestProviderContextWindowMetadata` | Every cloud provider model has a positive integer `context_window`; spot-checks known values |
| `TestGetContextWindow` | Lookup logic, default fallback for unknown models/providers, presence in exec_globals |
| `TestAgentFactoryContextWindowDocs` | Context window appears in model documentation when present, omitted when absent |
| `TestContextWindowOverflowHandling` | All three overflow error patterns caught and enriched; non-overflow errors pass through |
| `TestBatchProcessingGuidance` | Prompt contains all key patterns: `get_context_window`, `count_tokens`, `create_batches`, `preflight_check`, hierarchical consolidation, skip lists, retry/backoff |
| `TestAgentSandboxContextWindow` | Agent code can call `get_context_window()` at runtime; unknown models return safe default |

Run them with:

```bash
cd webapp/packages/api/user-service
python -m pytest tests/unit/test_context_window.py -v
```

## Troubleshooting

### "Prompt exceeded X's context window"

This means the assembled prompt was too large for the model. Solutions:

1. **Use a model with a larger context window** (e.g., GPT-4.1 at 1M tokens)
2. **Reduce batch sizes** — lower the `SAFE_INPUT_LIMIT` ratio from 0.40 to 0.30
3. **Filter more aggressively** — add skip patterns for files that aren't relevant to the task
4. **Check the consolidation step** — ensure hierarchical consolidation is being used, not naive join

### Agent code hardcodes context window values

If generated code uses magic numbers like `200000` instead of `get_context_window()`, the code generation prompt may not be reaching the LLM effectively. Check that:

1. The model's config has a `context_window` field (so it appears in the model docs section)
2. The `how_to_use_llm` prompt is being included in the code generation request
3. The "ALWAYS use `get_context_window()`" instruction is present in `prompts.py`

### Unknown model returns 128,000 default

This is by design. If `get_context_window()` returns 128,000 for a model you expect to be configured, verify that the provider and model strings match exactly what's in the config (including version suffixes like `-v1:0` for Bedrock models).

---

**Related:** [LLM Provider Configuration](llm-provider-configuration.md) · [Issue #565](https://github.com/The-AI-Alliance/gofannon/issues/565) · [PR #567](https://github.com/The-AI-Alliance/gofannon/pull/567)

**Last Updated:** February 2026
**Maintainer:** AI Alliance Gofannon Team