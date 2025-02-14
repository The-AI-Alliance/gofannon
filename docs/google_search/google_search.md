# docs/google_search/google_search.md
# google_search

The `google_search` API queries the Google Search API and returns snippets of search results.

## Parameters

*   `query`: The search query.
*   `num_results`: The maximum number of results to return (default: 5).

## Example Usage

```python  
from gofannon.google_search.google_search import GoogleSearch  
  
google_search = GoogleSearch(api_key="YOUR_API_KEY", engine_id="YOUR_ENGINE_ID")  
results = google_search.fn("What is the capital of France?", num_results=3)  
print(results)  
```