# List Agencies

The `ListAgencies` tool retrieves a paginated list of agencies from the Simpler Grants Gov API, with options for basic filtering.

Corresponds to the `POST /v1/agencies` API endpoint.

## Parameters

*   `pagination` (object, required): Controls pagination and sorting.
    *   `page_offset` (integer, required): Page number to retrieve (starts at 1).
    *   `page_size` (integer, required): Number of results per page.
    *   `sort_order` (array, required): Array of sort objects.
        *   `order_by` (string, required): Field to sort by. Allowed: `"agency_code"`, `"agency_name"`, `"created_at"`.
        *   `sort_direction` (string, required): Sort direction. Allowed: `"ascending"`, `"descending"`.
*   `filters` (object, optional): Filters the list of agencies.
    *   `agency_id` (string, optional): Filter by a specific agency UUID.
    *   `active` (boolean, optional): Filter by active status.

## Example Usage

```python  
from gofannon.simpler_grants_gov.list_agencies import ListAgencies

# Assumes SIMPLER_GRANTS_API_KEY is set in environment
list_agencies_tool = ListAgencies()

# Define pagination - required
pagination_settings = {  
    "page_offset": 1,  
    "page_size": 10,  
    "sort_order": [{"order_by": "agency_name", "sort_direction": "ascending"}]  
}

# Optional filters
agency_filters = {  
    "active": True  
}

# Call the tool function
result_json = list_agencies_tool.fn(  
pagination=pagination_settings,  
filters=agency_filters  
)

print(result_json) # Output is a JSON string  
```

## Return Value

Returns a JSON string containing the API response, which includes a `data` array of agency objects and `pagination_info`. If an error occurs, it returns a JSON string with an "error" key.  