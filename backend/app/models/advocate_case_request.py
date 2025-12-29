import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AdvocateCaseRequest(Base):
    __tablename__ = "advocate_case_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    advocate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Match details
    match_score = Column(Integer, nullable=True)
    match_explanation = Column(Text, nullable=True)

    # Status
    status = Column(SQLEnum(RequestStatus), default=RequestStatus.PENDING)
    response_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    case = relationship("Case", back_populates="case_requests")
    advocate_profile = relationship(
        "AdvocateProfile",
        back_populates="case_requests",
        foreign_keys=[advocate_id],
        primaryjoin="AdvocateCaseRequest.advocate_id == AdvocateProfile.user_id"
    )
