# Simpler Grants Gov API

The Gofannon tools for the Simpler Grants Gov API allow you to search for and retrieve details about federal grant opportunities.

## Obtaining an API Key and Configuration

To use these tools, you need to configure two main items, typically via environment variables:

1.  **API Key**:
    *   Set the `SIMPLER_GRANTS_API_KEY` environment variable to your Simpler Grants Gov API key.
    *   This key is required for all API interactions.

2.  **Base URL**:
    *   Set the `SIMPLER_GRANTS_BASE_URL` environment variable if you need to point to a specific API endpoint (e.g., a non-production environment).
    *   If not set, it defaults to a production-like URL (e.g., `https://api.grants.gov/grants`, but verify the default in `gofannon/config.py` matches your needs).

These configurations are loaded by the `ToolConfig` class within Gofannon.

## Status

| API                     | Function                                                                 | Status                        |  
| ----------------------- | ------------------------------------------------------------------------ | ----------------------------- |  
| Simpler Grants Gov API  | [GetOpportunity](get_opportunity.md)                                     | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryOpportunities](query_opportunities.md)                             | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryOpportunitiesByAgencyCode](query_opportunities_by_agency.md)         | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryByFundingDetails](query_by_funding_details.md)                     | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryByApplicantEligibility](query_by_applicant_eligibility.md)         | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryByAwardCriteria](query_by_award_criteria.md)                       | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryByDates](query_by_dates.md)                                         | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryByAssistanceListing](query_by_assistance_listing.md)               | :white_check_mark: Implemented |  
| Simpler Grants Gov API  | [QueryByMultipleCriteria](query_by_multiple_criteria.md)                 | :white_check_mark: Implemented |  
  