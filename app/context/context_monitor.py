"""
Context Monitor - Monitoring and logging for context operations
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of context failures"""
    LOW_CONFIDENCE = "low_confidence"
    TOOL_FAILURE = "tool_failure"
    TIMEOUT = "timeout"
    ROUTING_ERROR = "routing_error"
    CONTEXT_ERROR = "context_error"
    VALIDATION_ERROR = "validation_error"

@dataclass
class ContextFailure:
    """Represents a context-related failure"""
    timestamp: datetime
    failure_type: FailureType
    query_id: str
    query: str
    context_snapshot: Dict[str, Any]
    error_message: str
    confidence_score: float = 0.0
    tools_attempted: List[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False

@dataclass
class PerformanceMetric:
    """Performance metric for context operations"""
    timestamp: datetime
    metric_name: str
    metric_value: float
    context_id: str
    additional_data: Dict[str, Any] = None

class ContextMonitor:
    """
    Monitors context operations and provides logging,
    failure tracking, and performance analysis
    """
    
    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.context_snapshots_dir = self.log_directory / "context_snapshots"
        self.context_failures_dir = self.log_directory / "context_failures"
        self.performance_logs_dir = self.log_directory / "performance"
        
        # In-memory storage for recent data
        self.recent_snapshots: List[Dict[str, Any]] = []
        self.recent_failures: List[ContextFailure] = []
        self.performance_metrics: List[PerformanceMetric] = []
        
        # Configuration
        self.max_recent_items = 100
        self.enable_file_logging = True
        self.enable_performance_tracking = True
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize the context monitor"""
        try:
            # Create log directories
            if self.enable_file_logging:
                self._create_log_directories()
            
            self._initialized = True
            logger.info("Context Monitor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Context Monitor: {e}")
            raise
    
    def _create_log_directories(self):
        """Create necessary log directories"""
        directories = [
            self.log_directory,
            self.context_snapshots_dir,
            self.context_failures_dir,
            self.performance_logs_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def log_context_snapshot(self, snapshot: 'ContextSnapshot'):
        """Log a context snapshot"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Convert snapshot to dictionary
            snapshot_dict = {
                "timestamp": snapshot.timestamp.isoformat(),
                "query_id": snapshot.query_id,
                "processing_stage": snapshot.processing_stage,
                "context_data": snapshot.context_data,
                "confidence_score": snapshot.confidence_score,
                "tools_selected": snapshot.tools_selected,
                "routing_decisions": snapshot.routing_decisions
            }
            
            # Add to recent snapshots
            self.recent_snapshots.append(snapshot_dict)
            if len(self.recent_snapshots) > self.max_recent_items:
                self.recent_snapshots = self.recent_snapshots[-self.max_recent_items:]
            
            # Write to file if enabled
            if self.enable_file_logging:
                await self._write_snapshot_to_file(snapshot_dict)
            
            logger.debug(f"Context snapshot logged for query {snapshot.query_id}")
            
        except Exception as e:
            logger.error(f"Failed to log context snapshot: {e}")
    
    async def log_context_failure(
        self,
        failure_type: FailureType,
        query_id: str,
        query: str,
        context_snapshot: Dict[str, Any],
        error_message: str,
        confidence_score: float = 0.0,
        tools_attempted: List[str] = None
    ):
        """Log a context failure"""
        if not self._initialized:
            await self.initialize()
        
        try:
            failure = ContextFailure(
                timestamp=datetime.utcnow(),
                failure_type=failure_type,
                query_id=query_id,
                query=query,
                context_snapshot=context_snapshot,
                error_message=error_message,
                confidence_score=confidence_score,
                tools_attempted=tools_attempted or []
            )
            
            # Add to recent failures
            self.recent_failures.append(failure)
            if len(self.recent_failures) > self.max_recent_items:
                self.recent_failures = self.recent_failures[-self.max_recent_items:]
            
            # Write to file if enabled
            if self.enable_file_logging:
                await self._write_failure_to_file(failure)
            
            logger.warning(f"Context failure logged: {failure_type.value} for query {query_id}")
            
        except Exception as e:
            logger.error(f"Failed to log context failure: {e}")
    
    async def log_performance_metric(
        self,
        metric_name: str,
        metric_value: float,
        context_id: str,
        additional_data: Dict[str, Any] = None
    ):
        """Log a performance metric"""
        if not self.enable_performance_tracking:
            return
        
        try:
            metric = PerformanceMetric(
                timestamp=datetime.utcnow(),
                metric_name=metric_name,
                metric_value=metric_value,
                context_id=context_id,
                additional_data=additional_data or {}
            )
            
            # Add to performance metrics
            self.performance_metrics.append(metric)
            if len(self.performance_metrics) > self.max_recent_items:
                self.performance_metrics = self.performance_metrics[-self.max_recent_items:]
            
            # Write to file if enabled
            if self.enable_file_logging:
                await self._write_performance_metric_to_file(metric)
            
        except Exception as e:
            logger.error(f"Failed to log performance metric: {e}")
    
    async def _write_snapshot_to_file(self, snapshot_dict: Dict[str, Any]):
        """Write context snapshot to file"""
        try:
            timestamp = datetime.utcnow()
            filename = f"snapshot_{timestamp.strftime('%Y%m%d_%H%M%S')}_{snapshot_dict['query_id']}.json"
            filepath = self.context_snapshots_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to write snapshot to file: {e}")
    
    async def _write_failure_to_file(self, failure: ContextFailure):
        """Write context failure to file"""
        try:
            timestamp = failure.timestamp
            filename = f"failure_{timestamp.strftime('%Y%m%d_%H%M%S')}_{failure.query_id}.json"
            filepath = self.context_failures_dir / filename
            
            failure_dict = asdict(failure)
            failure_dict["timestamp"] = failure.timestamp.isoformat()
            failure_dict["failure_type"] = failure.failure_type.value
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(failure_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to write failure to file: {e}")
    
    async def _write_performance_metric_to_file(self, metric: PerformanceMetric):
        """Write performance metric to file"""
        try:
            # Use daily log files for performance metrics
            date_str = metric.timestamp.strftime('%Y%m%d')
            filename = f"performance_{date_str}.jsonl"
            filepath = self.performance_logs_dir / filename
            
            metric_dict = asdict(metric)
            metric_dict["timestamp"] = metric.timestamp.isoformat()
            
            # Append to daily log file
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metric_dict, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write performance metric to file: {e}")
    
    def get_recent_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent context snapshots"""
        return self.recent_snapshots[-limit:]
    
    def get_recent_failures(self, limit: int = 10) -> List[ContextFailure]:
        """Get recent context failures"""
        return self.recent_failures[-limit:]
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get failure statistics"""
        if not self.recent_failures:
            return {"total_failures": 0, "failure_types": {}}
        
        failure_types = {}
        total_failures = len(self.recent_failures)
        
        for failure in self.recent_failures:
            failure_type = failure.failure_type.value
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        
        return {
            "total_failures": total_failures,
            "failure_types": failure_types,
            "failure_rate": total_failures / max(len(self.recent_snapshots), 1)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_metrics:
            return {"metrics": {}}
        
        metrics_summary = {}
        
        for metric in self.performance_metrics:
            metric_name = metric.metric_name
            if metric_name not in metrics_summary:
                metrics_summary[metric_name] = {
                    "count": 0,
                    "total": 0.0,
                    "min": float('inf'),
                    "max": float('-inf'),
                    "values": []
                }
            
            summary = metrics_summary[metric_name]
            summary["count"] += 1
            summary["total"] += metric.metric_value
            summary["min"] = min(summary["min"], metric.metric_value)
            summary["max"] = max(summary["max"], metric.metric_value)
            summary["values"].append(metric.metric_value)
        
        # Calculate averages
        for metric_name, summary in metrics_summary.items():
            summary["average"] = summary["total"] / summary["count"]
            # Remove raw values to reduce size
            del summary["values"]
        
        return {"metrics": metrics_summary}
    
    def analyze_context_quality(self) -> Dict[str, Any]:
        """Analyze overall context quality"""
        if not self.recent_snapshots:
            return {"quality_score": 0.0, "analysis": "No data available"}
        
        # Calculate quality metrics
        total_snapshots = len(self.recent_snapshots)
        high_confidence_count = sum(
            1 for snapshot in self.recent_snapshots
            if snapshot.get("confidence_score", 0) >= 0.8
        )
        
        failure_count = len(self.recent_failures)
        
        # Quality score calculation
        confidence_score = high_confidence_count / total_snapshots if total_snapshots > 0 else 0
        failure_penalty = min(failure_count / total_snapshots, 0.5) if total_snapshots > 0 else 0
        quality_score = max(0, confidence_score - failure_penalty)
        
        analysis = []
        if quality_score >= 0.8:
            analysis.append("Excellent context quality")
        elif quality_score >= 0.6:
            analysis.append("Good context quality")
        elif quality_score >= 0.4:
            analysis.append("Moderate context quality - consider improvements")
        else:
            analysis.append("Poor context quality - immediate attention needed")
        
        if failure_count > total_snapshots * 0.1:
            analysis.append("High failure rate detected")
        
        return {
            "quality_score": quality_score,
            "confidence_rate": confidence_score,
            "failure_rate": failure_penalty,
            "total_snapshots": total_snapshots,
            "high_confidence_count": high_confidence_count,
            "failure_count": failure_count,
            "analysis": "; ".join(analysis)
        }
