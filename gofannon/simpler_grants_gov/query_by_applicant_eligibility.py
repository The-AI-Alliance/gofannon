import logging
import json
from typing import Optional, Dict, Any, List

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryByApplicantEligibility(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities based on applicant types and/or cost-sharing requirements.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "query_opportunities_by_applicant_eligibility"):
        super().__init__(api_key=api_key, base_url=base_url, name=name)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        specific_params = {
            "applicant_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional. List of applicant types (e.g., ['state_governments', 'nonprofits_with_501c3']). Valid values: "
                               "city_or_township_governments, county_governments, federal_government_agencies_fed_recognized_tribes_excluded, "
                               "independent_school_districts, individuals, native_american_tribal_governments_federally_recognized, "
                               "native_american_tribal_organizations_other_than_federally_recognized_tribal_governments, "
                               "nonprofits_having_a_501c3_status_with_the_irs_other_than_institutions_of_higher_education, "
                               "nonprofits_that_do_not_have_a_501c3_status_with_the_irs_other_than_institutions_of_higher_education, "
                               "private_institutions_of_higher_education, public_and_state_controlled_institutions_of_higher_education, "
                               "public_housing_authorities_or_indian_housing_authorities, small_businesses, special_district_governments, state_governments, other."
            },
            "requires_cost_sharing": { # Parameter name is more direct for LLM
                "type": "boolean",
                "description": "Optional. Filter by cost-sharing requirement. True for opportunities requiring cost sharing, False for those not requiring it. Omit to not filter by this."
            },
            "query_text": {
                "type": "string",
                "description": "Optional. Text to search for within the results filtered by eligibility."
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
                    "Search for grant opportunities by applicant types and/or cost-sharing requirements. "
                    "At least one of 'applicant_types' or 'requires_cost_sharing' must be specified if used for filtering. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": [] # Logic in fn enforces condition
                }
            }
        }

    def fn(self,
           applicant_types: Optional[List[str]] = None,
           requires_cost_sharing: Optional[bool] = None,
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

        self.logger.info(f"Querying by applicant eligibility: types={applicant_types}, cost_sharing={requires_cost_sharing}, query='{query_text}'")

        if applicant_types is None and requires_cost_sharing is None and not query_text: # if no specific filters or query, it's too broad
            return json.dumps({"error": "Please provide 'applicant_types', 'requires_cost_sharing', or 'query_text' to refine the search.", "success": False})

        specific_filters: Dict[str, Any] = {}
        if applicant_types:
            specific_filters["applicant_type"] = {"one_of": applicant_types}
        if requires_cost_sharing is not None: # API expects list for boolean filters
            specific_filters["is_cost_sharing"] = {"one_of": [requires_cost_sharing]}

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