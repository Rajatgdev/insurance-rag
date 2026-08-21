"""OpenAI client wrappers (fast + reasoner models)."""
"""OpenAI wrappers: a lazy client + a structured-output parse helper.

Two models per the split: LLM_MODEL_FAST (gpt-4o-mini) for cheap triage, LLM_MODEL
(the stronger reasoner) for the grounded answer.
"""
from openai import AsyncOpenAI
from pydantic import BaseModel

from config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def parse_structured(model: str, system: str, messages: list[dict], schema: type[BaseModel]):
    """Call the model and parse its reply into `schema`. `messages` is the chat history."""
    resp = await _get_client().beta.chat.completions.parse(
        model=model,
        messages=[{"role": "system", "content": system}, *messages],
        response_format=schema,
    )
    return resp.choices[0].message.parsed