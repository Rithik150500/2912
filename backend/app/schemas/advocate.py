from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.advocate_profile import FeeCategory


class AdvocateProfileCreate(BaseModel):
    enrollment_number: str
    enrollment_year: Optional[int] = None
    bar_council: Optional[str] = None
    states: List[str] = []
    districts: List[str] = []
    home_court: Optional[str] = None
    primary_specializations: List[str] = []
    sub_specializations: List[str] = []
    experience_years: int = 0
    landmark_cases: Optional[str] = None
    fee_category: FeeCategory = FeeCategory.STANDARD
    consultation_fee: Optional[Decimal] = None
    languages: List[str] = []
    office_address: Optional[str] = None


class AdvocateProfileUpdate(BaseModel):
    enrollment_year: Optional[int] = None
    bar_council: Optional[str] = None
    states: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    home_court: Optional[str] = None
    primary_specializations: Optional[List[str]] = None
    sub_specializations: Optional[List[str]] = None
    experience_years: Optional[int] = None
    landmark_cases: Optional[str] = None
    fee_category: Optional[FeeCategory] = None
    consultation_fee: Optional[Decimal] = None
    languages: Optional[List[str]] = None
    office_address: Optional[str] = None
    max_case_capacity: Optional[int] = None
    is_available: Optional[bool] = None


class AdvocateProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str  # From user
    email: str  # From user
    phone: Optional[str]  # From user
    enrollment_number: str
    enrollment_year: Optional[int]
    bar_council: Optional[str]
    states: List[str]
    districts: List[str]
    home_court: Optional[str]
    primary_specializations: List[str]
    sub_specializations: List[str]
    experience_years: int
    landmark_cases: Optional[str]
    success_rate: Optional[float]
    current_case_load: int
    max_case_capacity: int
    fee_category: FeeCategory
    consultation_fee: Optional[float]
    languages: List[str]
    office_address: Optional[str]
    rating: float
    review_count: int
    is_verified: bool
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdvocateRecommendation(BaseModel):
    advocate_id: UUID
    profile: AdvocateProfileResponse
    match_score: int = Field(..., ge=0, le=100)
    match_explanation: str
    rank: int


class AvailabilityUpdate(BaseModel):
    is_available: bool
