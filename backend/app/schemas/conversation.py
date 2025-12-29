from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.conversation import ConversationPhase
from app.models.message import SenderType, MessageType


class ConversationCreate(BaseModel):
    matter_type: Optional[str] = None  # Optional initial matter type


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    message_type: MessageType = MessageType.TEXT
    file_url: Optional[str] = None
    file_name: Optional[str] = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_type: SenderType
    sender_id: Optional[UUID]
    sender_name: Optional[str] = None  # Will be populated from user
    content: str
    message_type: MessageType
    file_url: Optional[str]
    file_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    client_id: UUID
    case_id: Optional[UUID]
    phase: ConversationPhase
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: Optional[MessageResponse] = None

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: UUID
    client_id: UUID
    client_name: str
    case_id: Optional[UUID]
    phase: ConversationPhase
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class AIMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class AIMessageResponse(BaseModel):
    user_message: MessageResponse
    ai_message: MessageResponse
    case_profile_updated: bool = False
    recommendations_available: bool = False
