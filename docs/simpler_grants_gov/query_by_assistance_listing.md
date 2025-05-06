# QueryByAssistanceListing

The `QueryByAssistanceListing` tool searches for grant opportunities by one or more Assistance Listing Numbers (formerly CFDA numbers) using the Simpler Grants Gov API. Numbers should be in the format '##.###' or '##.##'. It supports pagination and opportunity status filters.

## Parameters

*   `assistance_listing_numbers` (array of strings, required): List of Assistance Listing Numbers (e.g., `["10.001", "93.123"]`). Must match pattern `##.###` or `##.##`.
*   `query_text` (string, optional): Text to search for within the results filtered by assistance listing.
*   `query_operator` (string, optional, enum: ["AND", "OR"], default: "AND"): Operator for `query_text` if provided.
*   `items_per_page` (integer, optional, default: 5): Number of results per page.
*   `page_number` (integer, optional, default: 1): The page number to retrieve.
*   `order_by` (string, optional, default: "relevancy"): Field to sort results by.
*   `sort_direction` (string, optional, enum: ["ascending", "descending"], default: "descending"): Direction to sort.
*   `show_posted` (boolean, optional, default: True): Include 'posted' opportunities.
*   `show_forecasted` (boolean, optional, default: False): Include 'forecasted' opportunities.
*   `show_closed` (boolean, optional, default: False): Include 'closed' opportunities.
*   `show_archived` (boolean, optional, default: False): Include 'archived' opportunities.

## Example Usage

```python  
from gofannon.simpler_grants_gov.query_by_assistance_listing import QueryByAssistanceListing
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
assistance_query_tool = QueryByAssistanceListing()

target_aln = ["43.001", "47.049"] # Example Assistance Listing Numbers

try:  
    search_results_json = assistance_query_tool.fn(  
        assistance_listing_numbers=target_aln,  
        query_text="space research",  
        items_per_page=5,  
        show_forecasted=True  
    )  
    print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   The `assistance_listing_numbers` list cannot be empty.
*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  