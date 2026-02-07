how_to_use_tools = """
# How to Call Tools

You are provided with a pre-initialized dictionary of clients called `mcpc`.
- The keys of `mcpc` are the MCP server URLs (e.g., 'http://example.com/mcp').
- The values are client objects used to call tools on that server.

**ALL tool calls are asynchronous and MUST use the `await` keyword.**

To call a tool, you **MUST** use the `.call()` method on the appropriate client object from the `mcpc` dictionary.

Here is the documentation for the `call` method:
`async def call(self, tool_name: str, **params: Any) -> Any:`
    Calls a specific tool exposed by the remote MCP server.

    This method sends a request to the server to execute a function
    (a "tool") by its registered name, passing the required arguments.

    :param tool_name:
        The **name** of the tool (function) as a string.
        (e.g., 'query_database', 'add_item').
    :param params:
        Keyword arguments (key=value) corresponding to the tool's expected
        input parameters.

    :return:
        The result from the remote tool. The type depends on what the tool returns.

    :Example:
    >>> # To call the 'calculate_tax' tool on the server at 'http://tax.api/mcp'
    >>> tax_result = await mcpc['http://tax.api/mcp'].call(
    ...     tool_name="calculate_tax",
    ...     amount=100.00,
    ...     rate=0.07
    ... )
    >>> print(tax_result)
    7.00
    
"""

how_to_use_llm = """
You have access to the `call_llm` function for making calls to language models.
The specific models you can call are listed in the section above.
For each invokable model, you are given the configured parameters and any selected built-in tool.
When you call a listed model, pass the parameters exactly as shown, and include the `tools` argument
only when a built-in tool is selected for that model.

To make a call, use `await call_llm()`:

async def call_llm(provider: str, model: str, messages: list, parameters: dict, ...) -> tuple[str, Any]:
    '''
    Makes an asynchronous call to a language model through the centralized LLM service.

    :param provider:
        The provider name (e.g., 'openai', 'anthropic', 'gemini').
    :param model:
        The model name without the provider prefix (e.g., 'gpt-4', 'claude-3-opus').
    :param messages:
        A list of dictionaries representing the conversation history,
        following the format: `[{"role": "user", "content": "Hello"}, ...]`.
    :param parameters:
        A dictionary of additional parameters to pass to the model provider's API,
        such as `temperature`, `max_tokens`, `top_p`, etc.
    :param tools:
        Optional list of built-in tool configurations. See "Using Built-in Tools" below.
    :param user_service:
        Optional user service for tracking usage (set to None if not needed).
    :param user_id:
        Optional user ID for tracking usage (set to None if not needed).

    :return:
        A tuple of (content, thoughts) where content is the string response
        and thoughts contains any reasoning/tool call information.

    :Example:
    >>> content, thoughts = await call_llm(
    ...     provider="openai",
    ...     model="gpt-4",
    ...     messages=[{"role": "user", "content": "Summarize this for me."}],
    ...     parameters={"temperature": 0.7, "max_tokens": 150},
    ...     user_service=None,
    ...     user_id=None,
    ... )
    >>> print(content)
    "This is a summary." # (Example Output)
    '''

## Context Window Lookup

You also have access to `get_context_window()` to look up a model's maximum input size at runtime:

```python
def get_context_window(provider: str, model: str) -> int:
    '''Returns the context window (max input tokens) for the given provider/model.
    Use this to dynamically size batches instead of hardcoding limits.'''

# Example:
ctx = get_context_window("anthropic", "claude-opus-4-6")  # returns 200000
ctx = get_context_window("openai", "gpt-4.1")             # returns 1000000
```

## Token Counting (CRITICAL for batch processing)

You have access to **exact token counting** functions. ALWAYS use these instead of character-based estimation:

```python
def count_tokens(text: str, provider: str = "anthropic", model: str = "claude-opus-4-6") -> int:
    '''Count exact tokens for a text string using the model's actual tokenizer.
    MUCH more accurate than character-based estimation (len(text) / N).'''

def count_message_tokens(messages: list, provider: str = "anthropic", model: str = "claude-opus-4-6") -> int:
    '''Count exact tokens for a full messages list (as you'd pass to call_llm).
    Includes message framing overhead. Use this for pre-flight checks.'''

# Example:
tokens = count_tokens("def hello():\n    print('hi')", "anthropic", "claude-opus-4-6")
msg_tokens = count_message_tokens([{"role": "user", "content": my_prompt}], provider, model)
```

**WARNING:** Character-based estimation (e.g., `len(text) / 3`) is unreliable and can undercount by 30-50% for code. Code, JSON, and structured data tokenize at ~2-3 chars/token, not 3-4. ALWAYS use `count_tokens()` or `count_message_tokens()` for accurate counts.

**ALWAYS use `get_context_window()` and `count_tokens()`/`count_message_tokens()` when implementing batch processing.** Never hardcode context window values or use character-based estimation.

## Using Built-in Tools

Some models support built-in tools like web search, code execution, or URL context.
To use these tools, pass the `tools` parameter with a list of tool configurations.

**OpenAI Web Search** (for models like gpt-4o, gpt-5, o3, etc.):
```python
content, thoughts = await call_llm(
    provider="openai",
    model="gpt-4o",
    messages=[{"role": "user", "content": "What are the latest news about AI?"}],
    parameters={},
    tools=[{"type": "web_search", "search_context_size": "medium"}],
    user_service=None,
    user_id=None,
)
```

**Gemini Google Search** (for models like gemini-2.5-pro, gemini-2.5-flash):
```python
content, thoughts = await call_llm(
    provider="gemini",
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Search for recent developments in quantum computing."}],
    parameters={},
    tools=[{"google_search": {}}],
    user_service=None,
    user_id=None,
)
```

**Gemini Code Execution**:
```python
content, thoughts = await call_llm(
    provider="gemini",
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Calculate the factorial of 10 using Python."}],
    parameters={},
    tools=[{"codeExecution": {}}],
    user_service=None,
    user_id=None,
)
```

**Note:** Not all models support all tools. Check the model documentation above to see which built-in tools are available for each model.

## Batch Processing Guidance

When processing large datasets or multiple items, follow these best practices to avoid token limits and ensure reliable results:

### CRITICAL: Context Window Limits
**Every model has a maximum input size (context window).** If your prompt exceeds this limit, the API call will FAIL with an error.
- **Use `get_context_window(provider, model)`** to look up the limit at runtime — NEVER hardcode it
- **Use `count_tokens(text, provider, model)`** for EXACT token counts — NEVER use character-based estimation (len(text)/N is unreliable and can undercount by 30-50%)
- **Use `count_message_tokens(messages, provider, model)`** to check the FULL messages list before calling call_llm
- **Use 40% of the model's context window as your safe limit** for batch content. The remaining 60% covers system prompts, user message templates, instructions, response tokens, and safety margin.
- **Pre-flight check**: Before EVERY `call_llm`, count exact tokens. If over 80% of context window, split further.
- **Error resilience**: ALWAYS wrap `call_llm` in try/except and continue on failure — don't retry the same oversized prompt.

### Token Counting and Context Window Lookup
```python
# ALWAYS look up the context window dynamically — never hardcode!
CONTEXT_WINDOW = get_context_window(provider, model)  # e.g. 200000 for claude-opus-4-6
SAFE_INPUT_LIMIT = int(CONTEXT_WINDOW * 0.40)  # 40% for content, 60% for prompts + response + margin

# Use EXACT token counting — never character-based estimation!
# count_tokens() and count_message_tokens() are available in the agent sandbox.
system_tokens = count_tokens(system_prompt, provider, model)
content_tokens = count_tokens(file_content, provider, model)

# Budget your prompt template overhead:
SYSTEM_PROMPT_TOKENS = count_tokens(system_prompt, provider, model)
USER_TEMPLATE_TOKENS = count_tokens(template_text_without_content, provider, model)
BATCH_CONTENT_LIMIT = SAFE_INPUT_LIMIT - SYSTEM_PROMPT_TOKENS - USER_TEMPLATE_TOKENS

# PRE-FLIGHT CHECK — REQUIRED before every call_llm:
def preflight_check(messages, provider, model):
    \"\"\"Verify assembled prompt fits within context window. Returns token count.\"\"\"
    total = count_message_tokens(messages, provider, model)
    limit = int(get_context_window(provider, model) * 0.80)
    if total > limit:
        raise ValueError(f\"Prompt too large: {{total}} tokens > {{limit}} limit (80% of context window)\")
    return total
```

### Token-Aware Batching
Create batches that fit within the model's context window:
```python
def create_batches(items_dict, max_tokens_per_batch, provider, model):
    \"\"\"Split items into batches that fit within the token budget.
    Uses exact token counting for accurate sizing.
    Oversized single items get their own batch — process_batch will chunk them.\"\"\"
    batches = []
    current_batch = {{}}
    current_tokens = 0
    for key, content in items_dict.items():
        content_str = content if isinstance(content, str) else json.dumps(content, default=str)
        item_tokens = count_tokens(content_str, provider, model)
        # If a single item exceeds the limit, give it its own batch
        # (process_batch will split it into overlapping chunks — no truncation here)
        if item_tokens > max_tokens_per_batch:
            if current_batch:
                batches.append(current_batch)
                current_batch = {{}}
                current_tokens = 0
            batches.append({{key: content_str}})
            continue
        if current_tokens + item_tokens > max_tokens_per_batch and current_batch:
            batches.append(current_batch)
            current_batch = {{}}
            current_tokens = 0
        current_batch[key] = content_str
        current_tokens += item_tokens
    if current_batch:
        batches.append(current_batch)
    return batches

batches = create_batches(file_contents, max_tokens_per_batch=BATCH_CONTENT_LIMIT, provider=provider, model=model)
```

### Processing Batches with Error Resilience
**ALWAYS wrap call_llm in try/except.** If a prompt is too large, split the batch and retry the halves — never lose data.
```python
def split_oversized_item(key, content, max_tokens, provider, model, overlap_lines=50):
    \"\"\"Split a single oversized item (e.g., a large file) into overlapping chunks.
    Each chunk shares `overlap_lines` lines with its neighbor so nothing is missed
    at chunk boundaries. Returns a list of (chunk_key, chunk_content) tuples.
    Falls back to character-based splitting for single-line files.\"\"\"
    lines = content.split("\\n")

    # If the file is effectively a single line (or very few lines that are each huge),
    # fall back to character-based splitting to avoid infinite recursion
    if len(lines) <= 2:
        # Character-based split: estimate chars per token, split by chars
        total_tokens = count_tokens(content, provider, model)
        if total_tokens <= max_tokens:
            return [(key, content)]  # Fits already
        chars_per_token = max(1, len(content) / max(1, total_tokens))
        chunk_size = int(max_tokens * chars_per_token * 0.9)  # 10% safety margin
        overlap_chars = min(500, chunk_size // 5)  # Character overlap
        chunks = []
        start = 0
        chunk_num = 1
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_content = content[start:end]
            chunk_key = f"{{key}} [char-chunk {{chunk_num}}/?, chars {{start}}-{{end}}]"
            chunks.append((chunk_key, chunk_content))
            chunk_num += 1
            start = end - overlap_chars if end < len(content) else end
        total = len(chunks)
        return [(k.replace("/?", f"/{{total}}"), v) for k, v in chunks]

    # Normal line-based splitting
    chunks = []
    start = 0
    chunk_num = 1
    while start < len(lines):
        # Binary search for how many lines fit
        end = len(lines)
        while end > start + 1:
            candidate = "\\n".join(lines[start:end])
            tokens = count_tokens(candidate, provider, model)
            if tokens <= max_tokens:
                break
            end = start + (end - start) // 2
        chunk_content = "\\n".join(lines[start:end])
        chunk_key = f"{{key}} [chunk {{chunk_num}}/?, lines {{start+1}}-{{end}}]"
        chunks.append((chunk_key, chunk_content))
        chunk_num += 1
        # Advance with overlap so boundary code is analyzed twice
        start = max(end - overlap_lines, end - 1) if end < len(lines) else end
    # Fix chunk labels now that we know the total
    total = len(chunks)
    return [(k.replace("/?", f"/{{total}}"), v) for k, v in chunks]

async def process_batch(batch, batch_label, provider, model, configured_params, context_window, _depth=0):
    \"\"\"Process a single batch with pre-flight check and automatic splitting.
    Returns a list of result strings (usually 1, but more if batch was split).\"\"\"
    MAX_RECURSION_DEPTH = 10
    if _depth >= MAX_RECURSION_DEPTH:
        keys = list(batch.keys())
        print(f"WARNING: {{batch_label}} hit max recursion depth ({{MAX_RECURSION_DEPTH}}). Skipping files: {{keys}}", flush=True)
        return [f"[Skipped {{batch_label}}: exceeded max split depth. Files may be too large or unsplittable: {{keys}}]"]

    # Build your prompt from the batch contents...
    user_message = build_prompt(batch)  # your prompt-building logic here
    messages = [{{"role": "user", "content": user_message}}]

    # Pre-flight check with exact counting
    try:
        actual_tokens = count_message_tokens(messages, provider, model)
        limit = int(context_window * 0.80)
        if actual_tokens > limit:
            print(f"{{batch_label}} too large ({{actual_tokens}} tokens > {{limit}} limit), splitting...", flush=True)
            items = list(batch.items())
            if len(items) > 1:
                # Multiple items — split batch in half, process each recursively
                mid = len(items) // 2
                left = dict(items[:mid])
                right = dict(items[mid:])
                results_left = await process_batch(left, f"{{batch_label}}a", provider, model, configured_params, context_window, _depth + 1)
                results_right = await process_batch(right, f"{{batch_label}}b", provider, model, configured_params, context_window, _depth + 1)
                return results_left + results_right
            else:
                # Single oversized item — split into overlapping chunks (no data loss)
                key, content = items[0]
                content_budget = limit - count_tokens(build_prompt_template(), provider, model)
                chunks = split_oversized_item(key, content, content_budget, provider, model)
                if len(chunks) <= 1 and count_tokens(chunks[0][1] if chunks else content, provider, model) > limit:
                    # split_oversized_item couldn't actually reduce size — bail out
                    print(f"  WARNING: Cannot split {{key}} further. Skipping.", flush=True)
                    return [f"[Skipped {{key}}: file too large to split ({{actual_tokens}} tokens)]"]
                print(f"  Split {{key}} into {{len(chunks)}} overlapping chunks", flush=True)
                results = []
                for chunk_key, chunk_content in chunks:
                    chunk_batch = {{chunk_key: chunk_content}}
                    chunk_results = await process_batch(chunk_batch, f"{{batch_label}}-{{chunk_key}}", provider, model, configured_params, context_window, _depth + 1)
                    results.extend(chunk_results)
                return results
    except Exception:
        pass  # If counting fails, try anyway

    try:
        content, thoughts = await call_llm(
            provider=provider, model=model,
            messages=messages,
            parameters=configured_params,
        )
        return [content]
    except Exception as e:
        error_str = str(e)
        if "prompt is too long" in error_str or "context_length_exceeded" in error_str or "context window" in error_str.lower():
            # Overflow at API level — split and retry
            items = list(batch.items())
            if len(items) > 1:
                mid = len(items) // 2
                print(f"{{batch_label}} overflowed API limit, splitting into 2 sub-batches...", flush=True)
                results_left = await process_batch(dict(items[:mid]), f"{{batch_label}}a", provider, model, configured_params, context_window, _depth + 1)
                results_right = await process_batch(dict(items[mid:]), f"{{batch_label}}b", provider, model, configured_params, context_window, _depth + 1)
                return results_left + results_right
            else:
                # Single item overflow — split into overlapping chunks
                key, content = items[0]
                safe_budget = int(context_window * 0.30)  # very conservative for retry
                chunks = split_oversized_item(key, content, safe_budget, provider, model)
                if len(chunks) <= 1:
                    return [f"[Skipped {{key}}: file too large to split after API overflow]"]
                print(f"  Split {{key}} into {{len(chunks)}} overlapping chunks after overflow", flush=True)
                results = []
                for chunk_key, chunk_content in chunks:
                    chunk_batch = {{chunk_key: chunk_content}}
                    try:
                        chunk_results = await process_batch(chunk_batch, f"{{batch_label}}-chunk", provider, model, configured_params, context_window, _depth + 1)
                        results.extend(chunk_results)
                    except Exception:
                        results.append(f"[Failed to process {{chunk_key}}]")
                return results if results else [f"[{{batch_label}} failed: {{error_str}}]"]
        else:
            return [f"[{{batch_label}} failed: {{error_str}}]"]

# Process all batches
batch_results = []
for i, batch in enumerate(batches):
    results = await process_batch(batch, f"Batch {{i+1}}", provider, model, configured_params, CONTEXT_WINDOW)
    batch_results.extend(results)
```

### Hierarchical Consolidation Pattern (REQUIRED for large datasets)
**IMPORTANT:** The consolidation step itself can exceed the context window if you join all batch results into one prompt.
**NEVER do this:**
```python
# ❌ WRONG — this will overflow if batch_results is large!
final_result, _ = await call_llm(..., f"Consolidate: {{batch_results}}", ...)
```

**Always use hierarchical (tree-style) consolidation** that groups results by exact token budget:
```python
# Hierarchical consolidation — merge groups that fit in the context window
CONSOLIDATION_TEMPLATE_TOKENS = count_tokens(consolidation_instructions, provider, model)
MAX_CONSOLIDATION_CONTENT = SAFE_INPUT_LIMIT - CONSOLIDATION_TEMPLATE_TOKENS

while len(batch_results) > 1:
    next_level = []
    group = []
    group_tokens = 0

    for result in batch_results:
        result_tokens = count_tokens(result, provider, model)
        if group and (group_tokens + result_tokens) > MAX_CONSOLIDATION_CONTENT:
            # This group is full — consolidate it
            try:
                consolidated, _ = await call_llm(
                    provider=provider, model=model,
                    messages=[{{"role": "user", "content":
                        f"Consolidate these analyses into a unified summary:\\n\\n"
                        + "\\n---\\n".join(group)}}],
                    parameters=parameters,
                )
                next_level.append(consolidated)
            except Exception as e:
                # If consolidation fails, keep the individual results
                next_level.extend(group)
            group = []
            group_tokens = 0
        group.append(result)
        group_tokens += result_tokens

    # Consolidate the remaining group
    if group:
        if len(group) == 1 and not next_level:
            # Only one result left — we're done
            next_level.append(group[0])
        else:
            try:
                consolidated, _ = await call_llm(
                    provider=provider, model=model,
                    messages=[{{"role": "user", "content":
                        f"Consolidate these analyses into a unified summary:\\n\\n"
                        + "\\n---\\n".join(group)}}],
                    parameters=parameters,
                )
                next_level.append(consolidated)
            except Exception as e:
                next_level.extend(group)

    batch_results = next_level

final_result = batch_results[0]
```

### Skip Lists for Efficiency
When processing files from repositories or data stores, skip non-code files that waste tokens and provide no security/analysis value:
```python
# Directories to skip entirely
SKIP_DIRS = {{
    'docs', 'doc', 'documentation',
    'node_modules', 'vendor', 'third_party', 'third-party',
    'dist', 'build', 'out', 'target',
    '__pycache__', '.pytest_cache', '.mypy_cache', 'coverage', '.next', '.nuxt',
    'assets', 'images', 'img', 'static/images', 'static/fonts', 'static/webfonts',
    'public/images', 'fonts', 'webfonts',
    '.github/workflows',
    'test', 'tests', 'spec', 'specs',
    'migrations',
    'venv', '.venv', 'env', '.env',
    '.git', '.idea', '.vscode',
}}

# Specific filenames to skip
SKIP_FILES = {{
    'package-lock.json', 'yarn.lock', 'poetry.lock', 'Cargo.lock',
    'composer.lock', 'pnpm-lock.yaml', 'Gemfile.lock', 'uv.lock',
    'LICENSE', 'LICENSE.md', 'LICENSE.txt',
    'README.md', 'README.rst', 'README.txt', 'README',
    'CHANGELOG.md', 'CHANGELOG', 'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md',
    '.gitignore', '.dockerignore', '.prettierrc', '.eslintrc', '.editorconfig',
    'Makefile', 'Dockerfile', '.npmrc', '.yarnrc',
    'tsconfig.json', 'jsconfig.json', 'babel.config.js',
    'webpack.config.js', 'rollup.config.js', 'vite.config.js', 'jest.config.js',
}}

# File extensions to skip (non-code, binary, minified, static assets)
SKIP_EXTENSIONS = {{
    # Minified / bundled
    '.min.js', '.min.css', '.bundle.js', '.bundle.css',
    # Source maps
    '.map',
    # Stylesheets (rarely security-relevant)
    '.css', '.scss', '.less', '.sass', '.styl',
    # Fonts
    '.woff', '.woff2', '.ttf', '.eot', '.otf',
    # Images
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.bmp',
    # Media
    '.mp3', '.mp4', '.wav', '.avi', '.mov', '.webm', '.ogg',
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    # Archives
    '.zip', '.tar', '.gz', '.rar', '.7z',
    # Lock files
    '.lock',
    # Binaries / compiled
    '.exe', '.dll', '.so', '.dylib', '.pyc', '.pyo', '.class', '.o', '.obj',
}}

def should_skip_file(filepath):
    \"\"\"Check if a file should be skipped based on directory, name, or extension rules.
    Returns (should_skip: bool, reason: str or None).\"\"\"
    path_lower = filepath.lower()
    parts = filepath.split('/')

    # Check directory patterns
    for part in parts[:-1]:  # all but filename
        if part.lower() in SKIP_DIRS:
            return True, f"directory: {{part}}"

    filename = parts[-1] if parts else ''

    # Check filename
    if filename in SKIP_FILES:
        return True, f"filename: {{filename}}"

    # Check extensions
    for ext in SKIP_EXTENSIONS:
        if path_lower.endswith(ext):
            return True, f"extension: {{ext}}"

    return False, None

# Filter files before batching
filtered_files = {{}}
skipped_count = 0
for key, content in all_files.items():
    skip, reason = should_skip_file(key)
    if skip:
        skipped_count += 1
        continue
    filtered_files[key] = content

print(f"Filtered: {{len(filtered_files)}} files to analyze, {{skipped_count}} skipped")
batches = create_batches(filtered_files, max_tokens_per_batch=BATCH_CONTENT_LIMIT, provider=provider, model=model)
```
**IMPORTANT:** Always filter files BEFORE batching, not after. This saves tokens and reduces the number of batches needed.

### Output Format Recommendations
- **Prefer Markdown over JSON** for large outputs — it's more token-efficient and readable
- Use structured Markdown (headers, lists, tables) for organized data
- Reserve JSON for programmatic consumption or when exact structure is required
- Markdown is also easier to consolidate across batches

### Consolidation Quality Checks
When consolidating multi-batch results:
- **Deduplicate** — merge findings describing the same thing
- **Check contradictions** — if something is positive in one batch and negative in another, investigate
- **Verify data origins** — ensure findings reference real data, not artifacts of batch splitting
- **Consistent formatting** — ensure severity ratings, categories, etc. are consistent

### Error Handling for Batch Operations
```python
async def process_with_retry(item, max_retries=3):
    for attempt in range(max_retries):
        try:
            result, _ = await call_llm(...)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                return {{"error": str(e), "item": item}}
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Memory Management
- For very large datasets (1000+ items), consider streaming results to storage
- Don't accumulate all results in memory before returning
- Use generators or async iterators when possible
"""


how_to_use_swagger_tools = """
# How to Call Tools from an OpenAPI/Swagger Spec

You are also provided with a pre-initialized asynchronous HTTP client called `http_client` from the `httpx` library.
You **MUST** use this client to make any HTTP requests to the APIs defined in the OpenAPI/Swagger specifications.

**Important notes:**
- The `http_client` is configured to automatically follow HTTP redirects.
- Always prefer `https://` URLs over `http://` URLs when available.
- **ALL HTTP calls are asynchronous and MUST use the `await` keyword.**

Here is an example of how to use `http_client` to make a GET request:

:Example:
>>> # To call the 'getUser' operation from the 'user_api' spec
>>> # The base URL is provided in the tool's documentation.
>>> response = await http_client.get(
...     "https://api.example.com/v1/users/123",
...     headers={"Authorization": "Bearer YOUR_API_KEY"} # if needed
... )
>>> # ALWAYS check if the request was successful
>>> response.raise_for_status() 
>>> user_data = response.json()
>>> print(user_data)

To make a POST request with a JSON body:
:Example:
>>> new_user_data = {"name": "John Doe", "email": "john.doe@example.com"}
>>> response = await http_client.post(
...     "https://api.example.com/v1/users",
...     json=new_user_data
... )
>>> response.raise_for_status()
>>> created_user = response.json()

Refer to the specific documentation for each tool to know the correct URL, HTTP method, and what parameters (query, path, body) are expected.
"""

how_to_use_gofannon_agents = """
# How to Call Other Gofannon Agents

You are provided with a pre-initialized client called `gofannon_client` to call other Gofannon agents that have been imported into your context.

**ALL agent calls are asynchronous and MUST use the `await` keyword.**

To call another agent, you **MUST** use the `.call()` method on the `gofannon_client`.

Here is the documentation for the `call` method:
`async def call(self, agent_name: str, input_dict: dict) -> Any:`
    Calls a specific Gofannon agent by its name.

    :param agent_name:
        The **name** of the agent as a string.
    :param input_dict:
        A dictionary conforming to the target agent's input schema.

    :return:
        The result from the remote agent. The type depends on what the agent returns.

    :Example:
    >>> # To call the 'stock_analyzer' agent
    >>> analysis = await gofannon_client.call(
    ...     agent_name="stock_analyzer",
    ...     input_dict={"stock_symbol": "GOOGL"}
    ... )
    >>> print(analysis)
    {"recommendation": "buy", "confidence": 0.85}
"""

how_to_use_data_store = """
# How to Use the Data Store

You are provided with a pre-initialized `data_store` object for persisting data across agent executions.
Data stored here is available to ALL agents owned by the same user, enabling workflows where one agent
creates data that another agent consumes.

**Data store operations are synchronous (no `await` needed).**

## Discovering Available Data

Before querying, you can discover what namespaces contain data:

```python
# List all namespaces that have data
namespaces = data_store.list_namespaces()
# Returns: ["default", "files:apache/repo", "summary:apache/repo", ...]

# Then work with discovered namespaces
for ns in namespaces:
    if ns.startswith("files:"):
        files_ns = data_store.use_namespace(ns)
        keys = files_ns.list_keys()
        print(f"Found {len(keys)} files in {ns}")
```

## Basic Operations

```python
# Store a value (any JSON-serializable data)
data_store.set("my-key", {"analysis": "results", "score": 95})

# Retrieve a value (returns None if not found)
value = data_store.get("my-key")

# Retrieve with a default value
value = data_store.get("missing-key", default={"empty": True})

# Delete a value
data_store.delete("my-key")

# List all keys in the current namespace
keys = data_store.list_keys()

# List keys matching a prefix
keys = data_store.list_keys(prefix="analysis:")
```

## Using Namespaces

Namespaces help organize data by purpose. The default namespace is "default".

```python
# Switch to a specific namespace
summaries = data_store.use_namespace("repo-summaries")
summaries.set("src/main.py", {"functions": ["main", "init"], "lines": 150})

# Read from the namespace
file_info = summaries.get("src/main.py")

# Use different namespaces for different purposes
cache = data_store.use_namespace("analysis-cache")
cache.set("last-run", {"timestamp": "2026-02-03", "status": "complete"})
```

## Batch Operations

```python
# Set multiple values at once
data_store.set_many({
    "file:a.py": {"lines": 100},
    "file:b.py": {"lines": 200},
    "file:c.py": {"lines": 50},
})

# Get multiple values at once
results = data_store.get_many(["file:a.py", "file:b.py"])
# Returns: {"file:a.py": {"lines": 100}, "file:b.py": {"lines": 200}}
```

## Common Patterns

### Discovering and searching across all data
```python
# Find all namespaces with data
namespaces = data_store.list_namespaces()

# Search for data across namespaces
for ns in namespaces:
    ns_store = data_store.use_namespace(ns)
    keys = ns_store.list_keys()
    # Process keys...
```

### Caching expensive operations
```python
cache_key = f"analysis:{file_path}"
cached = data_store.get(cache_key)
if cached:
    return cached

# Do expensive analysis...
result = await call_llm(...)

# Cache for future runs
data_store.set(cache_key, result)
return result
```

### Building up results across multiple runs
```python
summaries = data_store.use_namespace("code-summaries")

# Store this run's result
summaries.set(input_dict["file_path"], analysis_result)

# Get all accumulated results
all_keys = summaries.list_keys()
all_summaries = summaries.get_many(all_keys)
```

### Passing data between agents
```python
# Agent A: Store results for Agent B
data_store.use_namespace("shared-analysis").set("quarterly-report", report_data)

# Agent B: Read Agent A's results
report = data_store.use_namespace("shared-analysis").get("quarterly-report")
```

### Working with dynamic namespace names
```python
# Namespaces often include context like repo names
# e.g., "files:apache/tooling-trusted-releases", "summary:apache/tooling-trusted-releases"

repo_name = input_dict.get("repo", "")
files_ns = data_store.use_namespace(f"files:{repo_name}")
summary_ns = data_store.use_namespace(f"summary:{repo_name}")

# Store file content
files_ns.set(file_path, file_content)

# Store file summary
summary_ns.set(file_path, {"summary": "...", "key_points": [...]})
```
"""

what_to_do_prompt_template = """
You are tasked with writing the body of an asynchronous Python function with the signature `async def run(input_dict: dict, tools: dict) -> dict:`.

This function will receive:
- `input_dict`: A dictionary conforming to the following input schema.
- `tools`: A dictionary of tool configurations.

An asynchronous HTTP client `http_client` is available for making API calls to Swagger/OpenAPI specs.
A client for calling other Gofannon agents named `gofannon_client` is also available if you have imported any.
A dictionary of MCP clients named `mcpc` is already initialized for you like this:
`mcpc = {{ url : RemoteMCPClient(remote_url = url) for url in tools.keys() }}`
You can use it to call tools as described in the documentation.

**Available in the Sandbox:**
- `mcpc` - Dictionary of MCP clients for calling external tools
- `http_client` - Async HTTP client (httpx) for REST API calls
- `call_llm` - For calling language models via `await call_llm(provider, model, messages, parameters, ...)`
- `gofannon_client` - For calling other Gofannon agents
- `data_store` - For persisting and sharing data across agent executions (see data store documentation)
- `asyncio`, `json`, `re` - Standard Python libraries

**Input Schema:**
```json
{input_schema}
```

**Output Schema:**
The function **MUST** return a dictionary that conforms to the following output schema.
```json
{output_schema}
```

**Instructions:**
Your task is to implement the logic for this function based on the user's request.
ONLY return the Python code for the function body.
- Do NOT include the `async def run(...)` function signature.
- Do NOT include any imports.
- Do NOT wrap the code in Markdown backticks (```).
- Do NOT add any explanations or surrounding text.
- Your code will be executed inside an `async` function, so you can and should use `await` for async calls.
"""


how_to_build_demo_app_template = """
You are an expert web developer. Your task is to create a single-page web application using only vanilla HTML, CSS, and JavaScript.

**Restrictions:**
- **DO NOT** use any frameworks or libraries like React, Vue, Angular, jQuery, etc. Stick to modern, standard browser APIs.
- Your entire output **MUST** be a single JSON object.

**Instructions:**
1. You will be given a user's description of what the app should look like and do.
2. You will also be given a list of available REST APIs that you can call to fetch data.
3. The base URL for all API calls is available in a pre-defined JavaScript constant called `API_BASE_URL`. You **MUST** use this constant when making `fetch` requests.
   For example, to call an endpoint `/rest/my_api`, your JavaScript code should look like this: `fetch(`${{API_BASE_URL}}/rest/my_api`, ...)`
4. Make the user interface clean, modern, and user-friendly. Use CSS for styling.
5. Your JavaScript should be well-structured and handle API calls asynchronously using `async/await` and `fetch`. It should also include error handling for API calls.

**Output Format:**
Return your response as a single, valid JSON object with three keys: "html", "css", and "js".
- `html`: A string containing the HTML body content. Do not include `<html>`, `<head>`, or `<body>` tags.
- `css`: A string containing all the CSS styles for the application. Do not include `<style>` tags.
- `js`: A string containing all the JavaScript logic for the application. Do not include `<script>` tags.

**Available APIs:**
{api_docs}

**User's Request for the application:**
{user_prompt}
"""