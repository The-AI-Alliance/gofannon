# Search Agencies

The `SearchAgencies` tool searches for agencies based on a query string and specific filters using the Simpler Grants Gov API.

Corresponds to the `POST /v1/agencies/search` API endpoint.

## Parameters

*   `pagination` (object, required): Controls pagination and sorting.
    *   `page_offset` (integer, required): Page number (starts at 1).
    *   `page_size` (integer, required): Results per page.
    *   `sort_order` (array, required): Array of sort objects.
        *   `order_by` (string, required): Field to sort by. Allowed: `"agency_code"`, `"agency_name"`.
        *   `sort_direction` (string, required): Sort direction. Allowed: `"ascending"`, `"descending"`.
*   `query` (string, optional): Query string to search against agency text fields.
*   `query_operator` (string, optional): Operator (`"AND"` or `"OR"`) for combining query conditions. Default is `"OR"`.
*   `filters` (object, optional): Structured filters.
    *   `has_active_opportunity` (object, optional): Filter based on whether the agency has active opportunities. e.g., `{"one_of": [True]}` or `{"one_of": [False]}`.
    *   `is_test_agency` (object, optional): Filter based on whether the agency is a test agency. e.g., `{"one_of": [True]}` or `{"one_of": [False]}`.

## Example Usage

```python  
from gofannon.simpler_grants_gov.search_agencies import SearchAgencies

# Assumes SIMPLER_GRANTS_API_KEY is set in environment
search_agencies_tool = SearchAgencies()

# Define pagination - required
pagination_settings = {  
    "page_offset": 1,  
    "page_size": 5,  
    "sort_order": [{"order_by": "agency_code", "sort_direction": "ascending"}]  
}

# Optional query
search_query = "Health"

# Optional filters
agency_filters = {  
    "has_active_opportunity": {"one_of": [True]}  
}

# Call the tool function
result_json = search_agencies_tool.fn(  
    pagination=pagination_settings,  
    query=search_query,  
    filters=agency_filters,  
    query_operator="AND" # Optional, defaults to OR  
)

print(result_json) # Output is a JSON string  
```

## Return Value

Returns a JSON string containing the API response, which includes a `data` array of matching agency objects and `pagination_info`. If an error occurs, it returns a JSON string with an "error" key.  