"""
Unit tests for LegalResearchAgent
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from app.agents.legal_research_agent import (
    LegalResearchAgent, 
    ResearchStrategy, 
    AgenticResearchResponse,
    AgentMetadata,
    AgentMemory
)
from app.services.advanced.legal_rag import LegalSource, RAGResponse


class TestAgentMemory:
    """Test cases for AgentMemory class"""
    
    def test_memory_initialization_local(self):
        """Test memory initialization with local storage"""
        memory = AgentMemory()
        assert not memory.use_redis
        assert memory.max_memory_size == 100
        assert len(memory.local_memory) == 0
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_query_local(self):
        """Test storing and retrieving queries in local memory"""
        memory = AgentMemory(max_memory_size=5)
        
        # Store a query
        await memory.store_query("user1", "What is contract law?", {"context": "test"})
        
        # Retrieve queries
        queries = await memory.get_user_queries("user1", 10)
        assert len(queries) == 1
        assert queries[0]["query"] == "What is contract law?"
        assert queries[0]["user_id"] == "user1"
    
    @pytest.mark.asyncio
    async def test_memory_size_limit(self):
        """Test memory size limit enforcement"""
        memory = AgentMemory(max_memory_size=2)
        
        # Store more queries than limit
        await memory.store_query("user1", "Query 1", {})
        await memory.store_query("user1", "Query 2", {})
        await memory.store_query("user1", "Query 3", {})
        
        # Should only keep the last 2
        assert len(memory.local_memory) == 2
        queries = await memory.get_user_queries("user1", 10)
        assert len(queries) == 2
    
    @pytest.mark.asyncio
    async def test_related_queries(self):
        """Test finding related queries"""
        memory = AgentMemory()
        
        # Store related queries
        await memory.store_query("user1", "What is contract law in Kenya?", {})
        await memory.store_query("user1", "How to draft a contract?", {})
        await memory.store_query("user1", "Employment law basics", {})
        
        # Find related queries
        related = await memory.get_related_queries("user1", "contract formation rules", 5)
        
        # Should find contract-related queries
        contract_queries = [q for q in related if "contract" in q["query"].lower()]
        assert len(contract_queries) >= 2
    
    @pytest.mark.asyncio
    async def test_clear_user_memory(self):
        """Test clearing user memory"""
        memory = AgentMemory()
        
        # Store queries for different users
        await memory.store_query("user1", "Query 1", {})
        await memory.store_query("user2", "Query 2", {})
        
        # Clear user1's memory
        await memory.clear_user_memory("user1")
        
        # user1 should have no queries, user2 should still have queries
        user1_queries = await memory.get_user_queries("user1", 10)
        user2_queries = await memory.get_user_queries("user2", 10)
        
        assert len(user1_queries) == 0
        assert len(user2_queries) == 1


class TestLegalResearchAgent:
    """Test cases for LegalResearchAgent class"""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing"""
        mock_legal_rag = Mock()
        mock_intelligence_enhancer = Mock()
        mock_mcp_service = Mock()
        mock_ai_service = Mock()
        mock_vector_service = Mock()
        
        return {
            'legal_rag': mock_legal_rag,
            'intelligence_enhancer': mock_intelligence_enhancer,
            'mcp_service': mock_mcp_service,
            'ai_service': mock_ai_service,
            'vector_service': mock_vector_service
        }
    
    @pytest.fixture
    def agent(self, mock_services):
        """Create agent with mock services"""
        return LegalResearchAgent(
            legal_rag_service=mock_services['legal_rag'],
            intelligence_enhancer=mock_services['intelligence_enhancer'],
            mcp_service=mock_services['mcp_service'],
            ai_service=mock_services['ai_service'],
            vector_service=mock_services['vector_service']
        )
    
    def test_agent_initialization(self, agent):
        """Test agent initialization"""
        assert agent.default_confidence_threshold == 0.7
        assert agent.max_retry_attempts == 3
        assert agent.max_sources == 10
        assert agent.enable_memory is True
        assert not agent._initialized
    
    @pytest.mark.asyncio
    async def test_agent_initialize(self, agent, mock_services):
        """Test agent initialization"""
        # Mock the initialize methods
        mock_services['legal_rag'].initialize = AsyncMock()
        mock_services['vector_service'].initialize = AsyncMock()
        
        await agent.initialize()
        
        assert agent._initialized
        mock_services['legal_rag'].initialize.assert_called_once()
        mock_services['vector_service'].initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_quick_research_strategy(self, agent, mock_services):
        """Test quick research strategy"""
        # Mock RAG response
        mock_sources = [
            LegalSource(
                title="Test Document",
                source="test_source",
                relevance_score=0.8,
                excerpt="Test excerpt",
                document_type="legislation"
            )
        ]
        
        mock_rag_response = RAGResponse(
            response_text="Test response",
            confidence_score=0.9,
            sources=mock_sources,
            model_used="claude-sonnet-4",
            retrieval_strategy="semantic"
        )
        
        mock_services['legal_rag'].query_with_sources = AsyncMock(return_value=mock_rag_response)
        mock_services['legal_rag']._initialized = True
        mock_services['vector_service']._initialized = True
        
        # Test quick research
        result = await agent.run_research(
            query="What is contract law?",
            strategy=ResearchStrategy.QUICK,
            user_id="test_user"
        )
        
        assert isinstance(result, AgenticResearchResponse)
        assert result.answer == "Test response"
        assert result.confidence == 0.9
        assert result.research_strategy == ResearchStrategy.QUICK
        assert len(result.citations) == 1
        assert result.citations[0].title == "Test Document"
    
    @pytest.mark.asyncio
    async def test_comprehensive_research_strategy(self, agent, mock_services):
        """Test comprehensive research strategy"""
        # Mock RAG response
        mock_sources = [
            LegalSource(
                title="Comprehensive Document",
                source="comprehensive_source",
                relevance_score=0.9,
                excerpt="Comprehensive excerpt",
                document_type="case_law"
            )
        ]
        
        mock_rag_response = RAGResponse(
            response_text="Comprehensive response",
            confidence_score=0.85,
            sources=mock_sources,
            model_used="claude-sonnet-4",
            retrieval_strategy="hybrid"
        )
        
        mock_services['legal_rag'].query_with_sources = AsyncMock(return_value=mock_rag_response)
        mock_services['legal_rag']._initialized = True
        mock_services['vector_service']._initialized = True
        
        # Mock intelligence enhancer
        mock_services['intelligence_enhancer'].enhance_intelligence = AsyncMock(
            return_value={"enhanced_response": "Enhanced comprehensive response"}
        )
        
        # Test comprehensive research
        result = await agent.run_research(
            query="Explain employment law in Kenya",
            strategy=ResearchStrategy.COMPREHENSIVE,
            user_id="test_user"
        )
        
        assert isinstance(result, AgenticResearchResponse)
        assert result.research_strategy == ResearchStrategy.COMPREHENSIVE
        assert len(result.reasoning_chain) > 1  # Should have multiple reasoning steps
        assert "Enhanced comprehensive response" in result.answer
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_retry(self, agent, mock_services):
        """Test retry logic when confidence is below threshold"""
        # Mock low confidence response first
        low_confidence_sources = [
            LegalSource(
                title="Low Confidence Doc",
                source="low_source",
                relevance_score=0.3,
                excerpt="Low confidence excerpt",
                document_type="unknown"
            )
        ]
        
        low_confidence_response = RAGResponse(
            response_text="Low confidence response",
            confidence_score=0.4,  # Below default threshold of 0.7
            sources=low_confidence_sources,
            model_used="claude-sonnet-4",
            retrieval_strategy="semantic"
        )
        
        # Mock higher confidence response for retry
        high_confidence_sources = [
            LegalSource(
                title="High Confidence Doc",
                source="high_source",
                relevance_score=0.9,
                excerpt="High confidence excerpt",
                document_type="legislation"
            )
        ]
        
        high_confidence_response = RAGResponse(
            response_text="High confidence response",
            confidence_score=0.8,
            sources=high_confidence_sources,
            model_used="claude-sonnet-4",
            retrieval_strategy="hybrid"
        )
        
        # Mock services to return low confidence first, then high confidence
        mock_services['legal_rag'].query_with_sources = AsyncMock(
            side_effect=[low_confidence_response, high_confidence_response]
        )
        mock_services['legal_rag']._initialized = True
        mock_services['vector_service']._initialized = True
        
        # Test with confidence threshold
        result = await agent.run_research(
            query="Test query",
            confidence_threshold=0.7,
            user_id="test_user"
        )
        
        assert result.confidence >= 0.7
        assert result.metadata.retry_count > 0
        assert result.metadata.fallback_used
    
    @pytest.mark.asyncio
    async def test_error_handling(self, agent, mock_services):
        """Test error handling in research"""
        # Mock service to raise exception
        mock_services['legal_rag'].query_with_sources = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_services['legal_rag']._initialized = True
        mock_services['vector_service']._initialized = True
        
        # Test error handling
        result = await agent.run_research(
            query="Test query",
            user_id="test_user"
        )
        
        assert result.confidence == 0.0
        assert "error" in result.answer.lower()
        assert "Test error" in result.answer
    
    @pytest.mark.asyncio
    async def test_memory_integration(self, agent):
        """Test memory integration in research"""
        # Store some queries in memory first
        await agent.memory.store_query("test_user", "Previous contract question", {})
        await agent.memory.store_query("test_user", "Another contract query", {})
        
        # Mock services
        mock_sources = [LegalSource(
            title="Contract Document",
            source="contract_source",
            relevance_score=0.8,
            excerpt="Contract excerpt",
            document_type="contract"
        )]
        
        mock_rag_response = RAGResponse(
            response_text="Contract response with memory context",
            confidence_score=0.8,
            sources=mock_sources,
            model_used="claude-sonnet-4",
            retrieval_strategy="semantic"
        )
        
        agent.legal_rag.query_with_sources = AsyncMock(return_value=mock_rag_response)
        agent.legal_rag._initialized = True
        agent.vector_service._initialized = True
        
        # Test research with memory context
        result = await agent.run_research(
            query="New contract question",
            user_id="test_user"
        )
        
        # Verify memory was used
        assert agent.metrics["memory_usage"] > 0
        
        # Check that related queries were found and used
        user_memory = await agent.get_user_memory_summary("test_user")
        assert user_memory["recent_queries_count"] >= 3  # Previous 2 + current 1
    
    def test_metrics_tracking(self, agent):
        """Test metrics tracking"""
        initial_metrics = agent.get_metrics()
        
        assert "total_queries" in initial_metrics
        assert "successful_queries" in initial_metrics
        assert "strategy_usage" in initial_metrics
        assert "memory_stats" in initial_metrics
        assert initial_metrics["success_rate"] == 0.0  # No queries yet
    
    @pytest.mark.asyncio
    async def test_health_check(self, agent, mock_services):
        """Test agent health check"""
        # Mock service health checks
        mock_services['legal_rag'].get_metrics = Mock(return_value={
            "initialized": True,
            "has_chromadb": True,
            "success_rate": 0.9
        })
        mock_services['vector_service']._initialized = True
        mock_services['mcp_service'].health_check = AsyncMock(return_value={"success": True})
        
        health_status = await agent.health_check()
        
        assert "agent_status" in health_status
        assert "services" in health_status
        assert "timestamp" in health_status
        assert health_status["services"]["legal_rag"]["status"] == "healthy"


class TestAgentIntegration:
    """Integration tests for LegalResearchAgent"""

    @pytest.mark.asyncio
    async def test_end_to_end_research_flow(self):
        """Test complete research flow from query to response"""
        # This would be an integration test with real services
        # For now, we'll test the flow with mocked services

        agent = LegalResearchAgent()

        # Mock all services
        with patch.object(agent.legal_rag, 'initialize', new_callable=AsyncMock), \
             patch.object(agent.vector_service, 'initialize', new_callable=AsyncMock), \
             patch.object(agent.legal_rag, 'query_with_sources', new_callable=AsyncMock) as mock_query:

            # Setup mock response
            mock_sources = [
                LegalSource(
                    title="Kenya Constitution",
                    source="constitution",
                    relevance_score=0.95,
                    excerpt="Article on fundamental rights",
                    document_type="constitution",
                    citation="Constitution of Kenya, 2010, Article 19"
                )
            ]

            mock_response = RAGResponse(
                response_text="The Constitution of Kenya guarantees fundamental rights...",
                confidence_score=0.9,
                sources=mock_sources,
                model_used="claude-sonnet-4",
                retrieval_strategy="hybrid"
            )

            mock_query.return_value = mock_response
            agent.legal_rag._initialized = True
            agent.vector_service._initialized = True

            # Perform research
            result = await agent.run_research(
                query="What are the fundamental rights in Kenya?",
                strategy=ResearchStrategy.COMPREHENSIVE,
                user_id="integration_test_user"
            )

            # Verify complete response structure
            assert isinstance(result, AgenticResearchResponse)
            assert result.answer
            assert result.confidence > 0.8
            assert len(result.citations) > 0
            assert result.citations[0].citation
            assert len(result.reasoning_chain) > 0
            assert len(result.follow_up_suggestions) > 0
            assert len(result.related_queries) > 0

    @pytest.mark.asyncio
    async def test_multiple_user_memory_isolation(self):
        """Test that memory is properly isolated between users"""
        agent = LegalResearchAgent()

        # Store queries for different users
        await agent.memory.store_query("user1", "Contract law question", {"type": "contract"})
        await agent.memory.store_query("user2", "Employment law question", {"type": "employment"})
        await agent.memory.store_query("user1", "Another contract question", {"type": "contract"})

        # Get memory for each user
        user1_memory = await agent.get_user_memory_summary("user1")
        user2_memory = await agent.get_user_memory_summary("user2")

        # Verify isolation
        assert user1_memory["recent_queries_count"] == 2
        assert user2_memory["recent_queries_count"] == 1

        # Verify content isolation
        user1_queries = user1_memory["recent_queries"]
        user2_queries = user2_memory["recent_queries"]

        assert all("contract" in q["query"].lower() for q in user1_queries)
        assert all("employment" in q["query"].lower() for q in user2_queries)

    @pytest.mark.asyncio
    async def test_research_strategy_differences(self):
        """Test that different research strategies produce different behaviors"""
        agent = LegalResearchAgent()

        # Mock services
        with patch.object(agent.legal_rag, 'query_with_sources', new_callable=AsyncMock) as mock_query:
            mock_sources = [LegalSource(
                title="Test Document",
                source="test",
                relevance_score=0.8,
                excerpt="Test excerpt",
                document_type="legislation"
            )]

            mock_response = RAGResponse(
                response_text="Test response",
                confidence_score=0.8,
                sources=mock_sources,
                model_used="claude-sonnet-4",
                retrieval_strategy="semantic"
            )

            mock_query.return_value = mock_response
            agent.legal_rag._initialized = True
            agent.vector_service._initialized = True

            # Test different strategies
            quick_result = await agent.run_research(
                "Test query",
                ResearchStrategy.QUICK,
                user_id="test"
            )

            comprehensive_result = await agent.run_research(
                "Test query",
                ResearchStrategy.COMPREHENSIVE,
                user_id="test"
            )

            focused_result = await agent.run_research(
                "Test query",
                ResearchStrategy.FOCUSED,
                user_id="test"
            )

            exploratory_result = await agent.run_research(
                "Test query",
                ResearchStrategy.EXPLORATORY,
                user_id="test"
            )

            # Verify different strategies
            strategies = [
                quick_result.research_strategy,
                comprehensive_result.research_strategy,
                focused_result.research_strategy,
                exploratory_result.research_strategy
            ]

            assert len(set(strategies)) == 4  # All different strategies

            # Comprehensive should have more reasoning steps
            assert len(comprehensive_result.reasoning_chain) >= len(quick_result.reasoning_chain)

    @pytest.mark.asyncio
    async def test_confidence_threshold_edge_cases(self):
        """Test edge cases for confidence thresholds"""
        agent = LegalResearchAgent()

        with patch.object(agent.legal_rag, 'query_with_sources', new_callable=AsyncMock) as mock_query:
            # Test with exactly threshold confidence
            mock_sources = [LegalSource(
                title="Threshold Test",
                source="test",
                relevance_score=0.7,
                excerpt="Threshold excerpt",
                document_type="test"
            )]

            threshold_response = RAGResponse(
                response_text="Threshold response",
                confidence_score=0.7,  # Exactly at threshold
                sources=mock_sources,
                model_used="claude-sonnet-4",
                retrieval_strategy="semantic"
            )

            mock_query.return_value = threshold_response
            agent.legal_rag._initialized = True
            agent.vector_service._initialized = True

            # Test with threshold = 0.7 (should not retry)
            result = await agent.run_research(
                "Test query",
                confidence_threshold=0.7,
                user_id="test"
            )

            assert result.confidence == 0.7
            assert result.metadata.retry_count == 0

            # Test with threshold = 0.8 (should retry)
            result = await agent.run_research(
                "Test query",
                confidence_threshold=0.8,
                user_id="test"
            )

            # Should have attempted retry
            assert result.metadata.retry_count > 0 or result.metadata.fallback_used


class TestAgentErrorScenarios:
    """Test error scenarios and edge cases"""

    @pytest.mark.asyncio
    async def test_service_initialization_failure(self):
        """Test handling of service initialization failures"""
        agent = LegalResearchAgent()

        # Mock initialization failure
        with patch.object(agent.legal_rag, 'initialize', side_effect=Exception("Init failed")):
            with pytest.raises(Exception):
                await agent.initialize()

    @pytest.mark.asyncio
    async def test_empty_query_handling(self):
        """Test handling of empty or invalid queries"""
        agent = LegalResearchAgent()

        with patch.object(agent.legal_rag, 'query_with_sources', new_callable=AsyncMock) as mock_query:
            # Mock empty response
            empty_response = RAGResponse(
                response_text="I couldn't find relevant legal documents to answer your question.",
                confidence_score=0.0,
                sources=[],
                model_used="claude-sonnet-4",
                retrieval_strategy="semantic"
            )

            mock_query.return_value = empty_response
            agent.legal_rag._initialized = True
            agent.vector_service._initialized = True

            # Test with empty query
            result = await agent.run_research("", user_id="test")

            assert result.confidence == 0.0
            assert len(result.citations) == 0

    @pytest.mark.asyncio
    async def test_memory_failure_graceful_degradation(self):
        """Test graceful degradation when memory operations fail"""
        agent = LegalResearchAgent()

        # Mock memory failure
        with patch.object(agent.memory, 'store_query', side_effect=Exception("Memory failed")):
            with patch.object(agent.legal_rag, 'query_with_sources', new_callable=AsyncMock) as mock_query:
                mock_sources = [LegalSource(
                    title="Test",
                    source="test",
                    relevance_score=0.8,
                    excerpt="Test",
                    document_type="test"
                )]

                mock_response = RAGResponse(
                    response_text="Test response",
                    confidence_score=0.8,
                    sources=mock_sources,
                    model_used="claude-sonnet-4",
                    retrieval_strategy="semantic"
                )

                mock_query.return_value = mock_response
                agent.legal_rag._initialized = True
                agent.vector_service._initialized = True

                # Should still work despite memory failure
                result = await agent.run_research("Test query", user_id="test")

                assert result.confidence > 0
                assert result.answer == "Test response"
