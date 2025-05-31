# How to Contribute to Gofannon

This guide will walk you through the process of adding a new function to the Gofannon repository. We'll cover everything from forking the repo to creating a pull request.

## 1. Fork the Repository
**TODO: Add link to forking in GitHub**

First, you'll need to fork the repository to your own GitHub account. This creates a copy of the repository where you can make changes without affecting the main project.

## 2. What Makes a Good Function?
When proposing a new function, consider these guidelines:

- **Single Responsibility**: Each function should do one thing well
- **Simple Interface**: Keep the API surface small and intuitive
- **Clear Documentation**: Include thorough documentation and examples
- **Error Handling**: Implement proper error handling and logging
- **Modular Design**: If an API has many functions, split them into multiple classes

## 3. Create an Issue
Before starting development, create an issue describing your proposed function:

1. Go to the Issues tab
2. Click "New Issue"
3. Use the "Function Proposal" template
4. Include:
    - Description of the function
    - Use cases
    - Proposed API interface
    - Any dependencies
    - If the tool requires `setup_parameters` (like API keys), define them in the issue.

**TODO: Add link to Issues tab**

## 4. Setting Up Your Development Environment
Clone your forked repository and set up the development environment:

```bash    
git clone https://github.com/YOUR_USERNAME/gofannon.git    
cd gofannon    
pip install -r requirements.txt    
```

## 5. Creating a New Function
### Directory Structure
Add your function under the appropriate directory in `gofannon/`. If it's a new API, create a new directory.

### Base Class Extension
All functions must extend the `BaseTool` class. Here's the basic structure:

```python    
from gofannon.base import BaseTool  
from gofannon.config import FunctionRegistry


@FunctionRegistry.register  
class NewFunction(BaseTool):  
def __init__(self, name="new_function"): # Add API_SERVICE here if needed, and other config params  
super().__init__()  
self.name = name  
# Example: self.API_SERVICE = 'new_api_service_name'

    @property  
    def definition(self):  
        return {  
            "type": "function",  
            "function": {  
                "name": self.name,  
                "description": "Description of what the function does",  
                "parameters": {  
                    "type": "object",  
                    "properties": {  
                        "param1": {  
                            "type": "string",  
                            "description": "Description of param1"  
                        }  
                    },  
                    "required": ["param1"]  
                }  
            }  
        }  
  
    def fn(self, param1):  
        # Implementation goes here    
        try:  
            # Your code    
            result = "..."  
            return result  
        except Exception as e:  
            self.logger.error(f"Error in new_function: {str(e)}") # Use self.logger  
            raise    
```

### Required Components
1. **Definition**: The JSON schema defining the function's interface.
2. **fn**: The main function implementation.
3. **Error Handling**: Proper error handling and logging (use `self.logger`).
4. **Documentation**: Add documentation in the `docs/` directory for your tool.
5. **Update `gofannon/manifest.json`**: Add an entry for your new tool in the manifest file.

### Updating `gofannon/manifest.json`

For your tool to be discoverable by external systems, you must add an entry to the `gofannon/manifest.json` file. This file is located at the root of the `gofannon` package directory.

1.  **Open `gofannon/manifest.json`**.
2.  **Add a new JSON object** for your tool to the `tools` array.
3.  **Structure of the entry:**  
    ```json  
    {  
    "id": "gofannon.new_api_name.your_function.NewFunction",  
    "name": "new_function", // Should match definition.function.name  
    "description": "Description of what the function does", // Should match definition.function.description  
    "module_path": "gofannon.new_api_name.your_function",  
    "class_name": "NewFunction",  
    "setup_parameters": [ // Optional: only if your tool __init__ takes config like api_key  
    {  
    "name": "api_key", // Matches the __init__ parameter name  
    "label": "New API Key",  
    "type": "secret",  
    "description": "API Key for the New API service.",  
    "required": true  
    }  
    ]  
    }  
    ```
4.  **Fill in the details**:
    *   `id`: `your_module_path.YourClassName`
    *   `name`: The functional name of your tool.
    *   `description`: A user-friendly description.
    *   `module_path`: The Python module path.
    *   `class_name`: The class name of your tool.
    *   `setup_parameters` (if applicable):
        *   `name`: The parameter name from your tool's `__init__` (e.g., `api_key`, `base_url`).
        *   `label`: A user-friendly label for UIs.
        *   `type`: Input type (e.g., "secret", "text").
        *   `description`: Help text.
        *   `required`: `true` or `false`.
5.  **Sort the `tools` array** alphabetically by `id` to maintain consistency.
6.  Validate the JSON structure.

### Documentation
Create a markdown file in the appropriate documentation directory:

```markdown
# New Function

## Description
Brief description of what the function does

## Parameters
- `param1`: Description of param1

## Example Usage
```python    
new_func = NewFunction()    
result = new_func.fn("example")    
```  
```

Add a link to your documentation in the appropriate `index.md` file (e.g., `docs/new_api_name/index.md`).

## 6. Testing Your Function

### Running Tests Locally

1. Install dependencies (if you haven't already):  
   ```bash  
   poetry install --all-extras  
   ```
2. Run tests:  
   ```bash  
   poetry run pytest tests/  
   ```

### GitHub Action

The GitHub Action will run automatically on pull requests to the main branch. You can view the test results in the GitHub Actions tab.

Write unit tests for your function. Create a new test file in the `tests/unit/your_api_name/` directory (e.g., `tests/unit/new_api_name/test_your_function.py`):

```python  
import pytest  
from gofannon.new_api_name.your_function import NewFunction # Adjust import path


def test_new_function():  
func = NewFunction()  
result = func.fn("test_param_value")  
expected_value = "expected_result_for_test_param" # Define expected result  
assert result == expected_value  
```

## 7. Committing Your Changes

Create a new branch for your feature:    
```bash    
git checkout -b feature/new-function    
```

Add and commit your changes. It's essential to include a DCO (Developer   
Certificate of Origin) sign off in your commit message. This sign off is a   
simple way for contributors to certify that they have the right to submit their   
work under the open-source license. By signing off on your commit, you're   
confirming that you're the original author of the work or have the necessary   
permissions to contribute it.

```bash    
git add --all    
git commit --signoff    
```

The `--signoff` flag will automatically append a "Signed-off-by" line to your   
commit message with your name and email address. You can learn more about DCO   
sign off on the [GitHub documentation](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).

Push your branch:    
```bash    
git push origin feature/new-function    
```

By including the DCO sign off, you're helping to ensure the long-term   
sustainability of the project and making it easier for others to use and   
distribute the code.

## 8. Creating a Pull Request

Go to your forked repository on GitHub  
Click "Compare & pull request"  
Fill out the PR template:  
Description of changes  
Related issues  
Testing performed  
Submit the PR

**TODO: Add link to PR creation**

## 9. Code Review

Be prepared to address feedback during code review. Common requests include:

* Adding more test cases
* Improving documentation or `manifest.json` entry
* Refactoring for better performance or readability

Tips for Success

* Keep your PRs focused on a single feature
* Write clear commit messages
* Follow the existing code style
* Add comprehensive documentation and update `manifest.json`
* Include meaningful test cases
* Be responsive to code review feedback

** TODO: Create and add link to coding style guide **  