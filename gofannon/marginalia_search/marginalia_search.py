from ..base import BaseTool
import requests

from ..config import ToolConfig, FunctionRegistry
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class MarginaliaSearch(BaseTool):
    def __init__(self, api_key=None, name="marginalia_search"):
        super().__init__()
        self.api_key = api_key or ToolConfig.get("marginalia_search_api_key") or 'public'
        self.name = name

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Searches Marginalia for the given query and returns snippets from the results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The maximum number of results to return (default: 10)."
                    },
                        "index": {
                            "type": "integer",
                            "description": "The offset of the result set to begin with (default: 0)."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def fn(self, query, index, limit=10):
        logger.debug(f"Searching Marginalia for: {query}")
        try:
            result = requests.get(f"https://api.marginalia.io/search?q={query}&index={index}&count={limit}")
            search_results = []
            for item in result['results']:
                search_results.append(f"Title: {item['title']}\nSnippet: {item['description']}\nLink: {item['url']}")
            return "\n\n".join(search_results)

        except Exception as e:
            logger.error(f"Error during Marginalia Search: {e}")
            return f"Error during Marginalia Search: {e}"