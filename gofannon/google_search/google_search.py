from ..base import BaseTool
from googleapiclient.discovery import build
from ..config import ToolConfig, FunctionRegistry
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class GoogleSearch(BaseTool):
    def __init__(self, api_key=None, engine_id=None, name="google_search"):
        super().__init__()
        self.api_key = api_key or ToolConfig.get("google_search_api_key")
        self.engine_id = engine_id or ToolConfig.get("google_search_engine_id")
        self.name = name
        self.API_SERVICE = 'google_search'

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Searches Google for the given query and returns snippets from the results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query."
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "The maximum number of results to return (default: 5)."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def fn(self, query, num_results=5):
        logger.debug(f"Searching Google for: {query}")
        try:
            service = build("customsearch", "v1", developerKey=self.api_key)
            cse = service.cse()
            result = cse.list(q=query, cx=self.engine_id, num=num_results).execute()

            search_results = []
            for item in result['items']:
                search_results.append(f"Title: {item['title']}\nSnippet: {item['snippet']}\nLink: {item['link']}")
            return "\n\n".join(search_results)

        except Exception as e:
            logger.error(f"Error during Google Search: {e}")
            return f"Error during Google Search: {e}"