import logging
from typing import Optional, Dict, Any

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryOpportunities(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities using a general text query.
    """
    def __init__(self, api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 name: str = "query_opportunities"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        specific_params = {
            "query_text": {
                "type": "string",
                "description": "The text to search for in opportunity titles, descriptions, etc."
            },
            "query_operator": {
                "type": "string",
                "enum": ["AND", "OR"],
                "description": "Operator for combining terms in 'query_text' (default: AND).",
                "default": "AND"
            }
        }

        # Combine and order parameters as desired for the definition
        # Typically, specific parameters first, then common ones.
        all_properties = {**specific_params, **base_params}

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search for grant opportunities using a text query. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": ["query_text"] # Only query_text is strictly required for this tool
                }
            }
        }

    def fn(self,
           query_text: str,
           query_operator: str = "AND",
           # Common params from base, with defaults
           items_per_page: int = 5,
           page_number: int = 1,
           order_by: str = "relevancy",
           sort_direction: str = "descending",
           show_posted: bool = True,
           show_forecasted: bool = False,
           show_closed: bool = False,
           show_archived: bool = False) -> str:
        """
        Executes the general opportunity search.
        """
        self.logger.info(f"Executing general opportunity query: '{query_text}'")

        specific_query_params = {
            "query": query_text  # API expects "query" not "query_text"
        }

        payload = self._build_api_payload(
            specific_query_params=specific_query_params,
            specific_filters=None, # No other specific filters for this tool
            items_per_page=items_per_page,
            page_number=page_number,
            order_by=order_by,
            sort_direction=sort_direction,
            show_posted=show_posted,
            show_forecasted=show_forecasted,
            show_closed=show_closed,
            show_archived=show_archived,
            query_operator=query_operator
        )

        return self._execute_search(payload)
