"""
Advocate API Endpoints
Handles advocate profile management, case requests, and client communication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Annotated, List, Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.advocate_profile import AdvocateProfile, FeeCategory
from app.models.conversation import Conversation, ConversationPhase
from app.models.message import Message, SenderType, MessageType
from app.models.case import Case, CaseStatus, AdvocateResponse
from app.models.advocate_case_request import AdvocateCaseRequest, RequestStatus
from app.schemas.advocate import (
    AdvocateProfileCreate,
    AdvocateProfileUpdate,
    AdvocateProfileResponse,
    AvailabilityUpdate
)
from app.schemas.case import (
    CaseRequestResponse,
    CaseRequestDetailResponse,
    CaseRequestAction,
    CaseResponse
)
from app.schemas.conversation import MessageResponse, MessageCreate
from app.api.auth import get_current_advocate
from app.services.notification_service import notification_service
from app.utils.websocket_manager import manager

router = APIRouter()


# =====================================
# PROFILE ENDPOINTS
# =====================================

@router.get("/profile", response_model=AdvocateProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Get the current advocate's profile."""
    result = await db.execute(
        select(AdvocateProfile)
        .where(AdvocateProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advocate profile not found. Please complete your profile setup."
        )

    return AdvocateProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        enrollment_number=profile.enrollment_number,
        enrollment_year=profile.enrollment_year,
        bar_council=profile.bar_council,
        states=profile.states or [],
        districts=profile.districts or [],
        home_court=profile.home_court,
        primary_specializations=profile.primary_specializations or [],
        sub_specializations=profile.sub_specializations or [],
        experience_years=profile.experience_years or 0,
        landmark_cases=profile.landmark_cases,
        success_rate=float(profile.success_rate) if profile.success_rate else None,
        current_case_load=profile.current_case_load or 0,
        max_case_capacity=profile.max_case_capacity or 20,
        fee_category=profile.fee_category or FeeCategory.STANDARD,
        consultation_fee=float(profile.consultation_fee) if profile.consultation_fee else None,
        languages=profile.languages or [],
        office_address=profile.office_address,
        rating=float(profile.rating) if profile.rating else 0.0,
        review_count=profile.review_count or 0,
        is_verified=profile.is_verified,
        is_available=profile.is_available,
        created_at=profile.created_at
    )


@router.post("/profile", response_model=AdvocateProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: AdvocateProfileCreate,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Create advocate profile (initial setup)."""
    # Check if profile already exists
    result = await db.execute(
        select(AdvocateProfile)
        .where(AdvocateProfile.user_id == current_user.id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PUT to update."
        )

    # Check enrollment number uniqueness
    result = await db.execute(
        select(AdvocateProfile)
        .where(AdvocateProfile.enrollment_number == profile_data.enrollment_number)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enrollment number already registered"
        )

    profile = AdvocateProfile(
        user_id=current_user.id,
        enrollment_number=profile_data.enrollment_number,
        enrollment_year=profile_data.enrollment_year,
        bar_council=profile_data.bar_council,
        states=profile_data.states,
        districts=profile_data.districts,
        home_court=profile_data.home_court,
        primary_specializations=profile_data.primary_specializations,
        sub_specializations=profile_data.sub_specializations,
        experience_years=profile_data.experience_years,
        landmark_cases=profile_data.landmark_cases,
        fee_category=profile_data.fee_category,
        consultation_fee=profile_data.consultation_fee,
        languages=profile_data.languages,
        office_address=profile_data.office_address
    )

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return AdvocateProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        enrollment_number=profile.enrollment_number,
        enrollment_year=profile.enrollment_year,
        bar_council=profile.bar_council,
        states=profile.states or [],
        districts=profile.districts or [],
        home_court=profile.home_court,
        primary_specializations=profile.primary_specializations or [],
        sub_specializations=profile.sub_specializations or [],
        experience_years=profile.experience_years or 0,
        landmark_cases=profile.landmark_cases,
        success_rate=None,
        current_case_load=0,
        max_case_capacity=profile.max_case_capacity or 20,
        fee_category=profile.fee_category or FeeCategory.STANDARD,
        consultation_fee=float(profile.consultation_fee) if profile.consultation_fee else None,
        languages=profile.languages or [],
        office_address=profile.office_address,
        rating=0.0,
        review_count=0,
        is_verified=False,
        is_available=True,
        created_at=profile.created_at
    )


@router.put("/profile", response_model=AdvocateProfileResponse)
async def update_profile(
    profile_data: AdvocateProfileUpdate,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Update advocate profile."""
    result = await db.execute(
        select(AdvocateProfile)
        .where(AdvocateProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    # Update fields if provided
    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(profile, field, value)

    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)

    return AdvocateProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        enrollment_number=profile.enrollment_number,
        enrollment_year=profile.enrollment_year,
        bar_council=profile.bar_council,
        states=profile.states or [],
        districts=profile.districts or [],
        home_court=profile.home_court,
        primary_specializations=profile.primary_specializations or [],
        sub_specializations=profile.sub_specializations or [],
        experience_years=profile.experience_years or 0,
        landmark_cases=profile.landmark_cases,
        success_rate=float(profile.success_rate) if profile.success_rate else None,
        current_case_load=profile.current_case_load or 0,
        max_case_capacity=profile.max_case_capacity or 20,
        fee_category=profile.fee_category or FeeCategory.STANDARD,
        consultation_fee=float(profile.consultation_fee) if profile.consultation_fee else None,
        languages=profile.languages or [],
        office_address=profile.office_address,
        rating=float(profile.rating) if profile.rating else 0.0,
        review_count=profile.review_count or 0,
        is_verified=profile.is_verified,
        is_available=profile.is_available,
        created_at=profile.created_at
    )


@router.put("/availability")
async def update_availability(
    data: AvailabilityUpdate,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Toggle advocate availability for new cases."""
    result = await db.execute(
        select(AdvocateProfile)
        .where(AdvocateProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    profile.is_available = data.is_available
    profile.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "is_available": profile.is_available,
        "message": "Availability updated successfully"
    }


# =====================================
# CASE REQUEST ENDPOINTS
# =====================================

@router.get("/case-requests", response_model=List[CaseRequestResponse])
async def list_case_requests(
    current_user: Annotated[User, Depends(get_current_advocate)],
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List case requests for the advocate."""
    query = select(AdvocateCaseRequest).where(
        AdvocateCaseRequest.advocate_id == current_user.id
    )

    if status_filter:
        try:
            filter_status = RequestStatus(status_filter)
            query = query.where(AdvocateCaseRequest.status == filter_status)
        except ValueError:
            pass

    query = query.order_by(AdvocateCaseRequest.created_at.desc())
    result = await db.execute(query)
    requests = result.scalars().all()

    response = []
    for req in requests:
        # Get case details
        case_result = await db.execute(
            select(Case).where(Case.id == req.case_id)
        )
        case = case_result.scalar_one_or_none()

        # Get client name
        client_result = await db.execute(
            select(User).where(User.id == req.client_id)
        )
        client = client_result.scalar_one_or_none()

        response.append(CaseRequestResponse(
            id=req.id,
            case_id=req.case_id,
            advocate_id=req.advocate_id,
            client_id=req.client_id,
            match_score=req.match_score,
            match_explanation=req.match_explanation,
            status=req.status,
            response_at=req.response_at,
            rejection_reason=req.rejection_reason,
            created_at=req.created_at,
            case=CaseResponse(
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
            ) if case else None,
            client_name=client.full_name if client else None
        ))

    return response


@router.get("/case-requests/{request_id}", response_model=CaseRequestDetailResponse)
async def get_case_request(
    request_id: UUID,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Get case request with full conversation history."""
    result = await db.execute(
        select(AdvocateCaseRequest)
        .where(and_(
            AdvocateCaseRequest.id == request_id,
            AdvocateCaseRequest.advocate_id == current_user.id
        ))
    )
    case_request = result.scalar_one_or_none()

    if not case_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case request not found"
        )

    # Get case details
    case_result = await db.execute(
        select(Case).where(Case.id == case_request.case_id)
    )
    case = case_result.scalar_one_or_none()

    # Get client name
    client_result = await db.execute(
        select(User).where(User.id == case_request.client_id)
    )
    client = client_result.scalar_one_or_none()

    # Get conversation messages (this is the key feature for advocates)
    messages = []
    if case and case.conversation_id:
        msg_result = await db.execute(
            select(Message)
            .where(and_(
                Message.conversation_id == case.conversation_id,
                Message.visible_to_advocate == True
            ))
            .order_by(Message.created_at.asc())
        )
        msg_list = msg_result.scalars().all()

        for msg in msg_list:
            # Get sender name
            sender_name = None
            if msg.sender_type == SenderType.CLIENT:
                sender_name = client.full_name if client else "Client"
            elif msg.sender_type == SenderType.AI:
                sender_name = "AI Assistant"
            elif msg.sender_type == SenderType.ADVOCATE:
                sender_name = current_user.full_name

            messages.append(MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                sender_type=msg.sender_type,
                sender_id=msg.sender_id,
                sender_name=sender_name,
                content=msg.content,
                message_type=msg.message_type,
                file_url=msg.file_url,
                file_name=msg.file_name,
                created_at=msg.created_at
            ))

    return CaseRequestDetailResponse(
        id=case_request.id,
        case_id=case_request.case_id,
        advocate_id=case_request.advocate_id,
        client_id=case_request.client_id,
        match_score=case_request.match_score,
        match_explanation=case_request.match_explanation,
        status=case_request.status,
        response_at=case_request.response_at,
        rejection_reason=case_request.rejection_reason,
        created_at=case_request.created_at,
        case=CaseResponse(
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
        ) if case else None,
        client_name=client.full_name if client else None,
        conversation_messages=messages
    )


@router.post("/case-requests/{request_id}/accept")
async def accept_case_request(
    request_id: UUID,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Accept a case request."""
    result = await db.execute(
        select(AdvocateCaseRequest)
        .where(and_(
            AdvocateCaseRequest.id == request_id,
            AdvocateCaseRequest.advocate_id == current_user.id
        ))
    )
    case_request = result.scalar_one_or_none()

    if not case_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case request not found"
        )

    if case_request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request has already been processed"
        )

    # Update request status
    case_request.status = RequestStatus.ACCEPTED
    case_request.response_at = datetime.utcnow()

    # Update case
    case_result = await db.execute(
        select(Case).where(Case.id == case_request.case_id)
    )
    case = case_result.scalar_one()

    case.advocate_id = current_user.id
    case.status = CaseStatus.ADVOCATE_ASSIGNED
    case.advocate_response = AdvocateResponse.ACCEPTED
    case.updated_at = datetime.utcnow()

    # Update conversation phase
    if case.conversation_id:
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == case.conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        if conversation:
            conversation.phase = ConversationPhase.ADVOCATE_ACTIVE
            conversation.updated_at = datetime.utcnow()

            # Add system message about advocate taking over
            system_message = Message(
                conversation_id=conversation.id,
                sender_type=SenderType.ADVOCATE,
                sender_id=current_user.id,
                content=f"Hello! I'm {current_user.full_name}, and I'll be assisting you with your case from now on. I've reviewed our AI assistant's conversation with you and am ready to help. Please feel free to ask any questions or share additional information.",
                message_type=MessageType.SYSTEM
            )
            db.add(system_message)

    # Update advocate case load
    profile_result = await db.execute(
        select(AdvocateProfile).where(AdvocateProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile:
        profile.current_case_load = (profile.current_case_load or 0) + 1

    await db.commit()

    # Notify client
    await notification_service.notify_advocate_accepted(
        db=db,
        client_id=case_request.client_id,
        case_id=case.id,
        advocate_name=current_user.full_name
    )

    return {
        "message": "Case accepted successfully",
        "case_id": str(case.id),
        "conversation_id": str(case.conversation_id) if case.conversation_id else None
    }


@router.post("/case-requests/{request_id}/reject")
async def reject_case_request(
    request_id: UUID,
    action: CaseRequestAction,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Reject a case request."""
    result = await db.execute(
        select(AdvocateCaseRequest)
        .where(and_(
            AdvocateCaseRequest.id == request_id,
            AdvocateCaseRequest.advocate_id == current_user.id
        ))
    )
    case_request = result.scalar_one_or_none()

    if not case_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case request not found"
        )

    if case_request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request has already been processed"
        )

    # Update request status
    case_request.status = RequestStatus.REJECTED
    case_request.response_at = datetime.utcnow()
    case_request.rejection_reason = action.rejection_reason

    # Update case
    case_result = await db.execute(
        select(Case).where(Case.id == case_request.case_id)
    )
    case = case_result.scalar_one()

    case.status = CaseStatus.ADVOCATE_REJECTED
    case.advocate_response = AdvocateResponse.REJECTED
    case.rejection_reason = action.rejection_reason
    case.updated_at = datetime.utcnow()

    await db.commit()

    # Notify client
    await notification_service.notify_advocate_rejected(
        db=db,
        client_id=case_request.client_id,
        case_id=case.id,
        advocate_name=current_user.full_name,
        reason=action.rejection_reason
    )

    return {
        "message": "Case request declined",
        "case_id": str(case.id)
    }


# =====================================
# ACCEPTED CASES ENDPOINTS
# =====================================

@router.get("/cases")
async def list_accepted_cases(
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """List cases accepted by the advocate."""
    result = await db.execute(
        select(Case)
        .where(Case.advocate_id == current_user.id)
        .order_by(Case.updated_at.desc())
    )
    cases = result.scalars().all()

    response = []
    for case in cases:
        # Get client name
        client_result = await db.execute(
            select(User).where(User.id == case.client_id)
        )
        client = client_result.scalar_one_or_none()

        response.append({
            "id": str(case.id),
            "client_id": str(case.client_id),
            "client_name": client.full_name if client else None,
            "conversation_id": str(case.conversation_id) if case.conversation_id else None,
            "matter_type": case.matter_type,
            "sub_category": case.sub_category,
            "state": case.state,
            "district": case.district,
            "case_summary": case.case_summary,
            "status": case.status.value,
            "created_at": case.created_at.isoformat(),
            "updated_at": case.updated_at.isoformat()
        })

    return {"cases": response}


@router.get("/cases/{case_id}")
async def get_accepted_case(
    case_id: UUID,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Get details of an accepted case with conversation history."""
    result = await db.execute(
        select(Case)
        .where(and_(
            Case.id == case_id,
            Case.advocate_id == current_user.id
        ))
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Get client
    client_result = await db.execute(
        select(User).where(User.id == case.client_id)
    )
    client = client_result.scalar_one_or_none()

    # Get messages
    messages = []
    if case.conversation_id:
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == case.conversation_id)
            .order_by(Message.created_at.asc())
        )
        msg_list = msg_result.scalars().all()

        for msg in msg_list:
            sender_name = None
            if msg.sender_type == SenderType.CLIENT:
                sender_name = client.full_name if client else "Client"
            elif msg.sender_type == SenderType.AI:
                sender_name = "AI Assistant"
            elif msg.sender_type == SenderType.ADVOCATE:
                sender_name = current_user.full_name

            messages.append({
                "id": str(msg.id),
                "sender_type": msg.sender_type.value,
                "sender_name": sender_name,
                "content": msg.content,
                "message_type": msg.message_type.value,
                "created_at": msg.created_at.isoformat()
            })

    return {
        "case": {
            "id": str(case.id),
            "client_id": str(case.client_id),
            "client_name": client.full_name if client else None,
            "client_email": client.email if client else None,
            "client_phone": client.phone if client else None,
            "conversation_id": str(case.conversation_id) if case.conversation_id else None,
            "matter_type": case.matter_type,
            "sub_category": case.sub_category,
            "state": case.state,
            "district": case.district,
            "court_level": case.court_level,
            "complexity": case.complexity,
            "case_summary": case.case_summary,
            "extracted_facts": case.extracted_facts,
            "status": case.status.value,
            "created_at": case.created_at.isoformat(),
            "updated_at": case.updated_at.isoformat()
        },
        "messages": messages
    }


@router.post("/cases/{case_id}/messages")
async def send_message_to_client(
    case_id: UUID,
    message_data: MessageCreate,
    current_user: Annotated[User, Depends(get_current_advocate)],
    db: AsyncSession = Depends(get_db)
):
    """Send a message to the client in an accepted case."""
    # Verify case belongs to advocate
    result = await db.execute(
        select(Case)
        .where(and_(
            Case.id == case_id,
            Case.advocate_id == current_user.id
        ))
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    if not case.conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No conversation associated with this case"
        )

    # Create message
    message = Message(
        conversation_id=case.conversation_id,
        sender_type=SenderType.ADVOCATE,
        sender_id=current_user.id,
        content=message_data.content,
        message_type=message_data.message_type,
        file_url=message_data.file_url,
        file_name=message_data.file_name
    )
    db.add(message)

    # Update conversation timestamp
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == case.conversation_id)
    )
    conversation = conv_result.scalar_one_or_none()
    if conversation:
        conversation.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(message)

    # Broadcast message via WebSocket
    await manager.broadcast_to_conversation(
        str(case.conversation_id),
        {
            "type": "new_message",
            "message": {
                "id": str(message.id),
                "sender_type": message.sender_type.value,
                "sender_name": current_user.full_name,
                "content": message.content,
                "message_type": message.message_type.value,
                "created_at": message.created_at.isoformat()
            }
        }
    )

    # Send notification to client
    await notification_service.notify_new_message(
        db=db,
        user_id=case.client_id,
        sender_name=current_user.full_name,
        case_id=case.id,
        preview=message.content
    )

    return {
        "id": str(message.id),
        "content": message.content,
        "created_at": message.created_at.isoformat()
    }


# =====================================
# NOTIFICATION ENDPOINTS
# =====================================

@router.get("/notifications")
async def get_notifications(
    current_user: Annotated[User, Depends(get_current_advocate)],
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for the advocate."""
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
