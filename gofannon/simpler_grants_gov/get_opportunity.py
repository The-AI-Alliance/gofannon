import logging
from typing import Optional
import json

from .base import SimplerGrantsGovBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class GetOpportunity(SimplerGrantsGovBase):
    """
    Tool to retrieve details for a specific grant opportunity by its ID.
    Corresponds to the GET /v1/opportunities/{opportunity_id} endpoint.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "get_opportunity"):
        super().__init__(api_key=api_key, base_url=base_url)
        self.name = name

    @property
    def definition(self):
        # Based on route GET /v1/opportunities/{opportunity_id} and OpportunityGetResponseV1Schema
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Retrieve the full details of a specific grant opportunity, including attachments, using its unique identifier.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "opportunity_id": {
                            "type": "integer",
                            "description": "The unique numeric identifier for the grant opportunity."
                        }
                    },
                    "required": ["opportunity_id"]
                }
            }
        }

    def fn(self, opportunity_id: int) -> str:
        """
        Executes the get opportunity request.

        Args:
            opportunity_id: The ID of the opportunity to retrieve.

        Returns:
            A JSON string representing the opportunity details.
        """
        self.logger.info(f"Executing Simpler Grants Gov get opportunity tool for ID: {opportunity_id}")

        if not isinstance(opportunity_id, int) or opportunity_id <= 0:
            # Add validation for the ID
            self.logger.error(f"Invalid opportunity_id provided: {opportunity_id}. Must be a positive integer.")
            return json.dumps({"error": "Invalid opportunity_id provided. Must be a positive integer.", "success": False})

        endpoint = f"/v1/opportunities/{opportunity_id}"
        try:
            result = self._make_request("GET", endpoint)
            self.logger.debug(f"Get opportunity successful for ID {opportunity_id}. Response length: {len(result)}")
            return result
        except Exception as e:
            self.logger.error(f"Get opportunity failed for ID {opportunity_id}: {e}", exc_info=True)
            # Return a JSON error string
            return json.dumps({"error": f"Get opportunity failed: {str(e)}", "success": False})
