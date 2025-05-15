# tests/unit/google/test_adk_mixin.py

import pytest
import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Type as TypingType, Union
from unittest.mock import MagicMock, patch

# Import the AdkMixin and its helper types
from gofannon.base.adk_mixin import (
    AdkMixin,
    _HAS_ADK,
    _adk_schema_to_gofannon_json_schema,
    _gofannon_json_schema_to_adk_schema
)

# Minimal Gofannon BaseTool for testing
from abc import ABC, abstractmethod
import logging

class MinimalGofannonBaseTool(ABC):
    def __init__(self, **kwargs):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._name = kwargs.get("name", self.__class__.__name__.lower())
        self._description = kwargs.get("description", "")
        self._definition_data = kwargs.get("definition", None)
        self._fn_impl = kwargs.get("fn", None)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def definition(self):
        return self._definition_data

    @definition.setter
    def definition(self, value):
        self._definition_data = value

    @property
    def fn(self):
        if not self._fn_impl:
            raise NotImplementedError
        return self._fn_impl

    @fn.setter
    def fn(self, value):
        self._fn_impl = value

    # Conditional ADK imports for testing
if _HAS_ADK:
    from google.adk.tools import BaseTool as AdkBaseTool
    from google.adk.tools import FunctionTool as AdkFunctionTool
    from google.adk.tools.tool_context import ToolContext as AdkToolContext
    from google.genai import types as adk_gemini_types
    import anyio
else: # Mock ADK types if not installed for basic test structure
    class AdkBaseTool:
        def __init__(self, name, description, **kwargs): self.name = name; self.description = description
        def _get_declaration(self) -> Optional['adk_gemini_types.FunctionDeclaration']: return None
        async def run_async(self, *, args: Dict[str, Any], tool_context: 'AdkToolContext') -> Any: raise NotImplementedError
        async def process_llm_request(self, *, tool_context: 'AdkToolContext', llm_request: Any) -> None: pass


    class AdkFunctionTool(AdkBaseTool): # type: ignore
        def __init__(self, func: Callable, **kwargs):
            super().__init__(name=func.__name__, description=func.__doc__ or "", **kwargs)
            self.func = func

        def _get_declaration(self) -> Optional['adk_gemini_types.FunctionDeclaration']:
            # Simplified mock declaration
            if hasattr(self.func, "_adk_declaration"):
                return self.func._adk_declaration # type: ignore

            # Basic mock for parameters based on inspect, if possible
            try:
                sig = inspect.signature(self.func)
                props = {}
                req = []
                for name, param in sig.parameters.items():
                    # A very basic type mapping for mock
                    param_type_map = {str: "STRING", int: "INTEGER", bool: "BOOLEAN", float: "NUMBER"}
                    adk_type = "OBJECT" # default
                    if param.annotation in param_type_map:
                        adk_type = getattr(adk_gemini_types.Type, param_type_map[param.annotation])

                    props[name] = adk_gemini_types.Schema(type=adk_type, description=f"Parameter {name}")
                    if param.default == inspect.Parameter.empty:
                        req.append(name)

                params_schema = adk_gemini_types.Schema(type=adk_gemini_types.Type.OBJECT, properties=props, required=req)
                return adk_gemini_types.FunctionDeclaration(name=self.name, description=self.description, parameters=params_schema)
            except: # Broad except for complex cases not handled by this simple mock
                return adk_gemini_types.FunctionDeclaration(name=self.name, description=self.description, parameters=None)


    class AdkToolContext: pass

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
            def __init__(self, type=None, description=None, properties=None, items=None, required=None, enum=None, nullable=None, **kwargs):
                self.type = type or adk_gemini_types.Type.OBJECT
                self.description = description
                self.properties = properties or {}
                self.items = items
                self.required = required or []
                self.enum = enum
                self.nullable = nullable

        class FunctionDeclaration: # type: ignore
            def __init__(self, name, description, parameters):
                self.name = name
                self.description = description
                self.parameters = parameters

    class anyio: # type: ignore
        @staticmethod
        async def to_thread_run_sync(func, *args, **kwargs):
            return func(*args, **kwargs) # Simplified for mock

# Test Gofannon Tool that uses the AdkMixin
class GofannonWithAdk(AdkMixin, MinimalGofannonBaseTool):
    pass

@pytest.fixture
def concrete_gofannon_tool_for_export():
    def sample_fn(param1: str, param2: int = 10) -> str:
        return f"Hello {param1}, number {param2}"

    return GofannonWithAdk(
        name="my_gofannon_exporter",
        description="Gofannon tool for ADK export.",
        definition={
            "function": {
                "name": "my_gofannon_exporter",
                "description": "Gofannon tool for ADK export.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "A string parameter"},
                        "param2": {"type": "integer", "description": "An integer parameter"}
                    },
                    "required": ["param1"]
                }
            }
        },
        fn=sample_fn
    )

@pytest.fixture
def concrete_gofannon_tool_for_export_async_fn():
    async def sample_async_fn(param_async: bool) -> Dict:
        return {"async_result": param_async}

    return GofannonWithAdk(
        name="my_gofannon_async_exporter",
        description="Gofannon async tool for ADK export.",
        definition={
            "function": {
                "name": "my_gofannon_async_exporter",
                "description": "Gofannon async tool for ADK export.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param_async": {"type": "boolean", "description": "Async boolean param"}
                    },
                    "required": ["param_async"]
                }
            }
        },
        fn=sample_async_fn
    )


@pytest.fixture
def concrete_gofannon_tool_for_import():
    return GofannonWithAdk(name="importer", description="Tool to import ADK stuff")


if _HAS_ADK:
    # Sample Python functions to be wrapped by AdkFunctionTool
    def adk_sync_function_example(name: str, count: int = 5) -> str:
        """A synchronous ADK function."""
        return f"Sync: {name} appeared {count} times."

    async def adk_async_function_example(item: str, active: bool = True) -> dict:
        """An asynchronous ADK function."""
        return {"item": item, "status": "active" if active else "inactive"}

    @pytest.fixture
    def mock_adk_function_tool_sync():
        return AdkFunctionTool(func=adk_sync_function_example)

    @pytest.fixture
    def mock_adk_function_tool_async():
        return AdkFunctionTool(func=adk_async_function_example)

    @pytest.fixture
    def mock_adk_base_tool_with_run_async():
        class CustomAdkTool(AdkBaseTool):
            def __init__(self):
                super().__init__(name="custom_adk_tool", description="Custom ADK tool with run_async.")

            def _get_declaration(self) -> Optional[adk_gemini_types.FunctionDeclaration]:
                return adk_gemini_types.FunctionDeclaration(
                    name=self.name,
                    description=self.description,
                    parameters=adk_gemini_types.Schema(
                        type=adk_gemini_types.Type.OBJECT,
                        properties={
                            "data": adk_gemini_types.Schema(type=adk_gemini_types.Type.STRING, description="Some data")
                        },
                        required=["data"]
                    )
                )
            async def run_async(self, *, args: Dict[str, Any], tool_context: AdkToolContext) -> Any:
                return f"Custom processed: {args.get('data')}"
        return CustomAdkTool()

    @pytest.fixture
    def mock_adk_tool_no_declaration():
        class NoDeclTool(AdkBaseTool):
            def __init__(self):
                super().__init__(name="no_decl_tool", description="Tool without declaration")
            def _get_declaration(self) -> Optional[adk_gemini_types.FunctionDeclaration]:
                return None # Explicitly no declaration
            async def run_async(self, *, args: Dict[str, Any], tool_context: AdkToolContext) -> Any:
                return "No declaration tool ran"
        return NoDeclTool()


    # --- Tests for AdkMixin ---

def test_mixin_raises_error_if_adk_not_installed():
    if not _HAS_ADK:
        tool = GofannonWithAdk(name="test", description="test")
        with pytest.raises(RuntimeError, match="google-adk-python is not installed"):
            tool.export_to_adk()
        with pytest.raises(RuntimeError, match="google-adk-python is not installed"):
            tool.import_from_adk(MagicMock()) # Pass a mock AdkBaseTool
    else:
        pytest.skip("ADK is installed, skipping this test.")

@pytest.mark.skipif(not _HAS_ADK, reason="ADK not installed")
class TestAdkMixinExport:
    async def test_export_sync_fn_with_params(self, concrete_gofannon_tool_for_export):
        adk_tool = concrete_gofannon_tool_for_export.export_to_adk()
        assert isinstance(adk_tool, AdkBaseTool)
        assert adk_tool.name == "my_gofannon_exporter"
        assert adk_tool.description == "Gofannon tool for ADK export."

        declaration = adk_tool._get_declaration()
        assert declaration is not None
        assert declaration.name == "my_gofannon_exporter"
        assert declaration.parameters.type == adk_gemini_types.Type.OBJECT # type: ignore
        assert "param1" in declaration.parameters.properties # type: ignore
        assert declaration.parameters.properties["param1"].type == adk_gemini_types.Type.STRING # type: ignore
        assert "param2" in declaration.parameters.properties # type: ignore
        assert declaration.parameters.properties["param2"].type == adk_gemini_types.Type.INTEGER # type: ignore
        assert "param1" in declaration.parameters.required # type: ignore
        assert "param2" not in declaration.parameters.required # type: ignore

        # Test execution
        result = await adk_tool.run_async(args={"param1": "User", "param2": 5}, tool_context=None) # type: ignore
        assert result == "Hello User, number 5"
        result_default_param2 = await adk_tool.run_async(args={"param1": "Test"}, tool_context=None) # type: ignore
        # Gofannon fn default is used if ADK passes only required. ADK doesn't inject defaults.
        assert result_default_param2 == "Hello Test, number 10"


    async def test_export_async_fn_with_params(self, concrete_gofannon_tool_for_export_async_fn):
        adk_tool = concrete_gofannon_tool_for_export_async_fn.export_to_adk()
        assert isinstance(adk_tool, AdkBaseTool)
        assert adk_tool.name == "my_gofannon_async_exporter"

        declaration = adk_tool._get_declaration()
        assert declaration is not None
        assert declaration.parameters.properties["param_async"].type == adk_gemini_types.Type.BOOLEAN # type: ignore

        result = await adk_tool.run_async(args={"param_async": True}, tool_context=None) # type: ignore
        assert result == {"async_result": True}

    def test_export_gofannon_tool_no_params(self):
        def no_param_fn(): return "Fixed"
        tool = GofannonWithAdk(
            name="no_param_tool", description="Tool with no params.",
            definition={"function": {"name": "no_param_tool", "description": "Tool with no params.",
                                     "parameters": {"type": "object", "properties": {}}}},
            fn=no_param_fn
        )
        adk_tool = tool.export_to_adk()
        declaration = adk_tool._get_declaration()
        assert declaration is not None
        assert not declaration.parameters.properties # type: ignore
        assert not declaration.parameters.required # type: ignore


@pytest.mark.skipif(not _HAS_ADK, reason="ADK not installed")
class TestAdkMixinImport:
    async def test_import_function_tool_sync_func_with_params(self, concrete_gofannon_tool_for_import, mock_adk_function_tool_sync):
        concrete_gofannon_tool_for_import.import_from_adk(mock_adk_function_tool_sync)

        assert concrete_gofannon_tool_for_import.name == "adk_sync_function_example"
        assert concrete_gofannon_tool_for_import.description == "A synchronous ADK function."

        gof_def = concrete_gofannon_tool_for_import.definition["function"]
        assert "name" in gof_def["parameters"]["properties"]
        assert gof_def["parameters"]["properties"]["name"]["type"] == "string"
        assert "count" in gof_def["parameters"]["properties"]
        assert gof_def["parameters"]["properties"]["count"]["type"] == "integer"
        assert "name" in gof_def["parameters"]["required"]
        assert "count" not in gof_def["parameters"]["required"]

        result = concrete_gofannon_tool_for_import.fn(name="Test", count=3) # type: ignore
        assert result == "Sync: Test appeared 3 times."
        result_default = concrete_gofannon_tool_for_import.fn(name="Default") # type: ignore
        assert result_default == "Sync: Default appeared 5 times."


    async def test_import_function_tool_async_func_with_params(self, concrete_gofannon_tool_for_import, mock_adk_function_tool_async):
        concrete_gofannon_tool_for_import.import_from_adk(mock_adk_function_tool_async)

        assert concrete_gofannon_tool_for_import.name == "adk_async_function_example"
        assert concrete_gofannon_tool_for_import.description == "An asynchronous ADK function."

        gof_def = concrete_gofannon_tool_for_import.definition["function"]
        assert "item" in gof_def["parameters"]["properties"]
        assert gof_def["parameters"]["properties"]["item"]["type"] == "string"
        assert "active" in gof_def["parameters"]["properties"]
        assert gof_def["parameters"]["properties"]["active"]["type"] == "boolean"

        result = await concrete_gofannon_tool_for_import.fn(item="Gadget", active=False) # type: ignore
        assert result == {"item": "Gadget", "status": "inactive"}

    async def test_import_base_tool_with_run_async(self, concrete_gofannon_tool_for_import, mock_adk_base_tool_with_run_async):
        concrete_gofannon_tool_for_import.import_from_adk(mock_adk_base_tool_with_run_async)

        assert concrete_gofannon_tool_for_import.name == "custom_adk_tool"
        gof_def = concrete_gofannon_tool_for_import.definition["function"]
        assert "data" in gof_def["parameters"]["properties"]
        assert gof_def["parameters"]["properties"]["data"]["type"] == "string"

        result = await concrete_gofannon_tool_for_import.fn(data="input_data") # type: ignore
        assert result == "Custom processed: input_data"

    def test_import_tool_with_no_declaration(self, concrete_gofannon_tool_for_import, mock_adk_tool_no_declaration):
        concrete_gofannon_tool_for_import.import_from_adk(mock_adk_tool_no_declaration)
        assert concrete_gofannon_tool_for_import.name == "no_decl_tool"
        gof_def = concrete_gofannon_tool_for_import.definition["function"]
        # Expect empty parameters schema
        assert gof_def["parameters"]["type"] == "object"
        assert not gof_def["parameters"]["properties"]
        assert not gof_def["parameters"].get("required", [])


    def test_import_adk_tool_no_executable_method(self, concrete_gofannon_tool_for_import):
        class NoExecAdkTool(AdkBaseTool):
            def __init__(self):
                super().__init__(name="no_exec", description="No executable method")
                # No func or run_async

        adk_tool_instance = NoExecAdkTool()
        concrete_gofannon_tool_for_import.import_from_adk(adk_tool_instance)

        with pytest.raises(NotImplementedError, match="Execution for imported ADK tool no_exec is not available."):
            concrete_gofannon_tool_for_import.fn() # type: ignore

        # Also test the logger warning. This is a bit trickier.
        # For simplicity, we'll assume the logger warning in the mixin is sufficient.


# --- Tests for Schema Conversion Helpers ---

@pytest.mark.skipif(not _HAS_ADK, reason="ADK not installed")
def test_gofannon_json_schema_to_adk_schema_conversion():
    gofannon_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "User name"},
            "age": {"type": "integer"},
            "is_member": {"type": "boolean", "nullable": True},
            "tags": {"type": "array", "items": {"type": "string"}},
            "address": {
                "type": "object",
                "properties": {"street": {"type": "string"}, "city": {"type": "string"}},
                "required": ["street"]
            }
        },
        "required": ["name", "age"]
    }
    adk_schema = _gofannon_json_schema_to_adk_schema(gofannon_schema)

    assert adk_schema.type == adk_gemini_types.Type.OBJECT # type: ignore
    assert "name" in adk_schema.properties # type: ignore
    assert adk_schema.properties["name"].type == adk_gemini_types.Type.STRING # type: ignore
    assert adk_schema.properties["name"].description == "User name" # type: ignore
    assert adk_schema.properties["age"].type == adk_gemini_types.Type.INTEGER # type: ignore
    assert adk_schema.properties["is_member"].type == adk_gemini_types.Type.BOOLEAN # type: ignore
    assert adk_schema.properties["is_member"].nullable == True # type: ignore
    assert adk_schema.properties["tags"].type == adk_gemini_types.Type.ARRAY # type: ignore
    assert adk_schema.properties["tags"].items.type == adk_gemini_types.Type.STRING # type: ignore
    assert adk_schema.properties["address"].type == adk_gemini_types.Type.OBJECT # type: ignore
    assert "street" in adk_schema.properties["address"].properties # type: ignore
    assert "street" in adk_schema.properties["address"].required # type: ignore
    assert "name" in adk_schema.required # type: ignore
    assert "age" in adk_schema.required # type: ignore

@pytest.mark.skipif(not _HAS_ADK, reason="ADK not installed")
def test_adk_schema_to_gofannon_json_schema_conversion():
    adk_schema = adk_gemini_types.Schema( # type: ignore
        type=adk_gemini_types.Type.OBJECT, # type: ignore
        properties={
            "id": adk_gemini_types.Schema(type=adk_gemini_types.Type.STRING, description="Item ID"), # type: ignore
            "value": adk_gemini_types.Schema(type=adk_gemini_types.Type.NUMBER), # type: ignore
            "active": adk_gemini_types.Schema(type=adk_gemini_types.Type.BOOLEAN, nullable=True), # type: ignore
            "scores": adk_gemini_types.Schema(type=adk_gemini_types.Type.ARRAY, items=adk_gemini_types.Schema(type=adk_gemini_types.Type.INTEGER)), # type: ignore
            "metadata": adk_gemini_types.Schema( # type: ignore
                type=adk_gemini_types.Type.OBJECT, # type: ignore
                properties={"source": adk_gemini_types.Schema(type=adk_gemini_types.Type.STRING)}, # type: ignore
                required=["source"]
            )
        },
        required=["id", "value"]
    )
    gof_schema = _adk_schema_to_gofannon_json_schema(adk_schema)

    assert gof_schema["type"] == "object"
    assert "id" in gof_schema["properties"]
    assert gof_schema["properties"]["id"]["type"] == "string"
    assert gof_schema["properties"]["id"]["description"] == "Item ID"
    assert gof_schema["properties"]["value"]["type"] == "number"
    assert gof_schema["properties"]["active"]["type"] == "boolean"
    assert gof_schema["properties"]["active"]["nullable"] is True
    assert gof_schema["properties"]["scores"]["type"] == "array"
    assert gof_schema["properties"]["scores"]["items"]["type"] == "integer"
    assert gof_schema["properties"]["metadata"]["type"] == "object"
    assert "source" in gof_schema["properties"]["metadata"]["properties"]
    assert "source" in gof_schema["properties"]["metadata"]["required"]
    assert "id" in gof_schema["required"]
    assert "value" in gof_schema["required"]

def test_empty_schema_conversions():
    # Gofannon to ADK
    empty_gof_schema = {}
    adk_s = _gofannon_json_schema_to_adk_schema(empty_gof_schema)
    assert adk_s.type == adk_gemini_types.Type.OBJECT # type: ignore
    assert adk_s.properties == {} # type: ignore

    empty_gof_schema_explicit = {"type": "object", "properties": {}}
    adk_s_exp = _gofannon_json_schema_to_adk_schema(empty_gof_schema_explicit)
    assert adk_s_exp.type == adk_gemini_types.Type.OBJECT # type: ignore
    assert adk_s_exp.properties == {} # type: ignore

    # ADK to Gofannon
    empty_adk_schema = None
    gof_s = _adk_schema_to_gofannon_json_schema(empty_adk_schema) # type: ignore
    assert gof_s["type"] == "object"
    assert gof_s["properties"] == {}

    empty_adk_schema_explicit = adk_gemini_types.Schema(type=adk_gemini_types.Type.OBJECT) # type: ignore
    gof_s_exp = _adk_schema_to_gofannon_json_schema(empty_adk_schema_explicit)
    assert gof_s_exp["type"] == "object"
    assert gof_s_exp["properties"] == {}
