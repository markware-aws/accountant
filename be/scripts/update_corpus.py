"""
Polls AADE news page for new circulars and ingests any not already in the DB.
Run weekly via cron or Lambda EventBridge.

Usage:
    DATABASE_URL=postgresql://... python be/scripts/update_corpus.py
"""
import asyncio, os, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import select

from models import Document
from services.embeddings import embed
from services.scraper import extract_text, chunk_document

AADE_NEWS_URL = "https://www.aade.gr/menoy/nea-anakoinoseis"
SOURCE_META = {"category": "ΑΑΔΕ Εγκύκλιος", "law_number": ""}

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql://", "postgresql+asyncpg://"
)
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def fetch_new_circulars() -> list[dict]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(AADE_NEWS_URL, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    return [
        {"url": link["href"], "title": link.get_text(strip=True)}
        for link in soup.select("a[href$='.pdf']")
    ]


async def main():
    docs = await fetch_new_circulars()
    print(f"Found {len(docs)} documents on AADE news page")

    async with Session() as session:
        async with httpx.AsyncClient(follow_redirects=True) as http:
            for doc in docs:
                url = doc["url"]
                source = Path(url).stem

                existing = await session.scalar(
                    select(Document).where(Document.source == source).limit(1)
                )
                if existing:
                    continue

                print(f"  Downloading {source}...")
                r = await http.get(url, timeout=30)
                if r.status_code != 200:
                    print(f"  ✗ failed ({r.status_code})")
                    continue

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(r.content)
                    tmp_path = tmp.name

                try:
                    text = extract_text(tmp_path)
                finally:
                    os.unlink(tmp_path)

                chunks = chunk_document(text, {**SOURCE_META, "source": source})
                for chunk in chunks:
                    embedding = await embed(chunk["content"])
                    session.add(Document(**{k: chunk[k] for k in chunk}, embedding=embedding))

                await session.commit()
                print(f"  ✓ {source} → {len(chunks)} chunks")


asyncio.run(main())
