import os
import json
import logging
import importlib.util
from github import Github
from openai import OpenAI
from gofannon.config import FunctionRegistry
from gofannon.base import BaseTool

logger = logging.getLogger(__name__)

def load_review_checks():
    """
    Dynamically load the review checks module from a configurable file.
    The path is specified via the environment variable PR_REVIEW_CHECKS_PATH.
    If not defined, it defaults to ".github/scripts/pr_review_checks.py".
    Returns a list of check classes (having names ending with 'Check').
    """
    checks_path = os.getenv("PR_REVIEW_CHECKS_PATH", ".github/scripts/pr_review_checks.py")
    spec = importlib.util.spec_from_file_location("pr_review_checks", checks_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Collect all classes in the module with names ending in 'Check'
    checks = [cls for name, cls in module.__dict__.items() if name.endswith("Check") and isinstance(cls, type)]
    return checks

@FunctionRegistry.register
class PRReviewTool(BaseTool):
    def __init__(self, name="pr_review_tool"):
        super().__init__()
        self.name = name
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model_name = os.getenv("OPENAI_MODEL_NAME")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Perform an automated pull request review using gofannon tools. "
                               "It aggregates configurable checks (e.g. code quality and schema validation).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pr_number": {
                            "type": "integer",
                            "description": "The pull request number."
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "The repository name in the format owner/repo."
                        }
                    },
                    "required": ["pr_number", "repo_name"]
                }
            }
        }

    def fn(self, pr_number, repo_name):
        # Connect to GitHub and get pull request details.
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        all_comments = []
        check_results = {}

        # Load review check classes dynamically.
        check_classes = load_review_checks()
        checks = [check_class(self.client, self.model_name) for check_class in check_classes]

        for check in checks:
            check_name = check.__class__.__name__
            check_results[check_name] = []
            if hasattr(check, 'process_pr_file'):
                for file in pr.get_files():
                    file_comments, analyzed = check.process_pr_file(file, repo, pr)
                    if analyzed:
                        for comment in file_comments:
                            comment['check_name'] = check_name
                            all_comments.append(comment)
                            check_results[check_name].append(comment)
            if hasattr(check, 'process_pr'):
                pr_comments, _ = check.process_pr(pr)
                for comment in pr_comments:
                    comment['check_name'] = check_name
                    all_comments.append(comment)
                    check_results[check_name].append(comment)

        summary = "## 🤖 Automated PR Review Summary 🤖\n\n"
        for check_name, comments in check_results.items():
            summary += f"### 🤖 {check_name} 🤖\n\n"
            for comment in comments:
                body = comment.get("body", "")
                file_path = comment.get("path", "")
                if file_path and file_path != "GENERAL":
                    body = f"**File:** `{file_path}`\n{body}"
                summary += f"{body}\n\n"
        if not all_comments:
            summary += "\nNo issues found. Code looks good!"

        return summary