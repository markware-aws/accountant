from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from db.session import get_db
from models import Conversation, Message
from schemas import ConversationRead, ConversationSummary

router = APIRouter()


@router.get("/list", response_model=list[ConversationSummary])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.created_at.desc()).limit(50)
    )
    conversations = result.scalars().all()

    summaries = []
    for conv in conversations:
        first_msg = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id, Message.role == "user")
            .order_by(Message.created_at)
            .limit(1)
        )
        msg = first_msg.scalar_one_or_none()
        preview = (msg.content[:80] + "…") if msg and len(msg.content) > 80 else (msg.content if msg else "Νέα συνομιλία")
        summaries.append({"id": conv.id, "created_at": conv.created_at, "preview": preview})

    return summaries


@router.get("/", response_model=ConversationRead)
async def get_history(session: UUID, db: AsyncSession = Depends(get_db)):
    conv = await db.get(Conversation, session)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == session)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    return {
        "id": conv.id,
        "created_at": conv.created_at,
        "messages": messages,
    }
