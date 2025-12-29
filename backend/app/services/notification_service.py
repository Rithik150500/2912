"""
Notification Service
Handles creating and managing user notifications.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.notification import Notification
from app.utils.websocket_manager import manager

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing user notifications."""

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Create a new notification for a user.

        Args:
            db: Database session
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Optional message body
            data: Optional additional data

        Returns:
            Created notification
        """
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            data=data
        )

        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Send real-time notification via WebSocket
        await self._send_realtime_notification(user_id, notification)

        return notification

    async def _send_realtime_notification(
        self,
        user_id: UUID,
        notification: Notification
    ):
        """Send notification via WebSocket if user is connected."""
        try:
            await manager.broadcast_notification(
                str(user_id),
                {
                    "id": str(notification.id),
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "data": notification.data,
                    "created_at": notification.created_at.isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send real-time notification: {e}")

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for a user.

        Args:
            db: Database session
            user_id: User ID
            unread_only: Only return unread notifications
            limit: Maximum notifications to return

        Returns:
            List of notifications
        """
        query = select(Notification).where(
            Notification.user_id == user_id
        ).order_by(Notification.created_at.desc()).limit(limit)

        if unread_only:
            query = query.where(Notification.is_read == False)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self,
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Mark a notification as read.

        Args:
            db: Database session
            notification_id: Notification ID
            user_id: User ID (for verification)

        Returns:
            True if successful
        """
        result = await db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.user_id == user_id)
            .values(is_read=True)
        )
        await db.commit()
        return result.rowcount > 0

    async def mark_all_as_read(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)
            .values(is_read=True)
        )
        await db.commit()
        return result.rowcount

    async def get_unread_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Get count of unread notifications for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Count of unread notifications
        """
        from sqlalchemy import func
        result = await db.execute(
            select(func.count(Notification.id))
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)
        )
        return result.scalar() or 0

    # Notification type helpers
    async def notify_case_request(
        self,
        db: AsyncSession,
        advocate_id: UUID,
        case_id: UUID,
        client_name: str,
        matter_type: str,
        match_score: int
    ) -> Notification:
        """Notify advocate of a new case request."""
        return await self.create_notification(
            db=db,
            user_id=advocate_id,
            notification_type="case_request",
            title="New Case Request",
            message=f"{client_name} has requested your assistance for a {matter_type} matter. Match score: {match_score}%",
            data={
                "case_id": str(case_id),
                "client_name": client_name,
                "matter_type": matter_type,
                "match_score": match_score
            }
        )

    async def notify_advocate_accepted(
        self,
        db: AsyncSession,
        client_id: UUID,
        case_id: UUID,
        advocate_name: str
    ) -> Notification:
        """Notify client that advocate accepted their case."""
        return await self.create_notification(
            db=db,
            user_id=client_id,
            notification_type="advocate_accepted",
            title="Advocate Accepted Your Case",
            message=f"{advocate_name} has accepted your case. You can now chat with them directly.",
            data={
                "case_id": str(case_id),
                "advocate_name": advocate_name
            }
        )

    async def notify_advocate_rejected(
        self,
        db: AsyncSession,
        client_id: UUID,
        case_id: UUID,
        advocate_name: str,
        reason: Optional[str] = None
    ) -> Notification:
        """Notify client that advocate declined their case."""
        message = f"{advocate_name} is unable to take your case at this time."
        if reason:
            message += f" Reason: {reason}"
        message += " Please select another advocate from the recommendations."

        return await self.create_notification(
            db=db,
            user_id=client_id,
            notification_type="advocate_rejected",
            title="Advocate Unavailable",
            message=message,
            data={
                "case_id": str(case_id),
                "advocate_name": advocate_name,
                "reason": reason
            }
        )

    async def notify_new_message(
        self,
        db: AsyncSession,
        user_id: UUID,
        sender_name: str,
        case_id: UUID,
        preview: str
    ) -> Notification:
        """Notify user of a new message."""
        return await self.create_notification(
            db=db,
            user_id=user_id,
            notification_type="new_message",
            title=f"New message from {sender_name}",
            message=preview[:100] + "..." if len(preview) > 100 else preview,
            data={
                "case_id": str(case_id),
                "sender_name": sender_name
            }
        )


# Global instance
notification_service = NotificationService()
