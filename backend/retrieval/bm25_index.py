"""BM25 lexical index load/query."""
"""BM25 lexical retrieval. Loads the on-disk index built by ingestion.build_indexes.

Returns (chunk_id, score) pairs — metadata is fetched later by the hybrid layer, keeping
this module a pure lexical scorer. Catches exact legal terms embeddings blur
("territorial limits", "excess", a specific euro limit).

Standalone check (needs the built index + DATABASE_URL_SYNC for the demo's content lookup):
    python -m retrieval.bm25_index "territorial limits outside Ireland"
"""
import json
from pathlib import Path

import bm25s

from config import settings

BACKEND = Path(__file__).resolve().parent.parent
INDEX_DIR = BACKEND / settings.BM25_INDEX_PATH

_retriever: bm25s.BM25 | None = None
_chunk_ids: list[int] | None = None


def load_bm25() -> bm25s.BM25:
    global _retriever, _chunk_ids
    _retriever = bm25s.BM25.load(str(INDEX_DIR), load_corpus=False)
    _chunk_ids = json.loads((INDEX_DIR / "chunk_ids.json").read_text())
    return _retriever


def bm25_search(query: str, k: int | None = None) -> list[tuple[int, float]]:
    k = k or settings.RETRIEVAL_TOP_K
    if _retriever is None or _chunk_ids is None:
        load_bm25()
    tokens = bm25s.tokenize(query, stopwords="en", show_progress=False)
    idxs, scores = _retriever.retrieve(tokens, k=min(k, len(_chunk_ids)), show_progress=False)
    return [(_chunk_ids[int(pos)], float(scores[0][j])) for j, pos in enumerate(idxs[0])]


if __name__ == "__main__":
    import sys
    import psycopg
    from ingestion.generate_embeddings import sync_url

    q = sys.argv[1] if len(sys.argv) > 1 else "territorial limits outside Ireland"
    hits = bm25_search(q, k=6)
    ids = [cid for cid, _ in hits]
    with psycopg.connect(sync_url()) as conn:
        rows = {r[0]: (r[1], r[2], r[3]) for r in conn.execute(
            "SELECT c.id, d.insurer, c.section, c.content FROM chunks c "
            "JOIN documents d ON d.id=c.document_id WHERE c.id = ANY(%s)", (ids,))}
    print(f"\nquery: {q!r}\n")
    for i, (cid, score) in enumerate(hits, 1):
        insurer, section, content = rows.get(cid, ("?", "?", ""))
        print(f"{i}. {insurer} | {section} score={score:.2f}")
        print(f"   {content[:130].strip()}...\n")