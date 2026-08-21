"""Async query helpers shared by the retrieval stack."""
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Chunk, Document
from retrieval.dense_index import Retrieved

_COLS = (
    Chunk.id, Document.insurer, Document.doc_type, Chunk.section, Chunk.clause_id,
    Chunk.is_exclusion, Chunk.page, Chunk.content, Document.source_url,
)


def _row_to_retrieved(r, role: str) -> Retrieved:
    return Retrieved(
        chunk_id=r.id, insurer=r.insurer, doc_type=r.doc_type, section=r.section,
        clause_id=r.clause_id, is_exclusion=r.is_exclusion, page=r.page,
        content=r.content, source_url=r.source_url, score=0.0, role=role,
    )


async def fetch_by_ids(session: AsyncSession, ids: list[int]) -> dict[int, Retrieved]:
    """Load citation metadata for chunk ids (e.g. BM25-only hits). score left 0.0."""
    if not ids:
        return {}
    stmt = select(*_COLS).join(Document, Document.id == Chunk.document_id).where(Chunk.id.in_(ids))
    rows = (await session.execute(stmt)).all()
    return {r.id: _row_to_retrieved(r, "match") for r in rows}


async def fetch_general_exclusions(session: AsyncSession, insurers: list[str]) -> list[Retrieved]:
    """Whole-policy General Exclusions/Exceptions for the given insurers — these apply to every
    grant and similarity reliably misses them. The structural grant -> governing-exclusion link."""
    if not insurers:
        return []
    stmt = (
        select(*_COLS)
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Document.insurer.in_(insurers),
            Chunk.is_exclusion.is_(True),
            or_(Chunk.section.ilike("%general exclusion%"), Chunk.section.ilike("%general exception%")),
        )
    )
    rows = (await session.execute(stmt)).all()
    return [_row_to_retrieved(r, "general_exclusion") for r in rows]


async def fetch_section_siblings(session: AsyncSession, pairs: list[tuple[str, str]]) -> list[Retrieved]:
    """Other chunks in the same (insurer, section) as a matched grant — completes split sections."""
    if not pairs:
        return []
    conds = [and_(Document.insurer == ins, Chunk.section == sec) for ins, sec in pairs]
    stmt = select(*_COLS).join(Document, Document.id == Chunk.document_id).where(or_(*conds))
    rows = (await session.execute(stmt)).all()
    return [_row_to_retrieved(r, "section") for r in rows]