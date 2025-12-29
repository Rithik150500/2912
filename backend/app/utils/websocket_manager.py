from typing import Dict, List, Set
from fastapi import WebSocket
import json
import uuid


class ConnectionManager:
    """Manages WebSocket connections for real-time chat."""

    def __init__(self):
        # Map conversation_id -> list of websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Map user_id -> set of websocket connections (for notifications)
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        # Add to conversation connections
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, conversation_id: str, user_id: str):
        """Remove a WebSocket connection."""
        # Remove from conversation connections
        if conversation_id in self.active_connections:
            if websocket in self.active_connections[conversation_id]:
                self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection."""
        await websocket.send_json(message)

    async def broadcast_to_conversation(self, conversation_id: str, message: dict):
        """Broadcast a message to all connections in a conversation."""
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass  # Connection might be closed

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections of a specific user."""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass  # Connection might be closed

    async def broadcast_notification(self, user_id: str, notification: dict):
        """Send a notification to a user."""
        await self.send_to_user(user_id, {
            "type": "notification",
            "data": notification
        })


# Global connection manager instance
manager = ConnectionManager()
