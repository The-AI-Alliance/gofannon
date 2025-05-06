import pytest
import responses
import json
from unittest.mock import patch

from gofannon.simpler_grants_gov.get_opportunity import GetOpportunity
from gofannon.simpler_grants_gov.query_opportunities import QueryOpportunities
from gofannon.simpler_grants_gov.query_opportunities_by_agency import QueryOpportunitiesByAgencyCode
from gofannon.simpler_grants_gov.query_by_funding_details import QueryByFundingDetails
from gofannon.simpler_grants_gov.query_by_applicant_eligibility import QueryByApplicantEligibility
from gofannon.simpler_grants_gov.query_by_award_criteria import QueryByAwardCriteria
from gofannon.simpler_grants_gov.query_by_dates import QueryByDates
from gofannon.simpler_grants_gov.query_by_assistance_listing import QueryByAssistanceListing
from gofannon.simpler_grants_gov.query_by_multiple_criteria import QueryByMultipleCriteria

MOCK_API_KEY = "test_sgg_api_key"
MOCK_BASE_URL = "https://mockapi.grants.gov/grants"

# Helper to mock ToolConfig.get
@pytestfixture(autouse=True)
def mock_tool_config():
    with patch('gofannon.config.ToolConfig.get') as mock_get:
        def side_effect(key):
            if key == "simpler_grants_api_key":
                return MOCK_API_KEY
            if key == "simpler_grants_base_url":
                return MOCK_BASE_URL
            return None
        mock_get.side_effect = side_effect
        yield mock_get

def mock_api_response(data=None, status=200, error_message=None):
    if error_message:
        return json.dumps({"error": error_message, "success": False})
    if data is None:
        data = {"message": "Success", "data": {}} # Default success if no data
    return json.dumps(data)


class TestGetOpportunity:
    TOOL_ENDPOINT_BASE = "/v1/opportunities"

    def test_definition(self):
        tool = GetOpportunity()
        definition = tool.definition
        assert definition["type"] == "function"
        assert definition["function"]["name"] == "get_opportunity"
        assert "opportunity_id" in definition["function"]["parameters"]["properties"]
        assert "opportunity_id" in definition["function"]["parameters"]["required"]

    @responses.activate
    def test_get_opportunity_success(self):
        opportunity_id = 12345
        expected_url = f"{MOCK_BASE_URL}{self.TOOL_ENDPOINT_BASE}/{opportunity_id}"
        mock_data = {"opportunity_id": opportunity_id, "opportunity_title": "Test Grant"}

        responses.add(
            responses.GET,
            expected_url,
            json=mock_data, # responses library handles json.dumps internally
            status=200,
            content_type='application/json'
        )

        tool = GetOpportunity()
        result_str = tool.fn(opportunity_id=opportunity_id)
        result = json.loads(result_str)

        assert result == mock_data # API returns raw data, not wrapped in Gofannon's structure

    @responses.activate
    def test_get_opportunity_not_found(self):
        opportunity_id = 99999
        expected_url = f"{MOCK_BASE_URL}{self.TOOL_ENDPOINT_BASE}/{opportunity_id}"

        responses.add(
            responses.GET,
            expected_url,
            json={"error": "Not Found"},
            status=404,
            content_type='application/json'
        )

        tool = GetOpportunity()
        result_str = tool.fn(opportunity_id=opportunity_id)
        result = json.loads(result_str)

        assert "error" in result
        assert "Get opportunity failed" in result["error"] # Tool wraps original error

    def test_get_opportunity_invalid_id(self):
        tool = GetOpportunity()
        result_str = tool.fn(opportunity_id=-1) # Invalid ID
        result = json.loads(result_str)
        assert "error" in result
        assert "Invalid opportunity_id" in result["error"]
        assert result.get("success") is False


class TestSearchToolsBaseFunctionality:
    SEARCH_ENDPOINT = f"{MOCK_BASE_URL}/v1/opportunities/search"

    @responses.activate
    def _test_search_tool_success(self, tool_instance, fn_args, expected_payload_elements):
        mock_response_data = {"data": [{"opportunity_id": 1}], "pagination_info": {"total_records": 1}}
        responses.add(
            responses.POST,
            self.SEARCH_ENDPOINT,
            json=mock_response_data, # API returns raw data
            status=200,
            content_type='application/json'
        )

        result_str = tool_instance.fn(**fn_args)
        result = json.loads(result_str)

        assert result == mock_response_data

        # Check payload
        assert len(responses.calls) == 1
        sent_payload = json.loads(responses.calls[0].request.body)

        for key, value in expected_payload_elements.items():
            if isinstance(value, dict): # For nested structures like filters or pagination
                assert key in sent_payload
                for sub_key, sub_value in value.items():
                    assert sent_payload[key].get(sub_key) == sub_value
            else:
                assert sent_payload.get(key) == value

                # Verify common pagination and status if not explicitly in expected_payload_elements
        if "pagination" not in expected_payload_elements:
            assert "pagination" in sent_payload
            assert sent_payload["pagination"]["page_offset"] == fn_args.get("page_number", 1)
            assert sent_payload["pagination"]["page_size"] == fn_args.get("items_per_page", 5)

        if "filters" not in expected_payload_elements or "opportunity_status" not in expected_payload_elements.get("filters", {}):
            if "filters" in sent_payload and "opportunity_status" in sent_payload["filters"]:
                expected_statuses = []
                if fn_args.get("show_posted", True): expected_statuses.append("posted")
                if fn_args.get("show_forecasted", False): expected_statuses.append("forecasted")
                if fn_args.get("show_closed", False): expected_statuses.append("closed")
                if fn_args.get("show_archived", False): expected_statuses.append("archived")
                if expected_statuses:
                    assert sent_payload["filters"]["opportunity_status"]["one_of"] == expected_statuses
                else: # if all show_ flags are false
                    assert "opportunity_status" not in sent_payload.get("filters", {})


    @responses.activate
    def _test_search_tool_api_error(self, tool_instance, fn_args):
        responses.add(
            responses.POST,
            self.SEARCH_ENDPOINT,
            json={"error": "Server Error"},
            status=500,
            content_type='application/json'
        )
        result_str = tool_instance.fn(**fn_args)
        result = json.loads(result_str)
        assert "error" in result
        assert "API request failed" in result["error"]

    def _test_tool_definition_common_params(self, definition):
        params = definition["function"]["parameters"]["properties"]
        assert "items_per_page" in params
        assert "page_number" in params
        assert "order_by" in params
        assert "sort_direction" in params
        assert "show_posted" in params
        assert "show_forecasted" in params
        assert "show_closed" in params
        assert "show_archived" in params

class TestQueryOpportunities(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryOpportunities()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities"
        assert "query_text" in definition["function"]["parameters"]["properties"]
        assert "query_operator" in definition["function"]["parameters"]["properties"]
        assert "query_text" in definition["function"]["parameters"]["required"]
        self._test_tool_definition_common_params(definition)

    def test_fn_success_basic_query(self):
        tool = QueryOpportunities()
        fn_args = {"query_text": "health research"}
        expected_payload = {"query": "health research", "query_operator": "AND"}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_with_options(self):
        tool = QueryOpportunities()
        fn_args = {
            "query_text": "education",
            "query_operator": "OR",
            "items_per_page": 10,
            "page_number": 2,
            "order_by": "post_date",
            "sort_direction": "ascending",
            "show_forecasted": True,
            "show_posted": False # Override default
        }
        expected_payload = {
            "query": "education",
            "query_operator": "OR",
            "pagination": {
                "page_offset": 2,
                "page_size": 10,
                "sort_order": [{"order_by": "post_date", "sort_direction": "ascending"}]
            },
            "filters": { "opportunity_status": {"one_of": ["forecasted"]} }
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_api_error(self):
        tool = QueryOpportunities()
        self._test_search_tool_api_error(tool, {"query_text": "test"})

class TestQueryOpportunitiesByAgencyCode(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryOpportunitiesByAgencyCode()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities_by_agency"
        assert "agency_codes" in definition["function"]["parameters"]["properties"]
        assert "query_text" in definition["function"]["parameters"]["properties"]
        assert "agency_codes" in definition["function"]["parameters"]["required"]
        self._test_tool_definition_common_params(definition)

    def test_fn_success_only_agency(self):
        tool = QueryOpportunitiesByAgencyCode()
        fn_args = {"agency_codes": ["USAID", "DOC"]}
        expected_payload = {
            "filters": { "agency": {"one_of": ["USAID", "DOC"]} }
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_agency_and_query(self):
        tool = QueryOpportunitiesByAgencyCode()
        fn_args = {"agency_codes": ["HHS"], "query_text": "cancer"}
        expected_payload = {
            "query": "cancer",
            "query_operator": "AND",
            "filters": { "agency": {"one_of": ["HHS"]} }
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_empty_agency_codes(self):
        tool = QueryOpportunitiesByAgencyCode()
        result_str = tool.fn(agency_codes=[])
        result = json.loads(result_str)
        assert "error" in result
        assert "agency_codes list cannot be empty" in result["error"]

    def test_fn_api_error(self):
        tool = QueryOpportunitiesByAgencyCode()
        self._test_search_tool_api_error(tool, {"agency_codes": ["TEST"]})


class TestQueryByFundingDetails(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryByFundingDetails()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities_by_funding_details"
        assert "funding_instruments" in definition["function"]["parameters"]["properties"]
        assert "funding_categories" in definition["function"]["parameters"]["properties"]
        assert not definition["function"]["parameters"].get("required") # No single required, logic in fn
        self._test_tool_definition_common_params(definition)

    def test_fn_success_instruments_only(self):
        tool = QueryByFundingDetails()
        fn_args = {"funding_instruments": ["grant"]}
        expected_payload = {"filters": {"funding_instrument": {"one_of": ["grant"]}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_categories_only(self):
        tool = QueryByFundingDetails()
        fn_args = {"funding_categories": ["health"]}
        expected_payload = {"filters": {"funding_category": {"one_of": ["health"]}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_both_and_query(self):
        tool = QueryByFundingDetails()
        fn_args = {
            "funding_instruments": ["cooperative_agreement"],
            "funding_categories": ["education"],
            "query_text": "early childhood"
        }
        expected_payload = {
            "query": "early childhood",
            "query_operator": "AND",
            "filters": {
                "funding_instrument": {"one_of": ["cooperative_agreement"]},
                "funding_category": {"one_of": ["education"]}
            }
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_no_funding_filters(self):
        tool = QueryByFundingDetails()
        result_str = tool.fn() # No instruments or categories
        result = json.loads(result_str)
        assert "error" in result
        assert "At least one of 'funding_instruments' or 'funding_categories' must be provided" in result["error"]

    def test_fn_api_error(self):
        tool = QueryByFundingDetails()
        self._test_search_tool_api_error(tool, {"funding_instruments": ["grant"]})


class TestQueryByApplicantEligibility(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryByApplicantEligibility()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities_by_applicant_eligibility"
        assert "applicant_types" in definition["function"]["parameters"]["properties"]
        assert "requires_cost_sharing" in definition["function"]["parameters"]["properties"]
        self._test_tool_definition_common_params(definition)

    def test_fn_success_types_only(self):
        tool = QueryByApplicantEligibility()
        fn_args = {"applicant_types": ["state_governments"]}
        expected_payload = {"filters": {"applicant_type": {"one_of": ["state_governments"]}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_cost_sharing_true(self):
        tool = QueryByApplicantEligibility()
        fn_args = {"requires_cost_sharing": True}
        expected_payload = {"filters": {"is_cost_sharing": {"one_of": [True]}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_cost_sharing_false(self):
        tool = QueryByApplicantEligibility()
        fn_args = {"requires_cost_sharing": False}
        expected_payload = {"filters": {"is_cost_sharing": {"one_of": [False]}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_both_and_query(self):
        tool = QueryByApplicantEligibility()
        fn_args = {
            "applicant_types": ["nonprofits_with_501c3"],
            "requires_cost_sharing": False,
            "query_text": "homelessness"
        }
        expected_payload = {
            "query": "homelessness",
            "filters": {
                "applicant_type": {"one_of": ["nonprofits_with_501c3"]},
                "is_cost_sharing": {"one_of": [False]}
            }
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_no_eligibility_filters_no_query(self):
        tool = QueryByApplicantEligibility()
        result_str = tool.fn() # Neither filter specified
        result = json.loads(result_str)
        assert "error" in result
        assert "Please provide 'applicant_types', 'requires_cost_sharing', or 'query_text'" in result["error"]

    def test_fn_api_error(self):
        tool = QueryByApplicantEligibility()
        self._test_search_tool_api_error(tool, {"applicant_types": ["individuals"]})


class TestQueryByAwardCriteria(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryByAwardCriteria()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities_by_award_criteria"
        assert "min_award_floor" in definition["function"]["parameters"]["properties"]
        assert "max_award_ceiling" in definition["function"]["parameters"]["properties"]
        # ... add more checks for other award params
        self._test_tool_definition_common_params(definition)

    def test_fn_success_min_floor(self):
        tool = QueryByAwardCriteria()
        fn_args = {"min_award_floor": 10000}
        expected_payload = {"filters": {"award_floor": {"min": 10000}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_max_ceiling_and_min_total(self):
        tool = QueryByAwardCriteria()
        fn_args = {"max_award_ceiling": 500000, "min_total_funding": 1000000}
        expected_payload = {
            "filters": {
                "award_ceiling": {"max": 500000},
                "estimated_total_program_funding": {"min": 1000000}
            }
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_expected_awards_range(self):
        tool = QueryByAwardCriteria()
        fn_args = {"min_expected_awards": 5, "max_expected_awards": 10}
        expected_payload = {
            "filters": {"expected_number_of_awards": {"min": 5, "max": 10}}
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_no_award_criteria_no_query(self):
        tool = QueryByAwardCriteria()
        result_str = tool.fn()
        result = json.loads(result_str)
        assert "error" in result
        assert "At least one award criterion or query_text must be specified" in result["error"]

    def test_fn_api_error(self):
        tool = QueryByAwardCriteria()
        self._test_search_tool_api_error(tool, {"min_award_floor": 0})

class TestQueryByDates(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryByDates()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities_by_dates"
        assert "post_start_date" in definition["function"]["parameters"]["properties"]
        # ... add more date params
        self._test_tool_definition_common_params(definition)

    def test_fn_success_post_date_range(self):
        tool = QueryByDates()
        fn_args = {"post_start_date": "2023-01-01", "post_end_date": "2023-01-31"}
        expected_payload = {"filters": {"post_date": {"start_date": "2023-01-01", "end_date": "2023-01-31"}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_close_start_only(self):
        tool = QueryByDates()
        fn_args = {"close_start_date": "2024-06-01"}
        expected_payload = {"filters": {"close_date": {"start_date": "2024-06-01"}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_no_date_criteria_no_query(self):
        tool = QueryByDates()
        result_str = tool.fn()
        result = json.loads(result_str)
        assert "error" in result
        assert "At least one date parameter or query_text must be specified" in result["error"]

    def test_fn_api_error(self):
        tool = QueryByDates()
        self._test_search_tool_api_error(tool, {"post_start_date": "2023-01-01"})

class TestQueryByAssistanceListing(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryByAssistanceListing()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities_by_assistance_listing"
        assert "assistance_listing_numbers" in definition["function"]["parameters"]["properties"]
        assert "assistance_listing_numbers" in definition["function"]["parameters"]["required"]
        self._test_tool_definition_common_params(definition)

    def test_fn_success(self):
        tool = QueryByAssistanceListing()
        fn_args = {"assistance_listing_numbers": ["10.001", "93.123"]}
        expected_payload = {"filters": {"assistance_listing_number": {"one_of": ["10.001", "93.123"]}}}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_empty_list(self):
        tool = QueryByAssistanceListing()
        result_str = tool.fn(assistance_listing_numbers=[])
        result = json.loads(result_str)
        assert "error" in result
        assert "assistance_listing_numbers list cannot be empty" in result["error"]

    def test_fn_api_error(self):
        tool = QueryByAssistanceListing()
        self._test_search_tool_api_error(tool, {"assistance_listing_numbers": ["00.000"]})

class TestQueryByMultipleCriteria(TestSearchToolsBaseFunctionality):
    def test_definition(self):
        tool = QueryByMultipleCriteria()
        definition = tool.definition
        assert definition["function"]["name"] == "query_opportunities_by_multiple_criteria"
        assert "agency_codes" in definition["function"]["parameters"]["properties"]
        assert "funding_instruments" in definition["function"]["parameters"]["properties"]
        # ... check other combined params
        self._test_tool_definition_common_params(definition)

    def test_fn_success_agency_and_funding(self):
        tool = QueryByMultipleCriteria()
        fn_args = {
            "agency_codes": ["DOE"],
            "funding_instruments": ["grant"],
            "show_forecasted": True
        }
        expected_payload = {
            "filters": {
                "agency": {"one_of": ["DOE"]},
                "funding_instrument": {"one_of": ["grant"]},
                "opportunity_status": {"one_of": ["posted", "forecasted"]} # Default posted + forecasted
            }
        }
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_success_query_only(self):
        tool = QueryByMultipleCriteria()
        fn_args = {"query_text": "renewable energy"}
        expected_payload = {"query": "renewable energy", "query_operator": "AND"}
        self._test_search_tool_success(tool, fn_args, expected_payload)

    def test_fn_no_filters_no_query(self):
        tool = QueryByMultipleCriteria()
        result_str = tool.fn()
        result = json.loads(result_str)
        assert "error" in result
        assert "At least one filter criterion or query_text must be specified" in result["error"]

    def test_fn_api_error(self):
        tool = QueryByMultipleCriteria()
        self._test_search_tool_api_error(tool, {"query_text": "complex search"})
  