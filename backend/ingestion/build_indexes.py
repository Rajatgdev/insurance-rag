"""Build BM25 + dense indexes into data/motor/."""
"""Build the on-disk BM25 index from the chunks in Neon.

Run from backend/ after generate_embeddings:  python -m ingestion.build_indexes

Built from the DB (not chunks.jsonl) so BM25 positions map to real chunk_ids — that's
what lets lexical and dense results fuse on the same key. Saves the bm25s index plus a
chunk_ids.json mapping into settings.BM25_INDEX_PATH.
"""
import json
from pathlib import Path

import bm25s
import psycopg

from config import settings
from ingestion.generate_embeddings import sync_url

BACKEND = Path(__file__).resolve().parent.parent
INDEX_DIR = BACKEND / settings.BM25_INDEX_PATH


def main() -> None:
    with psycopg.connect(sync_url()) as conn:
        rows = conn.execute("SELECT id, content FROM chunks ORDER BY id").fetchall()
    ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]
    print(f"{len(ids)} chunks from Neon")

    tokens = bm25s.tokenize(texts, stopwords="en", show_progress=False)
    retriever = bm25s.BM25()
    retriever.index(tokens, show_progress=False)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    retriever.save(str(INDEX_DIR))
    (INDEX_DIR / "chunk_ids.json").write_text(json.dumps(ids))
    print(f"BM25 index ({len(ids)} docs) -> {INDEX_DIR}")


if __name__ == "__main__":
    main()