"""
Agent Monitor Decorator - Context-aware monitoring and logging
"""

import logging
import time
import json
import asyncio
from pathlib import Path
from functools import wraps
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class FailureStage(Enum):
    """Stages where failures can occur"""
    CONTEXT_ANALYSIS = "context_analysis"
    TOOL_SELECTION = "tool_selection"
    RETRIEVAL = "retrieval"
    SUMMARIZATION = "summarization"
    REASONING = "reasoning"
    FORMATTING = "formatting"
    RESPONSE_GENERATION = "response_generation"

@dataclass
class ContextFailureLog:
    """Log entry for context failures"""
    timestamp: datetime
    query_id: str
    query: str
    failure_stage: FailureStage
    error_message: str
    context_snapshot: Dict[str, Any]
    confidence_score: float
    tools_attempted: List[str]
    recovery_attempted: bool = False
    recovery_successful: bool = False
    execution_time_ms: float = 0.0

@dataclass
class QualityMetrics:
    """Quality metrics for agent execution"""
    confidence_score: float
    response_completeness: float
    citation_quality: float
    reasoning_coherence: float
    context_utilization: float
    overall_quality: float

class AgentMonitor:
    """
    Decorator class for monitoring agent execution and context quality
    Provides logging, failure tracking, and context refinement capabilities
    """
    
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.context_failures_dir = self.log_directory / "context_failures"
        self.quality_logs_dir = self.log_directory / "quality_metrics"
        self.execution_logs_dir = self.log_directory / "execution_traces"
        
        # Create directories
        self._create_log_directories()
        
        # In-memory storage for recent data
        self.recent_failures: List[ContextFailureLog] = []
        self.quality_history: List[QualityMetrics] = []
        self.max_recent_items = 100
        
        # Configuration
        self.enable_file_logging = True
        self.enable_quality_tracking = True
        self.failure_threshold = 0.5  # Confidence threshold for failure detection
    
    def _create_log_directories(self):
        """Create necessary log directories"""
        directories = [
            self.log_directory,
            self.context_failures_dir,
            self.quality_logs_dir,
            self.execution_logs_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator implementation"""
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate unique execution ID
            execution_id = self._generate_execution_id()
            start_time = time.time()
            
            # Extract context and query information
            context_info = self._extract_context_info(args, kwargs)
            
            try:
                # Log execution start
                await self._log_execution_start(execution_id, context_info, func.__name__)
                
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = (time.time() - start_time) * 1000
                
                # Analyze result quality
                quality_metrics = self._analyze_result_quality(result, context_info)
                
                # Log successful execution
                await self._log_execution_success(
                    execution_id, context_info, result, quality_metrics, execution_time
                )
                
                # Check for quality issues
                if quality_metrics.overall_quality < self.failure_threshold:
                    await self._log_quality_failure(
                        execution_id, context_info, result, quality_metrics, execution_time
                    )
                
                return result
                
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                
                # Log execution failure
                await self._log_execution_failure(
                    execution_id, context_info, str(e), execution_time, func.__name__
                )
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    def _generate_execution_id(self) -> str:
        """Generate unique execution ID"""
        timestamp = int(time.time() * 1000)
        return f"exec_{timestamp}"
    
    def _extract_context_info(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Extract context information from function arguments"""
        
        context_info = {
            "query": "",
            "context": {},
            "agent_mode": False,
            "strategy": "default"
        }
        
        # Try to extract from common argument patterns
        if args:
            # First argument might be query
            if isinstance(args[0], str):
                context_info["query"] = args[0]
            elif isinstance(args[0], dict) and "query" in args[0]:
                context_info["query"] = args[0]["query"]
        
        # Extract from kwargs
        if "query" in kwargs:
            context_info["query"] = kwargs["query"]
        if "context" in kwargs:
            context_info["context"] = kwargs["context"]
        if "agent_mode" in kwargs:
            context_info["agent_mode"] = kwargs["agent_mode"]
        if "strategy" in kwargs:
            context_info["strategy"] = kwargs["strategy"]
        
        return context_info
    
    async def _log_execution_start(
        self,
        execution_id: str,
        context_info: Dict[str, Any],
        function_name: str
    ):
        """Log execution start"""
        
        log_entry = {
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "execution_start",
            "function": function_name,
            "query": context_info.get("query", ""),
            "context_summary": self._summarize_context(context_info.get("context", {}))
        }
        
        if self.enable_file_logging:
            await self._write_execution_log(execution_id, log_entry)
    
    async def _log_execution_success(
        self,
        execution_id: str,
        context_info: Dict[str, Any],
        result: Any,
        quality_metrics: QualityMetrics,
        execution_time: float
    ):
        """Log successful execution"""
        
        log_entry = {
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": "execution_success",
            "execution_time_ms": execution_time,
            "quality_metrics": asdict(quality_metrics),
            "result_summary": self._summarize_result(result)
        }
        
        # Store quality metrics
        if self.enable_quality_tracking:
            self.quality_history.append(quality_metrics)
            if len(self.quality_history) > self.max_recent_items:
                self.quality_history = self.quality_history[-self.max_recent_items:]
        
        if self.enable_file_logging:
            await self._write_execution_log(execution_id, log_entry)
            await self._write_quality_log(quality_metrics, execution_id)
    
    async def _log_execution_failure(
        self,
        execution_id: str,
        context_info: Dict[str, Any],
        error_message: str,
        execution_time: float,
        function_name: str
    ):
        """Log execution failure"""
        
        # Determine failure stage
        failure_stage = self._determine_failure_stage(error_message, function_name)
        
        # Create failure log
        failure_log = ContextFailureLog(
            timestamp=datetime.utcnow(),
            query_id=execution_id,
            query=context_info.get("query", ""),
            failure_stage=failure_stage,
            error_message=error_message,
            context_snapshot=context_info.get("context", {}),
            confidence_score=0.0,
            tools_attempted=[],
            execution_time_ms=execution_time
        )
        
        # Store failure
        self.recent_failures.append(failure_log)
        if len(self.recent_failures) > self.max_recent_items:
            self.recent_failures = self.recent_failures[-self.max_recent_items:]
        
        # Log to file
        if self.enable_file_logging:
            await self._write_failure_log(failure_log)
        
        logger.warning(f"Agent execution failed: {error_message}")
    
    async def _log_quality_failure(
        self,
        execution_id: str,
        context_info: Dict[str, Any],
        result: Any,
        quality_metrics: QualityMetrics,
        execution_time: float
    ):
        """Log quality failure (low quality result)"""
        
        failure_log = ContextFailureLog(
            timestamp=datetime.utcnow(),
            query_id=execution_id,
            query=context_info.get("query", ""),
            failure_stage=FailureStage.RESPONSE_GENERATION,
            error_message=f"Low quality result: overall_quality={quality_metrics.overall_quality:.3f}",
            context_snapshot=context_info.get("context", {}),
            confidence_score=quality_metrics.confidence_score,
            tools_attempted=[],
            execution_time_ms=execution_time
        )
        
        # Store failure
        self.recent_failures.append(failure_log)
        if len(self.recent_failures) > self.max_recent_items:
            self.recent_failures = self.recent_failures[-self.max_recent_items:]
        
        # Log to file
        if self.enable_file_logging:
            await self._write_failure_log(failure_log)
    
    def _analyze_result_quality(
        self,
        result: Any,
        context_info: Dict[str, Any]
    ) -> QualityMetrics:
        """Analyze the quality of the result"""
        
        # Extract metrics from result
        confidence_score = 0.0
        response_completeness = 0.0
        citation_quality = 0.0
        reasoning_coherence = 0.0
        context_utilization = 0.0
        
        if isinstance(result, dict):
            # Extract confidence
            confidence_score = result.get("confidence", 0.0)
            
            # Analyze response completeness
            response_text = result.get("final_answer", result.get("answer", ""))
            response_completeness = min(len(response_text) / 500, 1.0)  # Normalize to 500 chars
            
            # Analyze citation quality
            citations = result.get("citations", [])
            citation_quality = min(len(citations) / 3, 1.0)  # Normalize to 3 citations
            
            # Analyze reasoning coherence
            reasoning_chain = result.get("reasoning_chain", [])
            reasoning_coherence = min(len(reasoning_chain) / 5, 1.0)  # Normalize to 5 steps
            
            # Analyze context utilization
            context_used = result.get("context_used", {})
            context_utilization = 0.8 if context_used else 0.3  # Simple heuristic
        
        # Calculate overall quality
        overall_quality = (
            confidence_score * 0.3 +
            response_completeness * 0.2 +
            citation_quality * 0.2 +
            reasoning_coherence * 0.2 +
            context_utilization * 0.1
        )
        
        return QualityMetrics(
            confidence_score=confidence_score,
            response_completeness=response_completeness,
            citation_quality=citation_quality,
            reasoning_coherence=reasoning_coherence,
            context_utilization=context_utilization,
            overall_quality=overall_quality
        )
    
    def _determine_failure_stage(self, error_message: str, function_name: str) -> FailureStage:
        """Determine the stage where failure occurred"""
        
        error_lower = error_message.lower()
        
        if "context" in error_lower:
            return FailureStage.CONTEXT_ANALYSIS
        elif "tool" in error_lower or "routing" in error_lower:
            return FailureStage.TOOL_SELECTION
        elif "retrieval" in error_lower or "search" in error_lower:
            return FailureStage.RETRIEVAL
        elif "summariz" in error_lower:
            return FailureStage.SUMMARIZATION
        elif "reason" in error_lower:
            return FailureStage.REASONING
        elif "format" in error_lower:
            return FailureStage.FORMATTING
        else:
            return FailureStage.RESPONSE_GENERATION
    
    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of context for logging"""
        
        return {
            "has_query_info": "query_info" in context,
            "detected_domains": context.get("detected_domains", []),
            "urgency_level": context.get("urgency_analysis", {}).get("level", "unknown"),
            "complexity_level": context.get("query_complexity", {}).get("level", "unknown"),
            "routing_rules_count": len(context.get("routing_rules", {}))
        }
    
    def _summarize_result(self, result: Any) -> Dict[str, Any]:
        """Create a summary of result for logging"""
        
        if isinstance(result, dict):
            return {
                "has_answer": "final_answer" in result or "answer" in result,
                "confidence": result.get("confidence", 0.0),
                "citations_count": len(result.get("citations", [])),
                "reasoning_steps": len(result.get("reasoning_chain", [])),
                "response_length": len(str(result.get("final_answer", "")))
            }
        
        return {"result_type": type(result).__name__}
    
    async def _write_execution_log(self, execution_id: str, log_entry: Dict[str, Any]):
        """Write execution log to file"""
        
        try:
            log_file = self.execution_logs_dir / f"{execution_id}.json"
            
            # Read existing logs or create new
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            logs.append(log_entry)
            
            # Write updated logs
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to write execution log: {e}")
    
    async def _write_failure_log(self, failure_log: ContextFailureLog):
        """Write failure log to file"""
        
        try:
            timestamp = failure_log.timestamp
            filename = f"failure_{timestamp.strftime('%Y%m%d_%H%M%S')}_{failure_log.query_id}.json"
            filepath = self.context_failures_dir / filename
            
            failure_dict = asdict(failure_log)
            failure_dict["timestamp"] = failure_log.timestamp.isoformat()
            failure_dict["failure_stage"] = failure_log.failure_stage.value
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(failure_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to write failure log: {e}")
    
    async def _write_quality_log(self, quality_metrics: QualityMetrics, execution_id: str):
        """Write quality metrics to file"""
        
        try:
            date_str = datetime.utcnow().strftime('%Y%m%d')
            filename = f"quality_{date_str}.jsonl"
            filepath = self.quality_logs_dir / filename
            
            quality_dict = asdict(quality_metrics)
            quality_dict["timestamp"] = datetime.utcnow().isoformat()
            quality_dict["execution_id"] = execution_id
            
            # Append to daily log file
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(quality_dict, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write quality log: {e}")
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get failure statistics"""
        
        if not self.recent_failures:
            return {"total_failures": 0, "failure_stages": {}}
        
        failure_stages = {}
        total_failures = len(self.recent_failures)
        
        for failure in self.recent_failures:
            stage = failure.failure_stage.value
            failure_stages[stage] = failure_stages.get(stage, 0) + 1
        
        return {
            "total_failures": total_failures,
            "failure_stages": failure_stages,
            "recent_failures": [
                {
                    "query_id": f.query_id,
                    "stage": f.failure_stage.value,
                    "confidence": f.confidence_score,
                    "timestamp": f.timestamp.isoformat()
                }
                for f in self.recent_failures[-5:]  # Last 5 failures
            ]
        }
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get quality statistics"""
        
        if not self.quality_history:
            return {"average_quality": 0.0, "quality_trend": "no_data"}
        
        recent_metrics = self.quality_history[-10:]  # Last 10 executions
        
        avg_quality = sum(m.overall_quality for m in recent_metrics) / len(recent_metrics)
        avg_confidence = sum(m.confidence_score for m in recent_metrics) / len(recent_metrics)
        
        # Simple trend analysis
        if len(recent_metrics) >= 5:
            first_half = recent_metrics[:len(recent_metrics)//2]
            second_half = recent_metrics[len(recent_metrics)//2:]
            
            first_avg = sum(m.overall_quality for m in first_half) / len(first_half)
            second_avg = sum(m.overall_quality for m in second_half) / len(second_half)
            
            if second_avg > first_avg + 0.1:
                trend = "improving"
            elif second_avg < first_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "average_quality": avg_quality,
            "average_confidence": avg_confidence,
            "quality_trend": trend,
            "total_executions": len(self.quality_history)
        }


# Convenience decorator function
def monitor_agent_execution(log_directory: str = "logs"):
    """Convenience function to create AgentMonitor decorator"""
    return AgentMonitor(log_directory)
