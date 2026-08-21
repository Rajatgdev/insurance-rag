"""Dense retrieval over pgvector (cosine distance). Embeddings already live in Neon.

There is no file index to build/load for dense search — the HNSW index sits in Postgres
(see 001_initial.sql). load_dense() is a light readiness hook for the app lifespan.

Standalone check (needs DATABASE_URL async + OPENAI_API_KEY in .env):
    python -m retrieval.dense_index "is windscreen damage covered?"
"""
from dataclasses import dataclass

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.models import Chunk, Document

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


@dataclass
class Retrieved:
    """One retrieved chunk + its citation metadata. Shared across the retrieval stack."""
    chunk_id: int
    insurer: str
    doc_type: str
    section: str | None
    clause_id: str | None
    is_exclusion: bool
    page: int | None
    content: str
    source_url: str | None
    score: float
    role: str = "match"   # 'match' (core hit) | 'general_exclusion' | 'section' (neighbourhood)


def load_dense() -> None:
    """Nothing to load (index is in Postgres); present for the app lifespan hook."""
    return None


async def embed_query(text: str) -> list[float]:
    resp = await _get_client().embeddings.create(model=settings.EMBED_MODEL, input=[text])
    return resp.data[0].embedding


async def dense_search(session: AsyncSession, query: str, k: int | None = None,
                       insurer: str | None = None) -> list[Retrieved]:
    k = k or settings.RETRIEVAL_TOP_K
    qvec = await embed_query(query)
    dist = Chunk.embedding.cosine_distance(qvec).label("dist")

    # Select scalar columns only — never ship the embedding back.
    stmt = (
        select(
            Chunk.id, Document.insurer, Document.doc_type, Chunk.section, Chunk.clause_id,
            Chunk.is_exclusion, Chunk.page, Chunk.content, Document.source_url, dist,
        )
        .join(Document, Document.id == Chunk.document_id)
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

    q = sys.argv[1] if len(sys.argv) > 1 else "is windscreen damage covered?"

    async def _demo():
        async with async_session() as s:
            results = await dense_search(s, q, k=6)
        print(f"\nquery: {q!r}\n")
        for i, r in enumerate(results, 1):
            tag = " [EXCLUSION]" if r.is_exclusion else ""
            print(f"{i}. {r.insurer} | {r.section} (p{r.page}) score={r.score:.3f}{tag}")
            print(f"   {r.content[:130].strip()}...\n")

    asyncio.run(_demo())