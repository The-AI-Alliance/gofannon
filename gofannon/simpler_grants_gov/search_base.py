import logging
import json
from typing import Optional, Dict, Any, List

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry # Will be used by subclasses

logger = logging.getLogger(__name__)

class SearchOpportunitiesBase(SimplerGrantsGovBase):
    """
    Base class for Simpler Grants Gov tools that search for opportunities.
    Handles common pagination and opportunity status filtering logic.
    """

    # Common descriptions
    _pagination_description = (
        " Control the pagination of results. If not provided, defaults will be used by the API "
        "(typically page 1, a small number of items, and sorted by relevance or ID)."
    )
    _status_filter_description = (
        " Filter results by opportunity status. By default, only 'posted' opportunities are shown. "
        "Set other flags to True to include them."
    )
    _common_search_description_suffix = (
        " Returns a JSON string of matching opportunities."
    )

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "search_opportunities_base"):
        super().__init__(api_key=api_key, base_url=base_url, name=name)
        # 'name' will be overridden by subclasses for their specific tool name

    def _get_common_parameter_definitions(self) -> Dict[str, Any]:
        """
        Returns a dictionary of common parameter definitions for pagination and status.
        """
        return {
            "items_per_page": {
                "type": "integer",
                "description": "Number of results per page (e.g., 10, 25, 50). Default: 5.",
                "default": 5
            },
            "page_number": {
                "type": "integer",
                "description": "The page number to retrieve (starts at 1). Default: 1.",
                "default": 1
            },
            "order_by": {
                "type": "string",
                "description": "Field to sort results by (e.g., 'relevancy', 'post_date', 'opportunity_id', 'agency_code'). Default: 'relevancy'.",
                "default": "relevancy" # API default might be opportunity_id or post_date
            },
            "sort_direction": {
                "type": "string",
                "enum": ["ascending", "descending"],
                "description": "Direction to sort (ascending or descending). Default: 'descending'.",
                "default": "descending"
            },
            "show_posted": {
                "type": "boolean",
                "description": "Include 'posted' opportunities. Default: True.",
                "default": True
            },
            "show_forecasted": {
                "type": "boolean",
                "description": "Include 'forecasted' opportunities. Default: False.",
                "default": False
            },
            "show_closed": {
                "type": "boolean",
                "description": "Include 'closed' opportunities. Default: False.",
                "default": False
            },
            "show_archived": {
                "type": "boolean",
                "description": "Include 'archived' opportunities. Default: False.",
                "default": False
            }
        }

    def _build_api_payload(
            self,
            specific_query_params: Optional[Dict[str, Any]] = None,
            specific_filters: Optional[Dict[str, Any]] = None,
            # Pagination and status args from function call
            items_per_page: int = 5,
            page_number: int = 1,
            order_by: str = "relevancy",
            sort_direction: str = "descending",
            show_posted: bool = True,
            show_forecasted: bool = False,
            show_closed: bool = False,
            show_archived: bool = False,
            query_operator: str = "AND"
    ) -> Dict[str, Any]:
        """
        Constructs the full payload for the /v1/opportunities/search API endpoint.
        """
        payload: Dict[str, Any] = {}

        # 1. Pagination
        payload["pagination"] = {
            "page_offset": page_number,
            "page_size": items_per_page,
            "sort_order": [{"order_by": order_by, "sort_direction": sort_direction}]
        }

        # 2. Query and Specific Query Params
        if specific_query_params and specific_query_params.get("query"): # Check if 'query' key actually has a value
            payload.update(specific_query_params)
            payload["query_operator"] = query_operator
        elif specific_query_params: # If other specific_query_params exist without 'query'
            payload.update(specific_query_params)


            # 3. Filters
        filters_dict: Dict[str, Any] = {}

        # 3a. Opportunity Status Filter
        active_statuses: List[str] = []
        if show_posted:
            active_statuses.append("posted")
        if show_forecasted:
            active_statuses.append("forecasted")
        if show_closed:
            active_statuses.append("closed")
        if show_archived:
            active_statuses.append("archived")

        if active_statuses:
            filters_dict["opportunity_status"] = {"one_of": active_statuses}
        else:
            self.logger.warning("No opportunity statuses selected for filtering.")
            # Consider if an empty list should be sent or if the key should be omitted.
            # For now, omitting if empty, as API might require at least one status if key is present.
            # filters_dict["opportunity_status"] = {"one_of": []} # Alternative

        # 3b. Specific Filters
        if specific_filters:
            filters_dict.update(specific_filters)

        if filters_dict:
            payload["filters"] = filters_dict

        self.logger.debug(f"Constructed API payload: {json.dumps(payload, indent=2)}")
        return payload

    def _execute_search(self, payload: Dict[str, Any]) -> str:
        """
        Shared method to make the API call.
        """
        endpoint = "/v1/opportunities/search"
        try:
            result = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search successful. Response length: {len(result)}")
            return result
        except Exception as e:
            self.logger.error(f"Opportunity search failed: {e}", exc_info=True)
            return json.dumps({"error": f"Opportunity search API request failed: {str(e)}", "success": False})

            # Subclasses will implement their specific 'definition' and 'fn'
    @property
    def definition(self):
        raise NotImplementedError("Subclasses must implement the 'definition' property.")

    def fn(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the 'fn' method.")