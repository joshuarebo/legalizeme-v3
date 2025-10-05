"""
Token Tracking Models for CounselAI
Handles user token limits and usage history tracking
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.sql import func
from app.database import Base
import uuid


class UserTokens(Base):
    """Track token usage limits per user"""
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    user_id = Column(String(255), unique=True, index=True, nullable=False)
    plan = Column(String(50), default="free", nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    tokens_limit = Column(Integer, default=100000, nullable=False)  # 100k tokens for free tier
    is_active = Column(Boolean, default=True, nullable=False)
    reset_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<UserTokens(user_id={self.user_id}, plan={self.plan}, used={self.tokens_used}/{self.tokens_limit})>"


class TokenUsageHistory(Base):
    """Track individual token usage events"""
    __tablename__ = "token_usage_history"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, default=lambda: str(uuid.uuid4()), nullable=False)
    user_id = Column(String(255), index=True, nullable=False)
    query = Column(String(2000), nullable=True)
    tokens_used = Column(Integer, nullable=False)
    model_used = Column(String(100), nullable=True)
    endpoint = Column(String(100), nullable=True)
    cost_usd = Column(Float, default=0.0, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<TokenUsageHistory(user_id={self.user_id}, tokens={self.tokens_used}, model={self.model_used})>"


# Token plan limits and pricing
TOKEN_PLANS = {
    "free": {
        "tokens_per_month": 100000,
        "name": "Free Plan",
        "price": 0,
        "features": ["Basic queries", "Standard response time", "Community support"]
    },
    "basic": {
        "tokens_per_month": 500000,
        "name": "Basic Plan",
        "price": 9.99,
        "features": ["Enhanced RAG", "Priority response", "Email support"]
    },
    "pro": {
        "tokens_per_month": 2000000,
        "name": "Pro Plan",
        "price": 29.99,
        "features": ["Agent mode", "Research mode", "Priority support", "Advanced analytics"]
    },
    "enterprise": {
        "tokens_per_month": 10000000,
        "name": "Enterprise Plan",
        "price": 99.99,
        "features": ["Unlimited queries", "Dedicated support", "Custom integrations", "SLA guarantee"]
    },
    "unlimited": {
        "tokens_per_month": 999999999,
        "name": "Unlimited Plan",
        "price": 0,
        "features": ["Unlimited everything", "Admin access"]
    }
}
