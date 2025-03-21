import pytest  
from gofannon.wikipedia.wikipedia_lookup import WikipediaLookup
import responses

def test_wikipedia_lookup_successful_response():
    """Test WikipediaLookup with a successfull API response."""

    tool = WikipediaLookup()

    result = tool.fn("Python Programming")

    assert isinstance(result, dict)
    assert "title" in result
    assert "summary" in result
    assert "image" in result
    assert "url" in result

@responses.activate
def test_wikipedia_lookup_with_mock():
    """Test WikipediaLookup with mocked API response."""

    mock_response = {
        "title": "Test Article",
        "extract": "This is a test summary.",
        "thumbnail": {"source": "https://example.con/image.jpg"},
        "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Test"}}
    }

    responses.add(
        responses.GET,
        "https://en.wikipedia.org/api/rest_v1/page/summary/Test_Query",
        json=mock_response,
        status=200
    )

    tool = WikipediaLookup()

    result = tool.fn("Test Query")

    assert result["title"] == "Test Article"
    assert result["summary"] == "This is a test summary."
    assert result["image"] == "https://example.com/image.jpg"
    assert result["url"] == "https://en.wikipedia.org/wiki/Test"

@responses.activate
def test_wikipedia_lookup_error_response():
    """Test WikipediaLookup with a failing API response."""

    responses.add(
        responses.GET,
         "https://en.wikipedia.org/api/rest_v1/page/summary/Test_Query",
        status=404
    )

    tool = WikipediaLookup()

    result = tool.fn("Test Query")

    assert "error" in result
    assert result["error"] == "Failed to fetch Wikipedia summary for Test Query"

    def test_definition():
        """Test that the tool definition is correctly structured."""
        tool = WikipediaLookup()
        definition = tool.definition

        assert isinstance(definition, dict)
        assert definition["type"] == "function"
        assert definition["function"]["name"] == "wikipedia_lookup"
        assert "parameters" in definition["function"]
        assert "query" in definition["function"]["parameters"]["properties"]