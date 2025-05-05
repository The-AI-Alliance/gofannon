import logging
from typing import Optional, Dict, Any
import json

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class ListAgencies(SimplerGrantsGovBase):
    """
    Tool to retrieve a list of agencies, potentially filtered.
    Corresponds to the POST /v1/agencies endpoint.
    NOTE: The API uses POST for listing/filtering, not GET.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "list_agencies"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Based on AgencyListRequestSchema
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Retrieve a paginated list of agencies, optionally filtered by agency ID or active status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "description": "Optional. A JSON object for filtering. Can contain 'agency_id' (UUID string) or 'active' (boolean).",
                            "properties": {
                                "agency_id": {"type": "string", "format": "uuid"},
                                "active": {"type": "boolean"}
                            }
                        },
                        "pagination": {
                            "type": "object",
                            "description": "Required. A JSON object for pagination. Must include 'page_offset', 'page_size', and 'sort_order' (array of objects with 'order_by': ['agency_code', 'agency_name', 'created_at'] and 'sort_direction': ['ascending', 'descending']).",
                            "properties": {
                                "page_offset": {"type": "integer", "description": "Page number (starts at 1)."},
                                "page_size": {"type": "integer", "description": "Results per page."},
                                "sort_order": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "order_by": {"type": "string", "enum": ["agency_code", "agency_name", "created_at"]},
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

    def fn(self, pagination: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> str:
        """
        Executes the list agencies request.
        """
        self.logger.info("Executing Simpler Grants Gov list agencies tool")
        payload = {"pagination": pagination}
        if filters:
            payload["filters"] = filters

        endpoint = "/v1/agencies"
        try:
            result = self._make_request("POST", endpoint, json_payload=payload)
            self.logger.debug(f"List agencies successful. Response length: {len(result)}")
            return result
        except Exception as e:
            self.logger.error(f"List agencies failed: {e}", exc_info=True)
            return json.dumps({"error": f"List agencies failed: {str(e)}", "success": False})
  