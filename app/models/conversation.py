"""
Conversation Models for CounselAI
Handles conversation threading and message history
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.document import FlexibleJSON
import uuid


class Conversation(Base):
    """Conversation thread model"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), nullable=False, index=True)
    user_id = Column(String(255), index=True, nullable=False)
    title = Column(String(500), nullable=True)
    context = Column(FlexibleJSON, nullable=True)
    extra_data = Column(FlexibleJSON, nullable=True)  # Renamed from metadata (reserved word)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to messages
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(uuid={self.uuid}, user_id={self.user_id}, title={self.title})>"


class ConversationMessage(Base):
    """Individual message in a conversation"""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    extra_data = Column(FlexibleJSON, nullable=True)  # Renamed from metadata (reserved word)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<ConversationMessage(uuid={self.uuid}, role={self.role}, conversation_id={self.conversation_id})>"
