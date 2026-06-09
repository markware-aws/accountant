"""
OCR a scanned PDF using Tesseract with Greek language support.
Outputs a plain .txt file next to the original PDF, then ingests it.

Requirements:
    pip install pytesseract pdf2image Pillow
    Tesseract installed with Greek lang pack (ell)
    Poppler installed and on PATH (or set POPPLER_PATH below)

Usage:
    # OCR only — saves a .txt file next to the PDF (inside container)
    docker-compose exec api bash
    python scripts/ocr_pdf.py --file ./docs/kfe/n4172_2013.pdf

    # OCR + ingest directly into the DB
    python scripts/ocr_pdf.py --file ./docs/kfe/n4172_2013.pdf --ingest --category kfe
"""
import asyncio, argparse, sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# --- Config ---
# If Tesseract is not on PATH, set the full path here:
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# If poppler is not on PATH, set the bin directory here.
# Common locations after extracting the zip:
#   r"C:\poppler\Library\bin"
#   r"C:\poppler-24.08.0\bin"
#   r"C:\Program Files\poppler\bin"
POPPLER_PATH = r"C:\Users\spapa\Downloads\poppler-25.12.0\Library\bin"

# Adjust DPI for quality vs speed (300 is standard, 200 is faster for long docs)
DPI = 300


def ocr_pdf(pdf_path: Path) -> str:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

    print(f"Converting {pdf_path.name} to images at {DPI} DPI...")
    pages = convert_from_path(
        str(pdf_path),
        dpi=DPI,
        poppler_path=POPPLER_PATH,
    )
    print(f"  {len(pages)} pages — running OCR (this takes a while for large PDFs)...")

    texts = []
    for i, page in enumerate(pages, 1):
        print(f"  page {i}/{len(pages)}...", end="\r")
        text = pytesseract.image_to_string(page, lang="ell")
        texts.append(text)

    print()
    return "\n".join(texts)


async def ingest_text(text: str, pdf_path: Path, category: str):
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from sqlalchemy import select
    from models import Document
    from services.embeddings import embed
    from services.scraper import chunk_document

    SOURCE_META = {
        "aade": {"category": "ΑΑΔΕ Εγκύκλιος", "law_number": ""},
        "kfe":  {"category": "ΚΦΕ",             "law_number": "ν.4172/2013"},
        "fpa":  {"category": "ΦΠΑ",             "law_number": "ν.2859/2000"},
        "kfd":  {"category": "ΚΦΔ",             "law_number": "ν.4174/2013"},
    }

    db_url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    if "@postgres:" in db_url:
        db_url = db_url.replace("@postgres:", "@localhost:")

    from sqlalchemy.pool import NullPool
    engine = create_async_engine(db_url, poolclass=NullPool)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    stem = pdf_path.stem
    meta = {**SOURCE_META.get(category, SOURCE_META["aade"]), "source": stem}
    chunks = chunk_document(text, meta)

    async with Session() as db:
        existing = await db.scalar(select(Document).where(Document.source == stem).limit(1))
        if existing:
            print(f"  '{stem}' already ingested — skipping")
            return

        for i, chunk in enumerate(chunks, 1):
            print(f"  embedding chunk {i}/{len(chunks)}...", end="\r")
            embedding = await embed(chunk["content"])
            db.add(Document(
                source=chunk["source"],
                category=chunk["category"],
                law_number=chunk["law_number"],
                article=chunk["article"],
                content=chunk["content"],
                embedding=embedding,
            ))

        await db.commit()
        print(f"\n  ✓ {stem} → {len(chunks)} chunks ingested")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to scanned PDF")
    parser.add_argument("--ingest", action="store_true", help="Ingest into DB after OCR")
    parser.add_argument("--category", default="aade", help="aade | kfe | fpa | kfd")
    args = parser.parse_args()

    pdf_path = Path(args.file).resolve()
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    txt_path = pdf_path.with_suffix(".txt")

    # Run OCR
    text = ocr_pdf(pdf_path)
    word_count = len(text.split())
    print(f"Extracted ~{word_count} words")

    # Save .txt alongside the PDF
    txt_path.write_text(text, encoding="utf-8")
    print(f"Saved: {txt_path}")

    if word_count < 100:
        print("⚠  Very few words extracted — check that Greek lang pack is installed")
        print("   Run: tesseract --list-langs   (should include 'ell')")

    if args.ingest:
        asyncio.run(ingest_text(text, pdf_path, args.category))


if __name__ == "__main__":
    main()
