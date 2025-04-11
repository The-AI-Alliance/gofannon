from ..base import BaseTool
from ..config import FunctionRegistry, ToolConfig
import logging
import requests

logger = logging.getLogger(__name__)

"""Fetch the Astronomy Picture of the Day (APOD) from NASA's API.

This tool retrieves the daily astronomy image, including metadata such as the 
title, explanation, date, and media type. It interacts with NASA's APOD API 
and returns the data as a structured dictionary.

Authentication:
        Requires an API key from NASA, available at https://api.nasa.gov/
        The API key should be set in the environment as NASA_APOD_API_KEY
        or passed as an argument during initialization.
"""

@FunctionRegistry.register
class AstronomyPhotoOfTheDayTool(BaseTool):
    def __init__(self, api_key=None ,name='apod'):
        super().__init__()
        self.name = name
        self.api_key = api_key or ToolConfig.get("nasa_apod_api_key")

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Get the Astronomy Picture of the Day from NASA",
                "parameters":{
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "return_direct": True
        }
    
    def fn(self, params: dict, *args, **kwargs) -> dict:
        logger.debug("Fetching NASA APOD data")
        if not self.api_key:
            logger.error("API key is missing. Cannot fetch APOD data.")
            return {"error": "API key is missing. Please set it in the environment or pass it as an argument."}
        url = "https://api.nasa.gov/planetary/apod"
        params = {
            "api_key": self.api_key
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return{
                "title": data.get("title", "No title available"),
                "date": data.get("date", "No date available"),
                "explanation": data.get("explanation", "No explanation available"),
                "url": data.get("url", None),
                "media_type": data.get("media_type", "unknown"),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from NASA APOD: {e}")
            return {
                "error": str(e)
            }