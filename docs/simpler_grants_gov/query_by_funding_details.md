# QueryByFundingDetails

The `QueryByFundingDetails` tool searches for grant opportunities based on funding instruments and/or funding categories using the Simpler Grants Gov API. At least one of 'funding_instruments' or 'funding_categories' must be provided. It supports pagination and opportunity status filters.

## Parameters

*   `funding_instruments` (array of strings, optional): List of funding instruments (e.g., `["grant", "cooperative_agreement"]`). Valid values: `grant`, `cooperative_agreement`, `direct_payment_for_specified_use`, `direct_payment_with_unrestricted_use`, `direct_loan`, `guaranteed_or_insured_loan`, `insurance`, `other`, `procurement_contract`.
*   `funding_categories` (array of strings, optional): List of funding categories (e.g., `["health", "education"]`). Valid values: `agriculture`, `arts`, `business_and_commerce`, `community_development`, `consumer_protection`, `disaster_prevention_and_relief`, `education`, `employment_labor_and_training`, `energy`, `environment`, `food_and_nutrition`, `health`, `housing`, `humanities`, `information_and_statistics`, `infrastructure`, `income_security_and_social_services`, `international_affairs`, `law_justice_and_legal_services`, `natural_resources`, `opportunity_zone_benefits`, `recovery_act`, `regional_development`, `science_and_technology`, `transportation`, `other`.
*   `query_text` (string, optional): Text to search for within the results filtered by funding details.
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
from gofannon.simpler_grants_gov.query_by_funding_details import QueryByFundingDetails
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
funding_query_tool = QueryByFundingDetails()

try:  
    search_results_json = funding_query_tool.fn(  
        funding_instruments=["grant"],  
        funding_categories=["education", "science_and_technology"],  
        query_text="early childhood",  
        items_per_page=10,  
        show_posted=True  
    )  
    print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   At least one of `funding_instruments` or `funding_categories` must be provided.
*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  