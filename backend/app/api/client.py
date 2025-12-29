"""
Client API Endpoints
Handles all client-related operations including conversations, cases, and advocate selection.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, ConversationPhase
from app.models.message import Message, SenderType, MessageType
from app.models.case import Case, CaseStatus, AdvocateResponse
from app.models.advocate_case_request import AdvocateCaseRequest, RequestStatus
from app.models.notification import Notification
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    MessageCreate,
    MessageResponse,
    AIMessageRequest,
    AIMessageResponse
)
from app.schemas.case import (
    CaseResponse,
    CaseDetailResponse,
    SelectAdvocateRequest,
    CaseRequestResponse
)
from app.schemas.advocate import AdvocateRecommendation
from app.api.auth import get_current_client
from app.services.ai_service import ai_service
from app.services.matching_service import matching_service
from app.services.notification_service import notification_service

router = APIRouter()


# =====================================
# CONVERSATION ENDPOINTS
# =====================================

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Start a new AI conversation."""
    # Create conversation
    conversation = Conversation(
        client_id=current_user.id,
        phase=ConversationPhase.AI_INTERVIEW
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Create initial AI greeting message
    greeting = """Welcome! I'm your legal assistant. I'm here to help you with your legal matter.

To provide you with the best assistance, I'll need to understand your situation. Let's start with some questions.

**What type of legal matter do you need help with?**

1. Civil Dispute (property, contracts, recovery)
2. Matrimonial (divorce, maintenance, custody)
3. Criminal/Bail
4. Property/Conveyancing
5. Constitutional/Writ
6. Other

Please describe your legal issue, and I'll guide you through the process."""

    ai_message = Message(
        conversation_id=conversation.id,
        sender_type=SenderType.AI,
        content=greeting,
        message_type=MessageType.TEXT
    )
    db.add(ai_message)
    await db.commit()

    return ConversationResponse(
        id=conversation.id,
        client_id=conversation.client_id,
        case_id=conversation.case_id,
        phase=conversation.phase,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=1
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """List all conversations for the current client."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.client_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    response = []
    for conv in conversations:
        # Get message count
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = msg_result.scalar_one_or_none()

        response.append(ConversationResponse(
            id=conv.id,
            client_id=conv.client_id,
            case_id=conv.case_id,
            phase=conv.phase,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            last_message=MessageResponse(
                id=last_message.id,
                conversation_id=last_message.conversation_id,
                sender_type=last_message.sender_type,
                sender_id=last_message.sender_id,
                content=last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content,
                message_type=last_message.message_type,
                file_url=last_message.file_url,
                file_name=last_message.file_name,
                created_at=last_message.created_at
            ) if last_message else None
        ))

    return response


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Get conversation details with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(and_(
            Conversation.id == conversation_id,
            Conversation.client_id == current_user.id
        ))
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get all messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return ConversationDetailResponse(
        id=conversation.id,
        client_id=conversation.client_id,
        client_name=current_user.full_name,
        case_id=conversation.case_id,
        phase=conversation.phase,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                sender_type=msg.sender_type,
                sender_id=msg.sender_id,
                content=msg.content,
                message_type=msg.message_type,
                file_url=msg.file_url,
                file_name=msg.file_name,
                created_at=msg.created_at
            ) for msg in messages
        ]
    )


@router.post("/conversations/{conversation_id}/messages", response_model=AIMessageResponse)
async def send_message(
    conversation_id: UUID,
    message_data: AIMessageRequest,
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Send a message to the AI and get a response."""
    # Verify conversation belongs to user
    result = await db.execute(
        select(Conversation)
        .where(and_(
            Conversation.id == conversation_id,
            Conversation.client_id == current_user.id
        ))
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Check if conversation is in AI phase
    if conversation.phase not in [
        ConversationPhase.AI_INTERVIEW,
        ConversationPhase.AI_COUNSELLING,
        ConversationPhase.AI_DRAFTING
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This conversation is now with an advocate. AI responses are disabled."
        )

    # Save user message
    user_message = Message(
        conversation_id=conversation_id,
        sender_type=SenderType.CLIENT,
        sender_id=current_user.id,
        content=message_data.content,
        message_type=MessageType.TEXT
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    # Get conversation history
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    history = [
        {
            "sender_type": msg.sender_type.value,
            "content": msg.content
        }
        for msg in messages
    ]

    # Get AI response
    ai_response, new_container_id, case_profile, tool_used = await ai_service.process_message(
        message=message_data.content,
        conversation_history=history,
        container_id=conversation.ai_container_id
    )

    # Update conversation with container ID
    if new_container_id:
        conversation.ai_container_id = new_container_id

    # Save AI response
    ai_message = Message(
        conversation_id=conversation_id,
        sender_type=SenderType.AI,
        content=ai_response,
        message_type=MessageType.TEXT
    )
    db.add(ai_message)

    # If case profile extracted, update or create case
    case_profile_updated = False
    recommendations_available = False

    if case_profile:
        case_profile_updated = True

        # Check if case exists
        if conversation.case_id:
            case_result = await db.execute(
                select(Case).where(Case.id == conversation.case_id)
            )
            case = case_result.scalar_one_or_none()
            if case:
                # Update case profile
                for key, value in case_profile.items():
                    if hasattr(case, key) and value:
                        setattr(case, key, value)
        else:
            # Create new case
            case = Case(
                client_id=current_user.id,
                conversation_id=conversation_id,
                matter_type=case_profile.get("matter_type"),
                sub_category=case_profile.get("sub_category"),
                state=case_profile.get("state"),
                district=case_profile.get("district"),
                court_level=case_profile.get("court_level"),
                complexity=case_profile.get("complexity"),
                case_summary=case_profile.get("case_summary"),
                extracted_facts=case_profile,
                status=CaseStatus.AI_CONVERSATION
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)
            conversation.case_id = case.id

        # Check if we have enough info for recommendations
        if case_profile.get("matter_type") and case_profile.get("state"):
            recommendations_available = True

    conversation.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ai_message)

    return AIMessageResponse(
        user_message=MessageResponse(
            id=user_message.id,
            conversation_id=user_message.conversation_id,
            sender_type=user_message.sender_type,
            sender_id=user_message.sender_id,
            content=user_message.content,
            message_type=user_message.message_type,
            file_url=user_message.file_url,
            file_name=user_message.file_name,
            created_at=user_message.created_at
        ),
        ai_message=MessageResponse(
            id=ai_message.id,
            conversation_id=ai_message.conversation_id,
            sender_type=ai_message.sender_type,
            sender_id=ai_message.sender_id,
            content=ai_message.content,
            message_type=ai_message.message_type,
            file_url=ai_message.file_url,
            file_name=ai_message.file_name,
            created_at=ai_message.created_at
        ),
        case_profile_updated=case_profile_updated,
        recommendations_available=recommendations_available
    )


# =====================================
# CASE ENDPOINTS
# =====================================

@router.get("/cases", response_model=List[CaseResponse])
async def list_cases(
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """List all cases for the current client."""
    result = await db.execute(
        select(Case)
        .where(Case.client_id == current_user.id)
        .order_by(Case.updated_at.desc())
    )
    cases = result.scalars().all()

    return [
        CaseResponse(
            id=case.id,
            client_id=case.client_id,
            advocate_id=case.advocate_id,
            conversation_id=case.conversation_id,
            matter_type=case.matter_type,
            sub_category=case.sub_category,
            state=case.state,
            district=case.district,
            court_level=case.court_level,
            complexity=case.complexity,
            urgency=case.urgency,
            amount_in_dispute=float(case.amount_in_dispute) if case.amount_in_dispute else None,
            case_summary=case.case_summary,
            status=case.status,
            advocate_response=case.advocate_response,
            created_at=case.created_at,
            updated_at=case.updated_at
        ) for case in cases
    ]


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: UUID,
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Get case details."""
    result = await db.execute(
        select(Case)
        .where(and_(
            Case.id == case_id,
            Case.client_id == current_user.id
        ))
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Get advocate name if assigned
    advocate_name = None
    if case.advocate_id:
        adv_result = await db.execute(
            select(User).where(User.id == case.advocate_id)
        )
        advocate = adv_result.scalar_one_or_none()
        if advocate:
            advocate_name = advocate.full_name

    return CaseDetailResponse(
        id=case.id,
        client_id=case.client_id,
        advocate_id=case.advocate_id,
        conversation_id=case.conversation_id,
        matter_type=case.matter_type,
        sub_category=case.sub_category,
        state=case.state,
        district=case.district,
        court_level=case.court_level,
        complexity=case.complexity,
        urgency=case.urgency,
        amount_in_dispute=float(case.amount_in_dispute) if case.amount_in_dispute else None,
        case_summary=case.case_summary,
        status=case.status,
        advocate_response=case.advocate_response,
        created_at=case.created_at,
        updated_at=case.updated_at,
        client_name=current_user.full_name,
        advocate_name=advocate_name,
        extracted_facts=case.extracted_facts
    )


@router.get("/cases/{case_id}/recommendations")
async def get_recommendations(
    case_id: UUID,
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Get advocate recommendations for a case."""
    # Get case
    result = await db.execute(
        select(Case)
        .where(and_(
            Case.id == case_id,
            Case.client_id == current_user.id
        ))
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Build case profile from case data
    case_profile = {
        "matter_type": case.matter_type,
        "sub_category": case.sub_category,
        "state": case.state,
        "district": case.district,
        "court_level": case.court_level or "district",
        "complexity": case.complexity or "moderate",
        "urgency": case.urgency or "normal"
    }

    # Add extracted facts if available
    if case.extracted_facts:
        case_profile.update(case.extracted_facts)

    # Get recommendations
    recommendations = await matching_service.get_recommendations(db, case_profile)

    # Get previously rejected advocates for this case
    rejected_result = await db.execute(
        select(AdvocateCaseRequest.advocate_id)
        .where(and_(
            AdvocateCaseRequest.case_id == case_id,
            AdvocateCaseRequest.status == RequestStatus.REJECTED
        ))
    )
    rejected_ids = {str(r[0]) for r in rejected_result.all()}

    # Filter out rejected advocates
    available_recommendations = [
        r for r in recommendations
        if r["advocate_id"] not in rejected_ids
    ]

    return {
        "case_id": str(case_id),
        "recommendations": available_recommendations,
        "total": len(available_recommendations)
    }


@router.post("/cases/{case_id}/select-advocate")
async def select_advocate(
    case_id: UUID,
    request: SelectAdvocateRequest,
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Select an advocate for a case, sending them a case request."""
    # Get case
    result = await db.execute(
        select(Case)
        .where(and_(
            Case.id == case_id,
            Case.client_id == current_user.id
        ))
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    if case.status == CaseStatus.ADVOCATE_ASSIGNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An advocate has already been assigned to this case"
        )

    # Check if there's already a pending request
    pending_result = await db.execute(
        select(AdvocateCaseRequest)
        .where(and_(
            AdvocateCaseRequest.case_id == case_id,
            AdvocateCaseRequest.status == RequestStatus.PENDING
        ))
    )
    if pending_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="There is already a pending request for this case"
        )

    # Get advocate details
    advocate_data = await matching_service.get_advocate_by_id(db, request.advocate_id)
    if not advocate_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advocate not found"
        )

    # Calculate match score for this specific advocate
    case_profile = {
        "matter_type": case.matter_type,
        "sub_category": case.sub_category,
        "state": case.state,
        "district": case.district,
        "court_level": case.court_level or "district",
        "complexity": case.complexity or "moderate"
    }

    recommendations = await matching_service.get_recommendations(db, case_profile, limit=20)
    match_info = next(
        (r for r in recommendations if r["advocate_id"] == str(request.advocate_id)),
        {"match_score": 50, "match_reasons": ["Selected by client"]}
    )

    # Create case request
    case_request = AdvocateCaseRequest(
        case_id=case_id,
        advocate_id=request.advocate_id,
        client_id=current_user.id,
        match_score=int(match_info["match_score"]),
        match_explanation="; ".join(match_info.get("match_reasons", [])),
        status=RequestStatus.PENDING
    )
    db.add(case_request)

    # Update case status
    case.status = CaseStatus.PENDING_ADVOCATE
    case.selected_advocate_id = request.advocate_id
    case.advocate_response = AdvocateResponse.PENDING

    await db.commit()
    await db.refresh(case_request)

    # Send notification to advocate
    await notification_service.notify_case_request(
        db=db,
        advocate_id=request.advocate_id,
        case_id=case_id,
        client_name=current_user.full_name,
        matter_type=case.matter_type or "legal",
        match_score=case_request.match_score
    )

    return {
        "message": "Case request sent to advocate",
        "request_id": str(case_request.id),
        "advocate_name": advocate_data["name"],
        "status": "pending"
    }


# =====================================
# NOTIFICATION ENDPOINTS
# =====================================

@router.get("/notifications")
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_client)],
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the current client."""
    notifications = await notification_service.get_user_notifications(
        db, current_user.id, unread_only
    )

    return {
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "data": n.data,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            } for n in notifications
        ],
        "unread_count": await notification_service.get_unread_count(db, current_user.id)
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read."""
    success = await notification_service.mark_as_read(db, notification_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: Annotated[User, Depends(get_current_client)],
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read."""
    count = await notification_service.mark_all_as_read(db, current_user.id)
    return {"marked_read": count}
