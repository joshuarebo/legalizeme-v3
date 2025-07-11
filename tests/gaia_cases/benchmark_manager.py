"""
Benchmark Manager for GAIA-Style Legal Benchmarks
Manages loading, execution, and evaluation of legal AI benchmarks
"""

import yaml
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class BenchmarkLevel(Enum):
    """Benchmark difficulty levels"""
    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3

class BenchmarkStatus(Enum):
    """Benchmark execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class BenchmarkCase:
    """Represents a single benchmark case"""
    id: str
    category: str
    title: str
    question: str
    context: str
    ground_truth: Dict[str, Any]
    evaluation_criteria: Dict[str, Any]
    tools_expected: List[str]
    complexity_factors: List[str]
    level: int = 1
    
    # Execution metadata
    status: BenchmarkStatus = BenchmarkStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time_ms: float = 0.0

@dataclass
class BenchmarkResult:
    """Results from benchmark execution"""
    case_id: str
    status: BenchmarkStatus
    score: float
    confidence: float
    execution_time_ms: float
    
    # Response analysis
    agent_response: str = ""
    required_elements_found: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    legal_reasoning_quality: float = 0.0
    citation_quality: float = 0.0
    
    # Detailed scoring
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    reasoning_score: float = 0.0
    citation_score: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

class BenchmarkManager:
    """
    Manages GAIA-style legal benchmarks for evaluating
    LegalResearchAgent performance
    """
    
    def __init__(self, benchmarks_directory: str = None):
        self.benchmarks_directory = Path(benchmarks_directory or self._get_default_benchmarks_dir())
        self.benchmark_sets: Dict[str, Dict[str, Any]] = {}
        self.cases: Dict[str, BenchmarkCase] = {}
        self.results: List[BenchmarkResult] = []
        self._loaded = False
    
    def _get_default_benchmarks_dir(self) -> str:
        """Get default benchmarks directory"""
        return str(Path(__file__).parent)
    
    async def initialize(self) -> bool:
        """Initialize the benchmark manager"""
        try:
            await self.load_all_benchmarks()
            self._loaded = True
            logger.info(f"Benchmark Manager initialized with {len(self.cases)} cases")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Benchmark Manager: {e}")
            return False
    
    async def load_all_benchmarks(self):
        """Load all benchmark files"""
        if not self.benchmarks_directory.exists():
            logger.warning(f"Benchmarks directory not found: {self.benchmarks_directory}")
            return
        
        benchmark_files = list(self.benchmarks_directory.glob("level_*.yaml"))
        
        for benchmark_file in benchmark_files:
            try:
                benchmark_set = await self.load_benchmark_set(benchmark_file)
                if benchmark_set:
                    set_name = benchmark_set["benchmark_set"]
                    self.benchmark_sets[set_name] = benchmark_set
                    
                    # Load individual cases
                    for case_data in benchmark_set.get("cases", []):
                        case = self._create_benchmark_case(case_data, benchmark_set["level"])
                        self.cases[case.id] = case
                    
                    logger.debug(f"Loaded benchmark set: {set_name}")
                    
            except Exception as e:
                logger.error(f"Failed to load benchmark {benchmark_file}: {e}")
    
    async def load_benchmark_set(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Load a single benchmark set file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                benchmark_data = yaml.safe_load(file)
            
            # Validate required fields
            required_fields = ['benchmark_set', 'level', 'cases']
            for field in required_fields:
                if field not in benchmark_data:
                    logger.error(f"Benchmark {file_path} missing required field: {field}")
                    return None
            
            return benchmark_data
            
        except Exception as e:
            logger.error(f"Error loading benchmark from {file_path}: {e}")
            return None
    
    def _create_benchmark_case(self, case_data: Dict[str, Any], level: int) -> BenchmarkCase:
        """Create a BenchmarkCase from case data"""
        return BenchmarkCase(
            id=case_data["id"],
            category=case_data["category"],
            title=case_data["title"],
            question=case_data["question"],
            context=case_data["context"],
            ground_truth=case_data["ground_truth"],
            evaluation_criteria=case_data["evaluation_criteria"],
            tools_expected=case_data.get("tools_expected", []),
            complexity_factors=case_data.get("complexity_factors", []),
            level=level
        )
    
    def get_cases_by_level(self, level: Union[int, BenchmarkLevel]) -> List[BenchmarkCase]:
        """Get all cases for a specific level"""
        if isinstance(level, BenchmarkLevel):
            level = level.value
        
        return [case for case in self.cases.values() if case.level == level]
    
    def get_cases_by_category(self, category: str) -> List[BenchmarkCase]:
        """Get all cases for a specific category"""
        return [case for case in self.cases.values() if case.category == category]
    
    def get_case(self, case_id: str) -> Optional[BenchmarkCase]:
        """Get a specific case by ID"""
        return self.cases.get(case_id)
    
    async def run_benchmark_case(
        self,
        case_id: str,
        agent,
        timeout_seconds: int = 300
    ) -> BenchmarkResult:
        """Run a single benchmark case"""
        
        case = self.get_case(case_id)
        if not case:
            return BenchmarkResult(
                case_id=case_id,
                status=BenchmarkStatus.FAILED,
                score=0.0,
                confidence=0.0,
                execution_time_ms=0.0,
                error_message=f"Case not found: {case_id}"
            )
        
        case.status = BenchmarkStatus.RUNNING
        case.start_time = datetime.utcnow()
        
        try:
            # Execute the case with timeout
            response = await asyncio.wait_for(
                self._execute_case_with_agent(case, agent),
                timeout=timeout_seconds
            )
            
            case.end_time = datetime.utcnow()
            case.execution_time_ms = (case.end_time - case.start_time).total_seconds() * 1000
            case.status = BenchmarkStatus.COMPLETED
            
            # Evaluate the response
            result = await self._evaluate_response(case, response)
            result.execution_time_ms = case.execution_time_ms
            
            self.results.append(result)
            return result
            
        except asyncio.TimeoutError:
            case.status = BenchmarkStatus.TIMEOUT
            case.end_time = datetime.utcnow()
            case.execution_time_ms = timeout_seconds * 1000
            
            return BenchmarkResult(
                case_id=case_id,
                status=BenchmarkStatus.TIMEOUT,
                score=0.0,
                confidence=0.0,
                execution_time_ms=case.execution_time_ms,
                error_message="Execution timeout"
            )
            
        except Exception as e:
            case.status = BenchmarkStatus.FAILED
            case.end_time = datetime.utcnow()
            if case.start_time:
                case.execution_time_ms = (case.end_time - case.start_time).total_seconds() * 1000
            
            logger.error(f"Error executing benchmark case {case_id}: {e}")
            
            return BenchmarkResult(
                case_id=case_id,
                status=BenchmarkStatus.FAILED,
                score=0.0,
                confidence=0.0,
                execution_time_ms=case.execution_time_ms,
                error_message=str(e)
            )
    
    async def _execute_case_with_agent(self, case: BenchmarkCase, agent) -> Dict[str, Any]:
        """Execute a benchmark case with the agent"""
        
        # Prepare input for the agent
        agent_input = {
            "query": case.question,
            "context": case.context,
            "benchmark_mode": True,
            "expected_tools": case.tools_expected
        }
        
        # Execute the agent
        if hasattr(agent, 'research_with_context'):
            response = await agent.research_with_context(
                query=case.question,
                context=agent_input
            )
        elif hasattr(agent, 'research'):
            response = await agent.research(case.question)
        else:
            raise ValueError("Agent does not have a compatible research method")
        
        return response
    
    async def _evaluate_response(self, case: BenchmarkCase, response: Dict[str, Any]) -> BenchmarkResult:
        """Evaluate agent response against benchmark criteria"""
        
        from .evaluator import GAIAEvaluator
        
        evaluator = GAIAEvaluator()
        evaluation = await evaluator.evaluate_response(case, response)
        
        return BenchmarkResult(
            case_id=case.id,
            status=BenchmarkStatus.COMPLETED,
            score=evaluation["overall_score"],
            confidence=response.get("confidence", 0.0),
            agent_response=response.get("final_answer", ""),
            required_elements_found=evaluation["required_elements_found"],
            missing_elements=evaluation["missing_elements"],
            legal_reasoning_quality=evaluation["reasoning_score"],
            citation_quality=evaluation["citation_score"],
            accuracy_score=evaluation["accuracy_score"],
            completeness_score=evaluation["completeness_score"],
            reasoning_score=evaluation["reasoning_score"],
            citation_score=evaluation["citation_score"]
        )
    
    async def run_benchmark_suite(
        self,
        level: Optional[Union[int, BenchmarkLevel]] = None,
        category: Optional[str] = None,
        agent=None,
        max_cases: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run a suite of benchmark cases"""
        
        # Select cases to run
        if level is not None:
            cases = self.get_cases_by_level(level)
        elif category is not None:
            cases = self.get_cases_by_category(category)
        else:
            cases = list(self.cases.values())
        
        if max_cases:
            cases = cases[:max_cases]
        
        if not cases:
            return {"error": "No cases found for the specified criteria"}
        
        # Run cases
        suite_results = []
        start_time = datetime.utcnow()
        
        for case in cases:
            logger.info(f"Running benchmark case: {case.id}")
            result = await self.run_benchmark_case(case.id, agent)
            suite_results.append(result)
        
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()
        
        # Calculate suite statistics
        suite_stats = self._calculate_suite_statistics(suite_results, total_time)
        
        return {
            "suite_results": suite_results,
            "statistics": suite_stats,
            "total_cases": len(cases),
            "total_time_seconds": total_time
        }
    
    def _calculate_suite_statistics(self, results: List[BenchmarkResult], total_time: float) -> Dict[str, Any]:
        """Calculate statistics for a benchmark suite"""
        
        if not results:
            return {}
        
        completed_results = [r for r in results if r.status == BenchmarkStatus.COMPLETED]
        
        if not completed_results:
            return {
                "completion_rate": 0.0,
                "average_score": 0.0,
                "pass_rate": 0.0
            }
        
        # Basic statistics
        total_score = sum(r.score for r in completed_results)
        average_score = total_score / len(completed_results)
        
        # Pass rate (assuming 0.7 as passing threshold)
        passing_threshold = 0.7
        passed_cases = sum(1 for r in completed_results if r.score >= passing_threshold)
        pass_rate = passed_cases / len(completed_results)
        
        # Completion rate
        completion_rate = len(completed_results) / len(results)
        
        # Score distribution
        score_ranges = {
            "excellent": sum(1 for r in completed_results if r.score >= 0.9),
            "good": sum(1 for r in completed_results if 0.8 <= r.score < 0.9),
            "satisfactory": sum(1 for r in completed_results if 0.7 <= r.score < 0.8),
            "needs_improvement": sum(1 for r in completed_results if r.score < 0.7)
        }
        
        return {
            "completion_rate": completion_rate,
            "average_score": average_score,
            "pass_rate": pass_rate,
            "score_distribution": score_ranges,
            "total_execution_time": total_time,
            "average_case_time": sum(r.execution_time_ms for r in completed_results) / len(completed_results) / 1000
        }
    
    def get_benchmark_statistics(self) -> Dict[str, Any]:
        """Get overall benchmark statistics"""
        
        return {
            "total_benchmark_sets": len(self.benchmark_sets),
            "total_cases": len(self.cases),
            "cases_by_level": {
                level: len(self.get_cases_by_level(level))
                for level in [1, 2, 3]
            },
            "cases_by_category": {
                category: len(cases)
                for category, cases in self._group_cases_by_category().items()
            },
            "total_results": len(self.results),
            "loaded": self._loaded
        }
    
    def _group_cases_by_category(self) -> Dict[str, List[BenchmarkCase]]:
        """Group cases by category"""
        categories = {}
        for case in self.cases.values():
            if case.category not in categories:
                categories[case.category] = []
            categories[case.category].append(case)
        return categories
