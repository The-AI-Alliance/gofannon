
import requests
import json

from..base import BaseTool
from ..config import FunctionRegistry
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class CommitFile(BaseTool):
    def __init__(self,
                 api_key=None,
                 name="commit_file",):
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
                "description": "Commit a file to a GitHub repository on a specified branch. If the branch does not exist, it will be created from the base branch (default: main). If the file already exists, it will be updated.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "The owner of the repository, e.g. 'The-AI-Alliance'"
                        },
                        "repo": {
                            "type": "string",
                            "description": "The name of the repository, e.g. 'gofannon'"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path of the file in the repository (e.g., 'folder/file.txt')"
                        },
                        "file_content": {
                            "type": "string",
                            "description": "The content of the file as a string"
                        },
                        "commit_message": {
                            "type": "string",
                            "description": "The commit message, e.g. 'Added example.txt'"
                        },
                        "branch": {
                            "type": "string",
                            "description": "The branch to commit to, e.g. 'feature-branch'"
                        },
                        "base_branch": {
                            "type": "string",
                            "description": "The base branch to create the new branch from if it doesn't exist (default: 'main')",
                            "default": "main"
                        }
                    },
                    "required": ["owner", "repo", "file_path", "file_content", "commit_message", "branch"],
                    "additionalProperties": False
                }
            }
        }

    def fn(self, 
            owner: str,
            repo: str,
            file_path: str,
            file_content: str,
            commit_message: str,
            branch: str,
            base_branch: str = "main") -> str:
        logger.debug(f"Committing file {file_path} to {owner}/{repo} on branch {branch}")
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"token {self.api_key}"}

    # --- Step 1: Ensure the branch exists ---
    branch_url = f"{api_url}/git/ref/heads/{branch}"
    branch_resp = requests.get(branch_url, headers=headers)

    if branch_resp.status_code == 404:
        # Branch doesn't exist -> create it
        base_branch_url = f"{api_url}/git/ref/heads/{base_branch}"
        base_resp = requests.get(base_branch_url, headers=headers)
        if base_resp.status_code != 200:
            raise Exception(f"Base branch '{base_branch}' not found: {base_resp.text}")
        
        base_sha = base_resp.json()["object"]["sha"]

        create_branch_payload = {
            "ref": f"refs/heads/{branch}",
            "sha": base_sha
        }
        create_resp = requests.post(f"{api_url}/git/refs", headers=headers, json=create_branch_payload)
        if create_resp.status_code != 201:
            raise Exception(f"Error creating branch '{branch}': {create_resp.text}")
        print(f"Branch '{branch}' created from '{base_branch}'.")
    elif branch_resp.status_code != 200:
        raise Exception(f"Error checking branch: {branch_resp.status_code} {branch_resp.text}")

    # --- Step 2: Check if the file exists on that branch ---
    file_url = f"{api_url}/contents/{file_path}"
    response = requests.get(file_url, headers=headers, params={"ref": branch})

    if response.status_code == 200:
        sha = response.json()["sha"]
    elif response.status_code == 404:
        sha = None
    else:
        raise Exception(f"Error checking file: {response.status_code} {response.text}")

    # --- Step 3: Prepare payload ---
    payload = {
        "message": commit_message,
        "branch": branch,
        "content": base64.b64encode(file_content.encode()).decode()
    }
    if sha:
        payload["sha"] = sha

    # --- Step 4: Commit the file ---
    put_response = requests.put(file_url, headers=headers, json=payload)
    
    if put_response.status_code in [200, 201]:
        print("File committed successfully!")
        return put_response.json()
    else:
        raise Exception(f"Error committing file: {put_response.status_code} {put_response.text}")
