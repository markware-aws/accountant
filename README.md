# accountantAI

Greek tax law assistant with a FastAPI backend (RAG over pgvector) and a Next.js static frontend.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (for the API and database)
- [Node.js](https://nodejs.org/) 20+ and npm (for the frontend)
- API keys for at least one LLM provider (OpenAI or Anthropic), plus Supabase and Resend if you use auth/email features

## Project structure

```
accountantAI/
├── be/          FastAPI API, Postgres/pgvector, ingestion scripts
├── fe/          Next.js frontend (static export)
├── examples/    Separate myDATA reference project (has its own git repo)
└── docs/        Planning notes and API references at the repo root
```

## Quick start

### 1. Backend

```bash
cd be
cp .env.example .env
```

Edit `.env` with your keys. For Docker Compose, set `DATABASE_URL` to the compose hostname:

```
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/accountant
```

Start Postgres and the API:

```bash
docker-compose up
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The database schema is applied automatically from `be/db/init.sql` on first run.

#### Running the API without Docker

If you already have Postgres with pgvector running locally:

```bash
cd be
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Set `DATABASE_URL` to your local instance (e.g. `postgresql://postgres:postgres@localhost:5432/accountant`), apply `db/init.sql`, then:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

In a second terminal:

```bash
cd fe
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

### 3. Connect frontend to backend

Ensure `fe/.env.local` points at the running API:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## Environment variables

### Backend (`be/.env`)

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | `dev` uses OpenAI; `prod` uses Anthropic |
| `OPENAI_API_KEY` | Required when `ENVIRONMENT=dev` |
| `ANTHROPIC_API_KEY` | Required when `ENVIRONMENT=prod` |
| `DATABASE_URL` | Postgres connection string |
| `RESEND_API_KEY` | Magic link / transactional email |
| `EMAIL_FROM` | Sender address for Resend |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `MYDATA_SANDBOX` | `true` for sandbox myDATA API (default) |

See `be/.env.example` for a full template.

### Frontend (`fe/.env.local`)

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | FastAPI backend URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/public key |

All frontend env vars must use the `NEXT_PUBLIC_` prefix (static export has no server-side env).

## Common tasks

**Ingest PDFs (bulk):**

```bash
cd be
python scripts/ingest_initial.py
```

**Debug retrieval:**

```
http://localhost:8000/chat/debug/retrieve?q=your+query
```

**Production frontend build:**

```bash
cd fe
npm run build
```

Static files are written to `fe/out/` for deployment to S3, CloudFront, or any static host.

## Further reading

- `be/CLAUDE.md` — backend architecture, Lambda deployment, ingestion
- `fe/CLAUDE.md` — frontend conventions, SWR vs SSE, static export rules
- `myDATA_REST_API.md` — myDATA API reference
