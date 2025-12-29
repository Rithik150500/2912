import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class FeeCategory(str, enum.Enum):
    PREMIUM = "premium"
    STANDARD = "standard"
    AFFORDABLE = "affordable"
    PRO_BONO = "pro_bono"


class AdvocateProfile(Base):
    __tablename__ = "advocate_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Professional details
    enrollment_number = Column(String(50), unique=True, nullable=False)
    enrollment_year = Column(Integer, nullable=True)
    bar_council = Column(String(100), nullable=True)

    # Geographic coverage
    states = Column(ARRAY(String), default=list)
    districts = Column(ARRAY(String), default=list)
    home_court = Column(String(100), nullable=True)

    # Specializations
    primary_specializations = Column(ARRAY(String), default=list)
    sub_specializations = Column(ARRAY(String), default=list)

    # Experience
    experience_years = Column(Integer, default=0)
    landmark_cases = Column(Text, nullable=True)
    success_rate = Column(Numeric(5, 2), nullable=True)

    # Capacity
    current_case_load = Column(Integer, default=0)
    max_case_capacity = Column(Integer, default=20)

    # Fees
    fee_category = Column(SQLEnum(FeeCategory), default=FeeCategory.STANDARD)
    consultation_fee = Column(Numeric(10, 2), nullable=True)

    # Languages
    languages = Column(ARRAY(String), default=list)

    # Contact
    office_address = Column(Text, nullable=True)

    # Rating
    rating = Column(Numeric(3, 2), default=0.0)
    review_count = Column(Integer, default=0)

    # Status
    is_verified = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="advocate_profile")
    case_requests = relationship("AdvocateCaseRequest", back_populates="advocate_profile")
