import logging
import json
from typing import Optional, Dict, Any

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryByDates(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities based on post dates and/or close dates.
    Dates should be in YYYY-MM-DD format.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "query_opportunities_by_dates"):
        super().__init__(api_key=api_key, base_url=base_url, name=name)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        specific_params = {
            "post_start_date": {"type": "string", "description": "Optional. Start of post date range (YYYY-MM-DD)."},
            "post_end_date": {"type": "string", "description": "Optional. End of post date range (YYYY-MM-DD)."},
            "close_start_date": {"type": "string", "description": "Optional. Start of close date range (YYYY-MM-DD)."},
            "close_end_date": {"type": "string", "description": "Optional. End of close date range (YYYY-MM-DD)."},
            "query_text": {
                "type": "string",
                "description": "Optional. Text to search for within the results filtered by dates."
            },
            "query_operator": {
                "type": "string",
                "enum": ["AND", "OR"],
                "description": "Operator for 'query_text' if provided (default: AND).",
                "default": "AND"
            }
        }
        all_properties = {**specific_params, **base_params}

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search for grant opportunities by post and/or close date ranges. "
                    "At least one date parameter must be specified. Dates must be YYYY-MM-DD. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": [] # Logic in fn enforces one date
                }
            }
        }

    def fn(self,
           post_start_date: Optional[str] = None, post_end_date: Optional[str] = None,
           close_start_date: Optional[str] = None, close_end_date: Optional[str] = None,
           query_text: Optional[str] = None, query_operator: str = "AND",
           # Common params
           items_per_page: int = 5, page_number: int = 1, order_by: str = "relevancy",
           sort_direction: str = "descending", show_posted: bool = True, show_forecasted: bool = False,
           show_closed: bool = False, show_archived: bool = False) -> str:

        self.logger.info(f"Querying by dates: post={post_start_date}-{post_end_date}, close={close_start_date}-{close_end_date}, query='{query_text}'")

        specific_filters: Dict[str, Any] = {}
        date_criteria_provided = False

        post_date_filter = {}
        if post_start_date:
            post_date_filter["start_date"] = post_start_date
            date_criteria_provided = True
        if post_end_date:
            post_date_filter["end_date"] = post_end_date
            date_criteria_provided = True
        if post_date_filter:
            specific_filters["post_date"] = post_date_filter

        close_date_filter = {}
        if close_start_date:
            close_date_filter["start_date"] = close_start_date
            date_criteria_provided = True
        if close_end_date:
            close_date_filter["end_date"] = close_end_date
            date_criteria_provided = True
        if close_date_filter:
            specific_filters["close_date"] = close_date_filter

        if not date_criteria_provided and not query_text:
            return json.dumps({"error": "At least one date parameter or query_text must be specified.", "success": False})

        specific_query_params: Optional[Dict[str, Any]] = None
        if query_text:
            specific_query_params = {"query": query_text}

        payload = self._build_api_payload(
            specific_query_params=specific_query_params,
            specific_filters=specific_filters if specific_filters else None,
            items_per_page=items_per_page, page_number=page_number, order_by=order_by,
            sort_direction=sort_direction, show_posted=show_posted, show_forecasted=show_forecasted,
            show_closed=show_closed, show_archived=show_archived, query_operator=query_operator
        )
        return self._execute_search(payload)  