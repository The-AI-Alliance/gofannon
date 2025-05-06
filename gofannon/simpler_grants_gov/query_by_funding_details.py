import logging
import json
from typing import Optional, Dict, Any, List

from .search_base import SearchOpportunitiesBase
from ..config import FunctionRegistry

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class QueryByFundingDetails(SearchOpportunitiesBase):
    """
    Tool to search for grant opportunities based on funding instruments and/or categories.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, name: str = "query_opportunities_by_funding_details"):
        super().__init__(api_key=api_key, base_url=base_url, name=name)
        self.name = name

    @property
    def definition(self):
        base_params = self._get_common_parameter_definitions()
        specific_params = {
            "funding_instruments": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional. List of funding instruments (e.g., ['grant', 'cooperative_agreement']). Valid values: "
                               "grant, cooperative_agreement, direct_payment_for_specified_use, direct_payment_with_unrestricted_use, "
                               "direct_loan, guaranteed_or_insured_loan, insurance, other, procurement_contract."
            },
            "funding_categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional. List of funding categories (e.g., ['health', 'education']). Valid values: "
                               "agriculture, arts, business_and_commerce, community_development, consumer_protection, disaster_prevention_and_relief, "
                               "education, employment_labor_and_training, energy, environment, food_and_nutrition, health, housing, "
                               "humanities, information_and_statistics, infrastructure, income_security_and_social_services, "
                               "international_affairs, law_justice_and_legal_services, natural_resources, opportunity_zone_benefits, "
                               "recovery_act, regional_development, science_and_technology, transportation, other."
            },
            "query_text": {
                "type": "string",
                "description": "Optional. Text to search for within the results filtered by funding details."
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
                    "Search for grant opportunities by funding instruments and/or categories. "
                    "At least one of 'funding_instruments' or 'funding_categories' must be provided. "
                    f"{self._pagination_description}"
                    f"{self._status_filter_description}"
                    f"{self._common_search_description_suffix}"
                ),
                "parameters": {
                    "type": "object",
                    "properties": all_properties,
                    "required": [] # No single field is required, but logic in fn enforces at least one funding filter
                }
            }
        }

    def fn(self,
           funding_instruments: Optional[List[str]] = None,
           funding_categories: Optional[List[str]] = None,
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

        self.logger.info(f"Querying by funding details: instruments={funding_instruments}, categories={funding_categories}, query='{query_text}'")

        if not funding_instruments and not funding_categories:
            return json.dumps({"error": "At least one of 'funding_instruments' or 'funding_categories' must be provided.", "success": False})

        specific_filters: Dict[str, Any] = {}
        if funding_instruments:
            specific_filters["funding_instrument"] = {"one_of": funding_instruments}
        if funding_categories:
            specific_filters["funding_category"] = {"one_of": funding_categories}

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