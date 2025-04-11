from requests import post
from json import dumps
from..base import BaseTool
from ..config import FunctionRegistry
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class CreateIssue(BaseTool):
    def __init__(self,
                 api_key=None,
                 name="create_issue"):
        super().__init__()
        self.api_key = api_key
        self.name = name
        self.API_SERVICE = 'github'

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Create an issue in a GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_url": {
                            "type": "string",
                            "description": "The URL of the repository, e.g. https://github.com/The-AI-Alliance//gofannon"
                        },
                        "title": {
                            "type": "string",
                            "description": "The title of the issue"
                        },
                        "body": {
                            "type": "string",
                            "description": "The body of the issue"
                        },
                        "labels": {
                            "type": "string",
                            "description": "A comma separated list of labels to apply to the issue"
                        }
                    },
                    "required": ["repo_url", "title", "body"]
                }
            }
        }

    def fn(self, repo_url, title, body, labels=None):
        logger.debug(f"Crating issue'{title}' in repo {repo_url}")
        # Extracting the owner and repo name from the URL
        repo_parts = repo_url.rstrip('/').split('/')
        owner = repo_parts[-2]
        repo = repo_parts[-1]

        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        headers = {
            'Authorization': f'token {self.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            "title": title,
            "body": body
        }

        if labels:
            payload["labels"] = labels.split(',')

        response = post(api_url, headers=headers, json=payload)
        response.raise_for_status()

        return dumps(response.json())