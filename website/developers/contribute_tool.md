---    
layout: default    
title: Contributing A Tool  
redirect_from:
- /how-tos/contribute_tool.html
---    

# Tutorial: Contributing a New Tool to Gofannon

This guide will walk you through the process of contributing a new tool to the     
Gofannon repository. We'll focus on creating a simple REST API function that     
doesn't require authentication, making it ideal for first-time contributors.

For a comprehensive overview of what tools are, see the [functions and tools overview](https://the-ai-alliance.github.io/gofannon/docs/functions_and_tools_overview.html)

## Step 1: Add an Issue to the Repository

Before starting work on your contribution, create an issue in the Gofannon repository to discuss your proposed tool with the maintainers. This ensures your contribution aligns with the project's goals and avoids duplication of effort. Include:

- The API you plan to wrap
- A brief description of the tool's functionality
- Any authentication requirements (if applicable)
- If the tool requires `setup_parameters` (like API keys), define them in the issue.

Wait for feedback from the maintainers before proceeding to implementation.

## Step 2: Find a Simple REST API

Once your proposal is approved, identify a simple REST API that doesn't require authentication (requiring    
authentication introduces a degree of complexity and is covered in the appendix    
below). Some good examples include:

- Public APIs like [OpenNotify](http://open-notify.org/)
- Public datasets like [NASA APIs](https://api.nasa.gov/)
- Simple utility APIs like [JSONPlaceholder](https://jsonplaceholder.typicode.com/)

For this tutorial, we'll use the [OpenNotify ISS Location API](http://open-notify.org/Open-Notify-API/ISS-Location-Now/).    
**Note:** This has already been implemented.

If you're having a difficult time choosing a REST API, see Appendix C below.

## Step 3: Create a New Python File

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

## Step 4: Implement the Function

Follow this pattern to implement your function:

```python      
from ..base import BaseTool      
from ..config import FunctionRegistry      
import logging      
import requests

logger = logging.getLogger(__name__) # Use getLogger for module-level logger

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
        self.logger.debug("Fetching ISS location") # Use self.logger from BaseTool    
        response = requests.get("http://api.open-notify.org/iss-now.json")      
        response.raise_for_status()      
        return response.json()      
```

### Key Components Explained:

1. **BaseTool Inheritance**: Your class must inherit from `BaseTool` to get core functionality (including `self.logger`).
2. **FunctionRegistry.register**: This decorator registers your function with Gofannon's internal function registry. This is important for some Gofannon features like the `FunctionOrchestrator`.
3. **definition Property**: Defines the function's interface using OpenAI's function calling schema. This is used by LLMs to understand how to call your tool.
4. **fn Method**: Contains the actual implementation of your function.

## Step 5: Update `gofannon/manifest.json` and Add Documentation

### Update `gofannon/manifest.json`

For your tool to be discoverable by external systems that use Gofannon's manifest (like Agent UIs), you **must** add an entry for it in the `gofannon/manifest.json` file. This file is located at the root of the `gofannon` package directory.

1.  **Open `gofannon/manifest.json`**.
2.  **Add a new JSON object** for your tool to the `tools` array.
3.  **Structure of the entry:**  
    ```json  
    {  
    "id": "gofannon.your_api_directory.your_module_name.YourClassName",  
    "name": "your_tool_name",   
    "description": "Description of what your tool does",   
    "module_path": "gofannon.your_api_directory.your_module_name",  
    "class_name": "YourClassName",  
    "setup_parameters": [   
    // Optional: only if your tool __init__ takes config like api_key  
    // Example:  
    // {  
    //   "name": "api_key",   
    //   "label": "Your API Key Name",  
    //   "type": "secret",  
    //   "description": "API Key for Your API service.",  
    //   "required": true  
    // }  
    ]  
    }  
    ```
4.  **Fill in the details**:
    *   `id`: Should be unique, typically `your_full_module_path.YourClassName`.
    *   `name`: The functional name of your tool (should match `definition.function.name`).
    *   `description`: A user-friendly description (should match `definition.function.description`).
    *   `module_path`: The Python module path to your tool's file.
    *   `class_name`: The class name of your tool.
    *   `setup_parameters` (if applicable): If your tool's `__init__` method takes configuration parameters (e.g., `api_key`, `base_url`), define them here.
        *   `name`: The parameter name from `__init__`.
        *   `label`: A user-friendly label for UIs.
        *   `type`: Input type (e.g., "secret", "text").
        *   `description`: Help text.
        *   `required`: `true` or `false`.
5.  **Sort the `tools` array** alphabetically by `id` to maintain consistency.
6.  Validate the JSON structure.

### Add Documentation

Add a docstring to your class explaining what it does:

```python      
class IssLocator(BaseTool):      
"""Get the current location of the International Space Station (ISS)

    Uses the OpenNotify API to retrieve the ISS's current latitude and longitude.      
    Returns a dictionary with the ISS's position and timestamp.      
    """      
```

Create a markdown file for your tool in the appropriate `docs/` subdirectory (e.g., `docs/open_notify_space/iss_locator.md`). Describe its parameters and provide an example usage. Add a link to this new file in the corresponding `docs/.../index.md` file.

## Step 6: Test Your Function

#### 1. Create a test file:

```bash      
tests/unit/open_notify_space/test_iss_locator.py # Match your directory structure     
```

#### 2. Add basic tests:

```python      
import pytest      
from gofannon.open_notify_space.iss_locator import IssLocator # Adjust import

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
poetry install --all-extras # Ensure all optional dependencies for testing are included

# Run the tests
poetry run pytest tests/unit/open_notify_space/test_iss_locator.py -v # Or run all tests: poetry run pytest     
```

#### 4. Check the test output to ensure your function works as expected.

## Step 7: Submit Your Pull Request

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes (including `manifest.json` updates)
4. Push to your fork
5. Open a pull request

## Appendix A: Understanding the `@FunctionRegistry.register` Decorator

The `@FunctionRegistry.register` decorator primarily serves Gofannon's internal mechanisms:

1. Registers your function with Gofannon's central `FunctionRegistry`.
2. Makes your function available to internal Gofannon systems like the `FunctionOrchestrator`.

While important for these internal uses, for external discovery (e.g., by Agent UIs), the entry in `gofannon/manifest.json` is crucial. Ensure both are correctly set up.

## Next Steps

Once you're comfortable with simple REST functions, you can explore:
- Adding authentication (see Appendix B)
- Creating more complex parameter schemas
- Implementing more detailed error handling
- Adding caching or rate limiting

## Appendix B: Adding an API with Authentication

If you're working with an API that requires authentication, follow these additional steps:

### Step 1: Add API Key to Configuration

#### 1. Add your API key to the `.env` file (for local development):

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
from gofannon.base import BaseTool  
from gofannon.config import FunctionRegistry, ToolConfig # Import ToolConfig  
import requests  
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register  
class AuthenticatedApiTool(BaseTool):      
def __init__(self, api_key=None, name="authenticated_tool"): # 'name' is for the definition  
super().__init__()      
self.api_key = api_key or ToolConfig.get("new_api_key") # Load from config  
self.name = name      
# self.API_SERVICE = 'new_api_service_name' # If using API_SERVICE for auto key loading

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
        if not self.api_key:  
            self.logger.error("API key for AuthenticatedApiTool is missing.")  
            return {"error": "API key is missing."} # Or raise an exception  
              
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

### Step 3: Add Entry to `gofannon/manifest.json`

Ensure your authenticated tool has an entry in `gofannon/manifest.json` with appropriate `setup_parameters` for the `api_key`:

```json  
{  
"id": "gofannon.your_module.AuthenticatedApiTool",  
"name": "authenticated_tool",  
"description": "Description of your authenticated API function",  
"module_path": "gofannon.your_module",  
"class_name": "AuthenticatedApiTool",  
"setup_parameters": [  
{  
"name": "api_key",  
"label": "New API Key",  
"type": "secret",  
"description": "Your API key for the New API service.",  
"required": true   
}  
]  
}  
```  
*(Adjust `id`, `name`, `description`, `module_path`, `class_name`, and `label`/`description` for `api_key` as needed.)*

### Step 4: Add Error Handling

Add robust error handling for authentication failures:

```python      
def fn(self, **kwargs):      
if not self.api_key:  
self.logger.error("API key for AuthenticatedApiTool is missing.")  
# Consider raising a specific configuration error or returning a structured error  
return {"error": "Configuration error: API key is missing for AuthenticatedApiTool."}

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
                self.logger.error("Authentication failed: Invalid API key.")  
                return {"error": "Authentication failed: Invalid API key."} # Or raise  
                      
            response.raise_for_status() # For other HTTP errors (4xx, 5xx)     
            return response.json()      
                  
        except requests.exceptions.RequestException as e:      
            self.logger.error(f"API request failed: {e}")      
            return {"error": f"API request failed: {str(e)}"} # Or raise  
        except Exception as e: # Catch any other unexpected errors  
            self.logger.error(f"Unexpected error in AuthenticatedApiTool: {e}", exc_info=True)  
            return {"error": f"An unexpected error occurred: {str(e)}"} # Or raise  
```

### Step 5: Update Documentation

Update your function's documentation to include authentication requirements and how to configure the API key (e.g., via environment variable and `setup_parameters` in the UI).

```python      
class AuthenticatedApiTool(BaseTool):      
"""Description of your authenticated API function

    Requires an API key from https://api.example.com.      
    Configure this tool by providing the 'New API Key' during setup,   
    which corresponds to the NEW_API_KEY environment variable.  
    """      
```

### Step 6: Add Authentication Tests

Add tests for authentication scenarios:

```python      
def test_authentication_failure_if_key_is_invalid_mocked(mocker): # Assuming you mock requests  
# Mock ToolConfig.get to return an invalid key or None  
mocker.patch('gofannon.config.ToolConfig.get', return_value="invalid_key")

    # Mock requests.get to simulate a 401 error  
    mock_response = mocker.Mock()  
    mock_response.status_code = 401  
    mocker.patch('requests.get', return_value=mock_response)  
  
    tool = AuthenticatedApiTool() # Will attempt to load 'invalid_key'  
    result = tool.fn()      
              
    assert "error" in result  
    assert "Authentication failed" in result["error"]  

def test_missing_api_key(mocker):  
mocker.patch('gofannon.config.ToolConfig.get', return_value=None) # Simulate no key  
tool = AuthenticatedApiTool()  
result = tool.fn()  
assert "error" in result  
assert "API key is missing" in result["error"]  
```

### Best Practices for Authentication

1. Never hard-code API keys in your code.
2. Use environment variables (`.env` for local, secrets for CI/deployment) and `ToolConfig` for loading keys.
3. Define `setup_parameters` in `manifest.json` for UIs to prompt users for keys.
4. Handle authentication errors gracefully.
5. Consider adding rate limiting for API calls if the API enforces it.
6. Document authentication requirements clearly in the tool's docstring and markdown documentation.

# Appendix C: Choosing a REST API to Wrap a Tool: A Guide for New Contributors

If you're new to contributing tools for large language models (LLMs) or agentic systems, one of the most impactful ways to get started is by wrapping a REST API into a tool. REST APIs are widely used, well-documented, and provide access to a wealth of data and functionality. Here's a quick guide to help you choose the right REST API for your tool:

1. **Identify a Common Use Case**: Start by thinking about tasks that users frequently ask LLMs or agentic systems to perform. For example, retrieving weather data, fetching stock prices, or searching for information are common use cases. Choose an API that addresses one of these needs.

2. **Look for Well-Documented APIs**: A good REST API should have clear and comprehensive documentation. This makes it easier to understand how to use the API, what parameters it requires, and what kind of output it provides.

3. **Check for Accessibility**: Ensure the API is publicly accessible or provides an easy way to obtain an API key. Some APIs may require registration or have usage limits, so choose one that aligns with your project's goals.

4. **Consider Data Relevance**: The API should provide data or functionality that is relevant and useful to the end user. For example, a weather API is more universally useful than a niche API for a specific industry.

5. **Evaluate Performance and Reliability**: Choose an API that is reliable and has low latency. Users expect quick responses, so the API should be able to handle requests efficiently.

6. **Start Simple**: If you're new to this, start with a simple API that has a straightforward interface. For example, wrapping a currency conversion API or a public transportation schedule API is a great way to get started.

By following these guidelines, you can choose a REST API that will make a meaningful contribution to the ecosystem of tools for LLMs and agentic systems. Happy coding!    