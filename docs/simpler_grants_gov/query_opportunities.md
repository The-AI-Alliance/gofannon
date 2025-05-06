# QueryOpportunities

The `QueryOpportunities` tool searches for grant opportunities using a general text query against the Simpler Grants Gov API. It supports pagination and filtering by opportunity status.

## Parameters

*   `query_text` (string, required): The text to search for in opportunity titles, descriptions, etc.
*   `query_operator` (string, optional, enum: ["AND", "OR"], default: "AND"): Operator for combining terms in `query_text`.
*   `items_per_page` (integer, optional, default: 5): Number of results per page (e.g., 10, 25, 50).
*   `page_number` (integer, optional, default: 1): The page number to retrieve (starts at 1).
*   `order_by` (string, optional, default: "relevancy"): Field to sort results by (e.g., 'relevancy', 'post_date', 'opportunity_id', 'agency_code').
*   `sort_direction` (string, optional, enum: ["ascending", "descending"], default: "descending"): Direction to sort.
*   `show_posted` (boolean, optional, default: True): Include 'posted' opportunities.
*   `show_forecasted` (boolean, optional, default: False): Include 'forecasted' opportunities.
*   `show_closed` (boolean, optional, default: False): Include 'closed' opportunities.
*   `show_archived` (boolean, optional, default: False): Include 'archived' opportunities.

## Example Usage

```python  
from gofannon.simpler_grants_gov.query_opportunities import QueryOpportunities
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
query_tool = QueryOpportunities()

search_term = "environmental research"

try:  
    search_results_json = query_tool.fn(  
        query_text=search_term,  
        items_per_page=10,  
        page_number=1,  
        order_by="post_date",  
        sort_direction="descending",  
        show_posted=True,  
        show_forecasted=True  
    )  
print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  