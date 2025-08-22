import requests
import json
from ..base import BaseTool
from ..config import FunctionRegistry
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class ListRepoFiles(BaseTool):
    """
    Recursively list all files in a GitHub repository.
    This tool fetches the file tree for a given branch and returns a list
    of all file paths.
    """
    def __init__(self, api_key=None, name="list_repo_files"):
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
                "description": "Recursively list all file paths in a given repository and branch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_url": {
                            "type": "string",
                            "description": "The URL of the repository, e.g. https://github.com/The-AI-Alliance/gofannon"
                        },
                        "branch": {
                            "type": "string",
                            "description": "Optional. The branch to list files from. Defaults to the repository's default branch."
                        }
                    },
                    "required": ["repo_url"]
                }
            }
        }

    def fn(self, repo_url, branch=None):
        logger.debug(f"Listing files for repo {repo_url}")
        repo_parts = repo_url.rstrip('/').split('/')
        owner = repo_parts[-2]
        repo_name = repo_parts[-1]

        headers = {
            'Authorization': f'token {self.api_key}',
            'Accept': 'application/vnd.github.v3+json'
        }

        # 1. Get the default branch if one isn't specified
        if not branch:
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            repo_response = requests.get(repo_api_url, headers=headers)
            repo_response.raise_for_status()
            branch = repo_response.json()['default_branch']
            logger.debug(f"No branch specified, using default branch: {branch}")

        # 2. Get the latest commit SHA for the branch
        branch_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/branches/{branch}"
        branch_response = requests.get(branch_api_url, headers=headers)
        branch_response.raise_for_status()
        tree_sha = branch_response.json()['commit']['commit']['tree']['sha']

        # 3. Get the file tree recursively
        tree_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{tree_sha}?recursive=1"
        tree_response = requests.get(tree_api_url, headers=headers)
        tree_response.raise_for_status()
        tree_data = tree_response.json()

        if tree_data.get('truncated'):
            logger.warning(f"File list for {repo_url} on branch {branch} is truncated because it exceeds the maximum number of items.")
        
        # 4. Filter for files (blobs) and return their paths
        file_paths = [item['path'] for item in tree_data['tree'] if item['type'] == 'blob']
        
        return json.dumps(file_paths, indent=2)