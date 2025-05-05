# Search Opportunities

The `SearchOpportunities` tool searches for grant opportunities using various criteria like keywords, filters, and pagination settings via the Simpler Grants Gov API.

Corresponds to the `POST /v1/opportunities/search` API endpoint.

## Parameters

*   `pagination` (object, required): Controls pagination and sorting.
    *   `page_offset` (integer, required): Page number (starts at 1).
    *   `page_size` (integer, required): Results per page.
    *   `sort_order` (array, required): Array of sort objects.
        *   `order_by` (string, required): Field to sort by (e.g., `"post_date"`, `"close_date"`, `"opportunity_id"`, `"agency_code"`).
        *   `sort_direction` (string, required): Sort direction (`"ascending"` or `"descending"`).
*   `query` (string, optional): Keyword search string applied across multiple text fields.
*   `query_operator` (string, optional): Operator (`"AND"` or `"OR"`) for combining query conditions. Default is `"AND"`.
*   `filters` (object, optional): A complex object containing various filters. Refer to the API documentation or the tool's definition for the exact structure. Examples include:
    *   `opportunity_status`: e.g., `{"one_of": ["posted", "forecasted"]}`
    *   `agency`: e.g., `{"one_of": ["USAID", "HHS"]}`
    *   `funding_instrument`: e.g., `{"one_of": ["grant", "cooperative_agreement"]}`
    *   `post_date`: e.g., `{"start_date": "2024-01-01", "end_date": "2024-03-31"}`
    *   `award_ceiling`: e.g., `{"max": 500000}`
    *   *(Many other filters available)*

## Example Usage

```python  
from gofannon.simpler_grants_gov.search_opportunities import SearchOpportunities

# Assumes SIMPLER_GRANTS_API_KEY is set in environment
search_opps_tool = SearchOpportunities()

# Define pagination - required
pagination_settings = {  
    "page_offset": 1,  
    "page_size": 20,  
    "sort_order": [{"order_by": "post_date", "sort_direction": "descending"}]  
}

# Optional query
search_query = "climate research"

# Optional filters (structure depends on the specific filter)
search_filters = {  
        "opportunity_status": {"one_of": ["posted"]},  
        "funding_category": {"one_of": ["science_and_technology", "environment"]},  
        "agency": {"one_of": ["NSF"]},  
        "post_date": {"start_date": "2024-01-01"}  
}

# Call the tool function
result_json = search_opps_tool.fn(  
    pagination=pagination_settings,  
    query=search_query,  
    filters=search_filters,  
    query_operator="AND"  
)

print(result_json) # Output is a JSON string  
```

## Return Value

Returns a JSON string containing the API response, which typically includes a `data` array of matching opportunity objects, `facet_counts` (if applicable), and `pagination_info`. If an error occurs, it returns a JSON string with an "error" key.  