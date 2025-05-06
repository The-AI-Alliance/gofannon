# QueryByApplicantEligibility

The `QueryByApplicantEligibility` tool searches for grant opportunities based on applicant types and/or cost-sharing requirements using the Simpler Grants Gov API. It supports pagination and opportunity status filters.

## Parameters

*   `applicant_types` (array of strings, optional): List of applicant types (e.g., `["state_governments", "nonprofits_with_501c3"]`). Valid values: `city_or_township_governments`, `county_governments`, `federal_government_agencies_fed_recognized_tribes_excluded`, `independent_school_districts`, `individuals`, `native_american_tribal_governments_federally_recognized`, `native_american_tribal_organizations_other_than_federally_recognized_tribal_governments`, `nonprofits_having_a_501c3_status_with_the_irs_other_than_institutions_of_higher_education`, `nonprofits_that_do_not_have_a_501c3_status_with_the_irs_other_than_institutions_of_higher_education`, `private_institutions_of_higher_education`, `public_and_state_controlled_institutions_of_higher_education`, `public_housing_authorities_or_indian_housing_authorities`, `small_businesses`, `special_district_governments`, `state_governments`, `other`.
*   `requires_cost_sharing` (boolean, optional): Filter by cost-sharing requirement. `True` for opportunities requiring cost sharing, `False` for those not requiring it. Omit to not filter by this.
*   `query_text` (string, optional): Text to search for within the results filtered by eligibility.
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
from gofannon.simpler_grants_gov.query_by_applicant_eligibility import QueryByApplicantEligibility
# Assuming SIMPLER_GRANTS_API_KEY and SIMPLER_GRANTS_BASE_URL are set in environment

# Initialize the tool
eligibility_query_tool = QueryByApplicantEligibility()

try:  
    search_results_json = eligibility_query_tool.fn(  
        applicant_types=["small_businesses", "individuals"],  
        requires_cost_sharing=False,  
        query_text="technology grants",  
        items_per_page=3  
    )  
    print(search_results_json)  
# Further process the JSON string  
except Exception as e:  
    print(f"An error occurred: {e}")  
```

## Notes

*   If used for filtering, at least one of `applicant_types` or `requires_cost_sharing` should be specified, or a `query_text` must be provided.
*   The tool returns a JSON string of matching opportunities.
*   If the API request fails, a JSON string containing an error message will be returned.  