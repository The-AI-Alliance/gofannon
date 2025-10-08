webapp/packages/api/user-service/tests/test_agent_endpoints.py
import pytest
import httpx

# All tests in this suite will be treated as async
pytestmark = pytest.mark.asyncio

BASE_URL = "http://localhost:8000"

@pytest.fixture
def agent_generation_payload():
    """Provides a valid payload for the /agents/generate-code endpoint."""
    return {
        "tools": {},
        "description": "An agent that takes a user's name and returns a greeting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "greeting": {"type": "string"}
            }
        },
        "modelConfig": {
            "provider": "openai",
            "model": "gpt-4",
            "parameters": {"temperature": 0}
        },
        "invokableModels": []
    }

async def test_generate_agent_code(agent_generation_payload):
    """Tests code generation for a simple agent."""
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.post(f"{BASE_URL}/agents/generate-code", json=agent_generation_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "async def run(input_dict, tools):" in data["code"]
        assert "return" in data["code"]

async def test_run_agent_code_simple():
    """Tests running a simple, hardcoded piece of agent code."""
    
    # This simple code doesn't require an LLM and just manipulates input.
    # This makes the test fast and deterministic.
    simple_agent_code = """
import asyncio

async def run(input_dict, tools):
   name = input_dict.get("name", "World")
   # Simulate some async work
   await asyncio.sleep(0.1)
   return {"greeting": f"Hello, {name}!"}
"""
    
    run_payload = {
        "code": simple_agent_code,
        "inputDict": {"name": "Test Runner"},
        "tools": {}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/agents/run-code", json=run_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        assert "result" in data
        assert data["result"] == {"greeting": "Hello, Test Runner!"}

async def test_run_agent_code_with_error():
    """Tests that malformed agent code returns a proper error."""
    
    error_agent_code = """
async def run(input_dict, tools):
    # This will raise a SyntaxError
    return {"greeting": f"Hello, {name}!" # Missing closing brace
"""

    run_payload = {
        "code": error_agent_code,
        "inputDict": {"name": "Test Runner"},
        "tools": {}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/agents/run-code", json=run_payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["result"] is None
        assert "error" in data
        assert "SyntaxError" in data["error"]