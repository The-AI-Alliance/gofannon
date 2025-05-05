import logging
from typing import Optional, Dict, Any
import json

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

# Map filter keys to their corresponding enum lists for validation
ENUM_FILTER_VALIDATION_MAP = {
    "funding_instrument": FUNDING_INSTRUMENT_ENUM,
    "funding_category": FUNDING_CATEGORY_ENUM,
    "applicant_type": APPLICANT_TYPE_ENUM,
    "opportunity_status": OPPORTUNITY_STATUS_ENUM,
    "is_cost_sharing": IS_COST_SHARING_ENUM # Add boolean filter here
}
# --- End Enums ---


@FunctionRegistry.register
class SearchOpportunities(SimplerGrantsGovBase):
    """
    Tool to search for grant opportunities using the Simpler Grants Gov API.
    Corresponds to the POST /v1/opportunities/search endpoint.
    Includes input validation for pagination and filter enum values.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "search_opportunities"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Definition remains the same as the previous version with enums included
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Search for grant opportunities based on various criteria like query text, filters, and pagination. Validates filter enum values.",
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
                            "properties": {
                                "funding_instrument": {
                                    "type": "object",
                                    "description": "Filter by funding instrument type.",
                                    "properties": {
                                        "one_of": {"type": "array", "items": {"type": "string", "enum": FUNDING_INSTRUMENT_ENUM}}
                                    }
                                },
                                "funding_category": {
                                    "type": "object",
                                    "description": "Filter by funding category.",
                                    "properties": {
                                        "one_of": {"type": "array", "items": {"type": "string", "enum": FUNDING_CATEGORY_ENUM}}
                                    }
                                },
                                "applicant_type": {
                                    "type": "object",
                                    "description": "Filter by applicant type.",
                                    "properties": {
                                        "one_of": {"type": "array", "items": {"type": "string", "enum": APPLICANT_TYPE_ENUM}}
                                    }
                                },
                                "opportunity_status": {
                                    "type": "object",
                                    "description": "Filter by opportunity status.",
                                    "properties": {
                                        "one_of": {"type": "array", "items": {"type": "string", "enum": OPPORTUNITY_STATUS_ENUM}}
                                    }
                                },
                                "agency": {
                                    "type": "object",
                                    "description": "Filter by agency code (e.g., 'USAID', 'DOC').",
                                    "properties": {
                                        "one_of": {"type": "array", "items": {"type": "string", "description": "Agency code, e.g., HHS"}}
                                    }
                                },
                                "assistance_listing_number": {
                                    "type": "object",
                                    "description": "Filter by Assistance Listing Number (ALN, formerly CFDA), format ##.### (e.g., '45.149').",
                                    "properties": {
                                        "one_of": {"type": "array", "items": {"type": "string", "pattern": r"^\d{2}\.\d{2,3}$"}}
                                    }
                                },
                                "is_cost_sharing": {
                                    "type": "object",
                                    "description": "Filter by cost sharing requirement (true or false).",
                                    "properties": {
                                        "one_of": {"type": "array", "items": {"type": "boolean"}}
                                    }
                                },
                                "expected_number_of_awards": {
                                    "type": "object",
                                    "description": "Filter by expected number of awards range.",
                                    "properties": {
                                        "min": {"type": "integer", "minimum": 0},
                                        "max": {"type": "integer", "minimum": 0}
                                    }
                                },
                                "award_floor": {
                                    "type": "object",
                                    "description": "Filter by award floor range (minimum award amount).",
                                    "properties": {
                                        "min": {"type": "integer", "minimum": 0},
                                        "max": {"type": "integer", "minimum": 0}
                                    }
                                },
                                "award_ceiling": {
                                    "type": "object",
                                    "description": "Filter by award ceiling range (maximum award amount).",
                                    "properties": {
                                        "min": {"type": "integer", "minimum": 0},
                                        "max": {"type": "integer", "minimum": 0}
                                    }
                                },
                                "estimated_total_program_funding": {
                                    "type": "object",
                                    "description": "Filter by estimated total program funding range.",
                                    "properties": {
                                        "min": {"type": "integer", "minimum": 0},
                                        "max": {"type": "integer", "minimum": 0}
                                    }
                                },
                                "post_date": {
                                    "type": "object",
                                    "description": "Filter by post date range (YYYY-MM-DD).",
                                    "properties": {
                                        "start_date": {"type": "string", "format": "date"},
                                        "end_date": {"type": "string", "format": "date"}
                                    }
                                },
                                "close_date": {
                                    "type": "object",
                                    "description": "Filter by close date range (YYYY-MM-DD).",
                                    "properties": {
                                        "start_date": {"type": "string", "format": "date"},
                                        "end_date": {"type": "string", "format": "date"}
                                    }
                                }
                            },
                            "additionalProperties": False
                        },
                        "pagination": {
                            "type": "object",
                            "description": "Required. Pagination settings: 'page_offset' (integer >= 1), 'page_size' (integer), and 'sort_order' (array of objects).",
                            "properties": {
                                "page_offset": {"type": "integer", "description": "Page number to retrieve (starts at 1).", "minimum": 1},
                                "page_size": {"type": "integer", "description": "Number of results per page."},
                                "sort_order": {
                                    "type": "array",
                                    "description": f"Array of sort objects. 'order_by' must be one of: {', '.join(ALLOWED_SORT_ORDERS)}. 'sort_direction' should be 'ascending' or 'descending' (or 'asc'/'desc').",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "order_by": {"type": "string", "enum": ALLOWED_SORT_ORDERS},
                                            "sort_direction": {"type": "string", "description": "Use 'ascending'/'descending' or 'asc'/'desc'."}
                                        },
                                        "required": ["order_by", "sort_direction"]
                                    }
                                }
                            },
                            "required": ["page_offset", "page_size", "sort_order"]
                        },
                    },
                    "required": ["pagination"]
                }
            }
        }

    def fn(self, pagination: Dict[str, Any], query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, query_operator: str = "AND") -> str:
        """
        Executes the opportunity search with validation and correction for pagination and filter enums.

        Args:
            pagination: Pagination settings object.
            query: Optional search query string.
            filters: Optional filters object.
            query_operator: Optional query operator ('AND' or 'OR').

        Returns:
            A JSON string representing the search results or an error message listing allowed values if validation fails.
        """
        self.logger.info(f"Executing Simpler Grants Gov opportunity search tool with query='{query}'")

        try:
            # --- Pagination Validation and Correction ---
            if not isinstance(pagination, dict):
                raise ValueError("'pagination' must be a dictionary object.")

            required_pagination_keys = ["page_offset", "page_size", "sort_order"]
            if not all(k in pagination for k in required_pagination_keys):
                raise ValueError(f"Pagination object missing required keys: {required_pagination_keys}")

            if not isinstance(pagination.get("page_offset"), int) or pagination["page_offset"] < 1:
                raise ValueError("'page_offset' must be an integer greater than or equal to 1.")

            if not isinstance(pagination.get("page_size"), int):
                raise ValueError("'page_size' must be an integer.")

            sort_order = pagination.get("sort_order")
            if not isinstance(sort_order, list):
                raise ValueError("'sort_order' must be a list of objects.")

            corrected_sort_order = []
            for item in sort_order:
                if not isinstance(item, dict) or "order_by" not in item or "sort_direction" not in item:
                    self.logger.warning(f"Invalid item in sort_order list: {item}. Skipping.")
                    continue

                direction = str(item.get("sort_direction", "")).lower().strip()
                corrected_item = item.copy()

                if direction == "asc":
                    corrected_item["sort_direction"] = "ascending"
                    self.logger.debug("Corrected sort_direction 'asc' to 'ascending'.")
                elif direction == "desc":
                    corrected_item["sort_direction"] = "descending"
                    self.logger.debug("Corrected sort_direction 'desc' to 'descending'.")
                elif direction not in ["ascending", "descending"]:
                    self.logger.warning(f"Unexpected sort_direction value: '{item.get('sort_direction')}'. Using as is.")

                if corrected_item.get("order_by") not in ALLOWED_SORT_ORDERS:
                    self.logger.warning(f"Invalid 'order_by' value: '{corrected_item.get('order_by')}'. API may reject this.")

                corrected_sort_order.append(corrected_item)
            pagination["sort_order"] = corrected_sort_order

            # --- Filter Enum Validation ---
            if filters is not None:
                if not isinstance(filters, dict):
                    raise ValueError("'filters' must be a dictionary object if provided.")

                for filter_key, filter_value in filters.items():
                    # Check if this filter key has enums to validate
                    if filter_key in ENUM_FILTER_VALIDATION_MAP:
                        allowed_values = ENUM_FILTER_VALIDATION_MAP[filter_key]
                        allowed_values_set = set(allowed_values) # Use set for efficient lookup

                        # Expecting structure like {"one_of": [val1, val2]}
                        if not isinstance(filter_value, dict) or "one_of" not in filter_value:
                            logger.warning(f"Filter '{filter_key}' has unexpected structure: {filter_value}. Skipping enum validation for it.")
                            continue # Skip validation if structure is wrong

                        provided_values = filter_value.get("one_of")
                        if not isinstance(provided_values, list):
                            logger.warning(f"Filter '{filter_key}' 'one_of' value is not a list: {provided_values}. Skipping enum validation.")
                            continue # Skip validation if 'one_of' isn't a list

                        # Check each provided value against the allowed set
                        for provided in provided_values:
                            # Handle boolean filter separately for type check
                            if filter_key == "is_cost_sharing":
                                if not isinstance(provided, bool):
                                    raise ValueError(f"Invalid value type '{type(provided).__name__}' ('{provided}') for filter '{filter_key}'. Must be boolean (True or False). Allowed values are: True, False")
                                    # Booleans inherently match True/False in allowed_values_set
                            # Handle string enums
                            elif isinstance(provided, str):
                                if provided not in allowed_values_set:
                                    allowed_values_str = ", ".join(map(str, sorted(list(allowed_values_set))))
                                    raise ValueError(f"Invalid value '{provided}' for filter '{filter_key}'. Allowed values are: {allowed_values_str}")
                            else:
                                # If not a string for string enums, or not a bool for bool enum
                                allowed_values_str = ", ".join(map(str, sorted(list(allowed_values_set))))
                                raise ValueError(f"Invalid value type '{type(provided).__name__}' ('{provided}') for filter '{filter_key}'. Allowed values are: {allowed_values_str}")

                                # --- Payload Construction ---
            payload: Dict[str, Any] = {
                "pagination": pagination,
                "query_operator": query_operator
            }
            if query:
                payload["query"] = query
            if filters:
                payload["filters"] = filters

                # --- API Call ---
            endpoint = "/v1/opportunities/search"
            self.logger.debug(f"Making validated search request with payload: {json.dumps(payload)}")
            result = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search successful. Response length: {len(result)}")
            return result

        except ValueError as ve:
            # Catch validation errors (including the ones we raised for enums)
            self.logger.error(f"Input validation failed for SearchOpportunities: {ve}")
            # Return the specific error message about allowed values
            return json.dumps({"error": f"Invalid input: {str(ve)}", "success": False})
        except Exception as e:
            # Catch other errors (e.g., network, API issues)
            self.logger.error(f"Opportunity search failed unexpectedly: {e}", exc_info=True)
            return json.dumps({"error": f"Opportunity search failed: {str(e)}", "success": False})
  