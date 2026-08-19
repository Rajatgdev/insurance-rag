"""Generate embeddings (text-embedding-3-small) for chunks."""
"""Embed chunks.jsonl -> Neon (documents + chunks with pgvector).

Run from backend/:  python -m ingestion.generate_embeddings

Order is deliberate so a failure never leaves you half-loaded or overcharged:
  1. connect + apply schema (cheap)      -> bad DATABASE_URL fails here, before any OpenAI spend
  2. embed every chunk in memory         -> bad OPENAI_API_KEY fails here, before any DB writes
  3. reconnect, truncate, insert         -> full reload, idempotent (re-run = clean state)

Needs backend/.env: DATABASE_URL_SYNC, OPENAI_API_KEY.
"""
import json
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from openai import OpenAI

from config import settings

DATA = Path(__file__).resolve().parent.parent / "data" / "motor"
CHUNKS = DATA / "chunks.jsonl"
SCHEMA = Path(__file__).resolve().parent.parent / "db" / "001_initial.sql"
BATCH = 100


def sync_url() -> str:
    url = settings.DATABASE_URL_SYNC
    if "neon.tech" in url and "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def apply_schema() -> None:
    with psycopg.connect(sync_url()) as conn:
        for stmt in SCHEMA.read_text().split(";"):
            if stmt.strip():
                conn.execute(stmt)
        conn.commit()
    print("  schema applied / verified")


def embed_all(client: OpenAI, texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        resp = client.embeddings.create(model=settings.EMBED_MODEL, input=texts[i:i + BATCH])
        out.extend(d.embedding for d in resp.data)
        print(f"  embedded {min(i + BATCH, len(texts))}/{len(texts)}")
    return out


def main() -> None:
    rows = [json.loads(l) for l in CHUNKS.open()]
    print(f"{len(rows)} chunks from {CHUNKS.name}")

    # 1. validate DB + schema before spending anything
    apply_schema()

    # 2. embed in memory (fails before any DB write if the key is bad)
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    embeddings = embed_all(client, [r["content"] for r in rows])

    # 3. reconnect, fresh load
    with psycopg.connect(sync_url()) as conn:
        register_vector(conn)
        conn.execute("TRUNCATE chunks, documents RESTART IDENTITY CASCADE;")

        doc_ids: dict[tuple, int] = {}
        for r in rows:
            key = (r["insurer"], r["source_url"])
            if key not in doc_ids:
                cur = conn.execute(
                    "INSERT INTO documents (insurer, doc_type, title, version_date, source_url) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (r["insurer"], r["doc_type"], None, r["version_date"], r["source_url"]),
                )
                doc_ids[key] = cur.fetchone()[0]

        for r, emb in zip(rows, embeddings):
            conn.execute(
                "INSERT INTO chunks (document_id, section, clause_id, is_exclusion, page, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (doc_ids[(r["insurer"], r["source_url"])], r["section"], r["clause_id"],
                 r["is_exclusion"], r.get("page"), r["content"], emb),
            )
        conn.commit()

        n_doc = conn.execute("SELECT count(*) FROM documents").fetchone()[0]
        n_ch = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
        n_ex = conn.execute("SELECT count(*) FROM chunks WHERE is_exclusion").fetchone()[0]

    print(f"\nloaded: documents={n_doc}  chunks={n_ch}  exclusion={n_ex}")


if __name__ == "__main__":
    main()