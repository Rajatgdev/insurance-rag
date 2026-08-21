"""Chat endpoint: drives the persona-aware intern loop over HTTP.

The client keeps the conversation and POSTs the full message list + a persona id each turn.
The response is that persona's answer shape (verdict / wording read / comparison) — either
narrowing questions (mode=clarify) or a grounded answer. Stateless: all state is in `messages`.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from db.session import AsyncSessionLocal
from reasoning.answerer import answer

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    persona: str = "ciara"


@router.post("/chat", response_model=None)
async def chat(req: ChatRequest):
    async with AsyncSessionLocal() as session:
        return await answer(session, [m.model_dump() for m in req.messages], req.persona)