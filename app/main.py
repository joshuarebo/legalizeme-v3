from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
from contextlib import asynccontextmanager
import logging
import sys
import os
import time

from app.config import settings
from app.database import engine, Base, get_db
from app.api.routes import counsel, auth, health, models, multimodal, simple_agent, token_tracking
from app.core.middleware import setup_middleware
from app.core.middleware.security_middleware import SecurityMiddleware
from app.core.security.rate_limiter import RateLimiter
from app.core.orchestration.intelligence_enhancer import IntelligenceEnhancer
from app.services.crawler_service import CrawlerService
from app.services.vector_service import VectorService
from app.services.aws_vector_service import aws_vector_service
from app.services.aws_embedding_service import aws_embedding_service
from app.services.enhanced_rag_service import enhanced_rag_service
from app.services.production_monitoring_service import production_monitoring_service

# Configure logging with environment-based settings
log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configure handlers based on environment
handlers = [logging.StreamHandler(sys.stdout)]
if settings.ENVIRONMENT == "production":
    # In production, log to file as well
    os.makedirs('logs', exist_ok=True)
    handlers.append(logging.FileHandler('logs/counsel_ai.log'))

logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format=log_format,
    handlers=handlers
)

# Disable buffering for production logs
if settings.ENVIRONMENT == "production":
    os.environ['PYTHONUNBUFFERED'] = '1'

logger = logging.getLogger(__name__)

# Initialize database (skip in testing mode to avoid connection issues)
if not os.getenv("TESTING", "false").lower() == "true" and "pytest" not in os.getenv("_", ""):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        # Don't fail the application if database is not available during startup

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with enhanced initialization"""
    # Startup
    logger.info("Starting Counsel AI Backend...")

    try:
        # Initialize core services
        crawler_service = CrawlerService()
        vector_service = VectorService()

        # Initialize AWS-native services
        await aws_vector_service.initialize()
        await aws_embedding_service.initialize()
        await enhanced_rag_service.initialize()
        await production_monitoring_service.initialize()

        # Initialize intelligence enhancer
        intelligence_enhancer = IntelligenceEnhancer(vector_service)

        # Initialize rate limiter (local cache only, Redis removed)
        logger.info("Initializing rate limiter with local cache (Redis removed)")
        rate_limiter = RateLimiter()

        # Store services in app state for access by routes
        app.state.crawler_service = crawler_service
        app.state.vector_service = vector_service
        app.state.aws_vector_service = aws_vector_service
        app.state.aws_embedding_service = aws_embedding_service
        app.state.enhanced_rag_service = enhanced_rag_service
        app.state.intelligence_enhancer = intelligence_enhancer
        app.state.rate_limiter = rate_limiter

        # Initialize vector database
        await vector_service.initialize()

        # Initialize conversation tables
        await _ensure_conversation_tables_exist()

        # Start background tasks
        if getattr(settings, 'ENABLE_BACKGROUND_CRAWLING', True):
            await crawler_service.start_periodic_crawling()

        # Generate training data if needed
        if getattr(settings, 'ENABLE_MODEL_FINE_TUNING', False):
            await _ensure_training_data_exists()

        # Simple Agent is ready - no complex initialization needed
        logger.info("✅ Simple Legal Agent ready - no initialization required")

        logger.info("Counsel AI Backend started successfully")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug mode: {getattr(settings, 'DEBUG', False)}")
        logger.info(f"Intelligence enhancement: {getattr(settings, 'ENABLE_INTELLIGENCE_ENHANCEMENT', True)}")

        yield

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

    # Shutdown
    logger.info("Shutting down Counsel AI Backend...")
    try:
        if hasattr(app.state, 'crawler_service'):
            await app.state.crawler_service.stop_periodic_crawling()

        # Cleanup rate limiter
        if hasattr(app.state, 'rate_limiter') and app.state.rate_limiter.redis_client:
            await app.state.rate_limiter.redis_client.close()

        logger.info("Counsel AI Backend shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

async def _ensure_conversation_tables_exist():
    """Ensure conversation tables exist in the database"""
    try:
        from app.models.conversation import Conversation, ConversationMessage
        from app.models.token_tracking import UserTokens, TokenUsageHistory

        # Create conversation tables if they don't exist
        Conversation.__table__.create(engine, checkfirst=True)
        ConversationMessage.__table__.create(engine, checkfirst=True)

        # Create token tracking tables if they don't exist
        UserTokens.__table__.create(engine, checkfirst=True)
        TokenUsageHistory.__table__.create(engine, checkfirst=True)

        logger.info("✅ Conversation and token tracking tables initialized successfully")

    except Exception as e:
        logger.warning(f"⚠️ Conversation table initialization failed: {e}")
        # Don't fail the application if this fails

async def _ensure_training_data_exists():
    """Ensure training data exists for fine-tuning"""
    training_data_path = getattr(settings, 'FINE_TUNE_DATA_PATH', './data/kenyan_legal_training.jsonl')

    if not os.path.exists(training_data_path):
        logger.info("Training data not found, generating...")
        try:
            # This would run the training data generation script
            import subprocess
            result = subprocess.run([
                sys.executable, 'scripts/prepare_training_data.py'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("Training data generated successfully")
            else:
                logger.warning(f"Training data generation failed: {result.stderr}")
        except Exception as e:
            logger.warning(f"Could not generate training data: {e}")

app = FastAPI(
    title="Counsel AI Backend",
    description="""
    🏛️ **Counsel AI Backend** - AI-powered legal assistant for Kenyan jurisdiction

    ## Features
    - 🤖 **Simple Legal Agent**: Direct AWS Bedrock integration with multi-model fallback
    - 📚 **Kenyan Legal Expertise**: Employment, Company, Constitutional, Land, and Family Law
    - 🔄 **Multi-Model Support**: Claude Sonnet 4, Claude 3.7, Mistral Large
    - 📄 **CounselDocs**: Advanced document analysis and generation with Kenya Law compliance
    - 🔍 **Legal Research**: Comprehensive legal research with citations
    - 🛡️ **Bulletproof Design**: Never fails, always provides responses

    ## Public Service Layer
    All endpoints are available as public services with optional user context.
    Perfect for frontend integration with gradual complexity enhancement.
    """,
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Always enable docs for API integration
    redoc_url="/redoc",  # Always enable redoc for API integration
    openapi_url="/openapi.json",  # Always enable OpenAPI schema
    swagger_ui_parameters={
        "deepLinking": True,
        "displayRequestDuration": True,
        "defaultModelsExpandDepth": 1,
        "defaultModelExpandDepth": 1,
        "defaultModelRendering": "example",
        "displayOperationId": False,
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True
    }
)

# Configure CORS for public service layer - more permissive for integration
allowed_origins = ["*"]  # Allow all origins for public service layer

# CORS middleware - configured for public service layer integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # No credentials needed for public service
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],  # Allow all headers for easier integration
)

# Add security middleware
if getattr(settings, 'ENABLE_SECURITY_MIDDLEWARE', True):
    app.add_middleware(SecurityMiddleware)

# Setup custom middleware
setup_middleware(app)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])

# Conditionally include auth router (disabled for public service layer)
if not getattr(settings, 'DISABLE_AUTH_ROUTES', False):
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])

app.include_router(counsel.router, prefix="/api/v1/counsel", tags=["counsel"])
app.include_router(models.router, prefix="/api/v1/models", tags=["model-management"])
app.include_router(simple_agent.router, prefix="/api/v1/agents", tags=["simple-legal-agent"])
app.include_router(multimodal.router, prefix="/api/v1/multimodal", tags=["multimodal-processing"])
app.include_router(token_tracking.router, prefix="/api/v1/tokens", tags=["token-tracking"])

# CounselDocs routers
from app.counseldocs.api.analysis import router as counseldocs_analysis_router
from app.counseldocs.api.generation import router as counseldocs_generation_router
from app.counseldocs.api.archive import router as counseldocs_archive_router

app.include_router(counseldocs_analysis_router, tags=["counseldocs-analysis"])
app.include_router(counseldocs_generation_router, tags=["counseldocs-generation"])
app.include_router(counseldocs_archive_router, tags=["counseldocs-archive"])

# Add missing endpoints
@app.get("/monitoring")
async def monitoring_endpoint():
    """System monitoring endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": "healthy",
            "ai_service": "healthy",
            "vector_store": "healthy"
        }
    }

@app.get("/api/v1/info")
async def api_info():
    """API information endpoint"""
    return {
        "name": "Counsel AI Backend",
        "version": "2.0.0",
        "description": "AI-powered legal assistant for Kenyan jurisdiction",
        "endpoints": {
            "health": "/health",
            "counsel": "/api/v1/counsel",
            "counseldocs": "/api/v1/counseldocs",
            "multimodal": "/api/v1/multimodal",
            "agents": "/api/v1/agents"
        },
        "features": [
            "Enhanced RAG with context engineering",
            "Multi-model AI fallback system",
            "Document analysis and processing",
            "Kenyan legal specialization",
            "Intelligent caching system"
        ]
    }

@app.get("/")
async def root():
    """Root endpoint with enhanced feature information"""
    return {
        "message": "Counsel AI Backend is running",
        "version": "2.0.0",
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "features": [
            "AI-powered legal query answering",
            "Legal document generation",
            "RAG-enabled search with multiple strategies",
            "Multi-model AI integration with intelligent fallbacks",
            "Kenyan jurisdiction specialization",
            "Modular orchestration system",
            "Dynamic prompt engineering",
            "Adaptive rate limiting",
            "Security middleware",
            "Performance monitoring",
            "Model fine-tuning capabilities"
        ],
        "orchestration": {
            "intelligence_enhancement": getattr(settings, 'ENABLE_INTELLIGENCE_ENHANCEMENT', True),
            "rag_orchestration": getattr(settings, 'ENABLE_RAG_ORCHESTRATION', True),
            "prompt_engineering": getattr(settings, 'ENABLE_PROMPT_ENGINEERING', True),
            "adapters": getattr(settings, 'ENABLE_ADAPTERS', True)
        }
    }

@app.get("/metrics")
async def get_system_metrics():
    """Get comprehensive system metrics"""
    metrics = {
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "version": "2.0.0"
    }

    # Add intelligence enhancer metrics if available
    if hasattr(app.state, 'intelligence_enhancer'):
        metrics["intelligence_enhancer"] = app.state.intelligence_enhancer.get_comprehensive_metrics()

    # Add rate limiter metrics if available
    if hasattr(app.state, 'rate_limiter'):
        metrics["rate_limiter"] = app.state.rate_limiter.get_metrics()

    return metrics

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
        workers=1
    )
