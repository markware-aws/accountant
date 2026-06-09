import json
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db, AsyncSessionLocal
from models import Conversation, Message
from schemas import ChatRequest, Source
from services.retrieval import retrieve, SIMILARITY_THRESHOLD
from services.llm import stream_response

router = APIRouter()


async def _get_or_create_conversation(
    conversation_id, db: AsyncSession
) -> Conversation:
    if conversation_id:
        conv = await db.get(Conversation, conversation_id)
        if conv:
            return conv
    conv = Conversation()
    db.add(conv)
    await db.flush()  # populate conv.id without committing
    return conv


@router.post("/")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    chunks = await retrieve(req.question, db)
    good_chunks = [c for c in chunks if c["similarity"] >= SIMILARITY_THRESHOLD]

    # Get or create conversation and save user message before streaming
    conv = await _get_or_create_conversation(req.conversation_id, db)
    db.add(Message(
        conversation_id=conv.id,
        role="user",
        content=req.question,
        sources=[],
    ))
    await db.commit()

    if not good_chunks:
        no_source_msg = "Δεν βρέθηκε σαφής πηγή στη βάση νομοθεσίας για την ερώτησή σας."

        async def no_source():
            yield f"data: {json.dumps({'type': 'conversation_id', 'id': str(conv.id)})}\n\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': no_source_msg})}\n\n"
            yield "data: [DONE]\n\n"
            # Save assistant message
            async with AsyncSessionLocal() as save_db:
                save_db.add(Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=no_source_msg,
                    sources=[],
                ))
                await save_db.commit()

        return StreamingResponse(no_source(), media_type="text/event-stream")

    context = "\n\n---\n\n".join(
        f"Πηγή: {c['source']} | {c['law_number']} {c['article']}\n{c['content']}"
        for c in good_chunks
    )
    sources = [
        Source(source=c["source"], law=c["law_number"], article=c["article"])
        for c in good_chunks
    ]
    sources_payload = [s.model_dump() for s in sources]
    history = [m.model_dump() for m in req.history]

    async def generate():
        yield f"data: {json.dumps({'type': 'conversation_id', 'id': str(conv.id)})}\n\n"
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_payload})}\n\n"

        full_response = []
        async for token in stream_response(req.question, context, history):
            full_response.append(token)
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        yield "data: [DONE]\n\n"

        # Save assistant message after stream completes
        async with AsyncSessionLocal() as save_db:
            save_db.add(Message(
                conversation_id=conv.id,
                role="assistant",
                content="".join(full_response),
                sources=sources_payload,
            ))
            await save_db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/debug/retrieve")
async def debug_retrieve(q: str, db: AsyncSession = Depends(get_db)):
    """Returns raw chunks + similarity scores. Use during development to tune retrieval."""
    chunks = await retrieve(q, db)
    return {"query": q, "chunks": chunks}
