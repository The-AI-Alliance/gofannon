# QueryByAwardCriteria

The `QueryByAwardCriteria` tool searches for grant opportunities based on award amount criteria such as award floor, ceiling, number of expected awards, and total program funding, using the Simpler Grants Gov API. At least one award criterion or query_text must be specified. It supports pagination and opportunity status filters.

## Parameters

*   `min_award_floor` (integer, optional): Minimum award floor amount.
*   `max_award_ceiling` (integer, optional): Maximum award ceiling amount.
*   `min_expected_awards` (integer, optional): Minimum number of expected awards.
*   `max_expected_awards` (integer, optional): Maximum number of expected awards.
*   `min_total_funding` (integer, optional): Minimum estimated total program funding.
*   `max_total_funding` (integer, optional): Maximum estimated total program funding.
*   `query_text` (string, optional): Text to search for within the results filtered by award criteria.
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
from gofannon.simpler_grants_gov.query_by_award_criteria import QueryByAwardCriteria
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
award_query_tool = QueryByAwardCriteria()

try:  
    search_results_json = award_query_tool.fn(  
        min_award_floor=50000,  
        max_award_ceiling=200000,  
        min_expected_awards=3,  
        query_text="community projects",  
        items_per_page=5  
    )  
    print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   At least one award criterion (e.g., `min_award_floor`, `max_award_ceiling`, etc.) or `query_text` must be specified.
*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  