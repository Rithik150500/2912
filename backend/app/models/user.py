import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    CLIENT = "client"
    ADVOCATE = "advocate"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    advocate_profile = relationship("AdvocateProfile", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="client", foreign_keys="Conversation.client_id")
    cases_as_client = relationship("Case", back_populates="client", foreign_keys="Case.client_id")
    cases_as_advocate = relationship("Case", back_populates="advocate", foreign_keys="Case.advocate_id")
    notifications = relationship("Notification", back_populates="user")
