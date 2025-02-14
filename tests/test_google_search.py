import pytest
from unittest.mock import patch
from gofannon.google_search.google_search import GoogleSearch

@pytest.fixture
def mock_google_search():
    with patch("gofannon.google_search.google_search.build") as mock_build:
        yield mock_build

def test_google_search_valid_query(mock_google_search):
    # Mock the Google API response
    mock_execute = mock_google_search.return_value.cse.return_value.list.return_value.execute
    mock_execute.return_value = {
        'items': [
            {'title': 'Test Result 1', 'snippet': 'Test Snippet 1', 'link': 'http://example.com/1'},
            {'title': 'Test Result 2', 'snippet': 'Test Snippet 2', 'link': 'http://example.com/2'}
        ]
    }

    # Initialize the GoogleSearch tool (replace with your actual API key and engine ID)
    google_search = GoogleSearch(api_key="test_api_key", engine_id="test_engine_id")

    # Execute the search
    results = google_search.fn("test query", num_results=2)

    # Assert that the results are as expected
    assert "Title: Test Result 1" in results
    assert "Snippet: Test Snippet 1" in results
    assert "Link: http://example.com/1" in results
    assert "Title: Test Result 2" in results
    assert "Snippet: Test Snippet 2" in results
    assert "Link: http://example.com/2" in results

def test_google_search_no_results(mock_google_search):
    # Mock the Google API response with no results
    mock_execute = mock_google_search.return_value.cse.return_value.list.return_value.execute
    mock_execute.return_value = {'items': []}

    # Initialize the GoogleSearch tool
    google_search = GoogleSearch(api_key="test_api_key", engine_id="test_engine_id")

    # Execute the search
    results = google_search.fn("test query", num_results=2)

    # Assert that the results are empty
    assert results == ""

def test_google_search_api_error(mock_google_search):
    # Mock the Google API to raise an exception
    mock_execute = mock_google_search.return_value.cse.return_value.list.return_value.execute
    mock_execute.side_effect = Exception("API Error")

    # Initialize the GoogleSearch tool
    google_search = GoogleSearch(api_key="test_api_key", engine_id="test_engine_id")

    # Execute the search
    results = google_search.fn("test query", num_results=2)

    # Assert that the error message is returned
    assert "Error during Google Search: API Error" in results