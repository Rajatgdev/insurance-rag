-- Motor Insurance Co-Pilot — initial schema
CREATE EXTENSION IF NOT EXISTS vector;

-- One row per source document (policy wording or IPID)
CREATE TABLE IF NOT EXISTS documents (
    id            SERIAL PRIMARY KEY,
    insurer       TEXT NOT NULL,
    doc_type      TEXT NOT NULL,          -- 'wording' | 'ipid'
    title         TEXT,
    version_date  DATE,
    source_url    TEXT,
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- Structure-aware chunks (clause / sub-clause granularity)
CREATE TABLE IF NOT EXISTS chunks (
    id            SERIAL PRIMARY KEY,
    document_id   INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    section       TEXT,                   -- e.g. 'Section 4 - Liability to Others'
    clause_id     TEXT,                   -- e.g. '4.1'
    is_exclusion  BOOLEAN DEFAULT FALSE,  -- drives the separate exclusion-retrieval pass
    page          INTEGER,                -- source page, for citations
    content       TEXT NOT NULL,
    embedding     VECTOR(1536)            -- text-embedding-3-small
);

CREATE INDEX IF NOT EXISTS idx_chunks_document   ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_exclusion  ON chunks(is_exclusion);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding  ON chunks
    USING hnsw (embedding vector_cosine_ops);
