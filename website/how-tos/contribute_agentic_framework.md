---  
layout: default  
title: Contributing An Agentic Framework
---  

# Contributing a New Framework Integration

This guide explains how to contribute a new framework integration for Gofannon. Framework integrations are written as mixin classes in the `gofannon/base/` directory. They enable conversion between Gofannon’s native tool interface and a third‐party framework’s tool interface.

> **Note:** Before you start coding, please create an issue proposing your framework integration. Explain which framework you want to support, what capabilities you plan to implement (import, export, or both), and any potential challenges. This initial discussion will help ensure that your contribution aligns with the project’s roadmap.
  
---  

## Step 1: Propose Your Framework in an Issue

1. **Create a New Issue:**
    - Use the "[Framework Proposal]" template available in our GitHub issues.
    - Provide a clear description outlining:
        - The framework you intend to integrate.
        - What your integration will enable (e.g. importing tools from, exporting tools to, or both).
        - Any limitations or special considerations.
        - How it differs from existing mixins.

2. **Wait for Feedback:**
    - A maintainer or community member will review your proposal.
    - Incorporate any feedback before starting on your implementation.

---  

## Step 2: Create Your Mixin File

1. **File Location:**  
   Place your new file in the `gofannon/base/` directory. For example, if you are adding support for "YourFramework", create:

   ```bash  
   gofannon/base/your_framework.py  
   ```

   2. **File Structure and Required Methods:**  
      Your mixin class should implement at least the following two methods:
       - **import_from_yourframework:** Convert a tool from YourFramework’s interface to a Gofannon BaseTool.
       - **export_to_yourframework:** Convert a Gofannon BaseTool to YourFramework’s tool interface.

      Here is an example template:

      ```python  
      from gofannon.base import BaseTool

      class YourFrameworkMixin:  
        """  
        Mixin for integrating with YourFramework.

          Implement the following abstract methods:  
          - import_from_yourframework: Convert an external tool to a BaseTool-compatible instance.  
          - export_to_yourframework: Convert a BaseTool into a tool format compatible with YourFramework.  
          """  

          def import_from_yourframework(self, external_tool):  
              """  
              Import a tool from YourFramework into a BaseTool-compatible instance.  

              :param external_tool: An instance of a YourFramework tool.  
              :return: None (modify self accordingly).  
              """  
              # Example conversion logic:  
              self.name = getattr(external_tool, "name", "exported_yourframework_tool")  
              self.description = getattr(external_tool, "description", "No description provided.")  
              # Additional property mappings can go here.  
              def adapted_fn(*args, **kwargs):  
                  return external_tool.run(*args, **kwargs)  
              self.fn = adapted_fn  

          def export_to_yourframework(self):  
              """  
              Export the current BaseTool as a tool that is compatible with YourFramework.  

              :return: An instance of YourFramework's tool.  
              """  
              from yourframework_library import Tool as YourFrameworkTool  
              exported_tool = YourFrameworkTool()  
              exported_tool.name = self.name  
              exported_tool.description = self.definition.get("function", {}).get("description", "")  
              # Map any input/output schemas if applicable.  
              exported_tool.forward = self.fn  
              return exported_tool  
      ```

---  

## Step 3: Update Project Configuration

Framework integrations may require extra dependencies. To register your framework with Gofannon:

1. **Update `pyproject.toml` Extras:**
    - In the `[tool.poetry.extras]` section, add an entry for your framework. For example:

   ```toml  
   [tool.poetry.extras]  
   yourframework = ["yourframework-library>=1.0.0"]  
   ```

2. **Handling Multiple Constraints:**
    - If your framework has multiple version constraints, refer to the 
   [Poetry dependency specification](https://python-poetry.org/docs/dependency-specification/#multiple-constraints-project) 
   for guidance. *([Issue #197](https://github.com/The-AI-Alliance/gofannon/issues/197) may provide further improvements in the future.)*

---  

## Step 4: Write Tests

1. **Unit Tests:**
    - Create tests in the `tests/unit/` directory that verify your mixin correctly converts tools both ways. For example:

   ```python  
   def test_yourframework_import_export():  
       from gofannon.base.your_framework import YourFrameworkMixin

       # Dummy external tool with minimal attributes.  
       class DummyExternalTool:  
           name = "dummy_tool"  
           description = "A dummy tool for testing."  
           def run(self, *args, **kwargs):  
               return "result"  

       mixin = YourFrameworkMixin()  
       dummy = DummyExternalTool()  
       mixin.import_from_yourframework(dummy)  
         
       # Verify properties are correctly assigned.  
       assert mixin.name == "dummy_tool"  
         
       # Export back to YourFramework format.  
       exported = mixin.export_to_yourframework()  
       assert exported.name == "dummy_tool"  
       assert exported.forward() == "result"  
   ```

    Better writeups for testing is coming soon too.

2. **Integration Tests:**
    - If applicable, add integration tests to verify that the conversion works seamlessly within a real workflow.

---  

## Step 5: Add Documentation and Examples

1. **Documentation:**
    - Create a new file (for example, `docs/cross-framework_yourframework.md`) to explain how to use your framework integration.
    - Include detailed examples that demonstrate both importing and exporting tools.
    - Document any limitations, special instructions, or caveats.
    - **NOTE:** It is acceptable to contribute documentation and examples as follow on PRs.

2. **Example Usage:**
    - Provide code examples in your documentation. For instance:

   ```python
   # Example of using the YourFramework mixin with an existing tool.
   from gofannon.basic_math.addition import Addition  
   from gofannon.base.your_framework import YourFrameworkMixin

   addition_tool = Addition()
   # Export the addition tool to YourFramework format.
   yourframework_tool = addition_tool.export_to_yourframework()  
   print(yourframework_tool.forward(2, 3))  # Expected output: 5  
   ```

---  

## Step 6: Submit Your Pull Request

1. **Prepare Your Pull Request:**
    - Ensure all tests pass and documentation is updated.
    - Describe your mixin integration in detail, including:
        - Which methods you implemented (import/export or both).
        - The rationale behind your design decisions.
        - Any limitations or framework-specific considerations.
        - Updates made to `pyproject.toml` for dependencies.

2. **Follow the Contribution Guidelines:**
    - Read through the [CONTRIBUTING guidelines](https://github.com/The-AI-Alliance/gofannon/blob/main/CONTRIBUTING.md) for further details.
    - Include a reference to your initial framework proposal issue so reviewers can see the design discussion.

3. **Submit Your PR:**
    - Once the PR is submitted, be prepared to respond to any questions or feedback from maintainers.

---  

Happy contributing, and thank you for helping expand Gofannon’s cross-framework capabilities!  