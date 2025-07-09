from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/counsel_db")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_counsel.db")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-super-secret-key-here-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # AWS Bedrock
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    # AWS Bedrock Model IDs (Production Ready - Access Granted)
    AWS_BEDROCK_MODEL_ID_PRIMARY: str = os.getenv("AWS_BEDROCK_MODEL_ID_PRIMARY", "us.anthropic.claude-sonnet-4-20250514-v1:0")
    AWS_BEDROCK_MODEL_ID_SECONDARY: str = os.getenv("AWS_BEDROCK_MODEL_ID_SECONDARY", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    AWS_BEDROCK_MODEL_ID_FALLBACK: str = os.getenv("AWS_BEDROCK_MODEL_ID_FALLBACK", "mistral.mistral-large-2402-v1:0")

    # AI Models
    HUGGING_FACE_TOKEN: Optional[str] = os.getenv("HUGGING_FACE_TOKEN")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Crawler Settings
    KENYA_LAW_BASE_URL: str = os.getenv("KENYA_LAW_BASE_URL", "https://new.kenyalaw.org")
    PARLIAMENT_BASE_URL: str = os.getenv("PARLIAMENT_BASE_URL", "http://parliament.go.ke")
    CRAWLER_DELAY: int = int(os.getenv("CRAWLER_DELAY", "2"))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    
    # Vector Database
    CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    # Application
    MAX_QUERY_LENGTH: int = int(os.getenv("MAX_QUERY_LENGTH", "2000"))
    MAX_DOCUMENT_SIZE: int = int(os.getenv("MAX_DOCUMENT_SIZE", "10485760"))  # 10MB

    # Model Management
    DEFAULT_AI_MODEL: str = os.getenv("DEFAULT_AI_MODEL", "claude-sonnet-4")
    FALLBACK_AI_MODEL: str = os.getenv("FALLBACK_AI_MODEL", "hunyuan")
    ENABLE_LOCAL_MODELS: bool = os.getenv("ENABLE_LOCAL_MODELS", "true").lower() == "true"
    ENABLE_MODEL_FINE_TUNING: bool = os.getenv("ENABLE_MODEL_FINE_TUNING", "true").lower() == "true"
    MODEL_HEALTH_CHECK_INTERVAL: int = int(os.getenv("MODEL_HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes
    MODEL_CACHE_TTL: int = int(os.getenv("MODEL_CACHE_TTL", "3600"))  # 1 hour
    MAX_MODEL_RETRIES: int = int(os.getenv("MAX_MODEL_RETRIES", "3"))
    MODEL_TIMEOUT: int = int(os.getenv("MODEL_TIMEOUT", "60"))  # seconds

    # Fine-tuning Configuration
    FINE_TUNE_BATCH_SIZE: int = int(os.getenv("FINE_TUNE_BATCH_SIZE", "2"))
    FINE_TUNE_EPOCHS: int = int(os.getenv("FINE_TUNE_EPOCHS", "3"))
    FINE_TUNE_LEARNING_RATE: float = float(os.getenv("FINE_TUNE_LEARNING_RATE", "5e-5"))
    FINE_TUNE_DATA_PATH: str = os.getenv("FINE_TUNE_DATA_PATH", "./data/kenyan_legal_training.jsonl")

    # Performance Monitoring
    ENABLE_PERFORMANCE_MONITORING: bool = os.getenv("ENABLE_PERFORMANCE_MONITORING", "true").lower() == "true"
    MAX_ERROR_RATE_THRESHOLD: float = float(os.getenv("MAX_ERROR_RATE_THRESHOLD", "0.3"))
    MAX_RESPONSE_TIME_THRESHOLD: float = float(os.getenv("MAX_RESPONSE_TIME_THRESHOLD", "60.0"))
    MONITORING_WINDOW_SIZE: int = int(os.getenv("MONITORING_WINDOW_SIZE", "100"))  # Number of requests to track

    # Orchestration Configuration
    ENABLE_INTELLIGENCE_ENHANCEMENT: bool = os.getenv("ENABLE_INTELLIGENCE_ENHANCEMENT", "true").lower() == "true"
    ENHANCEMENT_MODE: str = os.getenv("ENHANCEMENT_MODE", "standard")
    ENABLE_RAG_ORCHESTRATION: bool = os.getenv("ENABLE_RAG_ORCHESTRATION", "true").lower() == "true"
    ENABLE_PROMPT_ENGINEERING: bool = os.getenv("ENABLE_PROMPT_ENGINEERING", "true").lower() == "true"
    ENABLE_ADAPTERS: bool = os.getenv("ENABLE_ADAPTERS", "true").lower() == "true"
    RAG_RETRIEVAL_STRATEGY: str = os.getenv("RAG_RETRIEVAL_STRATEGY", "hybrid")
    PROMPT_STRATEGY: str = os.getenv("PROMPT_STRATEGY", "chain_of_thought")
    MAX_ENHANCEMENT_TIME: float = float(os.getenv("MAX_ENHANCEMENT_TIME", "30.0"))
    CACHE_ENHANCEMENTS: bool = os.getenv("CACHE_ENHANCEMENTS", "true").lower() == "true"

    # Security Configuration
    ENABLE_SECURITY_MIDDLEWARE: bool = os.getenv("ENABLE_SECURITY_MIDDLEWARE", "true").lower() == "true"
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", str(10 * 1024 * 1024)))  # 10MB
    ENABLE_REQUEST_LOGGING: bool = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
    ENABLE_SECURITY_HEADERS: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
    ENABLE_CONTENT_VALIDATION: bool = os.getenv("ENABLE_CONTENT_VALIDATION", "true").lower() == "true"

    # Background Tasks
    ENABLE_BACKGROUND_CRAWLING: bool = os.getenv("ENABLE_BACKGROUND_CRAWLING", "true").lower() == "true"

    # Deployment Configuration
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    ALLOWED_METHODS: str = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
    ALLOWED_HEADERS: str = os.getenv("ALLOWED_HEADERS", "Content-Type,Authorization,X-Requested-With")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env file

settings = Settings()
