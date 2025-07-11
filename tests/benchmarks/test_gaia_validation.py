"""
GAIA-style benchmark validation tests for LegalResearchAgent
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from tests.gaia_cases import BenchmarkManager, BenchmarkCase, BenchmarkResult, BenchmarkStatus
from app.agents.legal_research_agent import LegalResearchAgent, ResearchStrategy


@pytest.fixture
def mock_agent():
    """Mock LegalResearchAgent for testing"""
    agent = MagicMock(spec=LegalResearchAgent)
    agent._initialized = True
    agent.research = AsyncMock()
    agent.initialize = AsyncMock()
    return agent

@pytest.fixture
def sample_benchmark_cases():
    """Sample benchmark cases for testing"""
    return [
        BenchmarkCase(
            case_id="emp_001",
            level=1,
            category="employment_law",
            query="What is the minimum notice period for employment termination in Kenya?",
            ground_truth="The minimum notice period is 28 days for employees who have worked for more than 6 months.",
            evaluation_criteria={
                "must_mention_28_days": True,
                "must_mention_6_months": True,
                "must_reference_employment_act": True
            },
            context={"domain": "employment_law", "complexity": "basic"},
            expected_confidence=0.8,
            max_execution_time_ms=5000
        ),
        BenchmarkCase(
            case_id="contract_002",
            level=2,
            category="contract_law",
            query="What are the essential elements of a valid contract under Kenyan law?",
            ground_truth="A valid contract requires: offer, acceptance, consideration, intention to create legal relations, and capacity of parties.",
            evaluation_criteria={
                "must_mention_offer": True,
                "must_mention_acceptance": True,
                "must_mention_consideration": True,
                "must_mention_intention": True,
                "must_mention_capacity": True
            },
            context={"domain": "contract_law", "complexity": "intermediate"},
            expected_confidence=0.75,
            max_execution_time_ms=7000
        ),
        BenchmarkCase(
            case_id="property_003",
            level=3,
            category="property_law",
            query="Analyze the legal implications of adverse possession under the Land Registration Act 2012.",
            ground_truth="Adverse possession requires 12 years of continuous, open, and notorious possession. The Land Registration Act 2012 modified traditional adverse possession rules.",
            evaluation_criteria={
                "must_mention_12_years": True,
                "must_mention_continuous_possession": True,
                "must_mention_land_registration_act": True,
                "must_analyze_implications": True,
                "must_show_legal_reasoning": True
            },
            context={"domain": "property_law", "complexity": "advanced"},
            expected_confidence=0.7,
            max_execution_time_ms=10000
        )
    ]


class TestBenchmarkManager:
    """Test suite for BenchmarkManager"""
    
    @pytest.mark.asyncio
    async def test_benchmark_manager_initialization(self):
        """Test BenchmarkManager initialization"""
        
        with patch('tests.gaia_cases.benchmark_manager.Path.exists', return_value=True), \
             patch('tests.gaia_cases.benchmark_manager.yaml.safe_load', return_value={}):
            
            manager = BenchmarkManager()
            await manager.initialize()
            
            assert manager._initialized is True
    
    @pytest.mark.asyncio
    async def test_load_benchmark_cases(self, sample_benchmark_cases):
        """Test loading benchmark cases"""
        
        mock_cases_data = [
            {
                "case_id": "emp_001",
                "level": 1,
                "category": "employment_law",
                "query": "Test query",
                "ground_truth": "Test answer",
                "evaluation_criteria": {"test": True},
                "context": {},
                "expected_confidence": 0.8,
                "max_execution_time_ms": 5000
            }
        ]
        
        with patch('tests.gaia_cases.benchmark_manager.Path.exists', return_value=True), \
             patch('tests.gaia_cases.benchmark_manager.yaml.safe_load', return_value=mock_cases_data):
            
            manager = BenchmarkManager()
            await manager.initialize()
            
            cases = await manager.load_benchmark_cases()
            
            assert len(cases) == 1
            assert cases[0].case_id == "emp_001"
            assert cases[0].level == 1
            assert cases[0].category == "employment_law"
    
    @pytest.mark.asyncio
    async def test_evaluate_single_case(self, mock_agent, sample_benchmark_cases):
        """Test evaluation of a single benchmark case"""
        
        # Mock agent response
        mock_agent.research.return_value = MagicMock(
            answer="The minimum notice period is 28 days for employees who have worked for more than 6 months according to the Employment Act.",
            confidence=0.85,
            reasoning_chain=["Retrieved Employment Act", "Analyzed notice period requirements"],
            citations=[MagicMock(title="Employment Act 2007")]
        )
        
        manager = BenchmarkManager()
        case = sample_benchmark_cases[0]  # employment_law case
        
        with patch('time.time', side_effect=[0, 1.5]):  # Mock execution time
            result = await manager.evaluate_case(case, mock_agent)
        
        assert isinstance(result, BenchmarkResult)
        assert result.case_id == "emp_001"
        assert result.status == BenchmarkStatus.COMPLETED
        assert result.score > 0.8  # Should pass evaluation criteria
        assert result.execution_time_ms == 1500
        assert result.accuracy_score > 0.0
        assert result.completeness_score > 0.0
    
    @pytest.mark.asyncio
    async def test_benchmark_suite_execution(self, mock_agent, sample_benchmark_cases):
        """Test execution of complete benchmark suite"""
        
        # Mock agent responses for different cases
        def mock_research_side_effect(*args, **kwargs):
            query = kwargs.get('query', '')
            if 'notice period' in query:
                return MagicMock(
                    answer="The minimum notice period is 28 days for employees who have worked for more than 6 months.",
                    confidence=0.85,
                    reasoning_chain=["Retrieved Employment Act"],
                    citations=[MagicMock(title="Employment Act 2007")]
                )
            elif 'contract' in query:
                return MagicMock(
                    answer="A valid contract requires offer, acceptance, consideration, intention to create legal relations, and capacity.",
                    confidence=0.80,
                    reasoning_chain=["Analyzed contract law principles"],
                    citations=[MagicMock(title="Contract Act")]
                )
            else:
                return MagicMock(
                    answer="Adverse possession requires 12 years of continuous possession under the Land Registration Act 2012.",
                    confidence=0.75,
                    reasoning_chain=["Analyzed property law"],
                    citations=[MagicMock(title="Land Registration Act 2012")]
                )
        
        mock_agent.research.side_effect = mock_research_side_effect
        
        with patch('tests.gaia_cases.benchmark_manager.Path.exists', return_value=True), \
             patch.object(BenchmarkManager, 'load_benchmark_cases', return_value=sample_benchmark_cases), \
             patch('time.time', side_effect=[0, 1, 2, 3, 4, 5]):  # Mock execution times
            
            manager = BenchmarkManager()
            await manager.initialize()
            
            results = await manager.run_benchmark_suite(
                level=None,  # All levels
                category=None,  # All categories
                agent=mock_agent,
                max_cases=3
            )
        
        assert results["total_cases"] == 3
        assert len(results["suite_results"]) == 3
        assert results["statistics"]["completion_rate"] == 1.0
        assert results["statistics"]["average_score"] > 0.7
        assert results["statistics"]["pass_rate"] >= 0.9  # Should meet 90% requirement
    
    @pytest.mark.asyncio
    async def test_benchmark_filtering(self, mock_agent, sample_benchmark_cases):
        """Test benchmark case filtering by level and category"""
        
        mock_agent.research.return_value = MagicMock(
            answer="Test answer",
            confidence=0.8,
            reasoning_chain=["Test reasoning"],
            citations=[]
        )
        
        with patch('tests.gaia_cases.benchmark_manager.Path.exists', return_value=True), \
             patch.object(BenchmarkManager, 'load_benchmark_cases', return_value=sample_benchmark_cases):
            
            manager = BenchmarkManager()
            await manager.initialize()
            
            # Test level filtering
            results = await manager.run_benchmark_suite(
                level=1,
                category=None,
                agent=mock_agent,
                max_cases=10
            )
            
            assert results["total_cases"] == 1  # Only level 1 case
            
            # Test category filtering
            results = await manager.run_benchmark_suite(
                level=None,
                category="employment_law",
                agent=mock_agent,
                max_cases=10
            )
            
            assert results["total_cases"] == 1  # Only employment_law case
    
    @pytest.mark.asyncio
    async def test_evaluation_criteria_checking(self, sample_benchmark_cases):
        """Test evaluation criteria checking logic"""
        
        manager = BenchmarkManager()
        case = sample_benchmark_cases[0]  # employment_law case
        
        # Test response that meets all criteria
        good_response = "The minimum notice period is 28 days for employees who have worked for more than 6 months according to the Employment Act."
        accuracy = manager._calculate_accuracy_score(good_response, case)
        assert accuracy > 0.8
        
        # Test response that meets some criteria
        partial_response = "The minimum notice period is 28 days."
        accuracy = manager._calculate_accuracy_score(partial_response, case)
        assert 0.3 < accuracy < 0.7
        
        # Test response that meets no criteria
        bad_response = "I don't know about employment law."
        accuracy = manager._calculate_accuracy_score(bad_response, case)
        assert accuracy < 0.3
    
    @pytest.mark.asyncio
    async def test_performance_metrics_calculation(self, mock_agent, sample_benchmark_cases):
        """Test calculation of performance metrics"""
        
        # Create mock results with known scores
        mock_results = [
            BenchmarkResult(
                case_id="test_1",
                status=BenchmarkStatus.COMPLETED,
                score=0.95,
                confidence=0.85,
                execution_time_ms=1000,
                accuracy_score=0.95,
                completeness_score=0.90,
                reasoning_score=0.85,
                citation_score=0.90
            ),
            BenchmarkResult(
                case_id="test_2",
                status=BenchmarkStatus.COMPLETED,
                score=0.88,
                confidence=0.80,
                execution_time_ms=1500,
                accuracy_score=0.85,
                completeness_score=0.85,
                reasoning_score=0.80,
                citation_score=0.85
            ),
            BenchmarkResult(
                case_id="test_3",
                status=BenchmarkStatus.FAILED,
                score=0.0,
                confidence=0.0,
                execution_time_ms=0,
                accuracy_score=0.0,
                completeness_score=0.0,
                reasoning_score=0.0,
                citation_score=0.0
            )
        ]
        
        manager = BenchmarkManager()
        statistics = manager._calculate_statistics(mock_results)
        
        assert statistics["total_cases"] == 3
        assert statistics["completed_cases"] == 2
        assert statistics["failed_cases"] == 1
        assert statistics["completion_rate"] == 2/3
        assert statistics["average_score"] == (0.95 + 0.88) / 2  # Only completed cases
        assert statistics["pass_rate"] == 2/3  # 2 out of 3 passed (score > 0.7)
        assert statistics["average_execution_time"] == (1000 + 1500) / 2


class TestBenchmarkIntegration:
    """Integration tests for benchmark system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_benchmark_execution(self):
        """Test complete end-to-end benchmark execution"""
        
        # Create a real agent instance (mocked dependencies)
        with patch('app.agents.legal_research_agent.LegalRAGService'), \
             patch('app.agents.legal_research_agent.IntelligenceEnhancer'), \
             patch('app.agents.legal_research_agent.MCPService'), \
             patch('app.agents.legal_research_agent.AIService'), \
             patch('app.agents.legal_research_agent.VectorService'), \
             patch('app.agents.legal_research_agent.ContextManager'), \
             patch('app.agents.legal_research_agent.PRPManager'), \
             patch('app.agents.legal_research_agent.VectorRetriever'), \
             patch('app.agents.legal_research_agent.MultiSourceSummarizer'), \
             patch('app.agents.legal_research_agent.LegalReasoner'), \
             patch('app.agents.legal_research_agent.AnswerFormatter'):
            
            agent = LegalResearchAgent(enable_context_framework=True)
            
            # Mock the research method
            agent.research = AsyncMock(return_value=MagicMock(
                answer="The minimum notice period is 28 days for employees who have worked for more than 6 months according to the Employment Act 2007.",
                confidence=0.85,
                reasoning_chain=["Retrieved Employment Act", "Analyzed notice requirements"],
                citations=[MagicMock(title="Employment Act 2007", source="legislation")]
            ))
            
            # Create simple test case
            test_case = BenchmarkCase(
                case_id="integration_test",
                level=1,
                category="employment_law",
                query="What is the minimum notice period for employment termination in Kenya?",
                ground_truth="The minimum notice period is 28 days for employees who have worked for more than 6 months.",
                evaluation_criteria={
                    "must_mention_28_days": True,
                    "must_mention_6_months": True,
                    "must_reference_employment_act": True
                },
                context={"domain": "employment_law"},
                expected_confidence=0.8,
                max_execution_time_ms=5000
            )
            
            with patch.object(BenchmarkManager, 'load_benchmark_cases', return_value=[test_case]):
                manager = BenchmarkManager()
                await manager.initialize()
                
                results = await manager.run_benchmark_suite(
                    level=1,
                    category="employment_law",
                    agent=agent,
                    max_cases=1
                )
                
                assert results["total_cases"] == 1
                assert results["statistics"]["completion_rate"] == 1.0
                assert results["statistics"]["pass_rate"] >= 0.9  # Should meet 90% requirement
                assert len(results["suite_results"]) == 1
                
                result = results["suite_results"][0]
                assert result.status == BenchmarkStatus.COMPLETED
                assert result.score > 0.8
    
    @pytest.mark.asyncio
    async def test_benchmark_failure_handling(self, mock_agent):
        """Test handling of benchmark failures"""
        
        # Mock agent failure
        mock_agent.research.side_effect = Exception("Agent processing failed")
        
        test_case = BenchmarkCase(
            case_id="failure_test",
            level=1,
            category="test",
            query="Test query",
            ground_truth="Test answer",
            evaluation_criteria={},
            context={},
            expected_confidence=0.8,
            max_execution_time_ms=5000
        )
        
        manager = BenchmarkManager()
        
        result = await manager.evaluate_case(test_case, mock_agent)
        
        assert result.status == BenchmarkStatus.FAILED
        assert result.score == 0.0
        assert "Agent processing failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_benchmark_timeout_handling(self, mock_agent):
        """Test handling of benchmark timeouts"""
        
        # Mock slow agent response
        async def slow_research(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow response
            return MagicMock(answer="Slow response", confidence=0.8)
        
        mock_agent.research.side_effect = slow_research
        
        test_case = BenchmarkCase(
            case_id="timeout_test",
            level=1,
            category="test",
            query="Test query",
            ground_truth="Test answer",
            evaluation_criteria={},
            context={},
            expected_confidence=0.8,
            max_execution_time_ms=1000  # 1 second timeout
        )
        
        manager = BenchmarkManager()
        
        result = await manager.evaluate_case(test_case, mock_agent)
        
        assert result.status == BenchmarkStatus.TIMEOUT
        assert result.score == 0.0
        assert "timeout" in result.error_message.lower()
