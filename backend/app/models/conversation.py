import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ConversationPhase(str, enum.Enum):
    AI_INTERVIEW = "ai_interview"
    AI_COUNSELLING = "ai_counselling"
    AI_DRAFTING = "ai_drafting"
    ADVOCATE_REVIEW = "advocate_review"
    ADVOCATE_ACTIVE = "advocate_active"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Conversation phase
    phase = Column(SQLEnum(ConversationPhase), default=ConversationPhase.AI_INTERVIEW)

    # AI state for Claude container
    ai_container_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("User", back_populates="conversations", foreign_keys=[client_id])
    case = relationship("Case", back_populates="conversation")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
