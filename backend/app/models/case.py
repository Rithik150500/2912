import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Numeric, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class CaseStatus(str, enum.Enum):
    AI_CONVERSATION = "ai_conversation"
    PENDING_ADVOCATE = "pending_advocate"
    ADVOCATE_ASSIGNED = "advocate_assigned"
    ADVOCATE_REJECTED = "advocate_rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"


class AdvocateResponse(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Case(Base):
    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    advocate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)

    # Case Profile (extracted from AI conversation)
    matter_type = Column(String(50), nullable=True)
    sub_category = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    court_level = Column(String(50), nullable=True)
    complexity = Column(String(20), nullable=True)
    urgency = Column(String(20), nullable=True)
    amount_in_dispute = Column(Numeric(15, 2), nullable=True)
    case_summary = Column(Text, nullable=True)
    extracted_facts = Column(JSONB, nullable=True)

    # Status Management
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.AI_CONVERSATION)

    # Advocate Selection
    selected_advocate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    advocate_response = Column(SQLEnum(AdvocateResponse), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("User", back_populates="cases_as_client", foreign_keys=[client_id])
    advocate = relationship("User", back_populates="cases_as_advocate", foreign_keys=[advocate_id])
    conversation = relationship("Conversation", back_populates="case")
    case_requests = relationship("AdvocateCaseRequest", back_populates="case")
