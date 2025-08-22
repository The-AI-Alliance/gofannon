import requests
import base64
from ..base import BaseTool
from ..config import FunctionRegistry
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class ReadFile(BaseTool):
    """
    Reads the content of a specific file from a GitHub repository.
    This tool takes a repository URL, a file path, and an optional branch name,
    and returns the content of the file as a string.
    """
    def __init__(self, api_key=None, name="read_file"):
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
                "description": "Fetches and returns the content of a specific file from a GitHub repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_url": {
                            "type": "string",
                            "description": "The URL of the repository, e.g. https://github.com/The-AI-Alliance/gofannon"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file within the repository, e.g. 'README.md'."
                        },
                        "branch": {
                            "type": "string",
                            "description": "Optional. The branch, tag, or commit SHA to get the file from. Defaults to the repository's default branch."
                        }
                    },
                    "required": ["repo_url", "file_path"]
                }
            }
        }

    def fn(self, repo_url, file_path, branch=None):
        logger.debug(f"Reading file {file_path} from repo {repo_url}")
        repo_parts = repo_url.rstrip('/').split('/')
        owner = repo_parts[-2]
        repo_name = repo_parts[-1]

        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}"
        headers = {
            'Authorization': f'token {self.api_key}',
            'Accept': 'application/vnd.github.v3+json'
        }
        params = {}
        if branch:
            params['ref'] = branch

        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()

        file_data = response.json()
        
        if 'content' not in file_data or file_data.get('encoding') != 'base64':
             raise ValueError(f"Could not retrieve file content. The path might be a directory or the encoding is not base64.")

        content_base64 = file_data['content']
        decoded_content = base64.b64decode(content_base64).decode('utf-8')
        
        return decoded_content