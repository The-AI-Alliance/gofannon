import logging
import json
from typing import Optional, Dict, Any, List

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryByAssistanceListing(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities by Assistance Listing Numbers (formerly CFDA numbers).
    Numbers should be in the format '##.###' or '##.##'.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "query_opportunities_by_assistance_listing"):
        super().__init__(api_key=api_key, base_url=base_url, name=name)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        specific_params = {
            "assistance_listing_numbers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of Assistance Listing Numbers (e.g., ['10.001', '93.123']). Must match pattern ##.### or ##.##."
            },
            "query_text": {
                "type": "string",
                "description": "Optional. Text to search for within the results filtered by assistance listing."
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
                    "Search for grant opportunities by one or more Assistance Listing Numbers. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": ["assistance_listing_numbers"]
                }
            }
        }

    def fn(self,
           assistance_listing_numbers: List[str],
           query_text: Optional[str] = None,
           query_operator: str = "AND",
           # Common params
           items_per_page: int = 5,
           page_number: int = 1,
           order_by: str = "relevancy",
           sort_direction: str = "descending",
           show_posted: bool = True,
           show_forecasted: bool = False,
           show_closed: bool = False,
           show_archived: bool = False) -> str:

        self.logger.info(f"Querying by Assistance Listing Numbers: {assistance_listing_numbers}, query='{query_text}'")

        if not assistance_listing_numbers:
            return json.dumps({"error": "assistance_listing_numbers list cannot be empty.", "success": False})
            # Basic pattern validation could be added here for each number if desired,
        # but the API will ultimately validate.

        specific_filters: Dict[str, Any] = {
            "assistance_listing_number": {"one_of": assistance_listing_numbers}
        }

        specific_query_params: Optional[Dict[str, Any]] = None
        if query_text:
            specific_query_params = {"query": query_text}

        payload = self._build_api_payload(
            specific_query_params=specific_query_params,
            specific_filters=specific_filters,
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