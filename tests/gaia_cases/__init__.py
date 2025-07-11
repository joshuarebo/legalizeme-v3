"""
GAIA-Style Legal Benchmarks for LegalResearchAgent
Provides structured evaluation cases for legal AI performance assessment
"""

from .benchmark_manager import BenchmarkManager, BenchmarkCase, BenchmarkResult
from .evaluator import GAIAEvaluator, EvaluationMetrics

__all__ = [
    'BenchmarkManager',
    'BenchmarkCase', 
    'BenchmarkResult',
    'GAIAEvaluator',
    'EvaluationMetrics'
]
