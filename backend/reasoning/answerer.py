"""The intern: triage the insurer cheaply, retrieve that policy, then clarify or answer.

Flow per turn:
  1. TRIAGE (fast model, no retrieval): which insurer? what issue?
     - insurer not yet named  -> ask which insurer (stop; cheap)
     - insurer named          -> retrieve scoped to that insurer
  2. REASON (strong model, scoped context): enough facts to answer precisely?
     - no  -> 1-3 narrowing questions grounded in that insurer's exclusions
     - yes -> verdict + cited clauses + confidence, having checked the exclusions

Standalone check (needs DB + OpenAI + BM25 index + reranker):
    python -m reasoning.answerer "my windscreen cracked, am I covered?"
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Document
from personas.loader import load_persona
from reasoning.llm import parse_structured
from reasoning.schemas import CoPilotResponse, Triage
from retrieval.dense_index import Retrieved
from retrieval.pipeline import retrieve


async def known_insurers(session: AsyncSession) -> list[str]:
    rows = (await session.execute(select(Document.insurer).distinct())).all()
    return sorted(r[0] for r in rows)


def _format_context(chunks: list[Retrieved]) -> str:
    lines = []
    for r in chunks:
        role = "EXCLUSION" if r.is_exclusion else r.role
        lines.append(f"[{r.insurer} | {r.section} | p{r.page} | {role}]\n{r.content}")
    return "\n\n---\n\n".join(lines)


def _triage_system(insurers: list[str]) -> str:
    return (
        "You route insurance coverage questions. From the whole conversation, identify:\n"
        f"- insurer: the policy's insurer, but ONLY if the user named one of these exactly: "
        f"{', '.join(insurers)}. If they have not named one, return null.\n"
        "- issue: the coverage topic in a few words.\n"
        "Do not guess an insurer the user hasn't stated."
    )


def _reason_system(persona: str, insurer: str, context: str) -> str:
    return f"""{persona}

You are answering about the customer's {insurer} motor policy. Use ONLY the retrieved
clauses below — never invent cover or exclusions. If the context doesn't settle it, say so.

DECIDE:
- If you cannot answer precisely because facts are missing that would change the outcome
  (type of cover, cause of damage, who was driving, licence, where, repair vs replace, etc.),
  return mode="clarify" with 1-3 questions. Ground each question in an actual exclusion or
  condition below — ask about the things that would flip this from covered to not.
- If you have enough, return mode="answer": state the grant of cover, then the section
  exceptions, then the general exclusions, then conclude. Give a verdict (Covered / Not
  covered / Partial / Unclear), cite each clause (insurer, section, page), list the
  exclusions you checked, and a confidence 0-1. Never say covered without checking exclusions.

RETRIEVED {insurer} POLICY CLAUSES:
{context}"""


async def answer(session: AsyncSession, messages: list[dict], persona: str = "generic") -> CoPilotResponse:
    insurers = await known_insurers(session)

    triage = await parse_structured(settings.LLM_MODEL_FAST, _triage_system(insurers), messages, Triage)

    if not triage.insurer or triage.insurer not in insurers:
        return CoPilotResponse(
            mode="clarify",
            questions=[f"Which insurer is the policy with? ({', '.join(insurers)})"],
        )

    context = _format_context(await retrieve(session, triage.issue, insurer=triage.insurer))
    system = _reason_system(load_persona(persona), triage.insurer, context)
    return await parse_structured(settings.LLM_MODEL, system, messages, CoPilotResponse)


if __name__ == "__main__":
    import asyncio
    import sys
    from db.session import async_session

    async def _repl():
        convo: list[dict] = []
        pending = sys.argv[1] if len(sys.argv) > 1 else input("you: ").strip()
        async with async_session() as s:
            while True:
                convo.append({"role": "user", "content": pending})
                r = await answer(s, convo)

                if r.mode == "clarify":
                    print("\nbot (needs a bit more):")
                    for q in r.questions:
                        print("   -", q)
                    convo.append({"role": "assistant", "content": " ".join(r.questions)})
                    pending = input("\nyou: ").strip()
                    if pending.lower() in {"quit", "exit", "q"}:
                        break
                else:
                    print(f"\nbot verdict: {r.verdict}   (confidence {r.confidence})")
                    print(r.answer or "")
                    for c in r.citations:
                        print(f"   - {c.insurer} | {c.section} p{c.page}: {c.detail}")
                    if r.exclusions_checked:
                        print("   exclusions checked:", "; ".join(r.exclusions_checked))
                    break

    asyncio.run(_repl())