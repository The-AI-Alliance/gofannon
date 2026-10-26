"""Unit tests for chat service."""
from __future__ import annotations

import json
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from services.chat_service import ChatService
from time_utils import naive_utc_now


pytestmark = pytest.mark.unit


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def chat_service(temp_storage):
    """Create a ChatService instance with temporary storage."""
    return ChatService(storage_dir=temp_storage)


@pytest.mark.asyncio
async def test_create_chat_ticket(chat_service, temp_storage):
    """Test creating a chat ticket."""
    messages = [{"role": "user", "content": "Hello"}]
    model = "openai/gpt-3.5-turbo"
    config = {"temperature": 0.7}
    session_id = "test-session"

    with patch("services.chat_service.call_llm", new_callable=AsyncMock) as mock_call_llm:
        mock_call_llm.return_value = ("Hi there!", None)

        ticket_id = await chat_service.create_chat_ticket(
            session_id=session_id,
            messages=messages,
            model=model,
            config=config
        )

    assert ticket_id is not None
    assert isinstance(ticket_id, str)

    # Verify ticket file exists
    ticket_path = Path(temp_storage) / f"{ticket_id}.json"
    assert ticket_path.exists()

    # Verify ticket contents
    with open(ticket_path) as f:
        ticket_data = json.load(f)

    assert ticket_data["id"] == ticket_id
    assert ticket_data["session_id"] == session_id
    assert ticket_data["status"] == "processing"
    assert ticket_data["model"] == model
    assert ticket_data["messages"] == messages
    assert ticket_data["config"] == config


@pytest.mark.asyncio
async def test_process_chat_success(chat_service, temp_storage):
    """Test successful chat processing."""
    messages = [{"role": "user", "content": "Test message"}]
    model = "openai/gpt-4"
    config = {"temperature": 0.5}
    session_id = "test-session"

    with patch("services.chat_service.call_llm", new_callable=AsyncMock) as mock_call_llm:
        mock_call_llm.return_value = ("Test response", {"some": "thoughts"})

        ticket_id = await chat_service.create_chat_ticket(
            session_id=session_id,
            messages=messages,
            model=model,
            config=config
        )

        # Wait for processing to complete
        if ticket_id in chat_service.active_tasks:
            await chat_service.active_tasks[ticket_id]

    # Verify ticket status
    ticket_data = await chat_service.get_ticket_status(ticket_id)

    assert ticket_data["status"] == "completed"
    assert ticket_data["response"]["content"] == "Test response"
    assert ticket_data["response"]["model"] == model
    assert ticket_data["response"]["finish_reason"] == "stop"
    assert ticket_data["response"]["thoughts"] == {"some": "thoughts"}
    assert "completed_at" in ticket_data

    # Verify call_llm was called with correct arguments
    mock_call_llm.assert_called_once()
    call_kwargs = mock_call_llm.call_args[1]
    assert call_kwargs["provider"] == "openai"
    assert call_kwargs["model"] == "gpt-4"
    assert call_kwargs["messages"] == messages
    assert call_kwargs["parameters"] == config


@pytest.mark.asyncio
async def test_process_chat_failure(chat_service, temp_storage):
    """Test chat processing with error."""
    messages = [{"role": "user", "content": "Test"}]
    model = "openai/gpt-3.5-turbo"
    config = {}
    session_id = "test-session"

    with patch("services.chat_service.call_llm", new_callable=AsyncMock) as mock_call_llm:
        mock_call_llm.side_effect = Exception("API Error")

        ticket_id = await chat_service.create_chat_ticket(
            session_id=session_id,
            messages=messages,
            model=model,
            config=config
        )

        # Wait for processing to complete
        if ticket_id in chat_service.active_tasks:
            await chat_service.active_tasks[ticket_id]

    # Verify ticket status shows failure
    ticket_data = await chat_service.get_ticket_status(ticket_id)

    assert ticket_data["status"] == "failed"
    assert ticket_data["error"] == "API Error"
    assert "completed_at" in ticket_data


@pytest.mark.asyncio
async def test_process_chat_no_provider_prefix(chat_service, temp_storage):
    """A model with no provider prefix is rejected, not silently defaulted."""
    messages = [{"role": "user", "content": "Test message"}]
    model = "gpt-4"  # No provider prefix
    config = {}
    session_id = "test-session"

    with patch("services.chat_service.call_llm", new_callable=AsyncMock) as mock_call_llm:
        ticket_id = await chat_service.create_chat_ticket(
            session_id=session_id,
            messages=messages,
            model=model,
            config=config
        )

        # Wait for processing to complete
        if ticket_id in chat_service.active_tasks:
            await chat_service.active_tasks[ticket_id]

        # The LLM is never reached — the prefix check fails first.
        mock_call_llm.assert_not_called()

    import json
    with open(chat_service.storage_dir / f"{ticket_id}.json") as f:
        ticket = json.load(f)
    assert ticket["status"] == "failed"
    assert "no provider prefix" in ticket["error"]


@pytest.mark.asyncio
async def test_get_ticket_status_not_found(chat_service):
    """Test getting status for non-existent ticket."""
    result = await chat_service.get_ticket_status("non-existent-ticket")
    assert result is None


@pytest.mark.asyncio
async def test_stream_chat_success(chat_service):
    """Test streaming chat completion."""
    messages = [{"role": "user", "content": "Hello"}]
    model = "openai/gpt-3.5-turbo"
    config = {"temperature": 0.7}
    session_id = "test-session"

    # Create mock streaming response
    class MockDelta:
        def __init__(self, content):
            self.content = content

    class MockStreamChoice:
        def __init__(self, delta):
            self.delta = delta

    class MockChunk:
        def __init__(self, content):
            self.choices = [MockStreamChoice(MockDelta(content))]

    async def mock_stream(*args, **kwargs):
        yield MockChunk("Hello")
        yield MockChunk(" there")
        yield MockChunk("!")

    with patch("services.chat_service.stream_llm", side_effect=mock_stream):
        chunks = []
        async for chunk in chat_service.stream_chat(
            session_id=session_id,
            messages=messages,
            model=model,
            config=config
        ):
            chunks.append(chunk)

    assert len(chunks) == 4  # 3 content chunks + 1 done
    assert chunks[0] == {"type": "content", "data": "Hello"}
    assert chunks[1] == {"type": "content", "data": " there"}
    assert chunks[2] == {"type": "content", "data": "!"}
    assert chunks[3] == {"type": "done", "data": None}


@pytest.mark.asyncio
async def test_stream_chat_error(chat_service):
    """Test streaming chat with error."""
    messages = [{"role": "user", "content": "Test"}]
    model = "openai/gpt-3.5-turbo"
    config = {}
    session_id = "test-session"

    async def mock_stream_error(*args, **kwargs):
        raise Exception("Stream error")
        # This yield is needed to make the function a generator
        yield  # pragma: no cover

    with patch("services.chat_service.stream_llm", side_effect=mock_stream_error):
        chunks = []
        async for chunk in chat_service.stream_chat(
            session_id=session_id,
            messages=messages,
            model=model,
            config=config
        ):
            chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0]["type"] == "error"
    assert chunks[0]["data"] == "Stream error"


def test_cleanup_old_tickets(chat_service, temp_storage):
    """Test cleanup of old ticket files."""
    # Create some test tickets with different ages
    now = naive_utc_now()
    old_time = now - timedelta(hours=25)
    recent_time = now - timedelta(hours=1)

    # Old ticket
    old_ticket = {
        "id": "old-ticket",
        "created_at": old_time.isoformat(),
        "status": "completed"
    }
    old_path = Path(temp_storage) / "old-ticket.json"
    with open(old_path, 'w') as f:
        json.dump(old_ticket, f)

    # Recent ticket
    recent_ticket = {
        "id": "recent-ticket",
        "created_at": recent_time.isoformat(),
        "status": "processing"
    }
    recent_path = Path(temp_storage) / "recent-ticket.json"
    with open(recent_path, 'w') as f:
        json.dump(recent_ticket, f)

    # Run cleanup
    chat_service.cleanup_old_tickets(max_age_hours=24)

    # Old ticket should be deleted
    assert not old_path.exists()

    # Recent ticket should still exist
    assert recent_path.exists()


def test_cleanup_handles_invalid_files(chat_service, temp_storage):
    """Test that cleanup handles invalid/corrupted ticket files gracefully."""
    # Create an invalid JSON file
    invalid_path = Path(temp_storage) / "invalid.json"
    with open(invalid_path, 'w') as f:
        f.write("not valid json{")

    # Should not raise an exception
    chat_service.cleanup_old_tickets(max_age_hours=24)

    # Invalid file should still exist (we skip it)
    assert invalid_path.exists()
