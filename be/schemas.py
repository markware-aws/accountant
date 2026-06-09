from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from uuid import UUID


# --- Document ---

class DocumentCreate(BaseModel):
    source: str
    category: Optional[str] = None
    law_number: Optional[str] = None
    article: Optional[str] = None
    published_at: Optional[date] = None
    content: str
    embedding: list[float]


class DocumentRead(BaseModel):
    id: UUID
    source: str
    category: Optional[str]
    law_number: Optional[str]
    article: Optional[str]
    published_at: Optional[date]
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Chat ---

class HistoryMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[HistoryMessage] = []
    conversation_id: Optional[UUID] = None  # omit to start a new conversation


class Source(BaseModel):
    source: str
    law: str
    article: str


# --- Conversation / Message ---

class MessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list[Source]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationRead(BaseModel):
    id: UUID
    created_at: datetime
    messages: list[MessageRead]

    model_config = {"from_attributes": True}


# --- Conversation List ---

class ConversationSummary(BaseModel):
    id: UUID
    created_at: datetime
    preview: str  # first user message truncated

    model_config = {"from_attributes": True}


# --- myDATA ---

class InvoiceLine(BaseModel):
    net_value: float
    vat_category: int        # 1=24% 2=13% 3=6% 7=exempt 8=n/a
    vat_amount: float


class Invoice(BaseModel):
    mark: str                # unique AADE identifier
    issue_date: date
    invoice_type: str        # e.g. "1.1", "2.1"
    counterpart_vat: Optional[str]
    net_value: float
    vat_amount: float
    gross_value: float
    lines: list[InvoiceLine] = []


class VatRateBucket(BaseModel):
    rate_pct: float          # 24.0 / 13.0 / 6.0 / 0.0
    net_value: float
    vat_amount: float


class VatSummary(BaseModel):
    date_from: date
    date_to: date
    # Output VAT (from income / sales)
    income_total_net: float
    income_total_vat: float
    income_by_rate: list[VatRateBucket]
    # Input VAT (from expenses / purchases)
    expenses_total_net: float
    expenses_total_vat: float
    expenses_by_rate: list[VatRateBucket]
    # Bottom line
    vat_payable: float       # income_total_vat - expenses_total_vat
    invoice_count_income: int
    invoice_count_expenses: int


# --- Auth ---

class MagicLinkRequest(BaseModel):
    email: EmailStr


# --- Ingest ---

class IngestResponse(BaseModel):
    file: str
    chunks: int
