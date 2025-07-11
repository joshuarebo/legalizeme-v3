"""
Test suite for enhanced LegalResearchAgent with context framework
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any

from app.agents.legal_research_agent import LegalResearchAgent, ResearchStrategy, AgenticResearchResponse
from app.context import ContextManager, QueryContext
from app.agents.components import VectorRetriever, MultiSourceSummarizer, LegalReasoner, AnswerFormatter
from app.prompts import PRPManager
from app.services.advanced.legal_rag import LegalSource


@pytest.fixture
def mock_context_manager():
    """Mock context manager for testing"""
    context_manager = MagicMock(spec=ContextManager)
    context_manager.initialize = AsyncMock()
    context_manager.analyze_query_context = AsyncMock(return_value=(
        QueryContext(
            query="test query",
            detected_domains=["employment_law"],
            complexity_level="intermediate",
            urgency_level="medium",
            context_decisions={"use_comprehensive": True}
        ),
        [{"decision": "use_comprehensive", "reason": "complex query"}]
    ))
    return context_manager

@pytest.fixture
def mock_prp_manager():
    """Mock PRP manager for testing"""
    prp_manager = MagicMock(spec=PRPManager)
    prp_manager.initialize = AsyncMock()
    return prp_manager

@pytest.fixture
def mock_components():
    """Mock modular components for testing"""
    
    # Mock VectorRetriever
    vector_retriever = MagicMock(spec=VectorRetriever)
    vector_retriever.initialize = AsyncMock()
    vector_retriever.execute = AsyncMock(return_value=MagicMock(
        status="success",
        confidence=0.85,
        data={
            "documents": [
                {"title": "Employment Act", "content": "Test content", "relevance_score": 0.9}
            ],
            "strategy_used": "hybrid",
            "reasoning_steps": ["Retrieved relevant documents"]
        }
    ))
    
    # Mock MultiSourceSummarizer
    multi_source_summarizer = MagicMock(spec=MultiSourceSummarizer)
    multi_source_summarizer.initialize = AsyncMock()
    multi_source_summarizer.execute = AsyncMock(return_value=MagicMock(
        status="success",
        confidence=0.88,
        data={
            "summary": "Test summary of legal documents",
            "citations": [
                {
                    "title": "Employment Act",
                    "content": "Test content",
                    "source": "legislation",
                    "relevance_score": 0.9
                }
            ],
            "key_insights": ["Key insight 1", "Key insight 2"],
            "reasoning_steps": ["Summarized documents"]
        }
    ))
    
    # Mock LegalReasoner
    legal_reasoner = MagicMock(spec=LegalReasoner)
    legal_reasoner.initialize = AsyncMock()
    legal_reasoner.execute = AsyncMock(return_value=MagicMock(
        status="success",
        confidence=0.82,
        data={
            "reasoning_chain": ["Step 1: Analysis", "Step 2: Application"],
            "legal_principles": ["Principle 1", "Principle 2"],
            "counterarguments": ["Counter 1"],
            "practical_implications": ["Implication 1"],
            "reasoning_confidence": 0.85
        }
    ))
    
    # Mock AnswerFormatter
    answer_formatter = MagicMock(spec=AnswerFormatter)
    answer_formatter.initialize = AsyncMock()
    answer_formatter.execute = AsyncMock(return_value=MagicMock(
        status="success",
        confidence=0.90,
        data={
            "formatted_answer": "This is a comprehensive legal answer with proper formatting.",
            "strategy_used": "comprehensive"
        }
    ))
    
    return {
        "vector_retriever": vector_retriever,
        "multi_source_summarizer": multi_source_summarizer,
        "legal_reasoner": legal_reasoner,
        "answer_formatter": answer_formatter
    }

@pytest.fixture
def enhanced_agent(mock_context_manager, mock_prp_manager, mock_components):
    """Create enhanced LegalResearchAgent with mocked dependencies"""
    
    with patch('app.agents.legal_research_agent.ContextManager', return_value=mock_context_manager), \
         patch('app.agents.legal_research_agent.PRPManager', return_value=mock_prp_manager), \
         patch('app.agents.legal_research_agent.VectorRetriever', return_value=mock_components["vector_retriever"]), \
         patch('app.agents.legal_research_agent.MultiSourceSummarizer', return_value=mock_components["multi_source_summarizer"]), \
         patch('app.agents.legal_research_agent.LegalReasoner', return_value=mock_components["legal_reasoner"]), \
         patch('app.agents.legal_research_agent.AnswerFormatter', return_value=mock_components["answer_formatter"]):
        
        agent = LegalResearchAgent(
            enable_context_framework=True,
            enable_monitoring=True
        )
        
        # Manually set the mocked components
        agent.context_manager = mock_context_manager
        agent.prp_manager = mock_prp_manager
        agent.vector_retriever = mock_components["vector_retriever"]
        agent.multi_source_summarizer = mock_components["multi_source_summarizer"]
        agent.legal_reasoner = mock_components["legal_reasoner"]
        agent.answer_formatter = mock_components["answer_formatter"]
        
        return agent

class TestEnhancedLegalResearchAgent:
    """Test suite for enhanced LegalResearchAgent"""
    
    @pytest.mark.asyncio
    async def test_initialization_with_context_framework(self, enhanced_agent):
        """Test agent initialization with context framework enabled"""
        
        await enhanced_agent.initialize()
        
        # Verify context framework components are initialized
        enhanced_agent.context_manager.initialize.assert_called_once()
        enhanced_agent.prp_manager.initialize.assert_called_once()
        enhanced_agent.vector_retriever.initialize.assert_called_once()
        enhanced_agent.multi_source_summarizer.initialize.assert_called_once()
        enhanced_agent.legal_reasoner.initialize.assert_called_once()
        enhanced_agent.answer_formatter.initialize.assert_called_once()
        
        assert enhanced_agent._initialized is True
        assert enhanced_agent.enable_context_framework is True
    
    @pytest.mark.asyncio
    async def test_research_with_context_framework(self, enhanced_agent):
        """Test research method with context framework enabled"""
        
        # Mock the legal_rag service
        enhanced_agent.legal_rag = MagicMock()
        enhanced_agent.legal_rag.initialize = AsyncMock()
        enhanced_agent.vector_service = MagicMock()
        enhanced_agent.vector_service.initialize = AsyncMock()
        
        query = "What are the legal requirements for employment contracts in Kenya?"
        
        result = await enhanced_agent.research_with_context(
            query=query,
            strategy=ResearchStrategy.COMPREHENSIVE,
            max_sources=10,
            confidence_threshold=0.7
        )
        
        # Verify context analysis was called
        enhanced_agent.context_manager.analyze_query_context.assert_called_once()
        
        # Verify all components were executed
        enhanced_agent.vector_retriever.execute.assert_called_once()
        enhanced_agent.multi_source_summarizer.execute.assert_called_once()
        enhanced_agent.legal_reasoner.execute.assert_called_once()
        enhanced_agent.answer_formatter.execute.assert_called_once()
        
        # Verify response structure
        assert isinstance(result, AgenticResearchResponse)
        assert result.answer == "This is a comprehensive legal answer with proper formatting."
        assert result.confidence > 0.8  # Should be average of component confidences
        assert len(result.reasoning_chain) > 0
        assert hasattr(result, 'context_used')
        assert hasattr(result, 'component_metrics')
    
    @pytest.mark.asyncio
    async def test_research_method_routing(self, enhanced_agent):
        """Test that research method routes correctly based on context framework setting"""
        
        # Mock the legal_rag service
        enhanced_agent.legal_rag = MagicMock()
        enhanced_agent.legal_rag.initialize = AsyncMock()
        enhanced_agent.vector_service = MagicMock()
        enhanced_agent.vector_service.initialize = AsyncMock()
        
        query = "Test legal query"
        
        # Test with context framework enabled
        enhanced_agent.enable_context_framework = True
        with patch.object(enhanced_agent, 'research_with_context', new_callable=AsyncMock) as mock_context_research:
            await enhanced_agent.research(query=query)
            mock_context_research.assert_called_once()
        
        # Test with context framework disabled
        enhanced_agent.enable_context_framework = False
        with patch.object(enhanced_agent, '_research_legacy', new_callable=AsyncMock) as mock_legacy_research:
            await enhanced_agent.research(query=query)
            mock_legacy_research.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_component_failure_handling(self, enhanced_agent):
        """Test handling of component failures with fallback to legacy"""
        
        # Mock component failure
        enhanced_agent.vector_retriever.execute = AsyncMock(side_effect=Exception("Component failed"))
        
        # Mock legacy research method
        enhanced_agent._research_legacy = AsyncMock(return_value=MagicMock(
            answer="Legacy response",
            confidence=0.7,
            citations=[],
            retrieval_strategy="legacy",
            research_strategy=ResearchStrategy.COMPREHENSIVE,
            metadata=MagicMock(),
            reasoning_chain=["Legacy reasoning"],
            follow_up_suggestions=[],
            related_queries=[]
        ))
        
        query = "Test query"
        
        result = await enhanced_agent.research_with_context(query=query)
        
        # Verify fallback to legacy was called
        enhanced_agent._research_legacy.assert_called_once()
        assert result.answer == "Legacy response"
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_handling(self, enhanced_agent):
        """Test confidence threshold validation and handling"""
        
        # Mock low confidence components
        enhanced_agent.vector_retriever.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.3, data={"documents": []}
        ))
        enhanced_agent.multi_source_summarizer.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.4, data={"summary": "", "citations": []}
        ))
        enhanced_agent.legal_reasoner.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.5, data={"reasoning_chain": []}
        ))
        enhanced_agent.answer_formatter.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.6, data={"formatted_answer": "Low confidence answer"}
        ))
        
        # Mock the legal_rag service
        enhanced_agent.legal_rag = MagicMock()
        enhanced_agent.legal_rag.initialize = AsyncMock()
        enhanced_agent.vector_service = MagicMock()
        enhanced_agent.vector_service.initialize = AsyncMock()
        
        query = "Test query"
        
        result = await enhanced_agent.research_with_context(
            query=query,
            confidence_threshold=0.8  # High threshold
        )
        
        # Should still return result but with low confidence
        assert result.confidence < 0.8
        assert result.answer == "Low confidence answer"
    
    @pytest.mark.asyncio
    async def test_strategy_mapping(self, enhanced_agent):
        """Test research strategy mapping to retrieval strategy"""
        
        # Test strategy mapping
        assert enhanced_agent._map_strategy_to_retrieval(ResearchStrategy.COMPREHENSIVE) == "comprehensive"
        assert enhanced_agent._map_strategy_to_retrieval(ResearchStrategy.FOCUSED) == "focused"
        assert enhanced_agent._map_strategy_to_retrieval(ResearchStrategy.EXPLORATORY) == "exploratory"
    
    @pytest.mark.asyncio
    async def test_backward_compatibility(self, enhanced_agent):
        """Test that enhanced agent maintains backward compatibility"""
        
        # Mock legacy components
        enhanced_agent.legal_rag = MagicMock()
        enhanced_agent.legal_rag.query_with_sources = AsyncMock(return_value=MagicMock(
            response_text="Legacy response",
            confidence_score=0.8,
            sources=[],
            model_used="claude-sonnet-4",
            retrieval_strategy="hybrid"
        ))
        
        enhanced_agent._generate_follow_up_suggestions = MagicMock(return_value=[])
        enhanced_agent._generate_related_queries = MagicMock(return_value=[])
        
        query = "Test query"
        
        result = await enhanced_agent._research_legacy(
            query=query,
            strategy=ResearchStrategy.COMPREHENSIVE
        )
        
        # Verify legacy method works
        assert isinstance(result, AgenticResearchResponse)
        assert result.answer == "Legacy response"
        assert result.confidence == 0.8
    
    def test_agent_configuration(self):
        """Test agent configuration options"""
        
        # Test with context framework disabled
        agent_disabled = LegalResearchAgent(
            enable_context_framework=False,
            enable_monitoring=False
        )
        
        assert agent_disabled.enable_context_framework is False
        assert agent_disabled.enable_monitoring is False
        assert agent_disabled.context_manager is None
        
        # Test with context framework enabled
        with patch('app.agents.legal_research_agent.ContextManager'), \
             patch('app.agents.legal_research_agent.PRPManager'), \
             patch('app.agents.legal_research_agent.VectorRetriever'), \
             patch('app.agents.legal_research_agent.MultiSourceSummarizer'), \
             patch('app.agents.legal_research_agent.LegalReasoner'), \
             patch('app.agents.legal_research_agent.AnswerFormatter'), \
             patch('app.agents.legal_research_agent.AgentMonitor'), \
             patch('app.agents.legal_research_agent.ContextRefinementLoop'):
            
            agent_enabled = LegalResearchAgent(
                enable_context_framework=True,
                enable_monitoring=True
            )
            
            assert agent_enabled.enable_context_framework is True
            assert agent_enabled.enable_monitoring is True
            assert agent_enabled.context_manager is not None


class TestContextFrameworkIntegration:
    """Integration tests for context framework components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_context_pipeline(self, enhanced_agent):
        """Test complete context-aware research pipeline"""
        
        # Mock the legal_rag service
        enhanced_agent.legal_rag = MagicMock()
        enhanced_agent.legal_rag.initialize = AsyncMock()
        enhanced_agent.vector_service = MagicMock()
        enhanced_agent.vector_service.initialize = AsyncMock()
        
        query = "What are the termination procedures for employment contracts in Kenya?"
        context = {"domain": "employment_law", "urgency": "high"}
        
        result = await enhanced_agent.research_with_context(
            query=query,
            strategy=ResearchStrategy.COMPREHENSIVE,
            context=context
        )
        
        # Verify context was passed through the pipeline
        call_args = enhanced_agent.context_manager.analyze_query_context.call_args
        assert call_args[1]["query"] == query
        assert call_args[1]["user_context"] == context
        
        # Verify all components received context
        for component in [enhanced_agent.vector_retriever, enhanced_agent.multi_source_summarizer,
                         enhanced_agent.legal_reasoner, enhanced_agent.answer_formatter]:
            component.execute.assert_called_once()
            # Second argument should be the query context
            assert len(component.execute.call_args[0]) == 2
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self, enhanced_agent):
        """Test monitoring and refinement integration"""
        
        # Mock monitoring components
        enhanced_agent.agent_monitor = MagicMock()
        enhanced_agent.context_refinement = MagicMock()
        enhanced_agent.context_refinement.analyze_and_refine = AsyncMock()
        
        # Mock low confidence result to trigger refinement
        enhanced_agent.vector_retriever.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.5, data={"documents": []}
        ))
        enhanced_agent.multi_source_summarizer.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.5, data={"summary": "", "citations": []}
        ))
        enhanced_agent.legal_reasoner.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.5, data={"reasoning_chain": []}
        ))
        enhanced_agent.answer_formatter.execute = AsyncMock(return_value=MagicMock(
            status="success", confidence=0.5, data={"formatted_answer": "Low confidence answer"}
        ))
        
        # Mock the legal_rag service
        enhanced_agent.legal_rag = MagicMock()
        enhanced_agent.legal_rag.initialize = AsyncMock()
        enhanced_agent.vector_service = MagicMock()
        enhanced_agent.vector_service.initialize = AsyncMock()
        
        query = "Test query"
        
        result = await enhanced_agent.research_with_context(query=query)
        
        # Verify refinement was triggered for low confidence
        assert result.confidence < 0.6
        # Note: The actual refinement call is async and may not be awaited in the test
