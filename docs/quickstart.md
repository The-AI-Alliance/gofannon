# Quickstart Guide for `gofannon`

`gofannon` is a Python library designed to simplify the creation and management 
of tools for LLM (Large Language Model) and agents. This guide will walk you 
through the basics of installing and using `gofannon`.

## Installation

First, install the library using pip:

```bash  
pip install gofannon  
```

gofannon is an ambitious upstart, things are happening fast. We have a git 
action that deploys to PyPi every Monday morning, so `pip install gofannon`
will get you pretty close to the tip of the spear. But if you absolutely _must_
have the latest and greatest, this will work too:

```bash
git+https://github.com/The-AI-Alliance/gofannon.git@main
```

## Tool Calling with LLMs

**NOTE:** This is a sidebar about what tool calling is and why its important for
agents, the reader can skip this section without loss of continuity.

Modern LLMs support structured tool calling capabilities that allow them to interact with external functions. Here's what you need to know:

### How LLMs Call Tools

1. **Tool Description**: The LLM receives JSON schema describing available tools
    - Includes function names, parameter descriptions, and purposes
2. **Parallel Tool Calling**: Some models can call multiple tools simultaneously
3. **Structured Responses**: Tools return structured data the LLM can reason about

### Example Tool Call Flow

```python
# Example of what an LLM might generate when deciding to use a tool
tool_call = {  
"name": "search_web",  
"arguments": {  
"query": "current weather in London"  
}  
}  
```

### Key Benefits

- **Extended Capabilities**: Access real-time data, calculations, or specialized operations
- **Deterministic Actions**: Tools provide reliable outputs unlike pure LLM generation
- **Controlled Environment**: Tools can include safety checks and validation

### Expanding the Power of Agents

LLM agents can extend their capabilities by calling external tools. Here's how it works:

1. **Tool Definition**: Tools are functions with clear descriptions of their purpose, inputs, and outputs
2. **Agent Decision**: The LLM determines when a tool would help complete a task
3. **Tool Execution**: The agent formats the proper inputs and calls the tool
4. **Result Processing**: The tool's output is returned to the agent for further reasoning


## Creating Your First Tool

A `gofannon` tool is a class that extends `gofannon.base.BaseTool` and has at a
minimum a `definition` method (marked with the `@property` decorator) which 
explains the interface to the function, and a `fn` method that contains the code that will be called. 


`gofannon` provides a decorator `@FunctionRegistry.register` to register the tool
in the function registry. Here's a simple example:

```python  
from gofannon.base import BaseTool
from gofannon.config import FunctionRegistry
import logging
import os

logger = logging.getLogger(__name__)

@FunctionRegistry.register
class ReadFile(BaseTool):
    def __init__(self, name="read_file"):
        super().__init__()
        self.name = name

    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Read the contents of a specified file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to be read."
                        }
                    },
                    "required": ["file_path"]
                }
            }
        }

    def fn(self, file_path):
        logger.debug(f"Reading file: {file_path}")
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"The file '{file_path}' does not exist.")

            with open(file_path, 'r') as file:
                content = file.read()

            return content
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return f"Error reading file: {e}"
# The tool is now registered and ready for use by an LLM agent!
```

## Loading Tools into an Agent


### Installing `gofannon` for use with your specific framework.

```bash
pip install gofannon[smolagents]
```

### Example Notebook

This example riffs om the `smolagents` quickstart by using OpenAI instead of a 
locally hosted huggingface model, and uses the tool `gofannon.google_search.google_search.GoogleSearch`
instead of `smolagent`'s `DuckDuckGoSearchTool`.

https://github.com/The-AI-Alliance/gofannon/blob/main/examples/smolagents%2Bgofannon_quickstart.ipynb

### Why frameworks are installed as extras

To keep the package lean and avoid unnecessary dependency conflicts, each supported framework—LangChain, smolagents, and AWS tools—is included as an optional install.

This modular approach lets you:

* Only install what you need
* Minimize dependency bloat
* Avoid version bumps from frameworks you’re not using

Install extras like so:
```bash 
pip install mypackage[langchain]
pip install mypackage[smolagents]
pip install mypackage[aws]
```

This setup helps ensure smoother upgrades and cleaner environments when working 
across multiple agentic systems.

### Modular by design 

Each supported framework—**LangChain**, **smolagents**, and **AWS tools**—is 
included as an *optional extra* to keep the core install minimal and reduce 
dependency conflicts. But more importantly, this modular design supports a 
powerful interoperability pattern.

The tools in this library are designed to be:

- **Composable across frameworks** – Build a tool once, then use it in LangChain, smolagents, or AWS agent workflows.
- **Reusable in multiple contexts** – Tools written in one framework can be imported and used in another.
- **Framework-agnostic at the core** – Letting you prototype fast and scale when ready.

#### Why this matters

Different frameworks serve different needs:

- **Framework 1** might be *super easy to get started with*, perfect for rapid prototyping or notebooks—but struggles to scale to production.
- **Framework 2** might be *built for production*—robust, fast, scalable—but is harder to experiment with or onboard new ideas.

With this package, you can prototype tools in the fast-and-loose environment of Framework 1, and—when ready—plug them directly into Framework 2 with minimal changes. This bridges the gap between **experimentation** and **production**, enabling faster iteration and long-term maintainability.

> A notebook demonstrating cross-framework tool composition is coming soon.

### Currently Supported

**Currently Supported:** `smolagents`, LangChain, AWS Bedrock
**Currently Being Developed:** [Up To Date List](https://github.com/The-AI-Alliance/gofannon/issues?q=is%3Aissue%20state%3Aopen%20label%3Aframework%20assignee:*)
**In The Roadmap:** [Up To Date List](https://github.com/The-AI-Alliance/gofannon/issues?q=is%3Aissue%20state%3Aopen%20label%3Aframework%20no%3Aassignee)

Don't see your desired Framework? [Open A Request](https://github.com/The-AI-Alliance/gofannon/issues/new?template=agentic_framework.md)

## Open for Contributions

One of the primary goals of the `gofannon` project is to enable and support new 
contributors making their first contributions in open source AI. 

We have documentation on [contributing your first tool](https://the-ai-alliance.github.io/gofannon/developers/contribute_tool.html),
[contributing your first framework (advanced)](https://the-ai-alliance.github.io/gofannon/developers/contribute_agentic_framework.html), 
and a fun [leaderboard](https://the-ai-alliance.github.io/gofannon/leaderboard.html)
to gamify the contribution process.

## Next Steps

- Talk to us [(discord, github discussions, and other links here)](https://the-ai-alliance.github.io/gofannon/community/)
- Check out our [examples](https://github.com/The-AI-Alliance/gofannon/tree/main/examples) for inspiration
- [Introduce yourself to the Community](https://github.com/The-AI-Alliance/gofannon/discussions/categories/introductions)

Happy building! 🚀  