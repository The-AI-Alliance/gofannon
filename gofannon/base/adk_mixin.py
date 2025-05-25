# gofannon/base/adk_mixin.py

import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Type as TypingType
import functools # Add this import

# Try to import ADK components
try:
    from google.adk.tools import BaseTool as AdkBaseTool
    from google.adk.tools import FunctionTool as AdkFunctionTool
    from google.adk.tools.tool_context import ToolContext as AdkToolContext
    # _automatic_function_calling_util is not typically a public export,
    # but FunctionTool uses it. For export, we might need a different strategy
    # or rely on AdkFunctionTool to build its declaration.
    # from google.adk.tools._automatic_function_calling_util import (
    #     build_function_declaration as adk_build_function_declaration,
    # )
    from google.genai import types as adk_gemini_types
    import anyio # For running sync Gofannon fn in async ADK tool

    _HAS_ADK = True
except ImportError:
    _HAS_ADK = False
    # Define dummy types for type hinting if ADK is not present
    class AdkBaseTool: pass
    class AdkFunctionTool(AdkBaseTool): pass # type: ignore
    class AdkToolContext: pass # type: ignore
    class adk_gemini_types: # type: ignore
        class Type:
            STRING = "STRING"
            INTEGER = "INTEGER"
            NUMBER = "NUMBER"
            BOOLEAN = "BOOLEAN"
            ARRAY = "ARRAY"
            OBJECT = "OBJECT"
            TYPE_UNSPECIFIED = "TYPE_UNSPECIFIED"
        class Schema: # type: ignore
            def __init__(self, **kwargs):
                self.type = kwargs.get('type', adk_gemini_types.Type.OBJECT)
                self.description = kwargs.get('description')
                self.properties = kwargs.get('properties', {})
                self.items = kwargs.get('items')
                self.required = kwargs.get('required', [])
                self.enum = kwargs.get('enum')
                self.nullable = kwargs.get('nullable')

        class FunctionDeclaration: # type: ignore
            def __init__(self, name, description, parameters):
                self.name = name
                self.description = description
                self.parameters = parameters


                # Helper for ADK Schema to Gofannon JSON Schema
ADK_GEMINI_TYPE_TO_JSON_TYPE = {
    adk_gemini_types.Type.STRING: "string",
    adk_gemini_types.Type.INTEGER: "integer",
    adk_gemini_types.Type.NUMBER: "number",
    adk_gemini_types.Type.BOOLEAN: "boolean",
    adk_gemini_types.Type.ARRAY: "array",
    adk_gemini_types.Type.OBJECT: "object",
    adk_gemini_types.Type.TYPE_UNSPECIFIED: "object", # Default for unspecified
}

def _adk_schema_to_gofannon_json_schema(adk_schema: Optional[adk_gemini_types.Schema]) -> Dict[str, Any]:
    if not adk_schema:
        return {"type": "object", "properties": {}}

    json_schema: Dict[str, Any] = {}

    adk_type_enum = getattr(adk_schema, 'type', adk_gemini_types.Type.TYPE_UNSPECIFIED)
    json_type_str = ADK_GEMINI_TYPE_TO_JSON_TYPE.get(adk_type_enum, "object")

    if getattr(adk_schema, 'nullable', False):
        # Represent nullable as a list of types including "null" if original type is singular
        # or handle it based on how Gofannon expects nullable
        json_schema["type"] = [json_type_str, "null"] if json_type_str != "object" else json_type_str # Pydantic v1 style for Optional[T]
        if json_type_str == "object": # For objects, nullable flag is more common in JSON schema
            json_schema["nullable"] = True
            json_schema["type"] = "object" # Keep type as object if it was object
    else:
        json_schema["type"] = json_type_str

    description = getattr(adk_schema, 'description', None)
    if description:
        json_schema["description"] = description

    if adk_type_enum == adk_gemini_types.Type.OBJECT:
        properties = getattr(adk_schema, 'properties', None)
        if properties:
            json_schema["properties"] = {
                name: _adk_schema_to_gofannon_json_schema(prop_schema)
                for name, prop_schema in properties.items()
            }
        else:
            json_schema["properties"] = {} # Ensure properties exist for object type

    items = getattr(adk_schema, 'items', None)
    if adk_type_enum == adk_gemini_types.Type.ARRAY and items:
        json_schema["items"] = _adk_schema_to_gofannon_json_schema(items)

    required_list = getattr(adk_schema, 'required', None)
    if required_list:
        json_schema["required"] = list(required_list)

    enum_list = getattr(adk_schema, 'enum', None)
    if enum_list:
        json_schema["enum"] = list(enum_list)

        # Ensure "properties" field exists if type is "object"
    if json_schema.get("type") == "object" and "properties" not in json_schema:
        json_schema["properties"] = {}

    return json_schema

# Helper for Gofannon JSON Schema to ADK Schema
JSON_TYPE_TO_ADK_GEMINI_TYPE = {
    "string": adk_gemini_types.Type.STRING,
    "integer": adk_gemini_types.Type.INTEGER,
    "number": adk_gemini_types.Type.NUMBER,
    "boolean": adk_gemini_types.Type.BOOLEAN,
    "array": adk_gemini_types.Type.ARRAY,
    "object": adk_gemini_types.Type.OBJECT,
    "null": adk_gemini_types.Type.TYPE_UNSPECIFIED, # ADK has no 'null' type, unspecified is closest
}

def _gofannon_json_schema_to_adk_schema(json_schema: Dict[str, Any]) -> adk_gemini_types.Schema:
    if not json_schema: # Handles empty dict {} case
        return adk_gemini_types.Schema(type=adk_gemini_types.Type.OBJECT, properties={})

    adk_schema_kwargs: Dict[str, Any] = {}

    json_type_val = json_schema.get("type", "object")
    is_nullable = json_schema.get("nullable", False) # Check for explicit "nullable"

    actual_json_type_str = json_type_val
    if isinstance(json_type_val, list): # Handles type: ["string", "null"]
        if "null" in json_type_val:
            is_nullable = True
        actual_json_type_str = next((t for t in json_type_val if t != "null"), "object")

    adk_type_enum = JSON_TYPE_TO_ADK_GEMINI_TYPE.get(str(actual_json_type_str).lower(), adk_gemini_types.Type.OBJECT)
    adk_schema_kwargs["type"] = adk_type_enum
    if is_nullable:
        adk_schema_kwargs["nullable"] = True

    if "description" in json_schema:
        adk_schema_kwargs["description"] = json_schema["description"]

    if adk_type_enum == adk_gemini_types.Type.OBJECT and "properties" in json_schema:
        adk_schema_kwargs["properties"] = {
            name: _gofannon_json_schema_to_adk_schema(prop_schema)
            for name, prop_schema in json_schema["properties"].items()
        }
    elif adk_type_enum == adk_gemini_types.Type.OBJECT: # Ensure properties for object type
        adk_schema_kwargs["properties"] = {}

    if adk_type_enum == adk_gemini_types.Type.ARRAY and "items" in json_schema:
        adk_schema_kwargs["items"] = _gofannon_json_schema_to_adk_schema(json_schema["items"])

    if "required" in json_schema:
        adk_schema_kwargs["required"] = list(json_schema["required"])

    if "enum" in json_schema:
        adk_schema_kwargs["enum"] = list(json_schema["enum"])

    return adk_gemini_types.Schema(**adk_schema_kwargs)


class AdkMixin:
    def import_from_adk(self, adk_tool: AdkBaseTool):
        """
        Adapts a google-adk-python tool to the Gofannon BaseTool structure.

        Args:
            adk_tool: An instance of a class derived from `google.adk.tools.BaseTool`.
        """
        if not _HAS_ADK:
            raise RuntimeError(
                "google-adk-python is not installed. Install with `pip install google-adk`"
            )
        if not isinstance(adk_tool, AdkBaseTool): # type: ignore
            raise TypeError("Input must be an instance of ADK BaseTool.")

        self.name = adk_tool.name # type: ignore
        self.description = adk_tool.description # type: ignore

        declaration = None
        # Ensure _get_declaration is callable and attempt to call it
        if hasattr(adk_tool, "_get_declaration") and callable(adk_tool._get_declaration): # type: ignore
            try:
                declaration = adk_tool._get_declaration() # type: ignore
            except Exception as e:
                self.logger.warning(f"Could not get declaration from ADK tool {self.name}: {e}. Assuming no parameters.") # type: ignore

        gofannon_params_schema: Dict[str, Any] = {"type": "object", "properties": {}}
        if declaration and hasattr(declaration, 'parameters') and declaration.parameters:
            gofannon_params_schema = _adk_schema_to_gofannon_json_schema(declaration.parameters)

        self.definition = { # type: ignore
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": gofannon_params_schema
            }
        }

        # Adapt the execution logic
        if isinstance(adk_tool, AdkFunctionTool) and hasattr(adk_tool, 'func'): # type: ignore
            target_callable = adk_tool.func # type: ignore
            self.fn = target_callable # type: ignore
        elif hasattr(adk_tool, 'run_async') and callable(adk_tool.run_async): # type: ignore
            self.logger.warning( # type: ignore
                f"Importing ADK tool {self.name} that is not a FunctionTool. "
                f"ADK ToolContext features will not be available or may require a dummy context. "
                f"Ensure this tool can operate correctly with args only."
            )
            # This wrapper will become self.fn. If self.fn is async, Gofannon's
            # execute_async can await it directly. Gofannon's sync execute
            # would need to handle running this async fn (e.g., using anyio.run).
            async def adk_run_async_wrapper(**kwargs):
                # This simplified call assumes the tool can function with a None ToolContext
                # or that its core logic doesn't strictly depend on it.
                return await adk_tool.run_async(args=kwargs, tool_context=None) # type: ignore
            self.fn = adk_run_async_wrapper # type: ignore
        else:
            self.logger.error( # type: ignore
                f"ADK tool {self.name} does not have a suitable execution method ('func' or 'run_async')."
            )
            def placeholder_fn(**kwargs):
                raise NotImplementedError(f"Execution for imported ADK tool {self.name} is not available.")
            self.fn = placeholder_fn # type: ignore


    def export_to_adk(self) -> AdkBaseTool:
        """
        Converts the Gofannon tool to a google-adk-python compatible tool.
        This typically creates a custom AdkBaseTool derivative that uses the
        Gofannon tool's definition and execution logic.

        Returns:
            An instance of a `google.adk.tools.BaseTool` derivative.
        """
        if not _HAS_ADK:
            raise RuntimeError(
                "google-adk-python is not installed. Install with `pip install google-adk`"
            )

        gofannon_def = self.definition.get("function", {}) # type: ignore
        tool_name = gofannon_def.get("name", getattr(self, "name", "gofannon_exported_tool"))
        tool_description = gofannon_def.get("description", getattr(self, "description", "No description provided."))

        gofannon_params_schema = gofannon_def.get("parameters", {"type": "object", "properties": {}})

        original_gofannon_fn = self.fn # type: ignore
        is_gofannon_fn_async = inspect.iscoroutinefunction(original_gofannon_fn)

        # Define a custom ADK Tool class
        class GofannonAdkTool(AdkBaseTool): # type: ignore
            def __init__(self, name, description, gofannon_json_schema, gofannon_exec_fn, is_fn_async):
                super().__init__(name=name, description=description) # type: ignore
                self._gofannon_json_schema = gofannon_json_schema
                self._gofannon_exec_fn = gofannon_exec_fn
                self._is_fn_async = is_fn_async

            def _get_declaration(self) -> Optional[adk_gemini_types.FunctionDeclaration]: # type: ignore
                adk_params_schema = _gofannon_json_schema_to_adk_schema(self._gofannon_json_schema)
                return adk_gemini_types.FunctionDeclaration( # type: ignore
                    name=self.name,
                    description=self.description,
                    parameters=adk_params_schema
                )

            async def run_async(self, *, args: Dict[str, Any], tool_context: AdkToolContext) -> Any: # type: ignore
                # The ADK tool_context is available here but the Gofannon fn doesn't expect it.
                # We simply pass the args to the Gofannon function.
                if self._is_fn_async:
                    return await self._gofannon_exec_fn(**args)
                else:
                    # Gofannon's synchronous fn needs to be run in a thread
                    # as ADK's run_async is an async method.
                    # Use functools.partial to create a callable with arguments pre-bound.
                    func_with_bound_args = functools.partial(self._gofannon_exec_fn, **args)
                    return await anyio.to_thread.run_sync(func_with_bound_args)

        exported_adk_tool = GofannonAdkTool(
            name=tool_name,
            description=tool_description,
            gofannon_json_schema=gofannon_params_schema,
            gofannon_exec_fn=original_gofannon_fn,
            is_fn_async=is_gofannon_fn_async
        )
        return exported_adk_tool  