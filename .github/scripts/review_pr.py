import os
import importlib.util
from github import Github
from openai import OpenAI

def load_checks():
    checks = []
    checks_dir = os.path.join(os.path.dirname(__file__), 'checks')

    for file in os.listdir(checks_dir):
        if file.endswith('.py') and file != '__init__.py':
            module_name = file[:-3]
            spec = importlib.util.spec_from_file_location(
                module_name,
                os.path.join(checks_dir, file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Add all classes that end with 'Check'
            for name, obj in module.__dict__.items():
                if name.endswith('Check') and isinstance(obj, type):
                    checks.append(obj)

    return checks

def main():
    pr_number = int(os.environ['PR_NUMBER'])
    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(os.environ['REPO_NAME'])
    pr = repo.get_pull(pr_number)

    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        base_url=os.environ['OPENAI_BASE_URL']
    )
    model_name = os.environ['OPENAI_MODEL_NAME']

    checks = [check(client, model_name) for check in load_checks()]
    all_comments = []
    analyzed_files = set()

    # Process file-specific checks
    for check in checks:
        if hasattr(check, 'process_pr_file'):
            for file in pr.get_files():
                file_comments, analyzed = check.process_pr_file(file, repo, pr)
                if analyzed:
                    analyzed_files.add(file.filename)
                all_comments.extend(file_comments)

                # Process PR-level checks
    for check in checks:
        if hasattr(check, 'process_pr'):
            pr_comments, analyzed = check.process_pr(pr)
            all_comments.extend(pr_comments)

    if all_comments:
        pr.create_issue_comment(f"🔍 Found {len(all_comments)} potential issues:")
        for comment in all_comments:
            # Get the commit object for the head of the PR
            commit = repo.get_commit(pr.head.sha)

            pr.create_review_comment(
                body=comment['body'],
                commit=commit,
                path=comment['path'],
                line=comment['line'] if comment['line'] > 0 else None
            )

    checks_list = "\n- ".join(["TODO: Implement Checks list"])
    files_list = "\n- ".join(sorted(analyzed_files))
    pr.create_issue_comment(
        f"✅ Automated review completed by {model_name}\n\n"
        f"Files analyzed:\n- {files_list}\n\n"
        f"Checks Performed:\n- {checks_list}"
    )

if __name__ == "__main__":
    main()