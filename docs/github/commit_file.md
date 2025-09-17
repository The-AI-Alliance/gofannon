# CommitFile

The `CommitFile` API allows you to commit a file to a GitHub repository.

## Parameters

* `owner`: The owner of the repository, e.g. 'The-AI-Alliance'
* `repo`: The name of the repository, e.g. 'gofannon'
* `file_path`: The path of the file in the repository, e.g. example.txt
* `file_content`: The contents of the file as a string
* `commit_message`: The commit message, e.g. 'Added example.txt'
* `branch`: The branch to commit to, e.g. 'feature-branch'
* `default_branch`: The base branch to create the new branch from if it doesn't exist (default: 'main')

## Example Usage

```python  
commit_file = CommitFile(api_key="your_api_key_here")  
result = commit_file.fn("https://github.com/The-AI-Alliance/gofannon", "example.txt", "Hello World!", "Added example.txt")  
print(result)  
```

This will commit a new file example.txt to the gofannon repository with the contents "Hello World!" and the commit message "Added example.txt".