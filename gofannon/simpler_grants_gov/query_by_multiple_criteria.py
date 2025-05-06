import logging
import json
from typing import Optional, Dict, Any, List

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryByMultipleCriteria(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities by combining multiple filter criteria.
    Use this for more complex queries not covered by specialized tools.
    All filter parameters are optional, but at least one filter or query_text should be provided.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "query_opportunities_by_multiple_criteria"):
        super().__init__(api_key=api_key, base_url=base_url, name=name)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        # Parameters from other specific tools, all optional here
        specific_params = {
            "agency_codes": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional. List of agency codes (e.g., ['USAID', 'DOC'])."
            },
            "funding_instruments": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional. List of funding instruments."
            },
            "funding_categories": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional. List of funding categories."
            },
            "applicant_types": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional. List of applicant types."
            },
            "assistance_listing_numbers": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional. List of Assistance Listing Numbers."
            },
            "requires_cost_sharing": {
                "type": "boolean",
                "description": "Optional. Filter by cost-sharing requirement."
            },
            # For simplicity, award criteria and dates are not individual params here.
            # If needed, they could be added, or a user could use a more specific tool.
            "query_text": {
                "type": "string",
                "description": "Optional. Text to search for within filtered results."
            },
            "query_operator": {
                "type": "string", "enum": ["AND", "OR"],
                "description": "Operator for 'query_text' if provided (default: AND).", "default": "AND"
            }
        }
        all_properties = {**specific_params, **base_params}

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search grant opportunities by combining various filters like agency, funding types, applicant types, etc. "
                    "Useful for complex queries. At least one filter criterion or query_text should be provided. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": [] # Logic in fn
                }
            }
        }

    def fn(self,
           agency_codes: Optional[List[str]] = None,
           funding_instruments: Optional[List[str]] = None,
           funding_categories: Optional[List[str]] = None,
           applicant_types: Optional[List[str]] = None,
           assistance_listing_numbers: Optional[List[str]] = None,
           requires_cost_sharing: Optional[bool] = None,
           query_text: Optional[str] = None,
           query_operator: str = "AND",
           # Common params
           items_per_page: int = 5, page_number: int = 1, order_by: str = "relevancy",
           sort_direction: str = "descending", show_posted: bool = True, show_forecasted: bool = False,
           show_closed: bool = False, show_archived: bool = False) -> str:

        self.logger.info(f"Querying by multiple criteria, query='{query_text}'")

        specific_filters: Dict[str, Any] = {}
        any_filter_provided = False

        if agency_codes:
            specific_filters["agency"] = {"one_of": agency_codes}
            any_filter_provided = True
        if funding_instruments:
            specific_filters["funding_instrument"] = {"one_of": funding_instruments}
            any_filter_provided = True
        if funding_categories:
            specific_filters["funding_category"] = {"one_of": funding_categories}
            any_filter_provided = True
        if applicant_types:
            specific_filters["applicant_type"] = {"one_of": applicant_types}
            any_filter_provided = True
        if assistance_listing_numbers:
            specific_filters["assistance_listing_number"] = {"one_of": assistance_listing_numbers}
            any_filter_provided = True
        if requires_cost_sharing is not None:
            specific_filters["is_cost_sharing"] = {"one_of": [requires_cost_sharing]}
            any_filter_provided = True

        if not any_filter_provided and not query_text:
            return json.dumps({"error": "At least one filter criterion or query_text must be specified for this tool.", "success": False})

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
