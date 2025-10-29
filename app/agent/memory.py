# app/agent/memory.py
"""
Simple in-memory conversation storage for multi-turn interactions
For production, replace with Redis or database
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import threading


class ConversationMemory:
    """
    Thread-safe in-memory storage for conversation history
    """

    def __init__(self, ttl_minutes: int = 60):
        """
        Args:
            ttl_minutes: How long to keep conversations in memory
        """
        self._conversations: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self.ttl_minutes = ttl_minutes

    def get_conversation(self, convo_id: str) -> Optional[List[Dict]]:
        """
        Get conversation history by ID

        Args:
            convo_id: Conversation identifier

        Returns:
            List of messages or None if not found
        """
        with self._lock:
            self._cleanup_expired()

            convo = self._conversations.get(convo_id)
            if not convo:
                return None

            # Check if expired
            if datetime.utcnow() > convo["expires_at"]:
                del self._conversations[convo_id]
                return None

            return convo["messages"]

    def save_conversation(
        self,
        convo_id: str,
        messages: List[Dict],
        user_email: str = None,
        role: str = None
    ):
        """
        Save or update conversation history

        Args:
            convo_id: Conversation identifier
            messages: List of message dicts
            user_email: Optional user email
            role: Optional user role
        """
        with self._lock:
            expires_at = datetime.utcnow() + timedelta(minutes=self.ttl_minutes)

            self._conversations[convo_id] = {
                "messages": messages,
                "user_email": user_email,
                "role": role,
                "created_at": self._conversations.get(convo_id, {}).get(
                    "created_at",
                    datetime.utcnow()
                ),
                "updated_at": datetime.utcnow(),
                "expires_at": expires_at
            }

    def clear_conversation(self, convo_id: str):
        """Delete a conversation"""
        with self._lock:
            if convo_id in self._conversations:
                del self._conversations[convo_id]

    def get_stats(self) -> Dict:
        """Get memory statistics"""
        with self._lock:
            self._cleanup_expired()
            return {
                "total_conversations": len(self._conversations),
                "ttl_minutes": self.ttl_minutes
            }

    def _cleanup_expired(self):
        """Remove expired conversations"""
        now = datetime.utcnow()
        expired = [
            cid for cid, convo in self._conversations.items()
            if now > convo["expires_at"]
        ]
        for cid in expired:
            del self._conversations[cid]


# Global memory instance (singleton)
_memory_instance: Optional[ConversationMemory] = None


def get_memory() -> ConversationMemory:
    """Get or create the global memory instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ConversationMemory(ttl_minutes=60)
    return _memory_instance


def clear_all_memory():
    """Clear all conversations (useful for testing)"""
    global _memory_instance
    if _memory_instance:
        _memory_instance._conversations.clear()
