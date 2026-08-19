# Motor Insurance Co-Pilot

An AI co-pilot for insurance professionals, case study: **Irish private motor**. Custom RAG
over motor policy wordings + IPIDs, with three expert personas (underwriter, claims assessor,
broker) over one shared retrieval pipeline.

Structure mirrors the HSC2-OKF reference: FastAPI backend on Railway, Postgres + pgvector on
Neon, Next.js + Tailwind frontend on Vercel.

## Pipeline

```
Query → expansion (gpt-4o-mini) → ┬─ BM25 ──┬→ RRF → rerank ─┐
                                  └─ dense ─┘                 ├→ grounded answer (gpt-4.1)
                     + separate exclusion-retrieval pass ─────┘   citations + confidence + fallback
```

## Structure

```
backend/                Railway
  config.py             env/settings (Pydantic BaseSettings singleton)
  main.py               FastAPI app + CORS + lifespan index load
  api/                  chat.py (/query, /persona/{id}), health.py
  db/                   session.py (Neon SSL), models.py, queries.py, 001_initial.sql
  ingestion/            fetch_docs → ingest_policies → generate_embeddings → build_indexes
  retrieval/            bm25 + dense + hybrid(RRF) + exclusion_pass + reranker + expansion
  reasoning/            answerer (grounded, cited), llm, schemas
  personas/             brian.md, ciara.md, darragh.md + loader
  data/motor/           built indexes (raw PDFs gitignored)
frontend/               Vercel — Next.js + Tailwind
  app/ components/ lib/api.ts
```

## Secrets

Same convention as HSC2-OKF: config values live in `config.py` as defaults; real secrets go in
`backend/.env` (gitignored). Copy the template:

```bash
cd backend
cp .env.example .env       # fill DATABASE_URL, DATABASE_URL_SYNC, OPENAI_API_KEY
```

Never commit `.env`. `.gitignore` already blocks `.env`, `backend/.env`, and raw data files.

## Quick start

```bash
# backend
cd backend
pip install -r requirements.txt
cp .env.example .env        # then edit
python -m ingestion.fetch_docs
python -m ingestion.ingest_policies
python -m ingestion.generate_embeddings
python -m ingestion.build_indexes
uvicorn main:app --reload

# frontend
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Deploy

Frontend → Vercel (set `NEXT_PUBLIC_API_URL`). Backend → Railway (set `DATABASE_URL`,
`DATABASE_URL_SYNC`, `OPENAI_API_KEY`, `CORS_ORIGINS`). DB → Neon (Postgres + pgvector).
