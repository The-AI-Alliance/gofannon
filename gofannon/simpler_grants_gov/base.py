import requests
import logging
import json
from typing import Optional, Dict, Any

from ..base import BaseTool
from ..config import ToolConfig

logger = logging.getLogger(__name__)

class SimplerGrantsGovBase(BaseTool):
    """
    Base class for tools interacting with the Simpler Grants Gov API.

    Handles common setup like API key and base URL management, and provides
    a helper method for making authenticated requests.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or ToolConfig.get("simpler_grants_api_key")
        self.base_url = base_url or ToolConfig.get("simpler_grants_base_url")

        if not self.api_key:
            msg = "Simpler Grants Gov API key is missing. Please set SIMPLER_GRANTS_API_KEY environment variable or pass api_key argument."
            logger.error(msg)
            # Decide on behavior: raise error or allow initialization but fail on execution?
            # Raising an error early is often clearer.
            # raise ValueError(msg)
            # Or, log and proceed, letting _make_request handle the missing key later.
            self.logger.warning(msg + " Tool execution will likely fail.")


        if not self.base_url:
            msg = "Simpler Grants Gov base URL is missing. Please set SIMPLER_GRANTS_BASE_URL environment variable or pass base_url argument."
            logger.error(msg)
            # raise ValueError(msg)
            self.logger.warning(msg + " Tool execution will likely fail.")

        self.logger.debug(f"Initialized {self.__class__.__name__} with base_url: {self.base_url} and API key {'present' if self.api_key else 'missing'}")


    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, json_payload: Optional[Dict[str, Any]] = None) -> str:
        """
        Makes an authenticated request to the Simpler Grants Gov API.

        Args:
            method: HTTP method (e.g., 'GET', 'POST').
            endpoint: API endpoint path (e.g., '/v1/opportunities/search').
            params: URL query parameters.
            json_payload: JSON body for POST/PUT requests.

        Returns:
            The JSON response content as a string.

        Raises:
            requests.exceptions.RequestException: If the request fails.
            ValueError: If API key or base URL is missing.
        """
        if not self.api_key:
            raise ValueError("Simpler Grants Gov API key is missing.")
        if not self.base_url:
            raise ValueError("Simpler Grants Gov base URL is missing.")

        full_url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            # Based on api_key_auth.py, the API expects the key in this header
            'X-Auth': self.api_key,
            'Content-Type': 'application/json',
            'accept': 'application/json'
        }

        self.logger.debug(f"Making {method} request to {full_url}")
        self.logger.debug(f"Headers: {{'X-Auth': '***', 'Content-Type': 'application/json', 'accept': 'application/json'}}") # Don't log key
        if params:
            self.logger.debug(f"Params: {params}")
        if json_payload:
            # Be careful logging potentially large/sensitive payloads
            log_payload = json.dumps(json_payload)[:500] # Log truncated payload
            self.logger.debug(f"JSON Payload (truncated): {log_payload}")


        try:
            response = requests.request(
                method,
                full_url,
                headers=headers,
                params=params,
                json=json_payload,
                timeout=30 # Add a reasonable timeout
            )
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            # Check if response is empty or not JSON before trying to parse
            content_type = response.headers.get('Content-Type', '')
            if response.content and 'application/json' in content_type:
                try:
                    # Return raw text which usually includes JSON string
                    return response.text
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to decode JSON response from {full_url}. Status: {response.status_code}. Content: {response.text[:500]}... Error: {e}")
                    # Return raw text even if not JSON, could be an error message
                    return response.text
            elif response.content:
                self.logger.warning(f"Response from {full_url} is not JSON (Content-Type: {content_type}). Returning raw text.")
                return response.text
            else:
                self.logger.warning(f"Received empty response from {full_url}. Status: {response.status_code}")
                return "" # Return empty string for empty response


        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request to {full_url} failed: {e}")
            # Re-raise the exception to be handled by the BaseTool's execute method
            # Or return a formatted error string
            # return json.dumps({"error": f"API request failed: {e}"})
            raise # Re-raise for BaseTool's error handling


    # Subclasses must implement definition and fn
    @property
    def definition(self):
        raise NotImplementedError("Subclasses must implement the 'definition' property.")

    def fn(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the 'fn' method.")