"""Fair multi-insurer retrieval for the broker (Darragh).

A single un-scoped pull over-represents whichever insurer ranks highest, so a comparison
could silently omit an insurer. Instead we run the existing scoped `retrieve()` once PER
insurer (small k each, its own general exclusions ride along) and merge — every insurer gets
equal footing. Results are grouped by insurer so the reasoning step can align terminology and
compare like with like.
"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from retrieval.dense_index import Retrieved
from retrieval.pipeline import retrieve


async def retrieve_for_comparison(
    session: AsyncSession, issue: str, insurers: list[str], per_insurer_k: int | None = None,
) -> dict[str, list[Retrieved]]:
    """Retrieve `issue` scoped to each insurer; return {insurer: chunks} preserving input order."""
    per_insurer_k = per_insurer_k or settings.COMPARE_PER_INSURER_K

    async def one(ins: str) -> tuple[str, list[Retrieved]]:
        return ins, await retrieve(session, issue, top_k=per_insurer_k, insurer=ins)

    results = await asyncio.gather(*(one(ins) for ins in insurers))
    # gather preserves order of the awaitables, so column order == input insurer order
    return {ins: chunks for ins, chunks in results}