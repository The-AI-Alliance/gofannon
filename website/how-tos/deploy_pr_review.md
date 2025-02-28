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