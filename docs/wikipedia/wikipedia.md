# docs/wikipedia/wikipedia_lookup.md

## wikipedia_lookup
The `wikipedia_lookup` tool queries the Wikipedia REST API and returns a summary of a specified article, including its title, content extract, thumbnail image, and URL.

## Function Constructor Parameters
Function accepts a search query and returns a structured dictionary with article data:

```
{
    "title": "Article Title", 
    "summary": "The article's text extract or summary...",
    "image": "https://example.com/thumbnail-image.jpg",
    "url": "https://en.wikipedia.org/wiki/Article_Title"
}
```

If the article isn't found or an error occurs, it returns:
```
{
    "error": "Failed to fetch Wikipedia summary for [query]"
}
```
## API Parameters
```query```: (string, required) The search term to look up on Wikipedia.

## Example Usage
```
from gofannon.wikipedia.wikipedia_lookup import WikipediaLookup
  
# Create an instance of the tool
wiki_tool = WikipediaLookup()

# Look up an article
result = wiki_tool.fn("Python programming")

# Print the article title and summary
print(f"Title: {result['title']}")
print(f"Summary: {result['summary']}")

# Access the article URL
if "url" in result and result["url"]:
    print(f"Read more: {result['url']}")
```    

## Error Handling

The tool handles API errors gracefully by returning an error dictionary rather than raising exceptions. This makes it safe to use in production environments where continuity is important.

If Wikipedia's API returns a non-200 status code, the tool will return:
```
{
    "error": "Failed to fetch Wikipedia summary for [query]"
}
```