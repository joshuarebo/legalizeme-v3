"""
Conversation Service - Manages conversation threading and context
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.conversation import Conversation, ConversationMessage
from app.models.query import Query
from app.config import settings
import json
import uuid

logger = logging.getLogger(__name__)

class ConversationService:
    """Service for managing conversations and message threading"""

    def __init__(self):
        # Simple in-memory cache for now (no S3 to avoid startup issues)
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
        logger.info("ConversationService initialized with in-memory caching")



    def create_conversation(
        self, 
        db: Session, 
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        agent_mode: bool = False,
        use_enhanced_rag: bool = True,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Create a new conversation"""
        try:
            conversation = Conversation(
                user_id=user_id,
                title=title or "New Conversation",
                agent_mode=agent_mode,
                use_enhanced_rag=use_enhanced_rag,
                context=initial_context or {},
                conversation_metadata={}
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            logger.info(f"Created conversation {conversation.uuid} for user {user_id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            db.rollback()
            raise
    
    def get_conversation(
        self, 
        db: Session, 
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Conversation]:
        """Get conversation by ID with optional user filtering"""
        try:
            query = db.query(Conversation).filter(Conversation.uuid == conversation_id)
            
            if user_id:
                query = query.filter(Conversation.user_id == user_id)
            
            return query.first()
            
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None
    
    def get_user_conversations(
        self, 
        db: Session, 
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        active_only: bool = True
    ) -> List[Conversation]:
        """Get conversations for a user"""
        try:
            query = db.query(Conversation).filter(Conversation.user_id == user_id)
            
            if active_only:
                query = query.filter(Conversation.is_active == True)
            
            conversations = query.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting conversations for user {user_id}: {e}")
            return []
    
    def add_message(
        self,
        db: Session,
        conversation_id: str,
        role: str,  # 'user' or 'assistant'
        content: str,
        query_id: Optional[str] = None,
        confidence: Optional[float] = None,
        model_used: Optional[str] = None,
        processing_time: Optional[float] = None,
        reasoning_chain: Optional[List[str]] = None,
        citations: Optional[List[Dict]] = None,
        follow_up_suggestions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ConversationMessage]:
        """Add a message to a conversation"""
        try:
            # Get conversation
            conversation = db.query(Conversation).filter(Conversation.uuid == conversation_id).first()
            if not conversation:
                logger.error(f"Conversation {conversation_id} not found")
                return None
            
            # Convert confidence to percentage if provided
            confidence_pct = None
            if confidence is not None:
                confidence_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
            
            # Convert processing time to milliseconds
            processing_time_ms = None
            if processing_time is not None:
                processing_time_ms = int(processing_time * 1000) if processing_time < 100 else int(processing_time)
            
            # Create message
            message = ConversationMessage(
                conversation_id=conversation.id,
                role=role,
                content=content,
                query_id=query_id,
                confidence=confidence_pct,
                model_used=model_used,
                processing_time=processing_time_ms,
                reasoning_chain=reasoning_chain,
                citations=citations,
                follow_up_suggestions=follow_up_suggestions,
                message_metadata=metadata or {}
            )
            
            db.add(message)
            
            # Update conversation
            conversation.message_count += 1
            conversation.last_message_at = datetime.utcnow()
            conversation.updated_at = datetime.utcnow()
            
            # Auto-generate title from first user message
            if role == 'user' and conversation.message_count == 1 and not conversation.title:
                conversation.title = self._generate_title(content)
            
            db.commit()
            db.refresh(message)
            
            # Clear cache for this conversation
            self._clear_conversation_cache(conversation_id)
            
            logger.info(f"Added {role} message to conversation {conversation_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error adding message to conversation {conversation_id}: {e}")
            db.rollback()
            return None
    
    def get_conversation_messages(
        self,
        db: Session,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConversationMessage]:
        """Get messages for a conversation"""
        try:
            # Try in-memory cache first
            cache_key = f"conversation_messages:{conversation_id}:{limit}:{offset}"
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                # Simple TTL check
                if (datetime.utcnow() - cached_data['timestamp']).total_seconds() < self.cache_ttl:
                    return cached_data['messages']
                else:
                    # Cache expired
                    del self.cache[cache_key]

            # Get from database
            conversation = db.query(Conversation).filter(Conversation.uuid == conversation_id).first()
            if not conversation:
                return []
            
            messages = db.query(ConversationMessage)\
                .filter(ConversationMessage.conversation_id == conversation.id)\
                .order_by(ConversationMessage.created_at)\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            # Cache the result in memory
            if messages:
                self.cache[cache_key] = {
                    'messages': messages,
                    'timestamp': datetime.utcnow()
                }

            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
            return []
    
    def update_conversation(
        self,
        db: Session,
        conversation_id: str,
        title: Optional[str] = None,
        agent_mode: Optional[bool] = None,
        use_enhanced_rag: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Conversation]:
        """Update conversation settings"""
        try:
            conversation = db.query(Conversation).filter(Conversation.uuid == conversation_id).first()
            if not conversation:
                return None
            
            if title is not None:
                conversation.title = title
            if agent_mode is not None:
                conversation.agent_mode = agent_mode
            if use_enhanced_rag is not None:
                conversation.use_enhanced_rag = use_enhanced_rag
            if context is not None:
                conversation.context = context
            if is_active is not None:
                conversation.is_active = is_active
            
            conversation.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(conversation)
            
            # Clear cache
            self._clear_conversation_cache(conversation_id)
            
            return conversation
            
        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id}: {e}")
            db.rollback()
            return None
    
    def delete_conversation(
        self,
        db: Session,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a conversation and all its messages"""
        try:
            query = db.query(Conversation).filter(Conversation.uuid == conversation_id)
            
            if user_id:
                query = query.filter(Conversation.user_id == user_id)
            
            conversation = query.first()
            if not conversation:
                return False
            
            db.delete(conversation)  # Cascade will delete messages
            db.commit()
            
            # Clear cache
            self._clear_conversation_cache(conversation_id)
            
            logger.info(f"Deleted conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            db.rollback()
            return False
    
    def get_conversation_context(
        self,
        db: Session,
        conversation_id: str,
        include_messages: bool = True,
        message_limit: int = 10
    ) -> Dict[str, Any]:
        """Get conversation context for AI processing"""
        try:
            conversation = self.get_conversation(db, conversation_id)
            if not conversation:
                return {}
            
            context = {
                "conversation_id": str(conversation.uuid),
                "agent_mode": conversation.agent_mode,
                "use_enhanced_rag": conversation.use_enhanced_rag,
                "conversation_context": conversation.context or {},
                "message_count": conversation.message_count
            }
            
            if include_messages:
                messages = self.get_conversation_messages(db, conversation_id, limit=message_limit)
                context["message_history"] = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None
                    }
                    for msg in messages
                ]
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for conversation {conversation_id}: {e}")
            return {}
    
    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate a title from the first message"""
        # Simple title generation - take first few words
        words = first_message.strip().split()[:8]
        title = " ".join(words)
        
        if len(title) > max_length:
            title = title[:max_length-3] + "..."
        
        return title or "New Conversation"
    
    def _clear_conversation_cache(self, conversation_id: str):
        """Clear in-memory cache for a conversation"""
        try:
            # Clear all cached keys for this conversation
            keys_to_delete = [key for key in self.cache.keys() if f"conversation_messages:{conversation_id}:" in key]
            for key in keys_to_delete:
                del self.cache[key]
        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")

    def _message_to_dict(self, message: ConversationMessage) -> Dict[str, Any]:
        """Convert message to dictionary for caching"""
        return {
            "id": message.id,
            "uuid": str(message.uuid),
            "conversation_id": message.conversation_id,
            "role": message.role,
            "content": message.content,
            "query_id": str(message.query_id) if message.query_id else None,
            "confidence": message.confidence,
            "model_used": message.model_used,
            "processing_time": message.processing_time,
            "reasoning_chain": message.reasoning_chain,
            "citations": message.citations,
            "follow_up_suggestions": message.follow_up_suggestions,
            "message_metadata": message.message_metadata,
            "created_at": message.created_at.isoformat() if message.created_at else None
        }
