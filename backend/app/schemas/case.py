from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.models.case import CaseStatus, AdvocateResponse
from app.models.advocate_case_request import RequestStatus
from app.schemas.advocate import AdvocateProfileResponse
from app.schemas.conversation import MessageResponse


class CaseCreate(BaseModel):
    conversation_id: UUID


class CaseProfileUpdate(BaseModel):
    matter_type: Optional[str] = None
    sub_category: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    court_level: Optional[str] = None
    complexity: Optional[str] = None
    urgency: Optional[str] = None
    amount_in_dispute: Optional[Decimal] = None
    case_summary: Optional[str] = None
    extracted_facts: Optional[Dict[str, Any]] = None


class CaseResponse(BaseModel):
    id: UUID
    client_id: UUID
    advocate_id: Optional[UUID]
    conversation_id: Optional[UUID]
    matter_type: Optional[str]
    sub_category: Optional[str]
    state: Optional[str]
    district: Optional[str]
    court_level: Optional[str]
    complexity: Optional[str]
    urgency: Optional[str]
    amount_in_dispute: Optional[float]
    case_summary: Optional[str]
    status: CaseStatus
    advocate_response: Optional[AdvocateResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseDetailResponse(CaseResponse):
    client_name: str
    advocate_name: Optional[str] = None
    extracted_facts: Optional[Dict[str, Any]] = None


class SelectAdvocateRequest(BaseModel):
    advocate_id: UUID


class CaseRequestResponse(BaseModel):
    id: UUID
    case_id: UUID
    advocate_id: UUID
    client_id: UUID
    match_score: Optional[int]
    match_explanation: Optional[str]
    status: RequestStatus
    response_at: Optional[datetime]
    rejection_reason: Optional[str]
    created_at: datetime
    # Populated fields
    case: Optional[CaseResponse] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


class CaseRequestDetailResponse(CaseRequestResponse):
    conversation_messages: List[MessageResponse] = []


class CaseRequestAction(BaseModel):
    action: str = Field(..., pattern="^(accept|reject)$")
    rejection_reason: Optional[str] = None


class AcceptedCaseResponse(BaseModel):
    id: UUID
    case: CaseResponse
    client_name: str
    conversation_id: UUID
    accepted_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True
