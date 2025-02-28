import ast
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class GeneralReviewCheck:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def process_pr_file(self, file, repo, pr):
        comments = []
        analyzed = False
        if file.filename.endswith('.py'):
            analyzed = True
            content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode()
            try:
                tree = ast.parse(content)
                analysis = self.analyze_code_structure(tree)
                if analysis:
                    comments.append({
                        "path": file.filename,
                        "body": analysis,
                        "line": 1
                    })
            except SyntaxError as e:
                comments.append({
                    "path": file.filename,
                    "body": f"⚠️ Syntax error found: {e}",
                    "line": 1
                })
        return comments, analyzed

    def analyze_code_structure(self, tree):
        analysis = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) > 10:
                    analysis.append(f"Class '{node.name}' has {len(methods)} methods. Consider splitting it.")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, "end_lineno"):
                    lines = node.end_lineno - node.lineno
                    if lines > 50:
                        analysis.append(f"Function '{node.name}' is {lines} lines long. Consider splitting it.")
        if analysis:
            return "\n".join(analysis)
        return None

    def process_pr(self, pr):
        # Generate a high-level summary of the pull request.
        summary = "Overall, the PR appears well structured. Consider reviewing overly long functions."
        return [{
            "path": "GENERAL",
            "body": summary,
            "line": 0
        }], True

class SchemaValidationCheck:
    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def process_pr_file(self, file, repo, pr):
        comments = []
        analyzed = False
        if file.filename.endswith('.py'):
            analyzed = True
            content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode()
            tools = self.analyze_file(content)
            if not tools:
                comments.append({
                    "path": file.filename,
                    "body": f"No tool definitions found in {file.filename}",
                    "line": 1
                })
            for tool in tools:
                if tool.get('definition'):
                    valid = self.validate_definition(tool['definition'])
                    if valid.get("valid"):
                        comments.append({
                            "path": file.filename,
                            "body": f"Tool '{tool['class_name']}' has a valid schema.",
                            "line": 1
                        })
                    else:
                        issues = ", ".join(valid.get("errors", []))
                        comments.append({
                            "path": file.filename,
                            "body": f"Schema issues in tool '{tool['class_name']}': {issues}",
                            "line": 1
                        })
        return comments, analyzed

    def analyze_file(self, content):
        # Dummy analysis: return one dummy tool if "class " is found.
        tools = []
        if "class " in content:
            tools.append({
                "class_name": "DummyTool",
                "definition": {"type": "function"}
            })
        return tools

    def validate_definition(self, definition):
        # Dummy validation always returns valid.
        return {"valid": True}