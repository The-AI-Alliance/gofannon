import logging
from typing import Optional, Dict, Any
import json

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class SearchAgencies(SimplerGrantsGovBase):
    """
    Tool to search for agencies based on query text and filters.
    Corresponds to the POST /v1/agencies/search endpoint.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "search_agencies"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Based on AgencySearchRequestSchema
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Search for agencies using a query string and structured filters like 'has_active_opportunity' or 'is_test_agency'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Optional. Query string which searches against agency text fields."
                        },
                        "query_operator": {
                            "type": "string",
                            "enum": ["AND", "OR"],
                            "description": "Optional. Operator for combining query conditions (default: OR).",
                            "default": "OR"
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional. A JSON object for filtering. Keys can be 'has_active_opportunity' or 'is_test_agency'. Each key holds an object like {'one_of': [true/false]} specifying the filter.",
                            "properties": {
                                "has_active_opportunity": {
                                    "type": "object",
                                    "properties": {"one_of": {"type": "array", "items": {"type": "boolean"}}}
                                },
                                "is_test_agency": {
                                    "type": "object",
                                    "properties": {"one_of": {"type": "array", "items": {"type": "boolean"}}}
                                }
                            }
                        },
                        "pagination": {
                            "type": "object",
                            "description": "Required. A JSON object for pagination. Must include 'page_offset', 'page_size', and 'sort_order' (array of objects with 'order_by': ['agency_code', 'agency_name'] and 'sort_direction': ['ascending', 'descending']).",
                            "properties": {
                                "page_offset": {"type": "integer", "description": "Page number (starts at 1)."},
                                "page_size": {"type": "integer", "description": "Results per page."},
                                "sort_order": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "order_by": {"type": "string", "enum": ["agency_code", "agency_name"]},
                                            "sort_direction": {"type": "string", "enum": ["ascending", "descending"]}
                                        },
                                        "required": ["order_by", "sort_direction"]
                                    }
                                }
                            },
                            "required": ["page_offset", "page_size", "sort_order"]
                        }
                    },
                    "required": ["pagination"]
                }
            }
        }

    def fn(self, pagination: Dict[str, Any], query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, query_operator: str = "OR") -> str:
        """
        Executes the search agencies request.
        """
        self.logger.info("Executing Simpler Grants Gov search agencies tool")
        payload: Dict[str, Any] = {
            "pagination": pagination,
            "query_operator": query_operator
        }
        if query:
            payload["query"] = query
        if filters:
            payload["filters"] = filters

        endpoint = "/v1/agencies/search"
        try:
            result = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"Search agencies successful. Response length: {len(result)}")
            return result
        except Exception as e:
            self.logger.error(f"Search agencies failed: {e}", exc_info=True)
            return json.dumps({"error": f"Search agencies failed: {str(e)}", "success": False})  