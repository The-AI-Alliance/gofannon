import logging
from typing import Optional, Dict, Any, List
import json

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

# Enum values extracted from API source for definition and validation
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
    Invalid enum values provided in list filters will be omitted with a warning.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "search_opportunities"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Definition remains largely the same, but descriptions can emphasize valid values
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Search for grant opportunities based on optional criteria like query text and various filters. Returns the first page of results. Invalid filter values may be omitted.",
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
                            "items": {"type": "string"}, # Don't use enum here, validate in fn
                            "description": f"Optional. Filter by a list of funding instrument types. Valid values: {', '.join(FUNDING_INSTRUMENT_ENUM)}"
                        },
                        "funding_category": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": f"Optional. Filter by a list of funding categories. Valid values: {', '.join(FUNDING_CATEGORY_ENUM)}"
                        },
                        "applicant_type": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": f"Optional. Filter by a list of applicant types. Valid values: {', '.join(APPLICANT_TYPE_ENUM)}"
                        },
                        "opportunity_status": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": f"Optional. Filter by a list of opportunity statuses. Valid values: {', '.join(OPPORTUNITY_STATUS_ENUM)}"
                        },
                        "agency": {
                            "type": "array",
                            "items": {"type": "string", "description": "Agency code, e.g., HHS, USAID"},
                            "description": "Optional. Filter by a list of agency codes. No strict validation applied."
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

    def _validate_and_filter_list(self, input_list: Optional[List[str]], filter_name: str, valid_enums: List[str], warnings_list: List[Dict]) -> List[str]:
        """Helper to validate items in a list against enums and collect warnings."""
        if input_list is None:
            return []

        if not isinstance(input_list, list):
            # If the input is not a list, treat it as an invalid attempt and warn
            warning_msg = f"Invalid type for filter '{filter_name}': Expected a list, got {type(input_list).__name__}. Filter omitted."
            logger.warning(warning_msg)
            warnings_list.append({"filter": filter_name, "error": warning_msg})
            return []

        valid_items = []
        for item in input_list:
            if isinstance(item, str) and item in valid_enums:
                valid_items.append(item)
            else:
                # Log and record warning for the invalid item
                warning_msg = f"Invalid value '{item}' provided for filter '{filter_name}'. It was omitted. Valid values are: {', '.join(valid_enums)}."
                logger.warning(warning_msg)
                warnings_list.append({"filter": filter_name, "invalid_value": item, "valid_values": valid_enums, "message": warning_msg})

        return valid_items

    def _add_warnings_to_response(self, response_str: str, warnings_list: List[Dict]) -> str:
        """Adds a 'warnings' field to a JSON response string if warnings exist."""
        if not warnings_list:
            return response_str

        try:
            response_data = json.loads(response_str)
            # Ensure response_data is a dictionary before adding warnings
            if isinstance(response_data, dict):
                response_data['warnings'] = warnings_list
            else:
                # If the response wasn't a dict (e.g., just a string error message), wrap it
                logger.warning(f"Original response was not a dict, wrapping to add warnings. Original: {response_str[:100]}")
                response_data = {
                    "original_response": response_data,
                    "warnings": warnings_list
                }
            return json.dumps(response_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse response JSON to add warnings. Original response: {response_str[:500]}...")
            # Return original response string if parsing fails
            return response_str
        except Exception as e:
            logger.error(f"Unexpected error adding warnings to response: {e}", exc_info=True)
            return response_str # Fallback to original

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
        Executes the opportunity search with input validation, internal pagination,
        and reconstructed filters. Adds warnings to the response for omitted invalid filter values.

        Args:
            (Refer to definition for descriptions)

        Returns:
            A JSON string representing the search results (potentially with a 'warnings' field) or an error.
        """
        self.logger.info(f"Executing Simpler Grants Gov opportunity search tool with query='{query}'")
        warnings_list: List[Dict] = [] # Store warnings here

        try:
            # --- Internal Pagination ---
            internal_pagination = {
                "page_offset": DEFAULT_PAGE_OFFSET,
                "page_size": DEFAULT_PAGE_SIZE,
                "sort_order": DEFAULT_SORT_ORDER
            }
            self.logger.debug(f"Using internal pagination: {internal_pagination}")

            # --- Reconstruct and Validate Filters for API ---
            api_filters: Dict[str, Any] = {}

            # Validate and filter list-based enums
            valid_fi = self._validate_and_filter_list(funding_instrument, "funding_instrument", FUNDING_INSTRUMENT_ENUM, warnings_list)
            if valid_fi: api_filters["funding_instrument"] = {"one_of": valid_fi}

            valid_fc = self._validate_and_filter_list(funding_category, "funding_category", FUNDING_CATEGORY_ENUM, warnings_list)
            if valid_fc: api_filters["funding_category"] = {"one_of": valid_fc}

            valid_at = self._validate_and_filter_list(applicant_type, "applicant_type", APPLICANT_TYPE_ENUM, warnings_list)
            if valid_at: api_filters["applicant_type"] = {"one_of": valid_at}

            valid_os = self._validate_and_filter_list(opportunity_status, "opportunity_status", OPPORTUNITY_STATUS_ENUM, warnings_list)
            if valid_os: api_filters["opportunity_status"] = {"one_of": valid_os}

            # Filters without strict enum validation in this example (pass if list)
            if agency is not None:
                if isinstance(agency, list):
                    api_filters["agency"] = {"one_of": agency}
                else:
                    warnings_list.append({"filter": "agency", "error": f"Expected a list, got {type(agency).__name__}. Filter omitted."})
                    logger.warning(f"Invalid type for filter 'agency'. Expected list, got {type(agency).__name__}. Filter omitted.")

            if assistance_listing_number is not None:
                # Add pattern validation if needed, or rely on API
                if isinstance(assistance_listing_number, list):
                    api_filters["assistance_listing_number"] = {"one_of": assistance_listing_number}
                else:
                    warnings_list.append({"filter": "assistance_listing_number", "error": f"Expected a list, got {type(assistance_listing_number).__name__}. Filter omitted."})
                    logger.warning(f"Invalid type for filter 'assistance_listing_number'. Expected list, got {type(assistance_listing_number).__name__}. Filter omitted.")


                    # Boolean filter
            if is_cost_sharing is not None:
                if isinstance(is_cost_sharing, bool):
                    api_filters["is_cost_sharing"] = {"one_of": [is_cost_sharing]}
                else:
                    warnings_list.append({"filter": "is_cost_sharing", "error": f"Expected a boolean, got {type(is_cost_sharing).__name__}. Filter omitted."})
                    logger.warning(f"Invalid type for filter 'is_cost_sharing'. Expected boolean, got {type(is_cost_sharing).__name__}. Filter omitted.")


                    # Range/Date filters (basic type check)
            range_date_filters = {
                "expected_number_of_awards": expected_number_of_awards,
                "award_floor": award_floor,
                "award_ceiling": award_ceiling,
                "estimated_total_program_funding": estimated_total_program_funding,
                "post_date": post_date,
                "close_date": close_date
            }
            for name, value in range_date_filters.items():
                if value is not None:
                    if isinstance(value, dict):
                        api_filters[name] = value
                    else:
                        warnings_list.append({"filter": name, "error": f"Expected a dictionary object, got {type(value).__name__}. Filter omitted."})
                        logger.warning(f"Invalid type for filter '{name}'. Expected dict, got {type(value).__name__}. Filter omitted.")


                        # --- Payload Construction ---
            payload: Dict[str, Any] = {
                "pagination": internal_pagination,
                "query_operator": query_operator
            }
            if query:
                payload["query"] = query
            if api_filters:
                payload["filters"] = api_filters
                self.logger.debug(f"Constructed API filters: {api_filters}")
            elif not query:
                # If no query and no filters, API might require something? Or just return all?
                # Assuming returning all is ok. If not, add a check/error here.
                self.logger.info("No query or filters provided for opportunity search.")


                # --- API Call ---
            endpoint = "/v1/opportunities/search"
            api_response_str = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search successful. Response length: {len(api_response_str)}")

            # Add warnings to the successful response if any occurred during validation
            final_response_str = self._add_warnings_to_response(api_response_str, warnings_list)
            return final_response_str

        except ValueError as ve: # Catch potential errors during filter reconstruction if needed
            error_msg = f"Input processing failed for SearchOpportunities: {ve}"
            self.logger.error(error_msg)
            error_response = {"error": error_msg, "success": False}
            # Add warnings even to validation error responses
            if warnings_list:
                error_response["warnings"] = warnings_list
            return json.dumps(error_response)
        except Exception as e:
            error_msg = f"Opportunity search failed: {str(e)}"
            self.logger.error(f"Opportunity search failed: {e}", exc_info=True)
            error_response = {"error": error_msg, "success": False}
            # Add warnings even to general error responses
            if warnings_list:
                error_response["warnings"] = warnings_list
            return json.dumps(error_response)
