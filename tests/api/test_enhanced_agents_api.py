"""
Integration tests for enhanced agents API endpoints
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.agents.legal_research_agent import LegalResearchAgent, ResearchStrategy, AgenticResearchResponse
from app.models.user import User


@pytest.fixture
def client():
    """Test client for API testing"""
    return TestClient(app)

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.is_active = True
    return user

@pytest.fixture
def mock_agent_response():
    """Mock agent response for testing"""
    from app.services.advanced.legal_rag import LegalSource
    
    metadata = MagicMock()
    metadata.timestamp = datetime.utcnow()
    metadata.model_used = "claude-sonnet-4"
    metadata.retrieval_strategy = "hybrid"
    metadata.research_strategy = ResearchStrategy.COMPREHENSIVE
    metadata.processing_time_ms = 1500.0
    metadata.sources_consulted = 5
    metadata.confidence_threshold = 0.7
    metadata.retry_count = 0
    metadata.fallback_used = False
    
    return AgenticResearchResponse(
        answer="This is a comprehensive legal analysis of employment contract requirements in Kenya...",
        confidence=0.85,
        citations=[
            LegalSource(
                title="Employment Act 2007",
                source="legislation",
                url="https://example.com/employment-act",
                document_type="legislation",
                relevance_score=0.92,
                excerpt="Employment contracts must specify...",
                citation="Employment Act, 2007, Section 9"
            )
        ],
        retrieval_strategy="hybrid",
        research_strategy=ResearchStrategy.COMPREHENSIVE,
        metadata=metadata,
        reasoning_chain=[
            "Context analysis completed: 3 decisions made",
            "Retrieved 5 relevant documents",
            "Applied comprehensive legal reasoning",
            "Formatted response with citations"
        ],
        follow_up_suggestions=[
            "What are the penalties for non-compliance?",
            "How do probationary periods work?"
        ],
        related_queries=[
            "Employment termination procedures",
            "Minimum wage requirements"
        ],
        context_used={
            "detected_domains": ["employment_law"],
            "complexity_level": "intermediate",
            "urgency_level": "medium"
        },
        component_metrics={
            "retrieval_confidence": 0.88,
            "summarization_confidence": 0.82,
            "reasoning_confidence": 0.85,
            "formatting_confidence": 0.87
        }
    )


class TestEnhancedAgentsAPI:
    """Test suite for enhanced agents API endpoints"""
    
    @patch('app.api.routes.agents.get_current_user')
    @patch('app.api.routes.agents.get_db')
    @patch('app.api.routes.agents.legal_research_agent')
    def test_agent_research_endpoint(self, mock_agent, mock_db, mock_auth, client, mock_user, mock_agent_response):
        """Test /agents/research endpoint with context framework"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = MagicMock()
        
        # Mock agent
        mock_agent._initialized = True
        mock_agent.enable_context_framework = True
        mock_agent.research = AsyncMock(return_value=mock_agent_response)
        
        # Test request
        request_data = {
            "query": "What are the legal requirements for employment contracts in Kenya?",
            "strategy": "comprehensive",
            "max_sources": 10,
            "confidence_threshold": 0.7,
            "enable_context_framework": True,
            "context": {
                "domain": "employment_law",
                "urgency": "high"
            }
        }
        
        response = client.post("/api/v1/agents/research", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["answer"] == mock_agent_response.answer
        assert data["confidence"] == mock_agent_response.confidence
        assert data["research_strategy"] == "comprehensive"
        assert len(data["citations"]) == 1
        assert len(data["reasoning_chain"]) == 4
        assert data["context_used"] is not None
        assert data["component_metrics"] is not None
        
        # Verify agent was called correctly
        mock_agent.research.assert_called_once()
        call_args = mock_agent.research.call_args
        assert call_args[1]["query"] == request_data["query"]
        assert call_args[1]["strategy"] == ResearchStrategy.COMPREHENSIVE
        assert call_args[1]["max_sources"] == 10
        assert call_args[1]["confidence_threshold"] == 0.7
    
    @patch('app.api.routes.agents.get_current_user')
    @patch('app.api.routes.agents.legal_research_agent')
    def test_agent_health_endpoint(self, mock_agent, mock_auth, client, mock_user):
        """Test /agents/health endpoint"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_agent._initialized = True
        mock_agent.enable_context_framework = True
        mock_agent.health_check = AsyncMock(return_value={
            "status": "healthy",
            "services": {
                "legal_rag": {"status": "healthy"},
                "vector_service": {"status": "healthy"}
            }
        })
        
        # Mock components
        mock_agent.vector_retriever = MagicMock()
        mock_agent.vector_retriever.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_agent.multi_source_summarizer = MagicMock()
        mock_agent.multi_source_summarizer.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_agent.legal_reasoner = MagicMock()
        mock_agent.legal_reasoner.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_agent.answer_formatter = MagicMock()
        mock_agent.answer_formatter.health_check = AsyncMock(return_value={"status": "healthy"})
        
        mock_agent.metrics = {"total_queries": 100, "success_rate": 0.95}
        
        response = client.get("/api/v1/agents/health")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["agent_available"] is True
        assert data["context_framework_enabled"] is True
        assert "components_status" in data
        assert "metrics" in data
    
    @patch('app.api.routes.agents.get_current_user')
    @patch('app.api.routes.agents.legal_research_agent')
    def test_agent_metrics_endpoint(self, mock_agent, mock_auth, client, mock_user):
        """Test /agents/metrics endpoint"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_agent.metrics = {
            "total_queries": 150,
            "successful_queries": 142,
            "success_rate": 0.947,
            "avg_confidence": 0.82
        }
        
        # Mock context manager metrics
        mock_agent.context_manager = MagicMock()
        mock_agent.context_manager.get_context_metrics = MagicMock(return_value={
            "total_contexts_analyzed": 150,
            "avg_complexity_score": 0.65,
            "domain_distribution": {"employment_law": 45, "contract_law": 30}
        })
        
        # Mock component metrics
        mock_agent.enable_context_framework = True
        mock_agent.vector_retriever = MagicMock()
        mock_agent.vector_retriever.get_metrics = MagicMock(return_value={"avg_retrieval_time": 250})
        mock_agent.multi_source_summarizer = MagicMock()
        mock_agent.multi_source_summarizer.get_metrics = MagicMock(return_value={"avg_summary_length": 500})
        mock_agent.legal_reasoner = MagicMock()
        mock_agent.legal_reasoner.get_metrics = MagicMock(return_value={"avg_reasoning_steps": 5})
        mock_agent.answer_formatter = MagicMock()
        mock_agent.answer_formatter.get_metrics = MagicMock(return_value={"avg_format_time": 100})
        
        # Mock monitoring metrics
        mock_agent.agent_monitor = MagicMock()
        mock_agent.agent_monitor.get_failure_statistics = MagicMock(return_value={
            "total_failures": 8,
            "failure_stages": {"retrieval": 3, "reasoning": 2}
        })
        mock_agent.agent_monitor.get_quality_statistics = MagicMock(return_value={
            "average_quality": 0.85,
            "quality_trend": "stable"
        })
        
        response = client.get("/api/v1/agents/metrics")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "metrics" in data
        assert data["metrics"]["agent"]["total_queries"] == 150
        assert data["metrics"]["context_manager"]["total_contexts_analyzed"] == 150
        assert "components" in data["metrics"]
        assert "monitoring" in data["metrics"]
    
    @patch('app.api.routes.agents.get_current_user')
    @patch('app.api.routes.agents.legal_research_agent')
    def test_benchmark_endpoint(self, mock_agent, mock_auth, client, mock_user):
        """Test /agents/benchmark endpoint"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_agent._initialized = True
        
        # Mock benchmark manager
        with patch('app.api.routes.agents.BenchmarkManager') as mock_benchmark_class:
            mock_benchmark = MagicMock()
            mock_benchmark_class.return_value = mock_benchmark
            mock_benchmark.initialize = AsyncMock()
            mock_benchmark.run_benchmark_suite = AsyncMock(return_value={
                "total_cases": 5,
                "suite_results": [
                    MagicMock(
                        case_id="emp_001",
                        status=MagicMock(value="completed"),
                        score=0.92,
                        confidence=0.88,
                        execution_time_ms=1200,
                        accuracy_score=0.95,
                        completeness_score=0.90,
                        reasoning_score=0.88,
                        citation_score=0.94
                    )
                ],
                "statistics": {
                    "completion_rate": 1.0,
                    "average_score": 0.92,
                    "pass_rate": 1.0
                }
            })
            
            request_data = {
                "level": 2,
                "category": "employment_law",
                "max_cases": 5
            }
            
            response = client.post("/api/v1/agents/benchmark", json=request_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_cases"] == 5
            assert data["completion_rate"] == 1.0
            assert data["average_score"] == 0.92
            assert data["pass_rate"] == 1.0
            assert len(data["results"]) == 1
            assert data["results"][0]["case_id"] == "emp_001"
    
    @patch('app.api.routes.agents.get_current_user')
    @patch('app.api.routes.agents.get_db')
    @patch('app.api.routes.agents.legal_research_agent')
    def test_agent_research_error_handling(self, mock_agent, mock_db, mock_auth, client, mock_user):
        """Test error handling in agent research endpoint"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = MagicMock()
        
        # Mock agent failure
        mock_agent._initialized = True
        mock_agent.research = AsyncMock(side_effect=Exception("Agent processing failed"))
        
        request_data = {
            "query": "Test query",
            "strategy": "comprehensive"
        }
        
        response = client.post("/api/v1/agents/research", json=request_data)
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert "Agent research failed" in data["detail"]
    
    @patch('app.api.routes.agents.get_current_user')
    def test_agent_unavailable_handling(self, mock_auth, client, mock_user):
        """Test handling when agent is not available"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        
        # Mock agent as unavailable
        with patch('app.api.routes.agents.HAS_AGENT', False), \
             patch('app.api.routes.agents.legal_research_agent', None):
            
            response = client.post("/api/v1/agents/research", json={"query": "test"})
            
            # Verify service unavailable response
            assert response.status_code == 503
            data = response.json()
            assert "Legal Research Agent is not available" in data["detail"]
    
    @patch('app.api.routes.agents.get_current_user')
    @patch('app.api.routes.agents.get_db')
    @patch('app.api.routes.agents.legal_research_agent')
    def test_request_validation(self, mock_agent, mock_db, mock_auth, client, mock_user):
        """Test request validation for agent endpoints"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = MagicMock()
        
        # Test invalid strategy
        response = client.post("/api/v1/agents/research", json={
            "query": "test",
            "strategy": "invalid_strategy"
        })
        assert response.status_code == 422
        
        # Test missing query
        response = client.post("/api/v1/agents/research", json={
            "strategy": "comprehensive"
        })
        assert response.status_code == 422
        
        # Test invalid confidence threshold
        response = client.post("/api/v1/agents/research", json={
            "query": "test",
            "confidence_threshold": 1.5  # > 1.0
        })
        assert response.status_code == 422
        
        # Test invalid max_sources
        response = client.post("/api/v1/agents/research", json={
            "query": "test",
            "max_sources": 0  # < 1
        })
        assert response.status_code == 422


class TestCounselQueryEnhancement:
    """Test enhanced counsel query endpoint with agent_mode"""
    
    @patch('app.api.routes.counsel.get_current_user')
    @patch('app.api.routes.counsel.get_db')
    @patch('app.api.routes.counsel.legal_research_agent')
    def test_counsel_query_with_agent_mode(self, mock_agent, mock_db, mock_auth, client, mock_user, mock_agent_response):
        """Test counsel query endpoint with agent_mode enabled"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = MagicMock()
        
        # Mock agent
        mock_agent.run_research = AsyncMock(return_value=mock_agent_response)
        
        request_data = {
            "query": "What are employment termination procedures in Kenya?",
            "agent_mode": True,
            "use_enhanced_rag": True,
            "context": {
                "domain": "employment_law"
            }
        }
        
        response = client.post("/api/v1/counsel/query", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_mode"] is True
        assert data["answer"] == mock_agent_response.answer
        assert data["confidence"] == mock_agent_response.confidence
        assert data["research_strategy"] == "comprehensive"
        assert len(data["reasoning_chain"]) > 0
    
    @patch('app.api.routes.counsel.get_current_user')
    @patch('app.api.routes.counsel.get_db')
    @patch('app.api.routes.counsel.legal_research_agent')
    def test_counsel_query_agent_fallback(self, mock_agent, mock_db, mock_auth, client, mock_user):
        """Test counsel query fallback when agent fails"""
        
        # Setup mocks
        mock_auth.return_value = mock_user
        mock_db.return_value = MagicMock()
        
        # Mock agent failure
        mock_agent.run_research = AsyncMock(side_effect=Exception("Agent failed"))
        
        # Mock enhanced RAG fallback
        with patch('app.api.routes.counsel.LegalRAGService') as mock_rag_class:
            mock_rag = MagicMock()
            mock_rag_class.return_value = mock_rag
            mock_rag.initialize = AsyncMock()
            mock_rag.query_with_sources = AsyncMock(return_value=MagicMock(
                response_text="Fallback response",
                confidence_score=0.75,
                sources=[],
                retrieval_strategy="hybrid"
            ))
            
            request_data = {
                "query": "Test query",
                "agent_mode": True,
                "use_enhanced_rag": True
            }
            
            response = client.post("/api/v1/counsel/query", json=request_data)
            
            # Verify fallback response
            assert response.status_code == 200
            data = response.json()
            
            assert data["agent_mode"] is False  # Agent failed, fell back
            assert data["enhanced"] is True     # Used enhanced RAG
            assert data["answer"] == "Fallback response"
