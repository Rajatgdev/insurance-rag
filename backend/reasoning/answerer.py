"""The intern, persona-driven. Triage the policy cheaply, retrieve it, then clarify or answer.

A Persona (personas/registry.py) parameterises the flow:
  - retrieval_mode 'single_insurer' (Ciara, Brian): triage one insurer, scope retrieval to it
  - retrieval_mode 'multi_insurer'  (Darragh): compare across insurers            [step 4]
The persona's operating contract (personas/*.md) carries the clarify-or-answer decision and
the output fields; this module stays persona-agnostic and parses into persona.schema.

Standalone check (needs DB + OpenAI + BM25 index + reranker):
    python -m reasoning.answerer "my windscreen cracked, am I covered?"
    python -m reasoning.answerer "..." brian
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Document
from personas.registry import Persona, get_persona
from reasoning.llm import parse_structured
from reasoning.schemas import PersonaAnswer, Triage, ComparisonTriage
from retrieval.dense_index import Retrieved
from retrieval.pipeline import retrieve
from retrieval.comparison import retrieve_for_comparison


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


def _comparison_triage_system(insurers: list[str]) -> str:
    return (
        "You set up a broker's cross-insurer comparison. From the whole conversation, identify:\n"
        f"- insurers: the insurers the user asked to compare, each EXACTLY one of: "
        f"{', '.join(insurers)}. If the user named none, return an empty list (means compare all).\n"
        "- issue: the coverage topic to compare, in a few words.\n"
        "Only include insurers the user actually named; do not invent any."
    )


def _format_grouped_context(grouped: dict) -> str:
    """Context labelled and grouped by insurer, so the model can align terminology per column."""
    blocks = []
    for insurer, chunks in grouped.items():
        clauses = "\n\n".join(
            f"[{c.section} | p{c.page} | {'EXCLUSION' if c.is_exclusion else c.role}]\n{c.content}"
            for c in chunks
        )
        blocks.append(f"=== {insurer} ===\n{clauses or '(no relevant clauses found)'}")
    return "\n\n".join(blocks)


def _comparison_reason_system(persona: Persona, insurers: list[str], context: str) -> str:
    return f"""{persona.prompt()}

You are comparing the SAME coverage topic across these insurers, in this column order:
{', '.join(insurers)}.
Use ONLY the retrieved clauses below. Each insurer's clauses are grouped under its name; insurers
name and place cover differently, so align them into shared dimensions and compare like with like.
Every cell must be cited (section, page). If an insurer is silent on a dimension, say so and set
is_gap=true. Do not invent cover an insurer's clauses don't show.

Guardrail: {persona.disclaimer}

RETRIEVED CLAUSES BY INSURER:
{context}"""


def _reason_system(persona: Persona, insurer: str, context: str) -> str:
    return f"""{persona.prompt()}

You are reading the {insurer} motor policy wording. Use ONLY the retrieved clauses below —
never invent cover or exclusions. If the context doesn't settle it, say so.

Guardrail: {persona.disclaimer}

RETRIEVED {insurer} POLICY CLAUSES:
{context}"""


async def _answer_single_insurer(session: AsyncSession, messages: list[dict], persona: Persona) -> PersonaAnswer:
    insurers = await known_insurers(session)
    triage = await parse_structured(settings.LLM_MODEL_FAST, _triage_system(insurers), messages, Triage)

    if not triage.insurer or triage.insurer not in insurers:
        return persona.schema(
            mode="clarify",
            questions=[f"Which insurer is the policy with? ({', '.join(insurers)})"],
        )

    context = _format_context(await retrieve(session, triage.issue, insurer=triage.insurer))
    system = _reason_system(persona, triage.insurer, context)
    return await parse_structured(settings.LLM_MODEL, system, messages, persona.schema)


async def _answer_multi_insurer(session: AsyncSession, messages: list[dict], persona: Persona) -> PersonaAnswer:
    known = await known_insurers(session)
    triage = await parse_structured(
        settings.LLM_MODEL_FAST, _comparison_triage_system(known), messages, ComparisonTriage)

    # keep only valid named insurers; none named -> compare all
    chosen = [i for i in triage.insurers if i in known] or known
    if len(chosen) < 2:
        return persona.schema(
            mode="clarify",
            questions=[f"Which insurers should I compare? Name at least two of: {', '.join(known)}."],
        )

    grouped = await retrieve_for_comparison(session, triage.issue, chosen)
    system = _comparison_reason_system(persona, chosen, _format_grouped_context(grouped))
    return await parse_structured(settings.LLM_MODEL, system, messages, persona.schema)


async def answer(session: AsyncSession, messages: list[dict], persona: str = "ciara") -> PersonaAnswer:
    p = get_persona(persona)
    if p.retrieval_mode == "single_insurer":
        return await _answer_single_insurer(session, messages, p)
    if p.retrieval_mode == "multi_insurer":
        return await _answer_multi_insurer(session, messages, p)
    raise NotImplementedError(f"unknown retrieval_mode {p.retrieval_mode!r}")


if __name__ == "__main__":
    import asyncio
    import sys
    from db.session import async_session

    async def _repl():
        args = [a for a in sys.argv[1:]]
        persona = args.pop() if args and args[-1] in ("ciara", "brian", "darragh") else "ciara"
        kind = get_persona(persona).output_kind
        convo: list[dict] = []
        pending = args[0] if args else input("you: ").strip()
        print(f"[persona: {persona}]")
        async with async_session() as s:
            while True:
                convo.append({"role": "user", "content": pending})
                r = await answer(s, convo, persona)

                if r.mode == "clarify":
                    print("\nbot (needs a bit more):")
                    for q in r.questions:
                        print("   -", q)
                    convo.append({"role": "assistant", "content": " ".join(r.questions)})
                    pending = input("\nyou: ").strip()
                    if pending.lower() in {"quit", "exit", "q"}:
                        break
                else:
                    _render(r, kind)
                    break

    def _cites(items):
        for c in items:
            print(f"      - {c.insurer} | {c.section} p{c.page}: {c.detail}")

    def _render(r, kind):
        if kind == "verdict":
            print(f"\nverdict: {r.verdict}   (confidence {r.confidence})")
            print(r.answer or "")
            if r.excess:
                print("   excess:", r.excess)
            _cites(r.citations)
            if r.exclusions_checked:
                print("   exclusions checked:", "; ".join(r.exclusions_checked))
        elif kind == "wording_read":
            print(f"\nwording read   (confidence {r.confidence})")
            print("  summary:", r.summary or "")
            if r.grants:
                print("  grants:")
                for g in r.grants:
                    print("      +", g)
            if r.notable_exclusions:
                print("  notable exclusions:")
                _cites(r.notable_exclusions)
            if r.warranties_conditions:
                print("  warranties/conditions:")
                _cites(r.warranties_conditions)
            if r.gaps:
                print("  gaps:")
                for g in r.gaps:
                    print("      !", g)
            if r.endorsements_plain:
                print("  endorsements:")
                for e in r.endorsements_plain:
                    print("      ~", e)
        else:
            # comparison (Darragh)
            print(f"\ncomparison: {r.topic}   (confidence {r.confidence})")
            cols = r.insurers
            print("  insurers:", " | ".join(cols))
            for row in r.rows:
                print(f"\n  · {row.dimension}")
                for cell in row.cells:
                    gap = "  [GAP]" if cell.is_gap else ""
                    src = f" ({cell.section} p{cell.page})" if cell.section else ""
                    print(f"      {cell.insurer}: {cell.value}{src}{gap}")
            if r.gaps:
                print("\n  gaps to raise:")
                for g in r.gaps:
                    print("      !", g)
            if r.summary:
                print("\n  summary:", r.summary)

    asyncio.run(_repl())