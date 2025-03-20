---  
layout: default  
title: Contributing A Tool
---  

# Tutorial: Contributing a New Tool to Gofannon

This guide will walk you through the process of contributing a new tool to the 
Gofannon repository. We'll focus on creating a simple REST API function that 
doesn't require authentication, making it ideal for first-time contributors.

For a comprehensive overview of what tools are, see the [functions and tools overview](https://the-ai-alliance.github.io/gofannon/docs/functions_and_tools_overview.html)

## Step 1: Find a Simple REST API

Start by identifying a simple REST API that doesn't require authentication (requiring
authentication introduces a degree of complexity and is covered in the appendix
below). Some good examples include:

- Public APIs like [OpenNotify](http://open-notify.org/)
- Public datasets like [NASA APIs](https://api.nasa.gov/)
- Simple utility APIs like [JSONPlaceholder](https://jsonplaceholder.typicode.com/)

For this tutorial, we'll use the [OpenNotify ISS Location API](http://open-notify.org/Open-Notify-API/ISS-Location-Now/).
**Note:** This has already been implemented.

## Step 2: Create a New Python File

Create a new Python file in the appropriate directory. For our ISS location function, we'll create:

```bash  
gofannon/open_notify_space/iss_locator.py  
```

### Handling New APIs

If you're working with a new API that doesn't have an existing folder in the repository, you'll need to:

1. Create a new directory for your API:

```bash  
gofannon/new_api_name/  
```

2. Add an empty `__init__.py` file:

```bash  
gofannon/new_api_name/__init__.py  
```

3. Create your function file in the new directory:

```bash  
gofannon/new_api_name/your_function.py  
```

#### Important Notes:

- The `__init__.py` file should remain empty
- Do not import your function in the `__init__.py` file
- The function registration happens automatically through the decorator
- Follow the same pattern as existing functions for consistency

#### Example Directory Structure

For our ISS Locator example, the structure would look like:

```bash  
gofannon/  
├── open_notify_space/  
│   ├── __init__.py  
│   └── iss_locator.py  
```

## Step 3: Implement the Function

Follow this pattern to implement your function:

```python  
from ..base import BaseTool  
from ..config import FunctionRegistry  
import logging  
import requests

logger = logging.getLogger(__name__)

@FunctionRegistry.register  
class IssLocator(BaseTool):  
def __init__(self, name="iss_locator"):  
    super().__init__()  
    self.name = name

    @property  
    def definition(self):  
        return {  
            "type": "function",  
            "function": {  
                "name": self.name,  
                "description": "Get current location of the International Space Station",  
                "parameters": {  
                    "type": "object",  
                    "properties": {},  
                    "required": []  
                }  
            }  
        }  
  
    def fn(self):  
        logger.debug("Fetching ISS location")  
        response = requests.get("http://api.open-notify.org/iss-now.json")  
        response.raise_for_status()  
        return response.json()  
```

### Key Components Explained:

1. **BaseTool Inheritance**: Your class must inherit from `BaseTool` to get core functionality
2. **FunctionRegistry.register**: This decorator registers your function with Gofannon's function registry
3. **definition Property**: Defines the function's interface using OpenAI's function calling schema
4. **fn Method**: Contains the actual implementation of your function

## Step 4: Add Documentation

Add a docstring to your class explaining what it does:

```python  
class IssLocator(BaseTool):  
"""Get the current location of the International Space Station (ISS)

    Uses the OpenNotify API to retrieve the ISS's current latitude and longitude.  
    Returns a dictionary with the ISS's position and timestamp.  
    """  
```

## Step 5: Test Your Function

#### 1. Create a test file:

```bash  
tests/test_iss_locator.py  
```

#### 2. Add basic tests:

```python  
import pytest  
from gofannon.open_notify_space.iss_locator import IssLocator

def test_iss_locator():  
    tool = IssLocator()  
    result = tool.fn()

    assert isinstance(result, dict)  
    assert 'iss_position' in result  
    assert 'latitude' in result['iss_position']  
    assert 'longitude' in result['iss_position']  
```

#### 3. Run the tests locally using Poetry:

```bash
# Install dependencies (if you haven't already)
poetry install

# Run the tests
poetry run pytest tests/test_iss_locator.py -v  
```

#### 4. Check the test output to ensure your function works as expected.

## Step 6: Submit Your Pull Request

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to your fork
5. Open a pull request

## Appendix A: Understanding the Decorators

The `@FunctionRegistry.register` decorator does several important things:

1. Registers your function with Gofannon's central registry
2. Makes your function available to the orchestration system
3. Enables automatic documentation generation
4. Allows your function to be exported to different platforms (LangChain, Bedrock, etc.)

By following this pattern, you ensure your function integrates seamlessly with the rest of the Gofannon ecosystem.

## Next Steps

Once you're comfortable with simple REST functions, you can explore:
- Adding authentication
- Creating more complex parameter schemas
- Implementing error handling
- Adding caching or rate limiting  

## Appendix B: Adding an API with Authentication

If you're working with an API that requires authentication, follow these additional steps:

### Step 1: Add API Key to Configuration

#### 1. Add your API key to the `.env` file:

```bash  
NEW_API_KEY=your_api_key_here  
```

#### 2. Update the `ToolConfig` class in `gofannon/config.py`:

```python  
class ToolConfig:  
_instance = None

    def __init__(self):  
        load_dotenv()  
        self.config = {  
            # Existing keys...  
            'new_api_key': os.getenv('NEW_API_KEY'),  
        }  
```

### Step 2: Modify Your Function Class

Update your function class to handle authentication:

```python  
class AuthenticatedApiTool(BaseTool):  
def __init__(self, api_key=None, name="authenticated_tool"):  
super().__init__()  
self.api_key = api_key or ToolConfig.get("new_api_key")  
self.name = name  
self.API_SERVICE = 'new_api'  # Add this for API-specific configuration

    @property  
    def definition(self):  
        return {  
            "type": "function",  
            "function": {  
                "name": self.name,  
                "description": "Description of your authenticated API function",  
                "parameters": {  
                    "type": "object",  
                    "properties": {  
                        # Add your parameters here  
                    },  
                    "required": []  # Add required parameters here  
                }  
            }  
        }  
  
    def fn(self, **kwargs):  
        headers = {  
            'Authorization': f'Bearer {self.api_key}',  
            'Content-Type': 'application/json'  
        }  
          
        # Make your authenticated API call  
        response = requests.get(  
            "https://api.example.com/endpoint",  
            headers=headers,  
            params=kwargs  
        )  
        response.raise_for_status()  
        return response.json()  
```

### Step 3: Add Error Handling

Add robust error handling for authentication failures:

```python  
def fn(self, **kwargs):  
try:  
headers = {  
'Authorization': f'Bearer {self.api_key}',  
'Content-Type': 'application/json'  
}

        response = requests.get(  
            "https://api.example.com/endpoint",  
            headers=headers,  
            params=kwargs  
        )  
          
        # Handle authentication errors  
        if response.status_code == 401:  
            raise ValueError("Invalid API key")  
              
        response.raise_for_status()  
        return response.json()  
          
    except requests.exceptions.RequestException as e:  
        logger.error(f"API request failed: {e}")  
        raise  
```

### Step 4: Update Documentation

Update your function's documentation to include authentication requirements:

```python  
class AuthenticatedApiTool(BaseTool):  
"""Description of your authenticated API function

    Requires an API key from https://api.example.com  
    Set the API key in your .env file as NEW_API_KEY=your_key  
    """  
```

### Step 5: Add Authentication Tests

Add tests for authentication scenarios:

```python  
def test_authentication_failure():  
tool = AuthenticatedApiTool(api_key="invalid_key")

    with pytest.raises(ValueError) as exc_info:  
        tool.fn()  
          
    assert "Invalid API key" in str(exc_info.value)  
```

### Best Practices for Authentication

1. Never hard-code API keys in your code
2. Use environment variables for configuration
3. Handle authentication errors gracefully
4. Consider adding rate limiting for API calls
5. Document authentication requirements clearly  