import pytest
from unittest.mock import MagicMock
from pydantic import BaseModel
from gofannon.base import BaseTool

# Test fixtures
@pytest.fixture
def mock_langflow_component():
    class MockComponent:
        display_name = "Test Component"
        description = "Test Description"

        class Inputs:
            text_input = MagicMock(name="text_input", spec=MessageTextInput)
            int_input = MagicMock(name="int_input", spec=IntInput)
            bool_input = MagicMock(name="bool_input", spec=BoolInput)

            text_input.name = "text_param"
            text_input.info = "Text parameter"
            text_input.required = True

            int_input.name = "num_param"
            int_input.info = "Number parameter"
            int_input.required = False

            bool_input.name = "flag_param"
            bool_input.info = "Boolean parameter"
            bool_input.required = True

        inputs = [text_input, int_input, bool_input]

        def build(self):
            return lambda **kwargs: kwargs

    return MockComponent()

@pytest.fixture
def sample_gofannon_tool():
    class SampleTool(BaseTool):
        @property
        def definition(self):
            return {
                "function": {
                    "name": "sample_tool",
                    "description": "Sample tool description",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number", "description": "First number"},
                            "b": {"type": "number", "description": "Second number"}
                        },
                        "required": ["a", "b"]
                    }
                }
            }

        def fn(self, a: float, b: float) -> float:
            return a + b

    return SampleTool()

# Tests
def test_import_from_langflow_success(mock_langflow_component):
    # Test successful import from Langflow component
    tool = BaseTool()
    tool.import_from_langflow(mock_langflow_component)

    assert tool.name == "test_component"
    assert tool.description == "Test Description"

    params = tool.definition["function"]["parameters"]
    assert params["properties"]["text_param"]["type"] == "string"
    assert params["properties"]["num_param"]["type"] == "number"
    assert params["properties"]["flag_param"]["type"] == "boolean"

    assert "text_param" in params["required"]
    assert "flag_param" in params["required"]
    assert "num_param" not in params["required"]

def test_export_to_langflow_success(sample_gofannon_tool):
    # Test successful export to Langflow component
    component_class = sample_gofannon_tool.export_to_langflow()
    component = component_class()

    assert component.display_name == "Sample Tool"
    assert component.description == "Sample tool description"

    input_names = [input.name for input in component.inputs]
    assert "a" in input_names
    assert "b" in input_names

    # Test component execution
    result = component.run_tool(a=2, b=3)
    assert result.data == 5

def test_type_mapping():
    # Test JSON schema to Langflow input type mapping
    tool = BaseTool()
    tool.definition = {
        "function": {
            "parameters": {
                "properties": {
                    "str_param": {"type": "string"},
                    "num_param": {"type": "number"},
                    "int_param": {"type": "integer"},
                    "bool_param": {"type": "boolean"}
                }
            }
        }
    }

    component_class = tool.export_to_langflow()
    input_types = {
        input.name: type(input).__name__
        for input in component_class.inputs
    }

    assert input_types["str_param"] == "MessageTextInput"
    assert input_types["num_param"] == "FloatInput"
    assert input_types["int_param"] == "IntInput"
    assert input_types["bool_param"] == "BoolInput"

def test_missing_langflow_import():
    # Test error when Langflow is not installed
    original_has_langflow = LangflowMixin._HAS_LANGFLOW
    LangflowMixin._HAS_LANGFLOW = False

    tool = BaseTool()

    with pytest.raises(RuntimeError) as excinfo:
        tool.import_from_langflow(MagicMock())
    assert "langflow is not installed" in str(excinfo.value)

    with pytest.raises(RuntimeError) as excinfo:
        tool.export_to_langflow()
    assert "langflow is not installed" in str(excinfo.value)

    LangflowMixin._HAS_LANGFLOW = original_has_langflow

def test_complex_parameter_handling():
    # Test component with complex parameter configuration
    class ComplexComponent:
        display_name = "Complex Component"
        description = "Component with complex parameters"

        class Inputs:
            required_input = MagicMock(spec=MessageTextInput)
            optional_input = MagicMock(spec=IntInput)

            required_input.name = "required"
            required_input.info = "Required parameter"
            required_input.required = True

            optional_input.name = "optional"
            optional_input.info = "Optional parameter"
            optional_input.required = False

        inputs = [required_input, optional_input]

        def build(self):
            return lambda **kwargs: kwargs

    tool = BaseTool()
    tool.import_from_langflow(ComplexComponent())

    params = tool.definition["function"]["parameters"]
    assert "required" in params["required"]
    assert "optional" not in params["required"]
    assert params["properties"]["required"]["type"] == "string"
    assert params["properties"]["optional"]["type"] == "integer"

def test_component_execution_flow():
    # Test full round-trip execution flow
    class TestTool(BaseTool):
        @property
        def definition(self):
            return {
                "function": {
                    "name": "test_tool",
                    "description": "Test execution flow",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "input": {"type": "string"}
                        },
                        "required": ["input"]
                    }
                }
            }

        def fn(self, input: str) -> str:
            return f"Processed: {input}"

            # Export to Langflow component
    tool = TestTool()
    component_class = tool.export_to_langflow()
    component = component_class()

    # Execute through Langflow interface
    result = component.run_tool(input="test")
    assert result.data == "Processed: test"

def test_error_handling_in_execution():
    # Test error handling in exported component
    class ErrorTool(BaseTool):
        @property
        def definition(self):
            return {
                "function": {
                    "name": "error_tool",
                    "description": "Tool that raises errors",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {"type": "number"}
                        }
                    }
                }
            }

        def fn(self, value: float):
            if value < 0:
                raise ValueError("Negative value")
            return value ** 0.5

            # Export and test
    component_class = ErrorTool().export_to_langflow()
    component = component_class()

    # Test valid input
    valid_result = component.run_tool(value=4)
    assert valid_result.data == 2.0

    # Test invalid input
    error_result = component.run_tool(value=-4)
    assert "error" in error_result.data
    assert "Negative value" in error_result.data["error"]