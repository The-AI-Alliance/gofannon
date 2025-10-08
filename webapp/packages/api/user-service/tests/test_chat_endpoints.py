webapp/packages/api/user-service/tests/test_chat_endpoints.py
import pytest
import httpx
import asyncio

# All tests in this suite will be treated as async
pytestmark = pytest.mark.asyncio

BASE_URL = "http://localhost:8000"

async def poll_for_result(client: httpx.AsyncClient, ticket_id: str, timeout: int = 20) -> dict:
    """Polls the chat status endpoint until completion or timeout."""
    for _ in range(timeout):
        await asyncio.sleep(1)
        response = await client.get(f"{BASE_URL}/chat/{ticket_id}")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "completed":
            return data
        if data["status"] == "failed":
            pytest.fail(f"Chat processing failed with error: {data.get('error')}")
    pytest.fail("Polling for chat result timed out.")

async def test_chat_flow():
    """Tests the full asynchronous chat flow from ticket creation to result retrieval."""
    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Submit a chat request
        chat_payload = {
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
            "provider": "openai",
            "model": "gpt-4",
            "parameters": {"temperature": 0.1}
        }
        response = await client.post(f"{BASE_URL}/chat", json=chat_payload)
        assert response.status_code == 200
        initial_data = response.json()
        assert initial_data["status"] == "pending"
        assert "ticket_id" in initial_data

        ticket_id = initial_data["ticket_id"]

        # Step 2: Poll for the result
        final_data = await poll_for_result(client, ticket_id)

        # Step 3: Verify the result
        assert final_data["status"] == "completed"
        assert final_data["result"] is not None
        assert "content" in final_data["result"]
        assert "Paris" in final_data["result"]["content"] # A reasonable expectation for this model and question
        assert "usage" in final_data["result"]