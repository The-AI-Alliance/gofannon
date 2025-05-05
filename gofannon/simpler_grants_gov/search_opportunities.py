import logging
from typing import Optional, Dict, Any, Tuple, List
import json
import copy # For deep copying the default pagination

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

# --- Enums and Allowed Values ---
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
IS_COST_SHARING_ENUM = [True, False] # Explicitly list boolean possibilities

ALLOWED_SORT_ORDERS = [
    "relevancy", "opportunity_id", "opportunity_number", "opportunity_title",
    "post_date", "close_date", "agency_code", "agency_name", "top_level_agency_name"
]
ALLOWED_SORT_DIRECTIONS = ["ascending", "descending"]

# Map filter keys to their corresponding enum lists for validation
ENUM_FILTER_VALIDATION_MAP = {
    "funding_instrument": FUNDING_INSTRUMENT_ENUM,
    "funding_category": FUNDING_CATEGORY_ENUM,
    "applicant_type": APPLICANT_TYPE_ENUM,
    "opportunity_status": OPPORTUNITY_STATUS_ENUM,
    "is_cost_sharing": IS_COST_SHARING_ENUM
}

# --- Default Pagination ---
DEFAULT_PAGINATION = {
    "page_offset": 1,
    "page_size": 5,
    "sort_order": [{"order_by": "relevancy", "sort_direction": "descending"}]
}
# --- End Constants ---


@FunctionRegistry.register
class SearchOpportunities(SimplerGrantsGovBase):
    """
    Tool to search for grant opportunities using the Simpler Grants Gov API.
    Corresponds to the POST /v1/opportunities/search endpoint.
    Validates filter enum values. If provided pagination is invalid, uses a default
    and includes warnings in the response.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "search_opportunities"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Definition updated to make pagination optional and describe default behavior
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"Search for grant opportunities based on various criteria. Validates filter values. If pagination is invalid or omitted, it defaults to {json.dumps(DEFAULT_PAGINATION)} and adds warnings to the response.",
                "parameters": {
                    "type": "object",
                    "properties": {
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
                        "filters": {
                            "type": "object",
                            "description": "Optional. A JSON object containing filters. Use the 'one_of' structure for list-based filters (e.g., opportunity_status), 'min'/'max' for ranges (e.g., award_ceiling), 'start_date'/'end_date' for dates.",
                            # Properties definition remains the same as before
                            "properties": {
                                "funding_instrument": {
                                    "type": "object", "properties": {"one_of": {"type": "array", "items": {"type": "string", "enum": FUNDING_INSTRUMENT_ENUM}}}
                                },
                                "funding_category": {
                                    "type": "object", "properties": {"one_of": {"type": "array", "items": {"type": "string", "enum": FUNDING_CATEGORY_ENUM}}}
                                },
                                "applicant_type": {
                                    "type": "object", "properties": {"one_of": {"type": "array", "items": {"type": "string", "enum": APPLICANT_TYPE_ENUM}}}
                                },
                                "opportunity_status": {
                                    "type": "object", "properties": {"one_of": {"type": "array", "items": {"type": "string", "enum": OPPORTUNITY_STATUS_ENUM}}}
                                },
                                "agency": {
                                    "type": "object", "properties": {"one_of": {"type": "array", "items": {"type": "string"}}}
                                },
                                "assistance_listing_number": {
                                    "type": "object", "properties": {"one_of": {"type": "array", "items": {"type": "string", "pattern": r"^\d{2}\.\d{2,3}$"}}}
                                },
                                "is_cost_sharing": {
                                    "type": "object", "properties": {"one_of": {"type": "array", "items": {"type": "boolean"}}}
                                },
                                "expected_number_of_awards": {
                                    "type": "object", "properties": {"min": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}
                                },
                                "award_floor": {
                                    "type": "object", "properties": {"min": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}
                                },
                                "award_ceiling": {
                                    "type": "object", "properties": {"min": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}
                                },
                                "estimated_total_program_funding": {
                                    "type": "object", "properties": {"min": {"type": "integer", "minimum": 0}, "max": {"type": "integer", "minimum": 0}}
                                },
                                "post_date": {
                                    "type": "object", "properties": {"start_date": {"type": "string", "format": "date"}, "end_date": {"type": "string", "format": "date"}}
                                },
                                "close_date": {
                                    "type": "object", "properties": {"start_date": {"type": "string", "format": "date"}, "end_date": {"type": "string", "format": "date"}}
                                }
                            },
                            "additionalProperties": False
                        },
                        "pagination": {
                            "type": "object",
                            "description": f"Optional. Pagination settings. If invalid or omitted, defaults to {json.dumps(DEFAULT_PAGINATION)}. Must contain 'page_offset' (integer >= 1), 'page_size' (integer), and 'sort_order' (array of objects).",
                            "properties": {
                                "page_offset": {"type": "integer", "description": "Page number (starts at 1).", "minimum": 1},
                                "page_size": {"type": "integer", "description": "Results per page."},
                                "sort_order": {
                                    "type": "array",
                                    "description": f"Array of sort objects. 'order_by' must be one of: {', '.join(ALLOWED_SORT_ORDERS)}. 'sort_direction' should be 'ascending' or 'descending' (or 'asc'/'desc').",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "order_by": {"type": "string", "enum": ALLOWED_SORT_ORDERS},
                                            "sort_direction": {"type": "string", "description": "'ascending'/'descending' or 'asc'/'desc'."}
                                        },
                                        "required": ["order_by", "sort_direction"]
                                    }
                                }
                            },
                            # No longer required at top level
                            # "required": ["page_offset", "page_size", "sort_order"]
                        },
                    },
                    # No longer required at top level
                    # "required": ["pagination"]
                }
            }
        }

    def _validate_and_correct_pagination(self, pagination_input: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
        """Validates the pagination input. Returns validated object and warnings."""
        warnings = []
        # Use deepcopy to avoid modifying the class constant
        pagination_to_use = copy.deepcopy(DEFAULT_PAGINATION)
        is_valid = True

        if pagination_input is None:
            warnings.append("Pagination not provided, using default.")
            return pagination_to_use, warnings # Return default immediately

        if not isinstance(pagination_input, dict):
            warnings.append("Pagination must be a dictionary object, using default.")
            return pagination_to_use, warnings # Return default immediately

        # --- Validate structure and types ---
        page_offset = pagination_input.get("page_offset")
        page_size = pagination_input.get("page_size")
        sort_order = pagination_input.get("sort_order")

        if "page_offset" not in pagination_input:
            warnings.append("Pagination missing required key 'page_offset'.")
            is_valid = False
        elif not isinstance(page_offset, int) or page_offset < 1:
            warnings.append(f"Pagination 'page_offset' must be an integer >= 1 (got: {page_offset}).")
            is_valid = False

        if "page_size" not in pagination_input:
            warnings.append("Pagination missing required key 'page_size'.")
            is_valid = False
        elif not isinstance(page_size, int):
            warnings.append(f"Pagination 'page_size' must be an integer (got: {type(page_size).__name__}).")
            is_valid = False

        if "sort_order" not in pagination_input:
            warnings.append("Pagination missing required key 'sort_order'.")
            is_valid = False
        elif not isinstance(sort_order, list):
            warnings.append(f"Pagination 'sort_order' must be a list (got: {type(sort_order).__name__}).")
            is_valid = False
        else:
            # --- Validate sort_order items ---
            corrected_sort_order = []
            for i, item in enumerate(sort_order):
                item_valid = True
                if not isinstance(item, dict):
                    warnings.append(f"Item {i} in 'sort_order' is not a dictionary object.")
                    is_valid = False
                    continue # Skip validation for this item

                order_by = item.get("order_by")
                sort_direction = item.get("sort_direction")
                corrected_item = item.copy() # Work on a copy

                if "order_by" not in item:
                    warnings.append(f"Item {i} in 'sort_order' missing required key 'order_by'.")
                    item_valid = False
                    is_valid = False
                elif order_by not in ALLOWED_SORT_ORDERS:
                    warnings.append(f"Item {i} 'order_by' has invalid value '{order_by}'. Allowed: {', '.join(ALLOWED_SORT_ORDERS)}.")
                    item_valid = False
                    is_valid = False # Mark main pagination as invalid

                if "sort_direction" not in item:
                    warnings.append(f"Item {i} in 'sort_order' missing required key 'sort_direction'.")
                    item_valid = False
                    is_valid = False
                else:
                    direction_str = str(sort_direction).lower().strip()
                    if direction_str == "asc":
                        corrected_item["sort_direction"] = "ascending"
                    elif direction_str == "desc":
                        corrected_item["sort_direction"] = "descending"
                    elif direction_str not in ALLOWED_SORT_DIRECTIONS:
                        warnings.append(f"Item {i} 'sort_direction' has invalid value '{sort_direction}'. Allowed: {', '.join(ALLOWED_SORT_DIRECTIONS)} or 'asc'/'desc'.")
                        item_valid = False
                        is_valid = False

                if item_valid:
                    corrected_sort_order.append(corrected_item)
                    # else: If item was invalid, we don't add it to the corrected list unless we intend to use partially valid sort_orders


            # If the overall pagination structure was valid so far, update it
            if is_valid:
                pagination_to_use["page_offset"] = page_offset
                pagination_to_use["page_size"] = page_size
                # Only update sort_order if it was structurally okay and items were processable
                if isinstance(sort_order, list):
                    # Decide if we use the partially corrected list or stick to default if any item was bad
                    # Sticking to default if *any* sort_order item is bad might be safer.
                    # Let's refine: If the list itself was structurally ok, use corrected items
                    if not any("sort_order' is not a list" in w for w in warnings):
                        pagination_to_use["sort_order"] = corrected_sort_order
                    else: # sort_order was not even a list
                        is_valid = False # Force using default pagination object

        # --- Final Decision ---
        if not is_valid:
            warnings.append("Provided pagination was invalid, using default.")
            # Return a clean default, not the partially modified one
            return copy.deepcopy(DEFAULT_PAGINATION), warnings
        else:
            # Return the validated (potentially corrected direction) pagination object
            return pagination_to_use, warnings # Warnings might be empty


    def fn(self, pagination: Optional[Dict[str, Any]] = None, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, query_operator: str = "AND") -> str:
        """
        Executes the opportunity search with validation and correction for pagination and filter enums.

        Args:
            pagination: Optional pagination settings object. Defaults will be used if omitted or invalid.
            query: Optional search query string.
            filters: Optional filters object. Invalid filter values will raise an error.
            query_operator: Optional query operator ('AND' or 'OR').

        Returns:
            A JSON string representing the search results. If default pagination was used due to errors,
            the response includes a 'warnings' key detailing the issues. Returns an error JSON if filter
            validation fails or the API call errors.
        """
        self.logger.info(f"Executing Simpler Grants Gov opportunity search tool with query='{query}'")

        final_response_warnings = []

        try:
            # --- Pagination Validation ---
            pagination_to_use, pagination_warnings = self._validate_and_correct_pagination(pagination)
            if pagination_warnings:
                final_response_warnings.extend(pagination_warnings)
                self.logger.warning(f"Pagination issues found, using {'default' if pagination is None else 'potentially corrected'} pagination: {pagination_to_use}. Warnings: {pagination_warnings}")

                # --- Filter Enum Validation (Raises ValueError on failure) ---
            if filters is not None:
                if not isinstance(filters, dict):
                    raise ValueError("'filters' must be a dictionary object if provided.")

                for filter_key, filter_value in filters.items():
                    if filter_key in ENUM_FILTER_VALIDATION_MAP:
                        allowed_values = ENUM_FILTER_VALIDATION_MAP[filter_key]
                        allowed_values_set = set(allowed_values)

                        if not isinstance(filter_value, dict) or "one_of" not in filter_value:
                            self.logger.warning(f"Filter '{filter_key}' structure invalid: {filter_value}. Skipping validation.")
                            continue

                        provided_values = filter_value.get("one_of")
                        if not isinstance(provided_values, list):
                            self.logger.warning(f"Filter '{filter_key}' 'one_of' not a list: {provided_values}. Skipping validation.")
                            continue

                        for provided in provided_values:
                            expected_type = bool if filter_key == "is_cost_sharing" else str
                            if not isinstance(provided, expected_type):
                                allowed_values_str = ", ".join(map(str, sorted(list(allowed_values_set))))
                                raise ValueError(f"Invalid value type '{type(provided).__name__}' ('{provided}') for filter '{filter_key}'. Expected {expected_type.__name__}. Allowed values are: {allowed_values_str}")

                            if provided not in allowed_values_set:
                                allowed_values_str = ", ".join(map(str, sorted(list(allowed_values_set))))
                                raise ValueError(f"Invalid value '{provided}' for filter '{filter_key}'. Allowed values are: {allowed_values_str}")

                                # --- Payload Construction ---
            payload: Dict[str, Any] = {
                "pagination": pagination_to_use, # Use the validated or default pagination
                "query_operator": query_operator
            }
            if query:
                payload["query"] = query
            if filters:
                payload["filters"] = filters # Use original filters (validation passed if we got here)

            # --- API Call ---
            endpoint = "/v1/opportunities/search"
            self.logger.debug(f"Making search request with payload: {json.dumps(payload)}")
            result_str = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search API call successful. Response length: {len(result_str)}")

            # --- Inject Warnings if Necessary ---
            if final_response_warnings:
                try:
                    response_data = json.loads(result_str)
                    # Ensure response_data is a dict before adding warnings
                    if isinstance(response_data, dict):
                        # Add or append to warnings list
                        if "warnings" not in response_data:
                            response_data["warnings"] = []
                        elif not isinstance(response_data["warnings"], list):
                            # Handle case where API might return non-list warnings
                            self.logger.warning("API response contained non-list 'warnings', overwriting.")
                            response_data["warnings"] = []
                        response_data["warnings"].extend(final_response_warnings)
                        return json.dumps(response_data)
                    else:
                        # API returned valid JSON but not an object? Log and return original.
                        self.logger.error(f"API response was valid JSON but not an object. Cannot inject warnings. Original response: {result_str[:500]}")
                        return result_str

                except json.JSONDecodeError:
                    # Should not happen if _make_request worked, but handle defensively
                    self.logger.error(f"Failed to parse successful API response JSON. Cannot inject warnings. Original response: {result_str[:500]}")
                    return result_str # Return original error response from API
            else:
                # No pagination warnings, return result directly
                return result_str

        except ValueError as ve:
            # Catch filter validation errors
            self.logger.error(f"Input validation failed for SearchOpportunities: {ve}")
            return json.dumps({"error": f"Invalid input: {str(ve)}", "success": False})
        except Exception as e:
            # Catch other errors (e.g., network, API issues)
            self.logger.error(f"Opportunity search failed unexpectedly: {e}", exc_info=True)
            return json.dumps({"error": f"Opportunity search failed: {str(e)}", "success": False})
  