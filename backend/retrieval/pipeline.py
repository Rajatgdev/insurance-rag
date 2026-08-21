"""Retrieval entry point: hybrid + forced exclusions -> dedup -> cross-encoder rerank.

This is the single function the API/answerer call. The exclusion pass guarantees carve-outs
are in the candidate pool; the reranker keeps whichever are actually relevant to the query.

Standalone check (needs DB + OpenAI + BM25 index + reranker model):
    python -m retrieval.pipeline "is windscreen replacement covered and what's the excess?"
"""
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from retrieval.dense_index import Retrieved
from retrieval.hybrid import hybrid_search
from retrieval.exclusion_pass import exclusion_search
from retrieval.reranker import rerank
from retrieval.expand import assemble_policy_context


def _guarantee_exclusions(ranked: list[Retrieved], top_k: int, reserved: int) -> list[Retrieved]:
    """Ensure the final top_k contains >= `reserved` exclusion chunks (if the pool has them).

    ranked is the full candidate list sorted by rerank score (desc). If the natural top_k
    is short on exclusions, swap the highest-reranked exclusions from below the cutoff in for
    the lowest-scoring NON-exclusions in the cutoff, then re-sort by score. This is the
    safety core: a coverage answer must never reach the model without its carve-outs.
    """
    top = ranked[:top_k]
    have = sum(r.is_exclusion for r in top)
    if have >= reserved:
        return top

    below_exclusions = [r for r in ranked[top_k:] if r.is_exclusion][: reserved - have]
    if not below_exclusions:
        return top  # pool simply has no more exclusions to add

    non_excl_idx = [i for i, r in enumerate(top) if not r.is_exclusion]
    drop = set(non_excl_idx[-len(below_exclusions):])          # weakest non-exclusions
    kept = [r for i, r in enumerate(top) if i not in drop]
    final = kept + below_exclusions
    final.sort(key=lambda r: r.score, reverse=True)
    return final


async def _core(session: AsyncSession, query: str, top_k: int, insurer: str | None = None) -> list[Retrieved]:
    """Precise core: hybrid + forced exclusions -> rerank -> guarantee exclusions survive."""
    hybrid = await hybrid_search(session, query, insurer=insurer)
    exclusions = await exclusion_search(session, query, insurer=insurer)

    seen = {r.chunk_id for r in hybrid}
    candidates = hybrid + [r for r in exclusions if r.chunk_id not in seen]

    ranked = rerank(query, candidates, top_k=len(candidates))
    return _guarantee_exclusions(ranked, top_k, settings.EXCLUSION_MIN_IN_CONTEXT)


async def retrieve(session: AsyncSession, query: str, top_k: int | None = None,
                   insurer: str | None = None) -> list[Retrieved]:
    """Full retrieval: the precise core, expanded into its policy neighbourhood.

    Pass insurer to scope everything to one policy (cheaper context, sharper recall)."""
    core = await _core(session, query, top_k or settings.RERANK_TOP_K, insurer=insurer)
    return await assemble_policy_context(session, core)


if __name__ == "__main__":
    import asyncio
    import sys
    from db.session import async_session

    q = sys.argv[1] if len(sys.argv) > 1 else "is windscreen replacement covered and what's the excess?"

    async def _demo():
        async with async_session() as s:
            results = await retrieve(s, q)
        print(f"\nquery: {q!r}   (core + policy neighbourhood)\n")
        for i, r in enumerate(results, 1):
            tag = " [EXCLUSION]" if r.is_exclusion else ""
            print(f"{i}. [{r.role}] {r.insurer} | {r.section} (p{r.page}){tag}")
            print(f"   {r.content[:110].strip()}...\n")

    asyncio.run(_demo())