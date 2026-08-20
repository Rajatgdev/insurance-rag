"""Expand precise hits into the full policy neighbourhood — how an underwriter reads.

The reranked core finds the RIGHT clauses. This adds the surrounding context the model
needs to reason correctly, scoped to the insurer(s) the query actually lands on:
  - the insurer's whole-policy General Exclusions (apply to every grant; similarity misses them)
  - sibling chunks of a matched grant's section (completes any split section)

New chunks are tagged by role so the answerer can walk grant -> exceptions -> general
exclusions and cite each. Core hits are never dropped, only added to.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from retrieval.dense_index import Retrieved
from db.queries import fetch_general_exclusions, fetch_section_siblings


def _primary_insurers(core: list[Retrieved], n: int) -> list[str]:
    """Top n insurers by first appearance in the reranked core (focus on the relevant policies)."""
    order: list[str] = []
    for r in core:
        if r.insurer not in order:
            order.append(r.insurer)
    return order[:n]


async def assemble_policy_context(
    session: AsyncSession, core: list[Retrieved],
    primary_insurers: int | None = None, cap: int | None = None,
) -> list[Retrieved]:
    primary_insurers = primary_insurers or settings.PRIMARY_INSURERS
    cap = cap or settings.EXPAND_CAP
    if not core:
        return core

    primaries = _primary_insurers(core, primary_insurers)
    # General exclusions for EVERY insurer with a match: never show insurer X's cover without
    # insurer X's own governing exclusions beside it. Bounded (~2 per insurer), so uncapped.
    all_insurers = list(dict.fromkeys(r.insurer for r in core))

    general = await fetch_general_exclusions(session, all_insurers)
    pairs = list({
        (r.insurer, r.section)
        for r in core
        if r.insurer in primaries and r.section and not r.is_exclusion
    })
    siblings = await fetch_section_siblings(session, pairs) if pairs else []

    seen = {r.chunk_id for r in core}
    extra: list[Retrieved] = []
    for r in general + siblings[:cap]:
        if r.chunk_id not in seen:
            seen.add(r.chunk_id)
            extra.append(r)

    return core + extra