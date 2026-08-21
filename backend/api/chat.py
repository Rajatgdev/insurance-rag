"""Chat endpoint: drives the persona-aware intern loop over HTTP.

The client keeps the conversation and POSTs the full message list + a persona id each turn.
The response is an Envelope: the persona's answer (verdict / wording read / comparison) plus
the audit trail (what was asked, which policies were read, what grounded it). Stateless.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from db.session import AsyncSessionLocal
from reasoning.answerer import answer
from reasoning.schemas import Envelope

router = APIRouter()


class Message(BaseModel):
    role: str
    content: str


class HandoffFactsIn(BaseModel):
    topic: str = ""
    insurers: list[str] = []
    circumstances: str = ""


class ChatRequest(BaseModel):
    messages: list[Message]
    persona: str = "ciara"
    handoff: HandoffFactsIn | None = None


@router.post("/chat", response_model=Envelope)
async def chat(req: ChatRequest) -> Envelope:
    async with AsyncSessionLocal() as session:
        return await answer(
            session,
            [m.model_dump() for m in req.messages],
            req.persona,
            handoff=req.handoff.model_dump() if req.handoff else None,
        )