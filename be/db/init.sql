CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE conversations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE messages (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content         TEXT NOT NULL,
  sources         JSONB NOT NULL DEFAULT '[]',
  created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON messages (conversation_id, created_at);

CREATE TABLE documents (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source       TEXT NOT NULL,
  category     TEXT,
  law_number   TEXT,
  article      TEXT,
  published_at DATE,
  content      TEXT NOT NULL,
  embedding    vector(1536),
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- Uncomment once corpus reaches ≥1000 rows
-- CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
