import os
import ast
import json
from github import Github
from openai import OpenAI

class ToolDefinitionVisitor(ast.NodeVisitor):
    def __init__(self):
        self.tools = []
        self.current_class = None
        self.definition = None

    def visit_ClassDef(self, node):
        self.current_class = node.name
        self.definition = None
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        if node.name == 'definition' and isinstance(node.decorator_list[0], ast.Name) and node.decorator_list[0].id == 'property':
            self.definition = node
        self.generic_visit(node)

    def get_definition_return(self):
        for node in ast.walk(self.definition):
            if isinstance(node, ast.Return):
                return ast.literal_eval(node.value)
        return None

def analyze_file(content):
    tree = ast.parse(content)
    visitor = ToolDefinitionVisitor()
    visitor.visit(tree)

    tools = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            base_names = [base.id for base in node.bases if isinstance(base, ast.Name)]
            if 'BaseTool' in base_names:
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and decorator.func.attr == 'register':
                        tool_info = {
                            'class_name': node.name,
                            'definition': None
                        }
                        for sub_node in node.body:
                            if isinstance(sub_node, ast.FunctionDef) and sub_node.name == 'definition':
                                visitor.definition = sub_node
                                tool_info['definition'] = visitor.get_definition_return()
                        tools.append(tool_info)
    return tools

def validate_definition(definition, client, model_name):
    schema_check_prompt = f"""Analyze this OpenAI function definition schema. Return JSON with:  
- "valid": boolean  
- "errors": list of strings describing schema violations  
- "missing_fields": list of required missing fields  
  
Schema to validate: {json.dumps(definition, indent=2)}  
  
Follow these validation rules from OpenAI's documentation:  
1. Must have 'type' set to 'function'  
2. Must have 'function' object containing:  
   a. 'name' (string, required)  
   b. 'description' (string, required)  
   c. 'parameters' (object, required) following JSON Schema format  
3. Parameters must define 'type' for each property  
4. No markdown formatting in descriptions"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[{
            "role": "system",
            "content": "You are a schema validation expert. Analyze OpenAI function definitions."
        }, {
            "role": "user",
            "content": schema_check_prompt
        }],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)

def main():
    pr_number = int(os.environ['GITHUB_EVENT_PULL_REQUEST_NUMBER'])
    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo(os.environ['GITHUB_REPOSITORY'])
    pr = repo.get_pull(pr_number)

    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        base_url=os.environ['OPENAI_BASE_URL']
    )
    model_name = os.environ['OPENAI_MODEL_NAME']

    comments = []

    for file in pr.get_files():
        if file.filename.startswith('gofannon/') and file.filename.endswith('.py'):
            content = repo.get_contents(file.filename, ref=pr.head.sha).decoded_content.decode()
            tools = analyze_file(content)

            for tool in tools:
                if tool['definition']:
                    validation = validate_definition(tool['definition'], client, model_name)

                    if not validation.get('valid', False):
                        message = f"⚠️ **Schema Issue in {tool['class_name']}**\n"
                        if validation.get('missing_fields'):
                            missing_fields = ', '.join(validation['missing_fields'])
                            message += f"Missing required fields: {missing_fields}\n"
                            if validation.get('errors'):
                                message += "Validation errors:\n- " + "\n- ".join(validation['errors'])

                        comments.append({
                            "path": file.filename,
                            "body": message,
                            "line": 1
                        })

    if comments:
        pr.create_issue_comment(f"🔍 Found {len(comments)} potential schema issues:")
        for comment in comments:
            pr.create_review_comment(body=comment['body'], commit_id=pr.head.sha, path=comment['path'], line=comment['line'])

if __name__ == "__main__":
    main()