import pytest
from gofannon.base import BaseTool
from gofannon.config import FunctionRegistry

@pytest.fixture
def tools():
    return [tool_class() for tool_class in FunctionRegistry._tools.values()]