import logging
from typing import Optional, Dict, Any, List
import json

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

# Enum values extracted from API source for definition
FUNDING_INSTRUMENT_ENUM = ["grant", "cooperative_agreement", "other"]
FUNDING_CATEGORY_ENUM = [
    "recovery_act", "agriculture", "arts", "business_and_commerce",
    "community_development", "consumer_protection", "disaster_prevention_and_relief",
    "education", "employment_labor_and_training", "energy", "environment",
    "food_and_nutrition", "health", "housing", "humanities",
    "information_and_statistics", "infrastructure", "internal_security",
    "law_justice_and_legal_services", "natural_resources", "opportunity_zone_benefits",
    "regional_development", "science_and_technology", "social_services",
    "transportation", "other"
]
APPLICANT_TYPE_ENUM = [
    "state_governments", "county_governments", "city_or_township_governments",
    "special_district_governments", "independent_school_districts",
    "public_and_state_controlled_institutions_of_higher_education",
    "indian_native_american_tribal_governments_federally_recognized",
    "indian_native_american_tribal_governments_other_than_federally_recognized",
    "indian_native_american_tribal_organizations_other_than_governments",
    "nonprofits_having_a_501c3_status_with_the_irs_other_than_institutions_of_higher_education",
    "nonprofits_that_do_not_have_a_501c3_status_with_the_irs_other_than_institutions_of_higher_education",
    "private_institutions_of_higher_education", "individuals",
    "for_profit_organizations_other_than_small_businesses", "small_businesses",
    "hispanic_serving_institutions", "historically_black_colleges_and_universities",
    "tribally_controlled_colleges_and_universities",
    "alaska_native_and_native_hawaiian_serving_institutions",
    "non_domestic_non_us_entities", "other"
]
OPPORTUNITY_STATUS_ENUM = ["forecasted", "posted", "closed", "archived"]
# Allowed sort orders for internal default pagination
ALLOWED_SORT_ORDERS = [
    "relevancy", "opportunity_id", "opportunity_number", "opportunity_title",
    "post_date", "close_date", "agency_code", "agency_name", "top_level_agency_name"
]
# Internal Defaults for Pagination
DEFAULT_PAGE_OFFSET = 1
DEFAULT_PAGE_SIZE = 10 # Return fewer results by default for LLM context
DEFAULT_SORT_ORDER = [{"order_by": "opportunity_id", "sort_direction": "descending"}]

@FunctionRegistry.register
class SearchOpportunities(SimplerGrantsGovBase):
    """
    Tool to search for grant opportunities using the Simpler Grants Gov API.
    Corresponds to the POST /v1/opportunities/search endpoint. Pagination is handled internally.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "search_opportunities"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Parameters are now top-level and optional. Pagination is removed.
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Search for grant opportunities based on optional criteria like query text and various filters. Returns the first page of results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        # --- Core Search ---
                        "query": {
                            "type": "string",
                            "description": "Optional. Query string which searches against several text fields (e.g., 'research', 'health')."
                        },
                        "query_operator": {
                            "type": "string",
                            "enum": ["AND", "OR"],
                            "description": "Optional. Query operator for combining search conditions if 'query' is provided (default: AND).",
                            "default": "AND"
                        },
                        # --- Elevated Filters ---
                        "funding_instrument": {
                            "type": "array",
                            "items": {"type": "string", "enum": FUNDING_INSTRUMENT_ENUM},
                            "description": "Optional. Filter by a list of funding instrument types."
                        },
                        "funding_category": {
                            "type": "array",
                            "items": {"type": "string", "enum": FUNDING_CATEGORY_ENUM},
                            "description": "Optional. Filter by a list of funding categories."
                        },
                        "applicant_type": {
                            "type": "array",
                            "items": {"type": "string", "enum": APPLICANT_TYPE_ENUM},
                            "description": "Optional. Filter by a list of applicant types."
                        },
                        "opportunity_status": {
                            "type": "array",
                            "items": {"type": "string", "enum": OPPORTUNITY_STATUS_ENUM},
                            "description": "Optional. Filter by a list of opportunity statuses."
                        },
                        "agency": {
                            "type": "array",
                            "items": {"type": "string", "description": "Agency code, e.g., HHS, USAID"},
                            "description": "Optional. Filter by a list of agency codes."
                        },
                        "assistance_listing_number": {
                            "type": "array",
                            "items": {"type": "string", "pattern": r"^\d{2}\.\d{2,3}$", "description": "ALN format ##.### e.g. 45.149"},
                            "description": "Optional. Filter by a list of Assistance Listing Numbers (ALN / CFDA)."
                        },
                        "is_cost_sharing": {
                            "type": "boolean",
                            "description": "Optional. Filter opportunities based on whether cost sharing is required (True) or not required (False)."
                        },
                        "expected_number_of_awards": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "integer", "minimum": 0},
                                "max": {"type": "integer", "minimum": 0}
                            },
                            "description": "Optional. Filter by expected number of awards range (provide 'min', 'max', or both)."
                        },
                        "award_floor": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "integer", "minimum": 0},
                                "max": {"type": "integer", "minimum": 0}
                            },
                            "description": "Optional. Filter by award floor range (minimum award amount)."
                        },
                        "award_ceiling": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "integer", "minimum": 0},
                                "max": {"type": "integer", "minimum": 0}
                            },
                            "description": "Optional. Filter by award ceiling range (maximum award amount)."
                        },
                        "estimated_total_program_funding": {
                            "type": "object",
                            "properties": {
                                "min": {"type": "integer", "minimum": 0},
                                "max": {"type": "integer", "minimum": 0}
                            },
                            "description": "Optional. Filter by estimated total program funding range."
                        },
                        "post_date": {
                            "type": "object",
                            "properties": {
                                "start_date": {"type": "string", "format": "date", "description": "YYYY-MM-DD"},
                                "end_date": {"type": "string", "format": "date", "description": "YYYY-MM-DD"}
                            },
                            "description": "Optional. Filter by post date range (provide 'start_date', 'end_date', or both)."
                        },
                        "close_date": {
                            "type": "object",
                            "properties": {
                                "start_date": {"type": "string", "format": "date", "description": "YYYY-MM-DD"},
                                "end_date": {"type": "string", "format": "date", "description": "YYYY-MM-DD"}
                            },
                            "description": "Optional. Filter by close date range (provide 'start_date', 'end_date', or both)."
                        }
                    },
                    "required": [] # No parameters are strictly required anymore
                }
            }
        }

    def fn(self,
           query: Optional[str] = None,
           query_operator: str = "AND",
           # --- Elevated Filter Args ---
           funding_instrument: Optional[List[str]] = None,
           funding_category: Optional[List[str]] = None,
           applicant_type: Optional[List[str]] = None,
           opportunity_status: Optional[List[str]] = None,
           agency: Optional[List[str]] = None,
           assistance_listing_number: Optional[List[str]] = None,
           is_cost_sharing: Optional[bool] = None,
           expected_number_of_awards: Optional[Dict[str, int]] = None,
           award_floor: Optional[Dict[str, int]] = None,
           award_ceiling: Optional[Dict[str, int]] = None,
           estimated_total_program_funding: Optional[Dict[str, int]] = None,
           post_date: Optional[Dict[str, str]] = None,
           close_date: Optional[Dict[str, str]] = None
           ) -> str:
        """
        Executes the opportunity search with internal pagination and reconstructed filters.

        Args:
            query: Optional search query string.
            query_operator: Optional query operator ('AND' or 'OR').
            funding_instrument: Optional list of funding instrument strings.
            funding_category: Optional list of funding category strings.
            applicant_type: Optional list of applicant type strings.
            opportunity_status: Optional list of opportunity status strings.
            agency: Optional list of agency code strings.
            assistance_listing_number: Optional list of ALN strings.
            is_cost_sharing: Optional boolean for cost sharing filter.
            expected_number_of_awards: Optional dict with 'min'/'max' keys for number of awards.
            award_floor: Optional dict with 'min'/'max' keys for award floor.
            award_ceiling: Optional dict with 'min'/'max' keys for award ceiling.
            estimated_total_program_funding: Optional dict with 'min'/'max' for total funding.
            post_date: Optional dict with 'start_date'/'end_date' (YYYY-MM-DD).
            close_date: Optional dict with 'start_date'/'end_date' (YYYY-MM-DD).

        Returns:
            A JSON string representing the search results or an error.
        """
        self.logger.info(f"Executing Simpler Grants Gov opportunity search tool with query='{query}'")

        try:
            # --- Internal Pagination ---
            # Use fixed defaults for the simplified tool interface
            internal_pagination = {
                "page_offset": DEFAULT_PAGE_OFFSET,
                "page_size": DEFAULT_PAGE_SIZE,
                "sort_order": DEFAULT_SORT_ORDER # Using default sort
            }
            self.logger.debug(f"Using internal pagination: {internal_pagination}")


            # --- Reconstruct Filters for API ---
            api_filters: Dict[str, Any] = {}

            if funding_instrument is not None:
                api_filters["funding_instrument"] = {"one_of": funding_instrument}
            if funding_category is not None:
                api_filters["funding_category"] = {"one_of": funding_category}
            if applicant_type is not None:
                api_filters["applicant_type"] = {"one_of": applicant_type}
            if opportunity_status is not None:
                api_filters["opportunity_status"] = {"one_of": opportunity_status}
            if agency is not None:
                api_filters["agency"] = {"one_of": agency}
            if assistance_listing_number is not None:
                api_filters["assistance_listing_number"] = {"one_of": assistance_listing_number}
            if is_cost_sharing is not None:
                # Map boolean back to the API's expected structure
                api_filters["is_cost_sharing"] = {"one_of": [is_cost_sharing]}

                # Range filters (pass dict directly if provided)
            if expected_number_of_awards is not None:
                api_filters["expected_number_of_awards"] = expected_number_of_awards
            if award_floor is not None:
                api_filters["award_floor"] = award_floor
            if award_ceiling is not None:
                api_filters["award_ceiling"] = award_ceiling
            if estimated_total_program_funding is not None:
                api_filters["estimated_total_program_funding"] = estimated_total_program_funding

                # Date filters (pass dict directly if provided)
            if post_date is not None:
                api_filters["post_date"] = post_date
            if close_date is not None:
                api_filters["close_date"] = close_date

                # --- Payload Construction ---
            payload: Dict[str, Any] = {
                "pagination": internal_pagination,
                "query_operator": query_operator
            }
            if query:
                payload["query"] = query
                # Only include the filters key if we actually have filters
            if api_filters:
                payload["filters"] = api_filters
                self.logger.debug(f"Constructed API filters: {api_filters}")


                # --- API Call ---
            endpoint = "/v1/opportunities/search"
            result = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search successful. Response length: {len(result)}")
            return result

        except ValueError as ve: # Catch potential errors during filter reconstruction if needed
            self.logger.error(f"Input processing failed for SearchOpportunities: {ve}")
            return json.dumps({"error": f"Invalid input: {str(ve)}", "success": False})
        except Exception as e:
            self.logger.error(f"Opportunity search failed: {e}", exc_info=True)
            return json.dumps({"error": f"Opportunity search failed: {str(e)}", "success": False})