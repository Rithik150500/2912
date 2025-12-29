import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class SenderType(str, enum.Enum):
    CLIENT = "client"
    AI = "ai"
    ADVOCATE = "advocate"


class MessageType(str, enum.Enum):
    TEXT = "text"
    FILE = "file"
    DOCUMENT = "document"
    SYSTEM = "system"


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)

    # Sender information
    sender_type = Column(SQLEnum(SenderType), nullable=False)
    sender_id = Column(UUID(as_uuid=True), nullable=True)  # NULL for AI messages

    # Content
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT)

    # File attachment
    file_url = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)

    # Visibility
    visible_to_advocate = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
