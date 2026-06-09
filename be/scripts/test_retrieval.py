"""
Sanity check for vector retrieval. Run after ingest to verify chunk quality
before building the chat UI.

Usage:
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/accountant \
    OPENAI_API_KEY=sk-... \
    python be/scripts/test_retrieval.py
"""
import asyncio, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Patch DATABASE_URL for scripts running outside Docker (localhost not postgres)
db_url = os.getenv("DATABASE_URL", "")
if "@postgres:" in db_url:
    db_url = db_url.replace("@postgres:", "@localhost:")
    os.environ["DATABASE_URL"] = db_url

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from services.retrieval import retrieve, SIMILARITY_THRESHOLD

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql://", "postgresql+asyncpg://"
)
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

TEST_QUERIES = [
    "ποια η προθεσμία υποβολής δήλωσης ΦΠΑ",
    "συντελεστής φόρου εισοδήματος ΑΕ",
    "πρόστιμο εκπρόθεσμης υποβολής",
    "τι είναι το myDATA",
    "αποσβέσεις παγίων στοιχείων",
]


async def main():
    async with Session() as db:
        for query in TEST_QUERIES:
            print(f"\n{'=' * 60}")
            print(f"Query: {query}")
            print(f"{'=' * 60}")

            chunks = await retrieve(query, db, top_k=3)

            if not chunks:
                print("  ✗ No results — is the DB empty?")
                continue

            for i, c in enumerate(chunks, 1):
                marker = "✓" if c["similarity"] >= SIMILARITY_THRESHOLD else "✗"
                print(f"\n  [{i}] {marker} similarity={c['similarity']:.3f}")
                print(f"       source: {c['source']} | {c['law_number']} {c['article']}")
                print(f"       text:   {c['content'][:200]}...")

    above = 0
    print(f"\nThreshold: {SIMILARITY_THRESHOLD}")
    print("Good: scores ≥ 0.75, chunks clearly relate to query, correct law numbers")
    print("Bad:  scores < 0.60, off-topic chunks, missing law refs → tune chunk_document()")


asyncio.run(main())
