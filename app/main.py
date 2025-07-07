from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import uvicorn
from contextlib import asynccontextmanager
import logging
import sys
import os

from app.config import settings
from app.database import engine, Base, get_db
from app.api.routes import counsel, documents, auth, health
from app.core.middleware import setup_middleware
from app.services.crawler_service import CrawlerService
from app.services.vector_service import VectorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('counsel_ai.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize database
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Counsel AI Backend...")
    
    try:
        # Initialize services
        crawler_service = CrawlerService()
        vector_service = VectorService()
        
        # Initialize vector database
        await vector_service.initialize()
        
        # Start background tasks
        await crawler_service.start_periodic_crawling()
        
        logger.info("Counsel AI Backend started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down Counsel AI Backend...")
    try:
        await crawler_service.stop_periodic_crawling()
        logger.info("Counsel AI Backend shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="Counsel AI Backend",
    description="AI-powered legal assistant for Kenyan jurisdiction with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.legalizeme.site", "https://legalizeme.site", "http://localhost:3000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup custom middleware
setup_middleware(app)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(counsel.router, prefix="/counsel", tags=["counsel"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Counsel AI Backend is running",
        "version": "1.0.0",
        "status": "healthy",
        "features": [
            "AI-powered legal query answering",
            "Legal document generation",
            "RAG-enabled search",
            "Multi-model AI integration",
            "Kenyan jurisdiction specialization"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False,
        workers=1
    )
