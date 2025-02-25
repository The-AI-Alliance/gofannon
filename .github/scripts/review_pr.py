import os
import importlib.util
from github import Github
from github.GithubObject import NotSet
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

    # Load all checks
    checks = [check(client, model_name) for check in load_checks()]

    all_comments = []
    analyzed_files = set()
    check_results = {}

    # Build a mapping of filename to diff hunk (patch)
    file_patches = {}
    for file in pr.get_files():
        # file.patch contains the diff snippet for that file
        file_patches[file.filename] = file.patch

        # Process each check for every file in the PR
    for check in checks:
        check_name = check.__class__.__name__
        check_results[check_name] = []

        # Process file-specific checks.
        if hasattr(check, 'process_pr_file'):
            for file in pr.get_files():
                file_comments, analyzed = check.process_pr_file(file, repo, pr)
                if analyzed:
                    analyzed_files.add(file.filename)
                    for comment in file_comments:
                        comment['check_name'] = check_name
                        all_comments.append(comment)
                        check_results[check_name].append(comment)

                        # Process PR-level checks.
        if hasattr(check, 'process_pr'):
            pr_comments, analyzed = check.process_pr(pr)
            for comment in pr_comments:
                comment['check_name'] = check_name
                all_comments.append(comment)
                check_results[check_name].append(comment)

                # Create a summary comment if there are any issues.
    if all_comments:
        summary = ["🔍 Found potential issues:"]
        for check_name, comments in check_results.items():
            if comments:
                summary.append(f"\n### {check_name.replace('Check', '')} ({len(comments)} issues)")
                for i, comment in enumerate(comments, 1):
                    local_comment = comment['body'].split('\n')[0]
                    summary.append(f"{i}. {local_comment}...")
        pr.create_issue_comment("\n".join(summary))

        # Post individual comments.
        # Use create_issue_comment for general comments
        # and create_review_comment for file-specific comments.
        for comment in all_comments:
            if comment['path'] == "GENERAL":
                pr.create_issue_comment(
                    f"**{comment['check_name'].replace('Check', '')}:**\n{comment['body']}"
                )
            else:
                commit = repo.get_commit(pr.head.sha)
                # NOTE: Although we build file_patches, we do not pass diff_hunk
                # because PyGithub's create_review_comment does not accept it.
                pr.create_review_comment(
                    body=f"**{comment['check_name'].replace('Check', '')}:**\n{comment['body']}",
                    commit=commit,
                    path=comment['path'],
                    line=comment['line'] if comment['line'] > 0 else NotSet,
                    side='RIGHT'
                )
    else:
        files_list = "\n- ".join(sorted(analyzed_files))
        pr.create_issue_comment(
            f"✅ Automated review completed by {model_name}\n\n"
            f"Files analyzed:\n- {files_list}\n\n"
            "No issues found. Everything looks good!"
        )

if __name__ == "__main__":
    main()