# Simpler Grants Gov API

This section documents the Gofannon tools for interacting with the Simpler Grants Gov API (api.grants.gov).

## Obtaining an API Key

To use these tools, you need an API key from Grants.gov.

1.  **Request Access:** Follow the instructions on the [Grants.gov Web Services page](https://www.grants.gov/web-services) to request an API key.
2.  **Configuration:** Once you have the key, set it as an environment variable named `SIMPLER_GRANTS_API_KEY`. You can also set the `SIMPLER_GRANTS_BASE_URL` environment variable if you need to point to a specific API endpoint (e.g., a non-production environment), otherwise it defaults to `https://api.grants.gov/grants`.

Add these to your `.env` file or export them in your shell:

```bash  
export SIMPLER_GRANTS_API_KEY="your_actual_api_key_here"
# Optional: export SIMPLER_GRANTS_BASE_URL="https://your_custom_url/grants"
```

Gofannon tools will automatically pick up these variables.

## Implemented Tools Status

| API Endpoint              | Gofannon Tool Function                      | Status                   |  
| :------------------------ | :------------------------------------------ | :----------------------- |  
| `POST /v1/agencies`       | [ListAgencies](list_agencies.md)            | :white_check_mark: Implemented |  
| `POST /v1/agencies/search`| [SearchAgencies](search_agencies.md)        | :white_check_mark: Implemented |  
| `GET /v1/opportunities/{id}`| [GetOpportunity](get_opportunity.md)        | :white_check_mark: Implemented |  
| `POST /v1/opportunities/search`| [SearchOpportunities](search_opportunities.md)| :white_check_mark: Implemented |  

*(Other endpoints like user management, extracts, alpha features are not yet implemented as Gofannon tools).*  