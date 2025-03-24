import os

import requests
import json
import git
from pathlib import Path

from..base import BaseTool
from ..config import FunctionRegistry
import logging

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class CommitFiles(BaseTool):
    def __init__(self,
                 api_key=None,
                 name="commit_files",
                 git_user_name=None,
                 git_user_email=None):
        super().__init__()
        self.api_key = api_key
        self.name = name
        self.git_user_name = git_user_name
        self.git_user_email = git_user_email
        self.API_SERVICE = 'github'


    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Commit multiple files to a GitHub repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo_url": {
                            "type": "string",
                            "description": "The URL of the repository, e.g. https://github.com/The-AI-Alliance//gofannon"
                        },
                        "branch": {
                            "type": "string",
                            "description": "The branch to commit to, e.g. 'main' or 'new-branch'"
                        },
                        "commit_msg": {
                            "type": "string",
                            "description": "The commit message, e.g. 'Added new files'"
                        },
                        "files_json": {
                            "type": "string",
                            "description": "A JSON string containing a list of files to commit, e.g. '{\"files\": [{\"path\": \"file1.py\", \"code\": \"import os\"}, {\"path\": \"file2.py\", \"code\": \"import sys\"}]}'"
                        },
                        "base_branch": {
                            "type": "string",
                            "description": "Optional. The base branch to create the new branch from. Default: 'main'"
                        }
                    },
                    "required": ["repo_url", "branch", "commit_msg", "files_json"]
                }
            }
        }

    def fn(self, repo_url, branch, commit_msg, files_json, base_branch='main'):
        logger.debug(f"Committing files to {repo_url}")
        # Extracting the owner and repo name from the URL
        repo_parts = repo_url.rstrip('/').split('/')
        owner = repo_parts[-2]
        repo = repo_parts[-1]

        if repo_url.startswith("https://"):
            repo_url = repo_url.replace("https://", "https://"+ self.api_key+"@")
        elif repo_url.startswith("github.com"):
            repo_url = f"https://{self.api_key}@{repo_url}"
        # Clone the repository
        repo_dir = f"/tmp/{repo}"


        if os.path.exists(repo_dir):
            repo = git.Repo(repo_dir)
        else:
            repo = git.Repo.clone_from(repo_url, repo_dir)
        repo.config_writer().set_value("user", "name", self.git_user_name).release()
        repo.config_writer().set_value("user", "email", self.git_user_email).release()

        # Check if the branch exists
        if branch in repo.heads:
            # If it does, checkout the branch and pull the latest changes
            repo.git.checkout(branch)
            # Explicit pull from origin/branch to avoid tracking dependency
            repo.git.pull('origin', branch)
        else:
            # If it does not exist, checkout the base branch and create a new branch
            try:
                repo.git.checkout(base_branch)
            except git.exc.GitCommandError:
                # If the base branch does not exist, raise an error
                raise ValueError(f"Base branch '{base_branch}' does not exist.")
            repo.git.checkout('-b', branch)

        # Load the JSON string
        files = json.loads(files_json)['files']
        # Update or create the files
        for file in files:
            file_path = file['path']
            code = file['code']
            with open(f"{repo_dir}/{file_path}", 'w') as f:
                f.write(code)
            repo.index.add(Path(file_path))

        # Commit the files
        repo.index.commit(commit_msg)

        origin = repo.remotes.origin
        # Push with tracking (still recommended)
        repo.git.push('-u', 'origin', branch)
        return "Files committed and pushed successfully"
