from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import tempfile, os

from db.session import get_db
from models import Document
from schemas import IngestResponse
from services.embeddings import embed
from services.scraper import extract_text, chunk_document

router = APIRouter()

SOURCE_META = {
    "aade": {"category": "ΑΑΔΕ Εγκύκλιος", "law_number": ""},
    "kfe":  {"category": "ΚΦΕ",             "law_number": "ν.4172/2013"},
    "fpa":  {"category": "ΦΠΑ",             "law_number": "ν.2859/2000"},
    "kfd":  {"category": "ΚΦΔ",             "law_number": "ν.4174/2013"},
}


@router.post("/", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    category: str = "aade",
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Dedup check
    stem = os.path.splitext(file.filename)[0]
    existing = await db.scalar(select(Document).where(Document.source == stem).limit(1))
    if existing:
        raise HTTPException(status_code=409, detail=f"'{stem}' already ingested")

    # Write to temp file for pdfplumber
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text = extract_text(tmp_path)
    finally:
        os.unlink(tmp_path)

    meta = {**SOURCE_META.get(category, SOURCE_META["aade"]), "source": stem}
    chunks = chunk_document(text, meta)

    for chunk in chunks:
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
    return IngestResponse(file=file.filename, chunks=len(chunks))
