# Create Issue

## Overview

The `CreateIssue` function creates a new issue in a GitHub repository.

## Parameters

* `repo_url`: The URL of the repository, e.g. https://github.com/The-AI-Alliance/gofannon
* `title`: The title of the issue
* `body`: The body of the issue
* `labels`: An comma seperated string of labels for the issue (optional)

## Example Usage

```python  
from gofannon.github.create_issue import CreateIssue  
  
create_issue = CreateIssue(api_key="your_api_key_here")  
issue_url = create_issue.fn("https://github.com/The-AI-Alliance/gofannon", "New issue", "This is a new issue")  
print(issue_url)  