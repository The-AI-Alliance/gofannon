import logging
import json
from typing import Optional, Dict, Any

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

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
        # Based on OpportunitySearchRequestV1Schema
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
                            "description": "Optional. A JSON object containing filters. Keys can include 'funding_instrument', 'funding_category', 'applicant_type', 'opportunity_status', 'agency', 'assistance_listing_number', 'is_cost_sharing', 'expected_number_of_awards', 'award_floor', 'award_ceiling', 'estimated_total_program_funding', 'post_date', 'close_date'. Each key holds an object specifying the filter type (e.g., 'one_of' for lists, 'min'/'max' for ranges, 'start_date'/'end_date' for dates). Refer to API documentation for exact structure.",
                            "additionalProperties": True # Allows flexibility but relies on description
                        },
                        "pagination": {
                            "type": "object",
                            "description": "Required. A JSON object for pagination settings. Must include 'page_offset' (integer, starting from 1), 'page_size' (integer, max usually 100), and 'sort_order' (array of objects with 'order_by' and 'sort_direction'). Default sort is usually by opportunity_id descending.",
                            "properties": {
                                "page_offset": {"type": "integer", "description": "Page number to retrieve (starts at 1)."},
                                "page_size": {"type": "integer", "description": "Number of results per page."},
                                "sort_order": {
                                    "type": "array",
                                    "description": "Array of sort objects, e.g., [{'order_by': 'post_date', 'sort_direction': 'descending'}].",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "order_by": {"type": "string"},
                                            "sort_direction": {"type": "string", "enum": ["ascending", "descending"]}
                                        },
                                        "required": ["order_by", "sort_direction"]
                                    }
                                }
                            },
                            "required": ["page_offset", "page_size", "sort_order"] # Ensure pagination object itself is required and has needed keys
                        },
                        # format: 'csv' is excluded as the tool should return structured data (JSON string)
                        # experimental: Excluded for simplicity unless specifically needed.
                    },
                    "required": ["pagination"] # Only pagination is strictly required by the schema
                }
            }
        }

    def fn(self, pagination: Dict[str, Any], query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, query_operator: str = "AND") -> str:
        """
        Executes the opportunity search.

        Args:
            pagination: Pagination settings object.
            query: Optional search query string.
            filters: Optional filters object.
            query_operator: Optional query operator ('AND' or 'OR').

        Returns:
            A JSON string representing the search results.
        """
        self.logger.info(f"Executing Simpler Grants Gov opportunity search tool with query='{query}'")

        payload: Dict[str, Any] = {
            "pagination": pagination,
            "query_operator": query_operator # Default is handled by schema/API if not sent
        }
        if query:
            payload["query"] = query
        if filters:
            payload["filters"] = filters

            # Note: We default to JSON format, ignoring the 'format: csv' possibility from the schema
        # as tools typically return structured data.

        endpoint = "/v1/opportunities/search"
        try:
            result = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search successful. Response length: {len(result)}")
            return result
        except Exception as e:
            self.logger.error(f"Opportunity search failed: {e}", exc_info=True)
            # Return a JSON error string consistent with other potential returns
            return json.dumps({"error": f"Opportunity search failed: {str(e)}", "success": False})