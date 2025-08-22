# ListRepoFiles

The `ListRepoFiles` tool allows you to recursively list all files in a GitHub repository for a specific branch.

## Parameters

* `repo_url`: The URL of the GitHub repository (e.g. `https://github.com/octocat/Hello-World`)
* `branch`: *(optional)* The branch to list files from. If not provided, it will use the repository's default branch.

## Example Usage

```python
from gofannon.github.list_repo_files import ListRepoFiles

tool = ListRepoFiles(api_key="your_github_token")
# Returns a JSON string containing a list of all file paths
files_json = tool.fn(
    repo_url="https://github.com/The-AI-Alliance/gofannon",
    branch="main"
)
print(files_json)