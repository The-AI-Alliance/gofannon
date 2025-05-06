# QueryByDates

The `QueryByDates` tool searches for grant opportunities based on post dates and/or close dates using the Simpler Grants Gov API. Dates should be in YYYY-MM-DD format. At least one date parameter or `query_text` must be specified. It supports pagination and opportunity status filters.

## Parameters

*   `post_start_date` (string, optional): Start of post date range (YYYY-MM-DD).
*   `post_end_date` (string, optional): End of post date range (YYYY-MM-DD).
*   `close_start_date` (string, optional): Start of close date range (YYYY-MM-DD).
*   `close_end_date` (string, optional): End of close date range (YYYY-MM-DD).
*   `query_text` (string, optional): Text to search for within the results filtered by dates.
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
from gofannon.simpler_grants_gov.query_by_dates import QueryByDates
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
date_query_tool = QueryByDates()

try:  
    search_results_json = date_query_tool.fn(  
        post_start_date="2023-01-01",  
        post_end_date="2023-03-31",  
        close_start_date="2023-04-01",  
        query_text="spring funding",  
        items_per_page=7,  
        order_by="close_date"  
    )  
    print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   At least one date parameter (e.g., `post_start_date`, `close_end_date`) or `query_text` must be specified.
*   Dates must be provided in "YYYY-MM-DD" format.
*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  