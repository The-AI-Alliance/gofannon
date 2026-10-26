import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from services.llm_service import call_llm, stream_llm
from time_utils import naive_utc_now

class ChatService:
    def __init__(self, storage_dir: str = "/tmp/chat_tickets"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.active_tasks = {}
    
    async def create_chat_ticket(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any]
    ) -> str:
        """Create a ticket and start async chat completion"""
        ticket_id = str(uuid.uuid4())
        
        # Create ticket file
        ticket_data = {
            "id": ticket_id,
            "session_id": session_id,
            "status": "processing",
            "created_at": naive_utc_now().isoformat(),
            "model": model,
            "messages": messages,
            "config": config,
            "response": None,
            "error": None
        }
        
        ticket_path = self.storage_dir / f"{ticket_id}.json"
        with open(ticket_path, 'w') as f:
            json.dump(ticket_data, f)
        
        # Start async processing
        task = asyncio.create_task(self._process_chat(ticket_id, messages, model, config))
        self.active_tasks[ticket_id] = task
        
        return ticket_id
    
    async def _process_chat(
        self,
        ticket_id: str,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any]
    ):
        """Process chat completion asynchronously"""
        ticket_path = self.storage_dir / f"{ticket_id}.json"

        try:
            # Parse provider/model format
            if "/" in model:
                provider, model_name = model.split("/", 1)
            else:
                # No silent default. A bare model name used to fall through to
                # "openai", which meant a typo or a dropped prefix quietly ran
                # on a different provider than intended -- and after the
                # provider cleanup it would fail deep in litellm with an
                # unrelated-looking error. Fail here, where the cause is
                # obvious.
                raise ValueError(
                    f"Model '{model}' has no provider prefix. Use "
                    f"'provider/model', e.g. 'bedrock/us.anthropic.claude-opus-5'."
                )

            # Call LLM through the centralized service
            content, thoughts = await call_llm(
                provider=provider,
                model=model_name,
                messages=messages,
                parameters=config,
                user_service=None,  # Chat service doesn't track user costs
                user_id=None,
            )

            # Update ticket with response
            with open(ticket_path, 'r') as f:
                ticket_data = json.load(f)

            ticket_data["status"] = "completed"
            ticket_data["response"] = {
                "content": content,
                "model": model,
                "usage": None,  # Usage tracking handled by llm_service
                "finish_reason": "stop",
                "thoughts": thoughts
            }
            ticket_data["completed_at"] = naive_utc_now().isoformat()

            with open(ticket_path, 'w') as f:
                json.dump(ticket_data, f)

        except Exception as e:
            # Update ticket with error
            with open(ticket_path, 'r') as f:
                ticket_data = json.load(f)

            ticket_data["status"] = "failed"
            ticket_data["error"] = str(e)
            ticket_data["completed_at"] = naive_utc_now().isoformat()

            with open(ticket_path, 'w') as f:
                json.dump(ticket_data, f)

        finally:
            # Clean up task reference
            if ticket_id in self.active_tasks:
                del self.active_tasks[ticket_id]
    
    async def get_ticket_status(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a ticket"""
        ticket_path = self.storage_dir / f"{ticket_id}.json"
        
        if not ticket_path.exists():
            return None
        
        with open(ticket_path, 'r') as f:
            return json.load(f)
    
    async def stream_chat(
        self,
        session_id: str,
        messages: List[Dict[str, str]],
        model: str,
        config: Dict[str, Any]
    ):
        """Stream chat completion responses"""
        try:
            # Parse provider/model format
            if "/" in model:
                provider, model_name = model.split("/", 1)
            else:
                # No silent default. A bare model name used to fall through to
                # "openai", which meant a typo or a dropped prefix quietly ran
                # on a different provider than intended -- and after the
                # provider cleanup it would fail deep in litellm with an
                # unrelated-looking error. Fail here, where the cause is
                # obvious.
                raise ValueError(
                    f"Model '{model}' has no provider prefix. Use "
                    f"'provider/model', e.g. 'bedrock/us.anthropic.claude-opus-5'."
                )

            # Stream through the centralized service
            async for chunk in stream_llm(
                provider=provider,
                model=model_name,
                messages=messages,
                parameters=config,
                user_service=None,  # Chat service doesn't track user costs
                user_id=None,
            ):
                if chunk.choices[0].delta.content:
                    yield {
                        "type": "content",
                        "data": chunk.choices[0].delta.content
                    }

            yield {
                "type": "done",
                "data": None
            }

        except Exception as e:
            yield {
                "type": "error",
                "data": str(e)
            }
    
    def cleanup_old_tickets(self, max_age_hours: int = 24):
        """Clean up old ticket files"""
        from datetime import timedelta
        
        cutoff_time = naive_utc_now() - timedelta(hours=max_age_hours)
        
        for ticket_file in self.storage_dir.glob("*.json"):
            try:
                with open(ticket_file, 'r') as f:
                    ticket_data = json.load(f)
                
                created_at = datetime.fromisoformat(ticket_data["created_at"])
                if created_at < cutoff_time:
                    ticket_file.unlink()
            except Exception:
                # If we can't read or parse the file, just skip it
                pass

# Singleton instance
chat_service = ChatService()

def get_chat_service() -> ChatService:
    return chat_service