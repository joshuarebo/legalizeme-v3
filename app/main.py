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
from app.api.routes import counsel, documents, auth, health, models
from app.core.middleware import setup_middleware
from app.core.middleware.security_middleware import SecurityMiddleware
from app.core.security.rate_limiter import RateLimiter
from app.core.orchestration.intelligence_enhancer import IntelligenceEnhancer
from app.services.crawler_service import CrawlerService
from app.services.vector_service import VectorService

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

# Initialize database
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with enhanced initialization"""
    # Startup
    logger.info("Starting Counsel AI Backend...")

    try:
        # Initialize core services
        crawler_service = CrawlerService()
        vector_service = VectorService()

        # Initialize intelligence enhancer
        intelligence_enhancer = IntelligenceEnhancer(vector_service)

        # Initialize rate limiter
        rate_limiter = RateLimiter(getattr(settings, 'REDIS_URL', None))

        # Store services in app state for access by routes
        app.state.crawler_service = crawler_service
        app.state.vector_service = vector_service
        app.state.intelligence_enhancer = intelligence_enhancer
        app.state.rate_limiter = rate_limiter

        # Initialize vector database
        await vector_service.initialize()

        # Start background tasks
        if getattr(settings, 'ENABLE_BACKGROUND_CRAWLING', True):
            await crawler_service.start_periodic_crawling()

        # Generate training data if needed
        if getattr(settings, 'ENABLE_MODEL_FINE_TUNING', False):
            await _ensure_training_data_exists()

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
    description="AI-powered legal assistant for Kenyan jurisdiction with modular orchestration, RAG capabilities, and intelligent fallbacks",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if getattr(settings, 'DEBUG', False) else None,
    redoc_url="/redoc" if getattr(settings, 'DEBUG', False) else None,
    openapi_url="/openapi.json" if getattr(settings, 'DEBUG', False) else None
)

# Configure CORS based on environment
allowed_origins = []
if settings.ENVIRONMENT == "development":
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:8080",
        "http://127.0.0.1:3000"
    ]
elif settings.ENVIRONMENT == "production":
    # Get from environment variable or use defaults
    origins_str = getattr(settings, 'ALLOWED_ORIGINS', 'https://www.legalizeme.site,https://legalizeme.site')
    allowed_origins = [origin.strip() for origin in origins_str.split(',')]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=getattr(settings, 'ALLOWED_METHODS', 'GET,POST,PUT,DELETE,OPTIONS').split(','),
    allow_headers=getattr(settings, 'ALLOWED_HEADERS', 'Content-Type,Authorization,X-Requested-With').split(','),
)

# Add security middleware
if getattr(settings, 'ENABLE_SECURITY_MIDDLEWARE', True):
    app.add_middleware(SecurityMiddleware)

# Setup custom middleware
setup_middleware(app)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(counsel.router, prefix="/counsel", tags=["counsel"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(models.router, prefix="/models", tags=["model-management"])

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
