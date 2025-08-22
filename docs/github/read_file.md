# ReadFile

The `ReadFile` API allows you to fetch the contents of a specific file from a GitHub repository.

## Parameters

* `repo_url`: The URL of the repository, e.g. `https://github.com/The-AI-Alliance/gofannon`
* `file_path`: The path to the file in the repository, e.g. `README.md`
* `branch`: *(optional)* The branch, tag, or commit SHA to retrieve the file from. If not provided, the repository's default branch is used.

## Example Usage

```python  
from gofannon.github.read_file import ReadFile

read_file = ReadFile(api_key="your_api_key_here")  
content = read_file.fn(
    repo_url="https://github.com/The-AI-Alliance/gofannon",
    file_path="README.md",
    branch="main"
)
print(content)