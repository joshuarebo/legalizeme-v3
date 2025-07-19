"""
PRODUCTION MONITORING SERVICE
============================
CloudWatch metrics, performance dashboards, and alerting for production monitoring.
Tracks API performance, model usage, cache efficiency, and system health.
"""

import json
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import boto3
from contextlib import asynccontextmanager

from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class MetricData:
    """CloudWatch metric data point"""
    metric_name: str
    value: float
    unit: str
    dimensions: Dict[str, str]
    timestamp: datetime

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring"""
    endpoint: str
    response_time_ms: float
    model_used: str
    success: bool
    cache_hit: bool
    confidence: float
    legal_area: str
    timestamp: datetime

class ProductionMonitoringService:
    """
    Production monitoring service for Kenyan Legal AI platform
    Integrates with AWS CloudWatch for metrics and alerting
    """
    
    def __init__(self):
        self.cloudwatch = None
        self.metrics_buffer: List[MetricData] = []
        self.performance_buffer: List[PerformanceMetrics] = []
        self.buffer_size = 100
        self.flush_interval = 60  # seconds
        self._initialized = False
        self._monitoring_task = None
        
        # Metric configurations
        self.metric_namespace = "KenyanLegalAI/Production"
        self.alert_thresholds = {
            "response_time_p95": 10000,  # 10 seconds
            "error_rate": 0.05,  # 5%
            "cache_hit_rate": 0.3,  # 30% minimum
            "model_failure_rate": 0.02  # 2%
        }
    
    async def initialize(self):
        """Initialize monitoring service"""
        if self._initialized:
            return
        
        try:
            # Initialize CloudWatch client
            self.cloudwatch = boto3.client(
                'cloudwatch',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            
            # Start background monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            self._initialized = True
            logger.info("Production Monitoring Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Production Monitoring Service: {e}")
            self._initialized = True  # Continue without CloudWatch
    
    async def record_api_request(
        self,
        endpoint: str,
        response_time_ms: float,
        model_used: str,
        success: bool,
        cache_hit: bool = False,
        confidence: float = 0.0,
        legal_area: str = "general",
        error_type: Optional[str] = None
    ):
        """Record API request metrics"""
        try:
            # Record performance metrics
            perf_metric = PerformanceMetrics(
                endpoint=endpoint,
                response_time_ms=response_time_ms,
                model_used=model_used,
                success=success,
                cache_hit=cache_hit,
                confidence=confidence,
                legal_area=legal_area,
                timestamp=datetime.utcnow()
            )
            self.performance_buffer.append(perf_metric)
            
            # Record CloudWatch metrics
            await self._record_cloudwatch_metrics(
                endpoint, response_time_ms, model_used, success, 
                cache_hit, confidence, legal_area, error_type
            )
            
            # Flush buffers if needed
            if len(self.metrics_buffer) >= self.buffer_size:
                await self._flush_metrics()
            
        except Exception as e:
            logger.error(f"Error recording API request metrics: {e}")
    
    async def _record_cloudwatch_metrics(
        self,
        endpoint: str,
        response_time_ms: float,
        model_used: str,
        success: bool,
        cache_hit: bool,
        confidence: float,
        legal_area: str,
        error_type: Optional[str]
    ):
        """Record metrics to CloudWatch"""
        try:
            timestamp = datetime.utcnow()
            
            # Base dimensions
            base_dimensions = {
                'Environment': settings.ENVIRONMENT,
                'Service': 'KenyanLegalAI'
            }
            
            # Response time metric
            self.metrics_buffer.append(MetricData(
                metric_name="ResponseTime",
                value=response_time_ms,
                unit="Milliseconds",
                dimensions={**base_dimensions, 'Endpoint': endpoint, 'Model': model_used},
                timestamp=timestamp
            ))
            
            # Success/Error metrics
            self.metrics_buffer.append(MetricData(
                metric_name="RequestCount",
                value=1.0,
                unit="Count",
                dimensions={**base_dimensions, 'Endpoint': endpoint, 'Status': 'Success' if success else 'Error'},
                timestamp=timestamp
            ))
            
            # Cache hit metric
            if cache_hit:
                self.metrics_buffer.append(MetricData(
                    metric_name="CacheHit",
                    value=1.0,
                    unit="Count",
                    dimensions={**base_dimensions, 'Endpoint': endpoint},
                    timestamp=timestamp
                ))
            
            # Confidence metric
            if confidence > 0:
                self.metrics_buffer.append(MetricData(
                    metric_name="ResponseConfidence",
                    value=confidence,
                    unit="None",
                    dimensions={**base_dimensions, 'LegalArea': legal_area},
                    timestamp=timestamp
                ))
            
            # Model usage metric
            self.metrics_buffer.append(MetricData(
                metric_name="ModelUsage",
                value=1.0,
                unit="Count",
                dimensions={**base_dimensions, 'Model': model_used, 'LegalArea': legal_area},
                timestamp=timestamp
            ))
            
            # Error type metric
            if not success and error_type:
                self.metrics_buffer.append(MetricData(
                    metric_name="ErrorType",
                    value=1.0,
                    unit="Count",
                    dimensions={**base_dimensions, 'ErrorType': error_type},
                    timestamp=timestamp
                ))
            
        except Exception as e:
            logger.error(f"Error recording CloudWatch metrics: {e}")
    
    async def _flush_metrics(self):
        """Flush metrics buffer to CloudWatch"""
        if not self.cloudwatch or not self.metrics_buffer:
            return
        
        try:
            # Group metrics by namespace for batch sending
            metric_data = []
            
            for metric in self.metrics_buffer:
                metric_data.append({
                    'MetricName': metric.metric_name,
                    'Value': metric.value,
                    'Unit': metric.unit,
                    'Timestamp': metric.timestamp,
                    'Dimensions': [
                        {'Name': k, 'Value': v} for k, v in metric.dimensions.items()
                    ]
                })
            
            # Send metrics in batches (CloudWatch limit is 20 per request)
            batch_size = 20
            for i in range(0, len(metric_data), batch_size):
                batch = metric_data[i:i + batch_size]
                
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.cloudwatch.put_metric_data(
                        Namespace=self.metric_namespace,
                        MetricData=batch
                    )
                )
            
            logger.debug(f"Flushed {len(self.metrics_buffer)} metrics to CloudWatch")
            self.metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error flushing metrics to CloudWatch: {e}")
            # Clear buffer to prevent memory buildup
            self.metrics_buffer.clear()
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                
                # Flush metrics
                await self._flush_metrics()
                
                # Generate performance analytics
                await self._generate_performance_analytics()
                
                # Check alert thresholds
                await self._check_alert_thresholds()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _generate_performance_analytics(self):
        """Generate performance analytics from buffered data"""
        try:
            if not self.performance_buffer:
                return
            
            # Calculate metrics for last hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            recent_metrics = [
                m for m in self.performance_buffer 
                if m.timestamp > cutoff_time
            ]
            
            if not recent_metrics:
                return
            
            # Calculate key performance indicators
            total_requests = len(recent_metrics)
            successful_requests = sum(1 for m in recent_metrics if m.success)
            cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
            
            success_rate = successful_requests / total_requests if total_requests > 0 else 0
            cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
            
            response_times = [m.response_time_ms for m in recent_metrics]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
            
            # Log performance summary
            logger.info(f"Performance Analytics (Last Hour): "
                       f"Requests: {total_requests}, "
                       f"Success Rate: {success_rate:.2%}, "
                       f"Cache Hit Rate: {cache_hit_rate:.2%}, "
                       f"Avg Response Time: {avg_response_time:.0f}ms, "
                       f"P95 Response Time: {p95_response_time:.0f}ms")
            
            # Clean old metrics (keep last 24 hours)
            day_cutoff = datetime.utcnow() - timedelta(hours=24)
            self.performance_buffer = [
                m for m in self.performance_buffer 
                if m.timestamp > day_cutoff
            ]
            
        except Exception as e:
            logger.error(f"Error generating performance analytics: {e}")
    
    async def _check_alert_thresholds(self):
        """Check if any alert thresholds are breached"""
        try:
            if not self.performance_buffer:
                return
            
            # Get recent metrics (last 15 minutes)
            cutoff_time = datetime.utcnow() - timedelta(minutes=15)
            recent_metrics = [
                m for m in self.performance_buffer 
                if m.timestamp > cutoff_time
            ]
            
            if len(recent_metrics) < 10:  # Need minimum sample size
                return
            
            # Check error rate
            error_rate = sum(1 for m in recent_metrics if not m.success) / len(recent_metrics)
            if error_rate > self.alert_thresholds["error_rate"]:
                await self._send_alert("HIGH_ERROR_RATE", f"Error rate: {error_rate:.2%}")
            
            # Check response time P95
            response_times = [m.response_time_ms for m in recent_metrics]
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
            if p95_time > self.alert_thresholds["response_time_p95"]:
                await self._send_alert("HIGH_RESPONSE_TIME", f"P95 response time: {p95_time:.0f}ms")
            
            # Check cache hit rate
            cache_hit_rate = sum(1 for m in recent_metrics if m.cache_hit) / len(recent_metrics)
            if cache_hit_rate < self.alert_thresholds["cache_hit_rate"]:
                await self._send_alert("LOW_CACHE_HIT_RATE", f"Cache hit rate: {cache_hit_rate:.2%}")
            
        except Exception as e:
            logger.error(f"Error checking alert thresholds: {e}")
    
    async def _send_alert(self, alert_type: str, message: str):
        """Send alert notification"""
        try:
            alert_message = f"ALERT [{alert_type}]: {message} at {datetime.utcnow().isoformat()}"
            logger.warning(alert_message)
            
            # In production, this would send to SNS, Slack, etc.
            # For now, just log the alert
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get performance dashboard data"""
        try:
            if not self.performance_buffer:
                return {"message": "No performance data available"}
            
            # Get metrics for different time windows
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(hours=24)
            
            hour_metrics = [m for m in self.performance_buffer if m.timestamp > hour_ago]
            day_metrics = [m for m in self.performance_buffer if m.timestamp > day_ago]
            
            def calculate_stats(metrics):
                if not metrics:
                    return {}
                
                total = len(metrics)
                successful = sum(1 for m in metrics if m.success)
                cache_hits = sum(1 for m in metrics if m.cache_hit)
                response_times = [m.response_time_ms for m in metrics]
                
                return {
                    "total_requests": total,
                    "success_rate": successful / total if total > 0 else 0,
                    "cache_hit_rate": cache_hits / total if total > 0 else 0,
                    "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
                    "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0,
                    "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)] if response_times else 0
                }
            
            return {
                "last_hour": calculate_stats(hour_metrics),
                "last_24_hours": calculate_stats(day_metrics),
                "alert_thresholds": self.alert_thresholds,
                "monitoring_status": "active" if self._initialized else "inactive"
            }
            
        except Exception as e:
            logger.error(f"Error generating performance dashboard: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """Shutdown monitoring service"""
        try:
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Flush remaining metrics
            await self._flush_metrics()
            
            logger.info("Production Monitoring Service shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during monitoring service shutdown: {e}")

# Global monitoring service instance
production_monitoring_service = ProductionMonitoringService()
