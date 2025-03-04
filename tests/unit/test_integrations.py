# tests/test_integrations.py  

import pytest
from gofannon.base import BaseTool
from gofannon.basic_math.addition import Addition

# Add DummyTool subclass implementing abstract methods  
class DummyTool(BaseTool):
    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "properties": self._parameters,
                    "required": self._required
                }
            }
        }

    def fn(self, *args, **kwargs):
        return "dummy result"

        # LangChain tests
def test_langchain_import_export():
    try:
        from langchain.tools import BaseTool as LangchainBaseTool
        from langchain.tools import WikipediaQueryRun
    except ImportError:
        pytest.skip("langchain-core not installed")

        # Use DummyTool instead of BaseTool
    lc_tool = WikipediaQueryRun()
    base_tool = DummyTool()
    base_tool.import_from_langchain(lc_tool)

    assert base_tool.name == "wikipedia"
    assert "Wikipedia" in base_tool.description

    exported_tool = base_tool.export_to_langchain()
    assert isinstance(exported_tool, LangchainBaseTool)

def test_smolagents_import_export():
    try:
        from smolagents.tools import Tool as SmolTool
    except ImportError:
        pytest.skip("smolagents not installed")

    def test_fn(a: int, b: int) -> int:
        return a + b

    smol_tool = SmolTool()
    smol_tool.name="test_addition",
    smol_tool.description="Adds numbers",
    smol_tool.inputs={
            "a": {"type": "int", "description": "First number"},
            "b": {"type": "int", "description": "Second number"}
        },
    smol_tool.output_type="int",
    smol_tool.forward=test_fn

    base_tool = DummyTool()
    base_tool.import_from_smolagents(smol_tool)

    assert base_tool.name == "test_addition"
    assert "Adds numbers" in base_tool.description

    exported_tool = base_tool.export_to_smolagents()
    assert exported_tool.forward(2, 3) == 5

def test_cross_framework_roundtrip():
    native_tool = Addition()
    lc_tool = native_tool.export_to_langchain()

    # Use DummyTool for import test  
    imported_tool = DummyTool()
    imported_tool.import_from_langchain(lc_tool)

    assert imported_tool.fn(2, 3) == 5
    assert imported_tool.name == "addition"

    exported_smol = native_tool.export_to_smolagents()
    assert exported_smol.forward(4, 5) == 9  