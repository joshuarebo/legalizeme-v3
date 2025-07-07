import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "version" in data

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Counsel AI Backend is running"
    assert data["version"] == "1.0.0"
    assert "features" in data

def test_query_endpoint_unauthorized():
    """Test query endpoint without authentication"""
    response = client.post("/counsel/query", json={
        "query": "What is employment law in Kenya?"
    })
    assert response.status_code == 403

def test_generate_document_unauthorized():
    """Test document generation without authentication"""
    response = client.post("/counsel/generate-document", json={
        "document_type": "employment_contract",
        "parameters": {}
    })
    assert response.status_code == 403

def test_summarize_endpoint_unauthorized():
    """Test summarize endpoint without authentication"""
    response = client.post("/counsel/summarize", json={
        "content": "Legal document text",
        "context": "contract"
    })
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_register_user():
    """Test user registration"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User"
        })
        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == "test@example.com"
        assert "access_token" in data

@pytest.mark.asyncio
async def test_login_user():
    """Test user login"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First register
        await ac.post("/auth/register", json={
            "email": "login@example.com",
            "password": "SecurePass123!",
            "full_name": "Login User"
        })
        
        # Then login
        response = await ac.post("/auth/login", json={
            "email": "login@example.com",
            "password": "SecurePass123!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"