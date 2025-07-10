"""
Test configuration and fixtures for Counsel AI Backend
"""
import pytest
import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set testing environment variables before importing app modules
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///./test_counsel.db"
os.environ["REDIS_URL"] = ""  # Disable Redis for testing
os.environ["AWS_ACCESS_KEY_ID"] = "test-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.main import app
from app.database import Base, engine, get_db

# Create test database engine
test_engine = create_engine(
    "sqlite:///./test_counsel.db",
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database tables before all tests"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    # Clean up test database file
    try:
        os.remove("./test_counsel.db")
    except FileNotFoundError:
        pass

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
def auth_headers():
    """Create authentication headers for testing"""
    # This would normally create a valid JWT token
    # For now, we'll use a mock token
    return {"Authorization": "Bearer test-token"}

# Agent-specific fixtures
@pytest.fixture
def mock_legal_rag_service():
    """Mock LegalRAGService for testing"""
    from unittest.mock import Mock, AsyncMock
    mock = Mock()
    mock.initialize = AsyncMock()
    mock.query_with_sources = AsyncMock()
    mock.get_metrics = Mock(return_value={
        "initialized": True,
        "has_chromadb": True,
        "success_rate": 0.9
    })
    mock._initialized = True
    return mock

@pytest.fixture
def mock_intelligence_enhancer():
    """Mock IntelligenceEnhancer for testing"""
    from unittest.mock import Mock, AsyncMock
    mock = Mock()
    mock.enhance_intelligence = AsyncMock(return_value={
        "enhanced_response": "Enhanced test response"
    })
    return mock

@pytest.fixture
def sample_legal_sources():
    """Sample legal sources for testing"""
    from app.services.advanced.legal_rag import LegalSource

    return [
        LegalSource(
            title="Constitution of Kenya 2010",
            source="constitution",
            url="https://example.com/constitution",
            document_type="constitution",
            relevance_score=0.95,
            excerpt="The Republic of Kenya is a multi-party democratic state...",
            citation="Constitution of Kenya, 2010, Article 1"
        ),
        LegalSource(
            title="Employment Act 2007",
            source="legislation",
            url="https://example.com/employment-act",
            document_type="legislation",
            relevance_score=0.88,
            excerpt="This Act applies to all employees and employers...",
            citation="Employment Act, 2007, Section 1"
        )
    ]

@pytest.fixture
def sample_rag_response(sample_legal_sources):
    """Sample RAG response for testing"""
    from app.services.advanced.legal_rag import RAGResponse

    return RAGResponse(
        response_text="Based on Kenyan law, employment contracts are governed by...",
        confidence_score=0.85,
        sources=sample_legal_sources,
        model_used="claude-sonnet-4",
        retrieval_strategy="hybrid",
        processing_time_ms=1500.0,
        total_documents_searched=25
    )
