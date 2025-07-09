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
