import logging
from typing import Optional, Dict, Any
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
ALLOWED_SORT_ORDERS = [
    "relevancy", "opportunity_id", "opportunity_number", "opportunity_title",
    "post_date", "close_date", "agency_code", "agency_name", "top_level_agency_name"
]

@FunctionRegistry.register
class SearchOpportunities(SimplerGrantsGovBase):
    """
    Tool to search for grant opportunities using the Simpler Grants Gov API.
    Corresponds to the POST /v1/opportunities/search endpoint.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "search_opportunities"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Based on OpportunitySearchRequestV1Schema with enums added
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Search for grant opportunities based on various criteria like query text, filters, and pagination.",
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
                                    "description": "Filter by cost sharing requirement.",
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
                                        # Note: Relative dates are excluded for simplicity in the tool definition
                                    }
                                },
                                "close_date": {
                                    "type": "object",
                                    "description": "Filter by close date range (YYYY-MM-DD).",
                                    "properties": {
                                        "start_date": {"type": "string", "format": "date"},
                                        "end_date": {"type": "string", "format": "date"}
                                        # Note: Relative dates are excluded for simplicity
                                    }
                                }
                            },
                            "additionalProperties": False # Discourage undefined filters
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
        Executes the opportunity search with validation and correction.

        Args:
            pagination: Pagination settings object.
            query: Optional search query string.
            filters: Optional filters object.
            query_operator: Optional query operator ('AND' or 'OR').

        Returns:
            A JSON string representing the search results or an error.
        """
        self.logger.info(f"Executing Simpler Grants Gov opportunity search tool with query='{query}'")

        try:
            # --- Validation and Correction ---
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

                # Correct asc/desc in sort_order
            corrected_sort_order = []
            for item in sort_order:
                if not isinstance(item, dict) or "order_by" not in item or "sort_direction" not in item:
                    self.logger.warning(f"Invalid item in sort_order list: {item}. Skipping.")
                    continue # Skip invalid items or raise error? Logging for now.

                direction = str(item.get("sort_direction", "")).lower().strip()
                corrected_item = item.copy() # Avoid modifying original input dict directly if passed by reference

                if direction == "asc":
                    corrected_item["sort_direction"] = "ascending"
                    self.logger.debug("Corrected sort_direction 'asc' to 'ascending'.")
                elif direction == "desc":
                    corrected_item["sort_direction"] = "descending"
                    self.logger.debug("Corrected sort_direction 'desc' to 'descending'.")
                elif direction not in ["ascending", "descending"]:
                    # Keep original if it's already correct or something unexpected
                    self.logger.warning(f"Unexpected sort_direction value: '{item.get('sort_direction')}'. Using as is.")

                    # Validate order_by field
                if corrected_item.get("order_by") not in ALLOWED_SORT_ORDERS:
                    self.logger.warning(f"Invalid 'order_by' value: '{corrected_item.get('order_by')}'. API may reject this.")
                    # Decide: raise error, skip item, or let API handle? Letting API handle for now.

                corrected_sort_order.append(corrected_item)

                # Use the corrected sort order
            pagination["sort_order"] = corrected_sort_order

            # Basic check for filters type
            if filters is not None and not isinstance(filters, dict):
                raise ValueError("'filters' must be a dictionary object if provided.")
                # Deeper filter validation could be added here if needed, but relies on API schema knowledge

            # --- Payload Construction ---
            payload: Dict[str, Any] = {
                "pagination": pagination, # Use potentially corrected pagination
                "query_operator": query_operator
            }
            if query:
                payload["query"] = query
            if filters:
                payload["filters"] = filters

                # --- API Call ---
            endpoint = "/v1/opportunities/search"
            result = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search successful. Response length: {len(result)}")
            return result

        except ValueError as ve:
            self.logger.error(f"Input validation failed for SearchOpportunities: {ve}")
            return json.dumps({"error": f"Invalid input: {str(ve)}", "success": False})
        except Exception as e:
            self.logger.error(f"Opportunity search failed: {e}", exc_info=True)
            # Return a JSON error string consistent with other potential returns
            return json.dumps({"error": f"Opportunity search failed: {str(e)}", "success": False})
  