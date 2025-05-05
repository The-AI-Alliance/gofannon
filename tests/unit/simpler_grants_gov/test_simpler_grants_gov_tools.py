import pytest
import json
from unittest.mock import patch, MagicMock
import requests # Import requests to mock its exceptions

# Import the tool classes
from gofannon.simpler_grants_gov.list_agencies import ListAgencies
from gofannon.simpler_grants_gov.search_agencies import SearchAgencies
from gofannon.simpler_grants_gov.get_opportunity import GetOpportunity
from gofannon.simpler_grants_gov.search_opportunities import SearchOpportunities

# --- Constants for testing ---
MOCK_API_KEY = "test-key"
MOCK_BASE_URL = "https://test.grants.gov/grants"

# Sample valid inputs
SAMPLE_PAGINATION = {
    "page_offset": 1,
    "page_size": 10,
    "sort_order": [{"order_by": "created_at", "sort_direction": "descending"}]
}
SAMPLE_AGENCY_FILTERS = {"active": True}
SAMPLE_OPP_FILTERS = {"opportunity_status": {"one_of": ["posted"]}}
SAMPLE_QUERY = "research"
SAMPLE_OPPORTUNITY_ID = 12345
SAMPLE_SUCCESS_RESPONSE = json.dumps({"data": [{"id": 1}], "pagination_info": {}, "message": "Success", "success": True})
SAMPLE_ERROR_MESSAGE = "API Request Failed"

# --- Test GetOpportunity ---

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_get_opportunity_success(mock_make_request):
    """Test GetOpportunity successful execution."""
    mock_make_request.return_value = SAMPLE_SUCCESS_RESPONSE
    tool = GetOpportunity(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(opportunity_id=SAMPLE_OPPORTUNITY_ID)

    expected_endpoint = f"/v1/opportunities/{SAMPLE_OPPORTUNITY_ID}"
    mock_make_request.assert_called_once_with("GET", expected_endpoint)
    assert result == SAMPLE_SUCCESS_RESPONSE

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_get_opportunity_api_error(mock_make_request):
    """Test GetOpportunity handling an API error."""
    mock_make_request.side_effect = requests.exceptions.RequestException(SAMPLE_ERROR_MESSAGE)
    tool = GetOpportunity(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(opportunity_id=SAMPLE_OPPORTUNITY_ID)

    expected_endpoint = f"/v1/opportunities/{SAMPLE_OPPORTUNITY_ID}"
    mock_make_request.assert_called_once_with("GET", expected_endpoint)
    result_data = json.loads(result)
    assert not result_data.get("success")
    assert "error" in result_data
    assert SAMPLE_ERROR_MESSAGE in result_data["error"]

def test_get_opportunity_invalid_id():
    """Test GetOpportunity with an invalid ID."""
    tool = GetOpportunity(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result_neg = tool.fn(opportunity_id=-5)
    result_zero = tool.fn(opportunity_id=0)
    # result_str = tool.fn(opportunity_id="abc") # This would fail type hint before fn runs

    result_neg_data = json.loads(result_neg)
    assert not result_neg_data.get("success")
    assert "Invalid opportunity_id" in result_neg_data["error"]

    result_zero_data = json.loads(result_zero)
    assert not result_zero_data.get("success")
    assert "Invalid opportunity_id" in result_zero_data["error"]

# --- Test SearchOpportunities ---

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_search_opportunities_success_all_params(mock_make_request):
    """Test SearchOpportunities successful execution with all parameters."""
    mock_make_request.return_value = SAMPLE_SUCCESS_RESPONSE
    tool = SearchOpportunities(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(
        pagination=SAMPLE_PAGINATION,
        query=SAMPLE_QUERY,
        filters=SAMPLE_OPP_FILTERS,
        query_operator="OR"
    )

    expected_endpoint = "/v1/opportunities/search"
    expected_payload = {
        "pagination": SAMPLE_PAGINATION,
        "query": SAMPLE_QUERY,
        "filters": SAMPLE_OPP_FILTERS,
        "query_operator": "OR"
    }
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)
    assert result == SAMPLE_SUCCESS_RESPONSE

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_search_opportunities_success_minimal_params(mock_make_request):
    """Test SearchOpportunities successful execution with only required parameters."""
    mock_make_request.return_value = SAMPLE_SUCCESS_RESPONSE
    tool = SearchOpportunities(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    # Call with only pagination, relying on defaults for others
    result = tool.fn(pagination=SAMPLE_PAGINATION)

    expected_endpoint = "/v1/opportunities/search"
    # Default query_operator is 'AND'
    expected_payload = {
        "pagination": SAMPLE_PAGINATION,
        "query_operator": "AND"
    }
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)
    assert result == SAMPLE_SUCCESS_RESPONSE


@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_search_opportunities_api_error(mock_make_request):
    """Test SearchOpportunities handling an API error."""
    mock_make_request.side_effect = requests.exceptions.RequestException(SAMPLE_ERROR_MESSAGE)
    tool = SearchOpportunities(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(pagination=SAMPLE_PAGINATION)

    expected_endpoint = "/v1/opportunities/search"
    expected_payload = {"pagination": SAMPLE_PAGINATION, "query_operator": "AND"}
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)

    result_data = json.loads(result)
    assert not result_data.get("success")
    assert "error" in result_data
    assert SAMPLE_ERROR_MESSAGE in result_data["error"]

# --- Test ListAgencies ---

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_list_agencies_success_with_filters(mock_make_request):
    """Test ListAgencies successful execution with filters."""
    mock_make_request.return_value = SAMPLE_SUCCESS_RESPONSE
    tool = ListAgencies(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(
        pagination=SAMPLE_PAGINATION,
        filters=SAMPLE_AGENCY_FILTERS
    )

    expected_endpoint = "/v1/agencies"
    expected_payload = {
        "pagination": SAMPLE_PAGINATION,
        "filters": SAMPLE_AGENCY_FILTERS
    }
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)
    assert result == SAMPLE_SUCCESS_RESPONSE

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_list_agencies_success_minimal(mock_make_request):
    """Test ListAgencies successful execution with minimal parameters."""
    mock_make_request.return_value = SAMPLE_SUCCESS_RESPONSE
    tool = ListAgencies(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(pagination=SAMPLE_PAGINATION)

    expected_endpoint = "/v1/agencies"
    expected_payload = {"pagination": SAMPLE_PAGINATION}
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)
    assert result == SAMPLE_SUCCESS_RESPONSE

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_list_agencies_api_error(mock_make_request):
    """Test ListAgencies handling an API error."""
    mock_make_request.side_effect = requests.exceptions.RequestException(SAMPLE_ERROR_MESSAGE)
    tool = ListAgencies(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(pagination=SAMPLE_PAGINATION)

    expected_endpoint = "/v1/agencies"
    expected_payload = {"pagination": SAMPLE_PAGINATION}
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)

    result_data = json.loads(result)
    assert not result_data.get("success")
    assert "error" in result_data
    assert SAMPLE_ERROR_MESSAGE in result_data["error"]

# --- Test SearchAgencies ---

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_search_agencies_success_all_params(mock_make_request):
    """Test SearchAgencies successful execution with all parameters."""
    mock_make_request.return_value = SAMPLE_SUCCESS_RESPONSE
    tool = SearchAgencies(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(
        pagination=SAMPLE_PAGINATION,
        query=SAMPLE_QUERY,
        filters=SAMPLE_AGENCY_FILTERS,
        query_operator="AND" # Override default OR
    )

    expected_endpoint = "/v1/agencies/search"
    expected_payload = {
        "pagination": SAMPLE_PAGINATION,
        "query": SAMPLE_QUERY,
        "filters": SAMPLE_AGENCY_FILTERS,
        "query_operator": "AND"
    }
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)
    assert result == SAMPLE_SUCCESS_RESPONSE

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_search_agencies_success_minimal(mock_make_request):
    """Test SearchAgencies successful execution with minimal parameters."""
    mock_make_request.return_value = SAMPLE_SUCCESS_RESPONSE
    tool = SearchAgencies(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(pagination=SAMPLE_PAGINATION) # Default query_operator is OR

    expected_endpoint = "/v1/agencies/search"
    expected_payload = {
        "pagination": SAMPLE_PAGINATION,
        "query_operator": "OR" # Default
    }
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)
    assert result == SAMPLE_SUCCESS_RESPONSE

@patch('gofannon.simpler_grants_gov.base.SimplerGrantsGovBase._make_request')
def test_search_agencies_api_error(mock_make_request):
    """Test SearchAgencies handling an API error."""
    mock_make_request.side_effect = requests.exceptions.RequestException(SAMPLE_ERROR_MESSAGE)
    tool = SearchAgencies(api_key=MOCK_API_KEY, base_url=MOCK_BASE_URL)

    result = tool.fn(pagination=SAMPLE_PAGINATION)

    expected_endpoint = "/v1/agencies/search"
    expected_payload = {"pagination": SAMPLE_PAGINATION, "query_operator": "OR"}
    mock_make_request.assert_called_once_with("POST", expected_endpoint, json_payload=expected_payload)

    result_data = json.loads(result)
    assert not result_data.get("success")
    assert "error" in result_data
    assert SAMPLE_ERROR_MESSAGE in result_data["error"]