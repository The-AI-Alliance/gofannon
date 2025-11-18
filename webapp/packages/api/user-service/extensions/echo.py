
from fastapi import APIRouter, Request
from pydantic import BaseModel

# Create a new router for our echo endpoint
router = APIRouter()

class EchoRequest(BaseModel):
    text: str

@router.post("/echo")
async def echo(request: EchoRequest):
    """
    A simple endpoint that echoes back the text it receives.
    """
    return {"echo": request.text}
