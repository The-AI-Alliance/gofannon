import logging
from typing import Optional, Dict, Any, List

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryOpportunitiesByAgencyCode(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities filtered by agency code(s).
    Optionally, a text query can also be provided.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "query_opportunities_by_agency"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        specific_params = {
            "agency_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of agency codes to filter by (e.g., ['USAID', 'DOC'])."
            },
            "query_text": {
                "type": "string",
                "description": "Optional. Text to search for within the results filtered by agency."
            },
            "query_operator": {
                "type": "string",
                "enum": ["AND", "OR"],
                "description": "Operator for combining terms in 'query_text' if provided (default: AND).",
                "default": "AND"
            }
        }
        all_properties = {**specific_params, **base_params}

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search for grant opportunities filtered by one or more agency codes. "
                    "An optional text query can further refine results. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": ["agency_codes"]
                }
            }
        }

    def fn(self,
           agency_codes: List[str],
           query_text: Optional[str] = None,
           query_operator: str = "AND",
           # Common params from base
           items_per_page: int = 5,
           page_number: int = 1,
           order_by: str = "relevancy",
           sort_direction: str = "descending",
           show_posted: bool = True,
           show_forecasted: bool = False,
           show_closed: bool = False,
           show_archived: bool = False) -> str:
        """
        Executes the opportunity search filtered by agency codes.
        """
        self.logger.info(f"Executing opportunity query by agency codes: {agency_codes}, query_text: '{query_text}'")

        if not agency_codes:
            logger.error("agency_codes list cannot be empty.")
            return json.dumps({"error": "agency_codes list cannot be empty.", "success": False})

        specific_filters: Dict[str, Any] = {
            "agency": {"one_of": agency_codes}
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