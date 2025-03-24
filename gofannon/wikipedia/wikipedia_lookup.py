from ..base import BaseTool
from ..config import FunctionRegistry
import logging  
import requests

logger = logging.getLogger(__name__)

"""Wikipedia Lookup Tool for retrieving article summaries from Wikipedia.
This class provides functionality to fetch summaries of Wikipedia articles using the Wikipedia REST API.
Attributes:
    name (str): The name identifier for the tool, defaults to 'wikipedia_lookup'
Methods:
    definition: Returns the OpenAI function definition schema for the tool
    fn(query): Executes the Wikipedia lookup and returns article data
The tool performs the following:
1. Accepts a search query string
2. Makes a GET request to Wikipedia's REST API
3. Returns a dictionary containing:
   - title: The article title
   - summary: The article extract/summary
   - image: URL to the article's thumbnail image (if available)
   - url: URL to the full Wikipedia article page
If the API request fails, it returns an error dictionary.
Example:
    tool = WikipediaLookup()
    result = tool.fn("Python programming")
    # Returns dictionary with article data or error message
Raises:
    Handles HTTP errors internally by returning error dictionary
Returns:
    dict: Article data including title, summary, image URL, and article URL,
          or error message if lookup fails
"""

@FunctionRegistry.register
class WikipediaLookup(BaseTool):
    def __init__(self, name='wikipedia_lookup'):
        super().__init__()
        self.name = name

    @property
    def definition(self):
        return{
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Fetches a Wikipedia summary for a given search term.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search term to look up on Wikipedia."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    def fn(self, query):
        logger.debug(f"Fetching Wikipedia summary for: {query}")
        base_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
        response = requests.get(base_url + query.replace(" ", "_"))

        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title", "No title found"), 
                "summary": data.get("extract", "No summary found"),
                "image": data.get("thumbnail", {}).get("source", None),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", None)
            }
        else:
            return{
                "error": f"Failed to fetch Wikipedia summary for {query}"
            }

