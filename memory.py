"""
Memory Layer - State management and context

Stores:
- User preferences (collected at startup)
- Conversation history
- Session context
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# Pydantic Models
class UserPreferences(BaseModel):
    """User preferences collected at startup."""
    shopping_style: str = "balanced"  # quick, browsing, balanced, thorough
    budget_preference: str = "medium"  # low, medium, high
    preferred_categories: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    accessibility_needs: List[str] = Field(default_factory=list)


class Message(BaseModel):
    """Single conversation message."""
    role: str  # "user", "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class MemoryManager:
    """Simple memory for session context."""

    def __init__(self):
        self.user_preferences: Optional[UserPreferences] = None
        self.conversation_history: List[Message] = []

    def set_preferences(self, preferences: Dict[str, Any]):
        """Store user preferences collected at startup."""
        self.user_preferences = UserPreferences(**preferences)

    def get_preferences_dict(self) -> Dict[str, Any]:
        """Get preferences as dictionary."""
        if self.user_preferences:
            return self.user_preferences.dict()
        return {}

    def add_message(self, role: str, content: str):
        """Add message to history."""
        self.conversation_history.append(
            Message(role=role, content=content)
        )

    def get_recent_context(self, n: int = 5) -> List[Message]:
        """Get last n messages."""
        return self.conversation_history[-n:]

    def get_context_string(self) -> str:
        """Get conversation as formatted string."""
        if not self.conversation_history:
            return "No previous conversation."

        lines = []
        for msg in self.conversation_history[-5:]:
            lines.append(f"{msg.role}: {msg.content[:100]}")
        return "\n".join(lines)

    def clear_history(self):
        """Clear conversation (new session)."""
        self.conversation_history = []
