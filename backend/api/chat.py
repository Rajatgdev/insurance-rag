"""Chat + persona query endpoints: /query, /persona/{id}."""
"""Chat endpoint: drives the same intern loop as the CLI, over HTTP.

The client keeps the conversation and POSTs the full message list each turn. The response
is a CoPilotResponse — either narrowing questions (mode=clarify) or a grounded verdict
(mode=answer). Stateless: all state lives in `messages`.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from db.session import AsyncSessionLocal
from reasoning.answerer import answer
from reasoning.schemas import CoPilotResponse

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    persona: str = "generic"


@router.post("/chat", response_model=CoPilotResponse)
async def chat(req: ChatRequest) -> CoPilotResponse:
    async with AsyncSessionLocal() as session:
        return await answer(session, [m.model_dump() for m in req.messages], req.persona)