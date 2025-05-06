# QueryByMultipleCriteria

The `QueryByMultipleCriteria` tool allows searching for grant opportunities by combining various filter criteria such as agency codes, funding instruments/categories, applicant types, assistance listing numbers, and cost-sharing requirements using the Simpler Grants Gov API. This tool is useful for complex queries not covered by more specialized search tools. At least one filter criterion or `query_text` should be provided. It supports pagination and opportunity status filters.

## Parameters

*   `agency_codes` (array of strings, optional): List of agency codes (e.g., `["USAID", "DOC"]`).
*   `funding_instruments` (array of strings, optional): List of funding instruments. (See `QueryByFundingDetails` for valid values).
*   `funding_categories` (array of strings, optional): List of funding categories. (See `QueryByFundingDetails` for valid values).
*   `applicant_types` (array of strings, optional): List of applicant types. (See `QueryByApplicantEligibility` for valid values).
*   `assistance_listing_numbers` (array of strings, optional): List of Assistance Listing Numbers (e.g., `["10.001"]`).
*   `requires_cost_sharing` (boolean, optional): Filter by cost-sharing requirement.
*   `query_text` (string, optional): Text to search for within filtered results.
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
from gofannon.simpler_grants_gov.query_by_multiple_criteria import QueryByMultipleCriteria
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
multi_query_tool = QueryByMultipleCriteria()

try:  
    search_results_json = multi_query_tool.fn(  
        agency_codes=["DOE"],  
        funding_categories=["energy", "environment"],  
        applicant_types=["private_institutions_of_higher_education"],  
        requires_cost_sharing=True,  
        query_text="renewable energy innovation",  
        items_per_page=10,  
        order_by="post_date",  
        show_posted=True  
    )  
    print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   At least one filter criterion (e.g., `agency_codes`, `funding_instruments`) or `query_text` must be specified.
*   Refer to the documentation of specialized tools (`QueryByFundingDetails`, `QueryByApplicantEligibility`) for lists of valid string values for array parameters like `funding_instruments`, `funding_categories`, and `applicant_types`.
*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  