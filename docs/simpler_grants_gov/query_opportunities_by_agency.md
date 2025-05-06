# QueryOpportunitiesByAgencyCode

The `QueryOpportunitiesByAgencyCode` tool searches for grant opportunities filtered by one or more agency codes using the Simpler Grants Gov API. An optional text query can further refine results. It also supports standard pagination and opportunity status filters.

## Parameters

*   `agency_codes` (array of strings, required): A list of agency codes to filter by (e.g., `["USAID", "DOC"]`).
*   `query_text` (string, optional): Text to search for within the results filtered by agency.
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
from gofannon.simpler_grants_gov.query_opportunities_by_agency import QueryOpportunitiesByAgencyCode
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
agency_query_tool = QueryOpportunitiesByAgencyCode()

target_agencies = ["HHS", "NSF"] # Example agency codes

try:  
    search_results_json = agency_query_tool.fn(  
        agency_codes=target_agencies,  
        query_text="cancer research", # Optional text query  
        items_per_page=5,  
        show_posted=True  
    )
    
print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   The `agency_codes` list cannot be empty.
*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  