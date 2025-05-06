import logging
import json
from typing import Optional, Dict, Any

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryByAwardCriteria(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities based on award amount criteria.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "query_opportunities_by_award_criteria"):
        super().__init__(api_key=api_key, base_url=base_url, name=name)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        specific_params = {
            "min_award_floor": {"type": "integer", "description": "Optional. Minimum award floor amount."},
            "max_award_ceiling": {"type": "integer", "description": "Optional. Maximum award ceiling amount."},
            "min_expected_awards": {"type": "integer", "description": "Optional. Minimum number of expected awards."},
            "max_expected_awards": {"type": "integer", "description": "Optional. Maximum number of expected awards."},
            "min_total_funding": {"type": "integer", "description": "Optional. Minimum estimated total program funding."},
            "max_total_funding": {"type": "integer", "description": "Optional. Maximum estimated total program funding."},
            "query_text": {
                "type": "string",
                "description": "Optional. Text to search for within the results filtered by award criteria."
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
                    "Search for grant opportunities by award criteria (floor, ceiling, number of awards, total funding). "
                    "At least one award criterion must be specified. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": [] # Logic in fn enforces one award criteria
                }
            }
        }

    def fn(self,
           min_award_floor: Optional[int] = None, max_award_ceiling: Optional[int] = None,
           min_expected_awards: Optional[int] = None, max_expected_awards: Optional[int] = None,
           min_total_funding: Optional[int] = None, max_total_funding: Optional[int] = None,
           query_text: Optional[str] = None, query_operator: str = "AND",
           # Common params
           items_per_page: int = 5, page_number: int = 1, order_by: str = "relevancy",
           sort_direction: str = "descending", show_posted: bool = True, show_forecasted: bool = False,
           show_closed: bool = False, show_archived: bool = False) -> str:

        self.logger.info(f"Querying by award criteria: floor={min_award_floor}, ceiling={max_award_ceiling}, ... query='{query_text}'")

        specific_filters: Dict[str, Any] = {}
        award_criteria_provided = False

        if min_award_floor is not None:
            specific_filters.setdefault("award_floor", {})["min"] = min_award_floor
            award_criteria_provided = True
        if max_award_ceiling is not None:
            specific_filters.setdefault("award_ceiling", {})["max"] = max_award_ceiling
            award_criteria_provided = True

        expected_awards_filter = {}
        if min_expected_awards is not None:
            expected_awards_filter["min"] = min_expected_awards
            award_criteria_provided = True
        if max_expected_awards is not None:
            expected_awards_filter["max"] = max_expected_awards
            award_criteria_provided = True
        if expected_awards_filter:
            specific_filters["expected_number_of_awards"] = expected_awards_filter

        total_funding_filter = {}
        if min_total_funding is not None:
            total_funding_filter["min"] = min_total_funding
            award_criteria_provided = True
        if max_total_funding is not None:
            total_funding_filter["max"] = max_total_funding
            award_criteria_provided = True
        if total_funding_filter:
            specific_filters["estimated_total_program_funding"] = total_funding_filter

        if not award_criteria_provided and not query_text:
            return json.dumps({"error": "At least one award criterion or query_text must be specified.", "success": False})

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