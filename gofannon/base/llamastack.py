# gofannon/base/llamastack.py

import inspect
import re
from textwrap import dedent
from typing import Callable, Any

# Type mapping from Gofannon definition to Python types (primarily for potential future use,
# as Llama Stack example doesn't heavily rely on type hints in the generated function)
GOFANNON_TO_PYTHON_TYPE_MAP = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
}

# Type mapping from Python types/common hints to Gofannon definition types
PYTHON_TO_GOFANNON_TYPE_MAP = {
    str: "string",
    float: "number",
    int: "integer",
    bool: "boolean",
    dict: "object",
    list: "array",
    Any: "string", # Default fallback
    type(None): "string" # Default fallback for untyped
}


class LlamaStackMixin:
    """
    Mixin for converting Gofannon tools to and from the Llama Stack custom tool format.

    Llama Stack expects custom tools as Python functions with specific docstrings.
    See: https://github.com/meta-llama/llama-stack/blob/main/docs/tools.md#adding-custom-tools
    """

    def _parse_llamastack_docstring(self, docstring: str) -> tuple[str, dict[str, str], list[str]]:
        """
        Parses a Llama Stack style docstring to extract description and parameters.

        Args:
            docstring: The docstring content.

        Returns:
            A tuple containing:
            - description (str): The main tool description.
            - params (dict): A dictionary mapping parameter names to their descriptions.
            - required (list): A list of required parameter names (inferred if not explicitly optional).
              NOTE: Llama Stack's doc example doesn't show optional syntax, so we assume all
              documented params are required unless function signature has defaults.
        """
        if not docstring:
            return "No description provided.", {}, []

        lines = docstring.strip().split('\n')
        description_lines = []
        params = {}
        param_section_started = False

        # Simple regex to find ':param <name>:' or ':param <name> (<type>):'
        param_regex = re.compile(r":param\s+([\w_]+)(?:\s*\([^)]+\))?:\s*(.*)")

        for line in lines:
            line = line.strip()
            if not line: # Skip empty lines between description and params
                if description_lines and not param_section_started:
                    param_section_started = True # Assume blank line separates desc from params
                continue

            match = param_regex.match(line)
            if match:
                param_section_started = True
                param_name = match.group(1)
                param_desc = match.group(2).strip()
                params[param_name] = param_desc
            elif not param_section_started:
                description_lines.append(line)

        description = " ".join(description_lines).strip()
        # Llama Stack example doesn't specify required/optional in docstring.
        # We'll infer from function signature later.
        # For now, return an empty required list based purely on docstring parsing.
        required = list(params.keys()) # Assume all documented params are required initially

        return description, params, required

    def import_from_llamastack(self, llamastack_tool_func: Callable):
        """
        Adapts a Llama Stack custom tool function to a Gofannon tool.

        Args:
            llamastack_tool_func: The Python function representing the Llama Stack tool.
        """
        if not callable(llamastack_tool_func):
            raise ValueError("Input must be a callable function.")

        self.name = llamastack_tool_func.__name__
        docstring = inspect.getdoc(llamastack_tool_func) or ""

        # Parse docstring for description and param descriptions
        description, param_descriptions, _ = self._parse_llamastack_docstring(docstring)
        self.description = description # Set top-level description

        # Use inspect.signature to get parameter names, types, and defaults
        try:
            sig = inspect.signature(llamastack_tool_func)
            parameters_properties = {}
            required_params = []

            for name, param in sig.parameters.items():
                param_type_hint = param.annotation
                gofannon_type = PYTHON_TO_GOFANNON_TYPE_MAP.get(param_type_hint, "string") # Default to string if unknown

                parameters_properties[name] = {
                    "type": gofannon_type,
                    "description": param_descriptions.get(name, f"Parameter '{name}'") # Use parsed desc or default
                }

                # If the parameter has no default value, it's required
                if param.default is inspect.Parameter.empty:
                    required_params.append(name)

            self.definition = {
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": parameters_properties,
                        "required": required_params,
                    }
                }
            }

        except Exception as e:
            # Fallback if signature inspection fails (e.g., built-in function)
            # Create a basic definition based only on name/docstring
            self.logger.warning(f"Could not inspect signature for {self.name}: {e}. Creating basic definition.")
            self.definition = {
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": { # Assume no parameters if signature fails
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }


            # The core function is the Llama Stack function itself
        self.fn = llamastack_tool_func

        self.logger.info(f"Imported Llama Stack tool: {self.name}")


    def export_to_llamastack(self) -> Callable:
        """
        Convert the Gofannon tool to a Llama Stack compatible function.

        Returns:
            A callable function with a Llama Stack-style docstring.
        """
        gofannon_def = self.definition.get("function", {})
        tool_name = gofannon_def.get("name", getattr(self, "name", "gofannon_exported_tool"))
        tool_description = gofannon_def.get("description", getattr(self, "description", "No description provided."))
        parameters = gofannon_def.get("parameters", {})
        param_properties = parameters.get("properties", {})
        required_params = parameters.get("required", [])

        # Construct the docstring
        docstring_lines = [tool_description, ""]
        param_lines = []
        arg_names = []

        for param_name, param_def in param_properties.items():
            param_desc = param_def.get("description", "")
            # Llama Stack example doesn't show type in docstring, just param name and description
            # param_type = param_def.get("type", "string") # Could potentially add :type if needed
            docstring_line = f":param {param_name}: {param_desc}"
            # NOTE: Llama Stack example doesn't explicitly mark required/optional in docstring
            # We could add (required) or (optional) if desired, but sticking to example format.
            # if param_name in required_params:
            #     docstring_line += " (required)"
            param_lines.append(docstring_line)
            arg_names.append(param_name)

        if param_lines:
            docstring_lines.extend(param_lines)
            docstring_lines.append("") # Add blank line after params if any

        # Add a basic return description (Gofannon definition doesn't store this explicitly)
        docstring_lines.append(":return: The result of executing the tool.")

        final_docstring = "\n".join(docstring_lines)

        # Create the wrapper function dynamically
        original_fn = self.fn
        args_string = ", ".join(arg_names)

        # We need to define the function in a scope where original_fn is accessible
        # Using exec can be risky, but is one way to dynamically create a function
        # with a specific signature and docstring. A safer alternative might involve
        # function factories or functools.wraps if the signature complexity allows.

        # Let's try a closure approach which is generally safer:
        def make_wrapper(original_func, doc, name, signature_args):
            # Construct the function signature string dynamically
            sig_str = f"({', '.join(signature_args)})"
            # Use eval to create the function with the correct signature
            # This is still somewhat risky, ensure signature_args are sanitized if needed.
            # Define the wrapper within this factory function's scope
            def wrapper(*args, **kwargs):
                # Map positional args to keywords if necessary, or rely on kwargs
                call_kwargs = {}
                if args:
                    for i, arg_val in enumerate(args):
                        if i < len(signature_args):
                            call_kwargs[signature_args[i]] = arg_val
                        else:
                            # Handle extra positional args if necessary, maybe raise error?
                            pass
                call_kwargs.update(kwargs)
                return original_func(**call_kwargs)

            wrapper.__doc__ = doc
            wrapper.__name__ = name
            # Try to mimic signature for inspection tools (might not be perfect)
            try:
                # Build parameter list for inspect.Signature
                params = [inspect.Parameter(arg, inspect.Parameter.POSITIONAL_OR_KEYWORD) for arg in signature_args]
                wrapper.__signature__ = inspect.Signature(parameters=params)
            except Exception as e:
                self.logger.warning(f"Could not set __signature__ for {name}: {e}")

            return wrapper

            # Generate the arguments list for the signature
        signature_args_list = list(param_properties.keys())
        exported_function = make_wrapper(original_fn, final_docstring, tool_name, signature_args_list)


        # Alternative using exec (use with caution):
        # func_code = f"""
        # def {tool_name}({args_string}):
        #     '''{final_docstring}'''
        #     # Prepare kwargs for the original function
        #     kwargs_for_original = {{}}
        # """
        # for arg_name in arg_names:
        #     func_code += f"    kwargs_for_original['{arg_name}'] = {arg_name}\n"
        #
        # func_code += f"""
        #     return original_fn(**kwargs_for_original)
        # """
        # local_scope = {'original_fn': original_fn}
        # exec(dedent(func_code), local_scope)
        # exported_function = local_scope[tool_name]

        self.logger.info(f"Exported Gofannon tool '{self.name}' to Llama Stack format as function '{tool_name}'")
        return exported_function
  