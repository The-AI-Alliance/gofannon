import pytest
from unittest.mock import patch
from gofannon.marginalia_search.marginalia_search import MarginaliaSearch

@pytest.fixture
def mock_marginalia_search():
    with patch("gofannon.marginalia_search.marginalia_search.requests.get") as mock_get:
        yield mock_get

def test_marginalia_search_valid_query(mock_marginalia_search):
    # Mock the Marginalia API response
    mock_marginalia_search.return_value = {
        'results': [
            {'title': 'Test Result 1', 'description': 'Test Snippet 1', 'url': 'http://example.com/1'},
            {'title': 'Test Result 2', 'description': 'Test Snippet 2', 'url': 'http://example.com/2'}
        ]
    }

    # Initialize the MarginaliaSearch tool (replace with your actual API key and engine ID)
    marginalia_search = MarginaliaSearch()

    # Execute the search
    results = marginalia_search.fn("test query", index=0, limit=2)

    # Assert that the results are as expected
    assert "Title: Test Result 1" in results
    assert "Snippet: Test Snippet 1" in results
    assert "Link: http://example.com/1" in results
    assert "Title: Test Result 2" in results
    assert "Snippet: Test Snippet 2" in results
    assert "Link: http://example.com/2" in results

def test_marginalia_search_no_results(mock_marginalia_search):
    # Mock the Marginalia API response with no results
    mock_marginalia_search.return_value = {'results': []}

    # Initialize the MarginaliaSearch tool
    marginalia_search = MarginaliaSearch()

    # Execute the search
    results = marginalia_search.fn("test query", index=0, limit=2)

    # Assert that the results are empty
    assert results == ""

def test_marginalia_search_api_error(mock_marginalia_search):
    # Mock the Marginalia API to raise an exception
    mock_marginalia_search.side_effect = Exception("API Error")

    # Initialize the MarginaliaSearch tool
    marginalia_search = MarginaliaSearch()

    # Execute the search
    results = marginalia_search.fn("test query", index=0, limit=2)

    # Assert that the error message is returned
    assert "Error during Marginalia Search: API Error" in results