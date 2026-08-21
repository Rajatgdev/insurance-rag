"""Hybrid retrieval: dense (pgvector) + BM25, fused with Reciprocal Rank Fusion.

RRF fuses by RANK, not score, so incomparable cosine/BM25 magnitudes never need
normalizing. Output is a fused candidate pool for the reranker to narrow.

Standalone check (needs DB + OpenAI + built BM25 index):
    python -m retrieval.hybrid "is windscreen replacement covered and what's the excess?"
"""
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from retrieval.dense_index import Retrieved, dense_search
from retrieval.bm25_index import bm25_search

RRF_K = 60


def rrf_fuse(dense_ids: list[int], lexical_ids: list[int], k: int,
             rrf_k: int = RRF_K) -> list[tuple[int, float]]:
    """Pure fusion: sum 1/(rrf_k + rank) across both ranked id lists. Top-k by fused score."""
    scores: dict[int, float] = {}
    for rank, cid in enumerate(dense_ids):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank)
    for rank, cid in enumerate(lexical_ids):
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]


async def hybrid_search(session: AsyncSession, query: str, k: int | None = None,
                        insurer: str | None = None) -> list[Retrieved]:
    k = k or settings.RETRIEVAL_TOP_K
    pool = settings.RETRIEVAL_TOP_K

    dense = await dense_search(session, query, k=pool, insurer=insurer)
    lexical = bm25_search(query, k=pool)

    fused = rrf_fuse([r.chunk_id for r in dense], [cid for cid, _ in lexical], k=k)

    dense_map = {r.chunk_id: r for r in dense}
    missing = [cid for cid, _ in fused if cid not in dense_map]
    if missing:
        from db.queries import fetch_by_ids
        dense_map.update(await fetch_by_ids(session, missing))

    out: list[Retrieved] = []
    for cid, score in fused:
        r = dense_map.get(cid)
        if r is not None and (insurer is None or r.insurer == insurer):  # drop cross-insurer BM25 hits
            r.score = score
            out.append(r)
    return out


if __name__ == "__main__":
    import asyncio
    import sys
    from db.session import async_session

    q = sys.argv[1] if len(sys.argv) > 1 else "is windscreen replacement covered and what's the excess?"

    async def _demo():
        async with async_session() as s:
            results = await hybrid_search(s, q, k=8)
        print(f"\nquery: {q!r}\n")
        for i, r in enumerate(results, 1):
            tag = " [EXCLUSION]" if r.is_exclusion else ""
            print(f"{i}. {r.insurer} | {r.section} (p{r.page}) rrf={r.score:.4f}{tag}")
            print(f"   {r.content[:120].strip()}...\n")

    asyncio.run(_demo())