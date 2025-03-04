---  
layout: default  
title: Deploying the PR Review Tool
---  

# Deploying the PR Review Tool with Gofannon

The PR Review Tool uses gofannon’s automated review capabilities to analyze pull requests and post helpful feedback.  
This guide explains how to integrate and configure the tool – including customizing the review checks – into your repository.

## Prerequisites

- Fork or clone the [gofannon repository](https://github.com/The-AI-Alliance/gofannon).
- A GitHub personal access token (set as GITHUB_TOKEN).
- OpenAI API credentials (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME).

## Setting Up the Tool

1. **Include the New Tools**

   Ensure these files are part of your repository:
   - `gofannon/github/pr_review_tool.py`
   - A customizable review checks file placed at `.github/scripts/pr_review_checks.py`  
     (You can alter the checks or provide a different filename and set the environment variable PR_REVIEW_CHECKS_PATH accordingly.)

2. **Update Your CI Workflow**

   Modify your CI configuration (example below) to run the review script.

```yaml  
name: PR Tool Review  
on:  
pull_request_target:  
types: [labeled]

jobs:  
review:  
if: github.event.label.name == 'run-tests'  
runs-on: ubuntu-latest  
steps:  
- name: Check out the repository  
uses: actions/checkout@v4  
with:  
fetch-depth: 0  
- name: Set up Python  
uses: actions/setup-python@v5  
with:  
python-version: '3.10'  
- name: Install dependencies  
run: |  
python -m pip install --upgrade pip  
pip install -r requirements.txt  
- name: Run PR Review Tool  
env:  
GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  
OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}  
OPENAI_BASE_URL: ${{ vars.OPENAI_BASE_URL }}  
OPENAI_MODEL_NAME: ${{ vars.OPENAI_MODEL_NAME }}  
PR_NUMBER: ${{ github.event.pull_request.number }}  
REPO_NAME: ${{ github.repository }}  
# Optionally, specify a custom review checks file:  
# PR_REVIEW_CHECKS_PATH: ".github/scripts/my_custom_checks.py"  
run: |  
python .github/scripts/review_pr.py  
```

## How It Works

- The workflow is triggered when a pull request receives the label "run-tests."
- It checks out your repository, installs dependencies, and runs the PR review script.
- The script loads review checks from the configurable file, executes them on the PR files, and posts a summary comment on the pull request.

By following these steps and adjusting the review checks as needed, you can enforce code quality and custom validation rules tailored to your repository.  

## Creating Custom Review Checks

The PR Review Tool is designed to be extensible, allowing you to create custom checks tailored to your repository's needs. Here's how to create and integrate new checks:

### 1. Check File Structure

Create a new Python file in `.github/scripts/checks/` following this structure:

```python  
from github import Github

class YourCustomCheck:  
def __init__(self, client, model_name):  
# Initialize with OpenAI client and model name  
self.client = client  
self.model_name = model_name

    def process_pr_file(self, file, repo, pr):  
        """  
        Analyze individual files in the PR  
        Must return: (comments, analyzed)  
        - comments: List of dicts with review comments  
        - analyzed: Boolean indicating if file was processed  
        """  
        comments = []  
        analyzed = False  
          
        # Your analysis logic here  
        if file.filename.endswith('.py'):  
            analyzed = True  
            # Example comment format  
            comments.append({  
                "path": file.filename,  
                "body": "Your analysis message",  
                "line": 1  # Line number for comment  
            })  
              
        return comments, analyzed  
  
    def process_pr(self, pr):  
        """  
        Analyze the entire PR (optional)  
        Must return: (comments, analyzed)  
        """  
        comments = []  
        analyzed = True  
          
        # Example general PR analysis  
        comments.append({  
            "path": "GENERAL",  # Use "GENERAL" for PR-wide comments  
            "body": "Your overall analysis",  
            "line": 0  # Use 0 for general comments  
        })  
          
        return comments, analyzed  
```

### 2. Required Methods

Each check class must implement at least one of these methods:

- `process_pr_file(file, repo, pr)`: For file-specific analysis
    - `file`: GitHub file object
    - `repo`: GitHub repository object
    - `pr`: GitHub pull request object
    - Returns: (comments, analyzed) tuple

- `process_pr(pr)`: For PR-wide analysis
    - `pr`: GitHub pull request object
    - Returns: (comments, analyzed) tuple

### 3. Comment Format

Comments must be returned as a list of dictionaries with these keys:

```python  
{  
"path": "filename.py",  # File path or "GENERAL" for PR-wide comments  
"body": "Your review comment",  # Markdown-formatted text  
"line": 1  # Line number (0 for general comments)  
}  
```

### 4. Registering Your Check

1. Add your check class to `.github/scripts/pr_review_checks.py`:

```python  
from checks.your_check_file import YourCustomCheck  
```

2. The tool will automatically detect and run any class whose name ends with "Check"

### 5. Example Check: Documentation Check

Here's an example check that verifies Python files have docstrings:

```python  
import ast

class DocumentationCheck:  
def __init__(self, client, model_name):  
self.client = client  
self.model_name = model_name

    def process_pr_file(self, file, repo, pr):  
        comments = []  
        analyzed = False  
  
        if file.filename.endswith('.py'):  
            analyzed = True  
            content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode()  
              
            try:  
                tree = ast.parse(content)  
                for node in ast.walk(tree):  
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)):  
                        if not ast.get_docstring(node):  
                            comments.append({  
                                "path": file.filename,  
                                "body": f"⚠️ Missing docstring for {node.name}",  
                                "line": node.lineno  
                            })  
            except SyntaxError:  
                pass  
                  
        return comments, analyzed  
```

### 6. Testing Your Check

1. Add your check file to `.github/scripts/checks/`
2. Update `pr_review_checks.py` to import your check
3. Create a test PR in your repository
4. Add the "run-tests" label to trigger the review
5. Verify your check's output in the PR comments

### Best Practices

- Keep checks focused on specific aspects of code quality
- Provide clear, actionable feedback in comments
- Handle errors gracefully and provide meaningful error messages
- Use markdown formatting in comments for better readability
- Consider performance when analyzing large files or repositories  

### Further Examples

More examples exist in the `gofannon` repository:
- (`The-AI-Alliance/gofannon/.github/scripts/pr_review_checks.py`)[https://github.com/The-AI-Alliance/gofannon/blob/main/.github/scripts/pr_review_checks.py]
- (`The-AI-Alliance/gofannon/.github/scripts/checks/general_review.py`)[https://github.com/The-AI-Alliance/gofannon/blob/main/.github/scripts/checks/general_review.py]
- (`The-AI-Alliance/gofannon/.github/scripts/checks/schema_validation.py`)[https://github.com/The-AI-Alliance/gofannon/blob/main/.github/scripts/checks/schema_validation.py]
