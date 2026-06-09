import uuid
from sqlalchemy import Column, Text, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source       = Column(Text, nullable=False)
    category     = Column(Text)
    law_number   = Column(Text)
    article      = Column(Text)
    published_at = Column(Date)
    content      = Column(Text, nullable=False)
    embedding    = Column(Vector(1536))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role            = Column(Text, nullable=False)   # "user" | "assistant"
    content         = Column(Text, nullable=False)
    sources         = Column(JSONB, nullable=False, default=list)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
