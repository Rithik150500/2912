"""
WebSocket API for real-time chat communication.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from uuid import UUID
import json
import logging

from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.conversation import Conversation, ConversationPhase
from app.models.message import Message, SenderType, MessageType
from app.models.case import Case
from app.utils.security import verify_token
from app.utils.websocket_manager import manager
from app.services.ai_service import ai_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_user_from_token(token: str) -> Optional[dict]:
    """Verify token and return user info."""
    payload = verify_token(token, "access")
    if payload:
        return {
            "user_id": payload.get("sub"),
            "role": payload.get("role")
        }
    return None


@router.websocket("/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time chat.

    Protocol:
    - Connect with token in query params: /ws/chat/{conversation_id}?token=xxx
    - Send messages as JSON: {"type": "message", "content": "..."}
    - Receive messages as JSON: {"type": "new_message", "message": {...}}
    """
    # Authenticate user
    user_info = await get_user_from_token(token)
    if not user_info:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = user_info["user_id"]
    user_role = user_info["role"]

    # Verify access to conversation
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation).where(Conversation.id == UUID(conversation_id))
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            await websocket.close(code=4004, reason="Conversation not found")
            return

        # Check access rights
        if user_role == "client" and str(conversation.client_id) != user_id:
            await websocket.close(code=4003, reason="Access denied")
            return

        if user_role == "advocate":
            # Check if advocate is assigned to this case
            case_result = await db.execute(
                select(Case).where(Case.conversation_id == conversation.id)
            )
            case = case_result.scalar_one_or_none()
            if not case or str(case.advocate_id) != user_id:
                await websocket.close(code=4003, reason="Access denied")
                return

        # Get user details
        user_result = await db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = user_result.scalar_one_or_none()
        user_name = user.full_name if user else "Unknown"

    # Accept connection
    await manager.connect(websocket, conversation_id, user_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": user_role
        })

        # Listen for messages
        while True:
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                message_type = message_data.get("type")

                if message_type == "message":
                    await handle_chat_message(
                        websocket=websocket,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        user_role=user_role,
                        user_name=user_name,
                        content=message_data.get("content", "")
                    )

                elif message_type == "typing":
                    # Broadcast typing indicator
                    await manager.broadcast_to_conversation(
                        conversation_id,
                        {
                            "type": "typing",
                            "user_id": user_id,
                            "user_name": user_name,
                            "is_typing": message_data.get("is_typing", True)
                        }
                    )

                elif message_type == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id, user_id)
        logger.info(f"Client {user_id} disconnected from conversation {conversation_id}")


async def handle_chat_message(
    websocket: WebSocket,
    conversation_id: str,
    user_id: str,
    user_role: str,
    user_name: str,
    content: str
):
    """Handle incoming chat message."""
    if not content.strip():
        return

    async with AsyncSessionLocal() as db:
        # Get conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == UUID(conversation_id))
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            await websocket.send_json({
                "type": "error",
                "message": "Conversation not found"
            })
            return

        # Determine sender type
        if user_role == "client":
            sender_type = SenderType.CLIENT
        else:
            sender_type = SenderType.ADVOCATE

        # Save message
        message = Message(
            conversation_id=conversation.id,
            sender_type=sender_type,
            sender_id=UUID(user_id),
            content=content,
            message_type=MessageType.TEXT
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)

        # Prepare message for broadcast
        message_response = {
            "id": str(message.id),
            "sender_type": sender_type.value,
            "sender_id": user_id,
            "sender_name": user_name,
            "content": content,
            "message_type": "text",
            "created_at": message.created_at.isoformat()
        }

        # Broadcast to all participants
        await manager.broadcast_to_conversation(
            conversation_id,
            {
                "type": "new_message",
                "message": message_response
            }
        )

        # If client is messaging and conversation is in AI phase, get AI response
        if (sender_type == SenderType.CLIENT and
            conversation.phase in [
                ConversationPhase.AI_INTERVIEW,
                ConversationPhase.AI_COUNSELLING,
                ConversationPhase.AI_DRAFTING
            ]):

            # Get conversation history
            msg_result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
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
                message=content,
                conversation_history=history,
                container_id=conversation.ai_container_id
            )

            # Update container ID
            if new_container_id:
                conversation.ai_container_id = new_container_id

            # Save AI response
            ai_message = Message(
                conversation_id=conversation.id,
                sender_type=SenderType.AI,
                content=ai_response,
                message_type=MessageType.TEXT
            )
            db.add(ai_message)
            await db.commit()
            await db.refresh(ai_message)

            # Broadcast AI response
            await manager.broadcast_to_conversation(
                conversation_id,
                {
                    "type": "new_message",
                    "message": {
                        "id": str(ai_message.id),
                        "sender_type": "ai",
                        "sender_name": "AI Assistant",
                        "content": ai_response,
                        "message_type": "text",
                        "created_at": ai_message.created_at.isoformat()
                    }
                }
            )

            # If case profile was extracted, notify
            if case_profile:
                await websocket.send_json({
                    "type": "case_profile_updated",
                    "profile": case_profile
                })

        # If advocate is messaging, notify client
        elif sender_type == SenderType.ADVOCATE:
            # Get case to find client
            case_result = await db.execute(
                select(Case).where(Case.conversation_id == conversation.id)
            )
            case = case_result.scalar_one_or_none()

            if case:
                await notification_service.notify_new_message(
                    db=db,
                    user_id=case.client_id,
                    sender_name=user_name,
                    case_id=case.id,
                    preview=content
                )


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time notifications.

    Connect with token: /ws/notifications?token=xxx
    Receive notifications as JSON: {"type": "notification", "data": {...}}
    """
    user_info = await get_user_from_token(token)
    if not user_info:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = user_info["user_id"]

    await websocket.accept()

    # Register for user notifications
    if user_id not in manager.user_connections:
        manager.user_connections[user_id] = set()
    manager.user_connections[user_id].add(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id
        })

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.user_connections.get(user_id, set()).discard(websocket)
        logger.info(f"User {user_id} disconnected from notifications")
