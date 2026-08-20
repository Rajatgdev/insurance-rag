"""Separate exclusion-retrieval pass — the core insurance-safety mechanism.

"Is X covered?" makes the grant-of-cover clauses dominate the main ranking, pushing the
carve-outs down or off the list. This pass runs an independent cosine search restricted to
is_exclusion chunks, so the exclusions relevant to the query are surfaced GUARANTEED and
merged into the candidate set before reranking. Without it the model reads the grant, says
"yes", and misses the exclusion three pages later.

Standalone check (needs DB + OpenAI):
    python -m retrieval.exclusion_pass "is my windscreen covered?"
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Chunk, Document
from retrieval.dense_index import Retrieved, embed_query


async def exclusion_search(session: AsyncSession, query: str, k: int | None = None,
                           insurer: str | None = None) -> list[Retrieved]:
    k = k or settings.EXCLUSION_TOP_K
    qvec = await embed_query(query)
    dist = Chunk.embedding.cosine_distance(qvec).label("dist")

    stmt = (
        select(
            Chunk.id, Document.insurer, Document.doc_type, Chunk.section, Chunk.clause_id,
            Chunk.is_exclusion, Chunk.page, Chunk.content, Document.source_url, dist,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.is_exclusion.is_(True))
    )
    if insurer:
        stmt = stmt.where(Document.insurer == insurer)
    stmt = stmt.order_by(dist).limit(k)
    rows = (await session.execute(stmt)).all()
    return [
        Retrieved(
            chunk_id=r.id, insurer=r.insurer, doc_type=r.doc_type, section=r.section,
            clause_id=r.clause_id, is_exclusion=r.is_exclusion, page=r.page,
            content=r.content, source_url=r.source_url, score=1.0 - float(r.dist),
        )
        for r in rows
    ]


if __name__ == "__main__":
    import asyncio
    import sys
    from db.session import async_session

    q = sys.argv[1] if len(sys.argv) > 1 else "is my windscreen covered?"

    async def _demo():
        async with async_session() as s:
            results = await exclusion_search(s, q)
        print(f"\nquery: {q!r}   (exclusions only)\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r.insurer} | {r.section} (p{r.page}) score={r.score:.3f}")
            print(f"   {r.content[:130].strip()}...\n")

    asyncio.run(_demo())