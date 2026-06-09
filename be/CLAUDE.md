# Backend — Claude Code Guide

FastAPI backend for accountantAI. Greek tax law RAG assistant.

## Stack

- **Python 3.12**, FastAPI, Mangum (Lambda handler)
- **ORM**: SQLAlchemy async (`postgresql+asyncpg://`), NullPool
- **Vector DB**: pgvector — similarity search via `cosine_distance()` ORM operator
- **LLM**: `ENVIRONMENT=dev` → OpenAI `gpt-4o-mini` | `ENVIRONMENT=prod` → Anthropic `claude-sonnet-4-6`
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dims) — same in both environments
- **Email**: Resend

## Running locally

```bash
# From be/
cp .env.example .env   # fill in keys
docker-compose up      # starts postgres (pgvector:pg16) + api on :8000
```

API docs: http://localhost:8000/docs
Debug retrieval: http://localhost:8000/chat/debug/retrieve?q=your+query

## Critical rules

**NullPool is mandatory** — never remove it from `db/session.py`. Lambda is stateless; the default SQLAlchemy pool leaks connections.

**Never hallucinate citations** — `SIMILARITY_THRESHOLD = 0.75` in `services/retrieval.py` gates every response. If no chunks clear the threshold, the chat router returns a "not found" message instead of calling the LLM.

**All ORM models go in `models.py`** — one file, no exceptions.

**All Pydantic schemas go in `schemas.py`** — one file, no exceptions.

## Key files

| File | Purpose |
|---|---|
| `main.py` | App factory, CORS, router registration |
| `handler.py` | Mangum Lambda entry point (`InvokeMode: RESPONSE_STREAM`) |
| `models.py` | SQLAlchemy models — `Document` |
| `schemas.py` | Pydantic schemas — `ChatRequest`, `Source`, `DocumentCreate`, etc. |
| `db/session.py` | Async engine with NullPool, `get_db()` dependency |
| `db/init.sql` | Schema + pgvector extension. ivfflat index is commented out — enable in prod at ≥1000 rows |
| `services/retrieval.py` | Vector search using `Document.embedding.cosine_distance()` |
| `services/llm.py` | Claude streaming — `stream_response()` async generator |
| `services/embeddings.py` | OpenAI embed — `embed(text)` |
| `services/email.py` | Resend — `send_magic_link()`, `send_welcome()` |
| `services/scraper.py` | PDF text extraction + article-boundary chunking |
| `routers/chat.py` | `POST /chat/` SSE stream + `GET /chat/debug/retrieve` |
| `routers/ingest.py` | `POST /ingest/` PDF upload with dedup check |
| `routers/auth.py` | Resend magic link hook for Supabase Auth |
| `scripts/ingest_initial.py` | Bulk ingest from local PDF folder |
| `scripts/update_corpus.py` | Weekly AADE news page scraper |

## DATABASE_URL note

Inside Docker Compose the hostname is the service name `postgres`.
For scripts run outside Docker use `localhost:5432`.

## Lambda deployment

- Deploy as container image (avoids asyncpg native binary issues)
- Lambda Function URL with `InvokeMode: RESPONSE_STREAM` — required for SSE
- Set timeout ≥ 60s, memory ≥ 512MB
- `handler.py` is the entry point (`handler.handler`)

## Migrations

Local dev uses `db/init.sql` via Docker Compose.
Before production: `alembic init migrations`, generate from `models.py`, run against Supabase.
Alembic uses plain `postgresql://` (psycopg2) — not asyncpg.
