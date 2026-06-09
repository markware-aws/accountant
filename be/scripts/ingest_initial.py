"""
One-time bulk ingest. Point at a folder of PDFs organised by category subfolder.

Usage (inside container):
    docker-compose exec api bash
    python scripts/ingest_initial.py --dir ./docs/kfe

Folder structure expected (be/docs/):
    docs/
    ├── aade/   → category: ΑΑΔΕ Εγκύκλιος
    ├── kfe/    → category: ΚΦΕ  (ν.4172/2013)
    ├── fpa/    → category: ΦΠΑ  (ν.2859/2000)
    └── kfd/    → category: ΚΦΔ  (ν.4174/2013)
"""
import asyncio, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select

from models import Document
from services.embeddings import embed
from services.scraper import extract_text, chunk_document

SOURCE_META = {
    "aade": {"category": "ΑΑΔΕ Εγκύκλιος", "law_number": ""},
    "kfe":  {"category": "ΚΦΕ",             "law_number": "ν.4172/2013"},
    "fpa":  {"category": "ΦΠΑ",             "law_number": "ν.2859/2000"},
    "kfd":  {"category": "ΚΦΔ",             "law_number": "ν.4174/2013"},
}

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql://", "postgresql+asyncpg://"
)
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def ingest_file(path: Path, session: AsyncSession, category: str) -> int:
    stem = path.stem

    # Skip if already ingested
    existing = await session.scalar(select(Document).where(Document.source == stem).limit(1))
    if existing:
        print(f"  skip {path.name} (already ingested)")
        return 0

    text = extract_text(str(path))
    meta = {**SOURCE_META.get(category, SOURCE_META["aade"]), "source": stem}
    chunks = chunk_document(text, meta)

    for chunk in chunks:
        embedding = await embed(chunk["content"])
        session.add(Document(
            source=chunk["source"],
            category=chunk["category"],
            law_number=chunk["law_number"],
            article=chunk["article"],
            content=chunk["content"],
            embedding=embedding,
        ))

    await session.commit()
    print(f"  ✓ {path.name} → {len(chunks)} chunks")
    return len(chunks)


async def main():
    docs_dir = Path(sys.argv[sys.argv.index("--dir") + 1])
    total = 0

    async with Session() as session:
        for pdf_path in sorted(docs_dir.glob("**/*.pdf")):
            category = pdf_path.parent.name
            total += await ingest_file(pdf_path, session, category)

    print(f"\nDone — {total} chunks ingested")


asyncio.run(main())
