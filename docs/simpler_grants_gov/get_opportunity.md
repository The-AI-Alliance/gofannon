# Get Opportunity

The `GetOpportunity` tool retrieves the full details for a specific grant opportunity, including its attachments, using its unique numeric ID from the Simpler Grants Gov API.

Corresponds to the `GET /v1/opportunities/{opportunity_id}` API endpoint.

## Parameters

*   `opportunity_id` (integer, required): The unique numeric identifier for the grant opportunity.

## Example Usage

```python  
from gofannon.simpler_grants_gov.get_opportunity import GetOpportunity

# Assumes SIMPLER_GRANTS_API_KEY is set in environment
get_opportunity_tool = GetOpportunity()

# Specify the opportunity ID
opp_id = 12345 # Replace with a valid opportunity ID

# Call the tool function
result_json = get_opportunity_tool.fn(opportunity_id=opp_id)

print(result_json) # Output is a JSON string containing opportunity details  
```

## Return Value

Returns a JSON string containing the detailed API response for the specified opportunity. If the opportunity is not found or an error occurs, it returns a JSON string with an "error" key.  