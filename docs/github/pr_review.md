# PR Review Tool

This tool automates the pull request review process using gofannon’s internal checks.  
It loads review checks dynamically from a configurable file (default: .github/scripts/pr_review_checks.py).  
This makes it easy to substitute or rename checks for your repository.

```python
# Example usage in a Python script:
from gofannon.github.pr_review_tool import PRReviewTool

pr_review = PRReviewTool()  
summary = pr_review.fn(pr_number=123, repo_name="owner/repo")  
print(summary)  
```

## How It Works

The PR Review Tool does the following:
- Dynamically loads review check classes from a configurable file (via the PR_REVIEW_CHECKS_PATH environment variable).
- Runs each check on the files changed in the pull request.
- Aggregates any issues found (such as code quality problems or schema validation warnings) and produces a summary.

## Required Environment Variables

Ensure these variables are set in your CI/CD pipeline or local environment:
- GITHUB_TOKEN (with repo access)
- OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME
- PR_NUMBER (the pull request number)
- REPO_NAME (formatted as owner/repo)
- Optionally, PR_REVIEW_CHECKS_PATH (if you want to specify an alternate checks file)

## Integration in CI

You can invoke the PR Review Tool from your CI pipeline (see the workflow file example below). The tool outputs a summary review that is then posted as a comment on the pull request.  

## More Documentation
For more information on deploying in your repo, see the website [deploy pr review page](https://the-ai-alliance.github.io/gofannon/how-tos/deploy_pr_review.html).
