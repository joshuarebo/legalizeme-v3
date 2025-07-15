#!/usr/bin/env python3
"""
Comprehensive Health Monitoring System for Counsel AI
Monitors all endpoints, performance metrics, and triggers alerts/rollbacks
"""

import asyncio
import aiohttp
import boto3
import json
import logging
import time
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class EndpointHealth:
    endpoint: str
    status_code: int
    response_time_ms: float
    healthy: bool
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class SystemHealth:
    overall_status: HealthStatus
    healthy_endpoints: int
    total_endpoints: int
    average_response_time: float
    error_rate: float
    timestamp: datetime
    endpoint_results: List[EndpointHealth]
    alerts: List[str]


class HealthMonitor:
    """Comprehensive health monitoring system"""
    
    def __init__(self):
        self.base_url = os.getenv("MONITOR_BASE_URL", "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com")
        self.cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
        self.ecs = boto3.client('ecs', region_name='us-east-1')
        
        # Critical endpoints that must be working
        self.critical_endpoints = [
            "/health",
            "/api/v1/counsel/conversations",
            "/api/v1/counsel/query",
            "/api/v1/multimodal/capabilities"
        ]
        
        # All endpoints for comprehensive monitoring
        self.all_endpoints = [
            # Health & Monitoring
            "/health",
            "/docs",
            
            # Legal AI Queries
            "/api/v1/counsel/query",
            "/api/v1/counsel/query-direct",
            "/api/v1/counsel/suggestions?query=test&limit=3",
            
            # Multimodal Processing
            "/api/v1/multimodal/capabilities",
            "/api/v1/multimodal/documents",
            
            # Conversation Management
            "/api/v1/counsel/conversations",
        ]
        
        # Thresholds for alerts
        self.thresholds = {
            "max_response_time_ms": 5000,  # 5 seconds
            "max_error_rate": 0.05,        # 5%
            "min_healthy_percentage": 0.95, # 95%
            "critical_endpoint_failures": 1  # Any critical endpoint failure
        }
        
        # Historical data for trend analysis
        self.health_history = []
        self.max_history_size = 100
    
    async def check_endpoint_health(self, session: aiohttp.ClientSession, endpoint: str) -> EndpointHealth:
        """Check health of a specific endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "HealthMonitor/1.0"}
            ) as response:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                return EndpointHealth(
                    endpoint=endpoint,
                    status_code=response.status,
                    response_time_ms=response_time,
                    healthy=response.status == 200
                )
                
        except asyncio.TimeoutError:
            return EndpointHealth(
                endpoint=endpoint,
                status_code=0,
                response_time_ms=10000,  # Timeout
                healthy=False,
                error="Timeout"
            )
        except Exception as e:
            return EndpointHealth(
                endpoint=endpoint,
                status_code=0,
                response_time_ms=0,
                healthy=False,
                error=str(e)
            )
    
    async def run_comprehensive_health_check(self) -> SystemHealth:
        """Run comprehensive health check on all endpoints"""
        logger.info("🏥 Starting comprehensive health check")
        
        async with aiohttp.ClientSession() as session:
            # Check all endpoints concurrently
            tasks = [
                self.check_endpoint_health(session, endpoint)
                for endpoint in self.all_endpoints
            ]
            
            endpoint_results = await asyncio.gather(*tasks)
        
        # Analyze results
        healthy_endpoints = sum(1 for result in endpoint_results if result.healthy)
        total_endpoints = len(endpoint_results)
        error_rate = (total_endpoints - healthy_endpoints) / total_endpoints
        
        # Calculate average response time (only for successful requests)
        successful_results = [r for r in endpoint_results if r.healthy]
        avg_response_time = (
            sum(r.response_time_ms for r in successful_results) / len(successful_results)
            if successful_results else 0
        )
        
        # Determine overall status and generate alerts
        overall_status, alerts = self._analyze_system_health(
            endpoint_results, healthy_endpoints, total_endpoints, avg_response_time, error_rate
        )
        
        system_health = SystemHealth(
            overall_status=overall_status,
            healthy_endpoints=healthy_endpoints,
            total_endpoints=total_endpoints,
            average_response_time=avg_response_time,
            error_rate=error_rate,
            timestamp=datetime.utcnow(),
            endpoint_results=endpoint_results,
            alerts=alerts
        )
        
        # Store in history
        self.health_history.append(system_health)
        if len(self.health_history) > self.max_history_size:
            self.health_history.pop(0)
        
        return system_health
    
    def _analyze_system_health(
        self, 
        endpoint_results: List[EndpointHealth],
        healthy_endpoints: int,
        total_endpoints: int,
        avg_response_time: float,
        error_rate: float
    ) -> Tuple[HealthStatus, List[str]]:
        """Analyze system health and generate alerts"""
        alerts = []
        
        # Check critical endpoints
        critical_failures = []
        for result in endpoint_results:
            if result.endpoint in self.critical_endpoints and not result.healthy:
                critical_failures.append(result.endpoint)
                alerts.append(f"CRITICAL: {result.endpoint} is unhealthy - {result.error}")
        
        # Check response times
        slow_endpoints = [
            r.endpoint for r in endpoint_results 
            if r.healthy and r.response_time_ms > self.thresholds["max_response_time_ms"]
        ]
        if slow_endpoints:
            alerts.append(f"WARNING: Slow response times on {len(slow_endpoints)} endpoints")
        
        # Check error rate
        if error_rate > self.thresholds["max_error_rate"]:
            alerts.append(f"WARNING: High error rate {error_rate:.1%}")
        
        # Check healthy percentage
        healthy_percentage = healthy_endpoints / total_endpoints
        if healthy_percentage < self.thresholds["min_healthy_percentage"]:
            alerts.append(f"WARNING: Only {healthy_percentage:.1%} of endpoints healthy")
        
        # Determine overall status
        if critical_failures:
            return HealthStatus.CRITICAL, alerts
        elif error_rate > 0.1 or healthy_percentage < 0.8:
            return HealthStatus.UNHEALTHY, alerts
        elif error_rate > 0.05 or avg_response_time > 3000 or slow_endpoints:
            return HealthStatus.DEGRADED, alerts
        else:
            return HealthStatus.HEALTHY, alerts
    
    def publish_metrics_to_cloudwatch(self, system_health: SystemHealth):
        """Publish health metrics to CloudWatch"""
        try:
            metric_data = [
                {
                    'MetricName': 'OverallHealthStatus',
                    'Value': 1 if system_health.overall_status == HealthStatus.HEALTHY else 0,
                    'Unit': 'None',
                    'Timestamp': system_health.timestamp
                },
                {
                    'MetricName': 'HealthyEndpointCount',
                    'Value': system_health.healthy_endpoints,
                    'Unit': 'Count',
                    'Timestamp': system_health.timestamp
                },
                {
                    'MetricName': 'ErrorRate',
                    'Value': system_health.error_rate,
                    'Unit': 'Percent',
                    'Timestamp': system_health.timestamp
                },
                {
                    'MetricName': 'AverageResponseTime',
                    'Value': system_health.average_response_time,
                    'Unit': 'Milliseconds',
                    'Timestamp': system_health.timestamp
                }
            ]
            
            # Add individual endpoint metrics
            for result in system_health.endpoint_results:
                metric_data.extend([
                    {
                        'MetricName': 'EndpointHealth',
                        'Value': 1 if result.healthy else 0,
                        'Unit': 'None',
                        'Dimensions': [
                            {
                                'Name': 'Endpoint',
                                'Value': result.endpoint
                            }
                        ],
                        'Timestamp': result.timestamp
                    },
                    {
                        'MetricName': 'EndpointResponseTime',
                        'Value': result.response_time_ms,
                        'Unit': 'Milliseconds',
                        'Dimensions': [
                            {
                                'Name': 'Endpoint',
                                'Value': result.endpoint
                            }
                        ],
                        'Timestamp': result.timestamp
                    }
                ])
            
            # Publish metrics in batches (CloudWatch limit is 20 per call)
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                self.cloudwatch.put_metric_data(
                    Namespace='CounselAI/Health',
                    MetricData=batch
                )
            
            logger.info(f"Published {len(metric_data)} metrics to CloudWatch")
            
        except Exception as e:
            logger.error(f"Failed to publish metrics to CloudWatch: {e}")
    
    def should_trigger_rollback(self, system_health: SystemHealth) -> bool:
        """Determine if automatic rollback should be triggered"""
        # Trigger rollback if any critical endpoint is down
        critical_failures = [
            r for r in system_health.endpoint_results
            if r.endpoint in self.critical_endpoints and not r.healthy
        ]
        
        if critical_failures:
            logger.warning(f"Critical endpoints failing: {[r.endpoint for r in critical_failures]}")
            return True
        
        # Trigger rollback if error rate is very high
        if system_health.error_rate > 0.2:  # 20% error rate
            logger.warning(f"High error rate: {system_health.error_rate:.1%}")
            return True
        
        # Trigger rollback if less than 80% of endpoints are healthy
        healthy_percentage = system_health.healthy_endpoints / system_health.total_endpoints
        if healthy_percentage < 0.8:
            logger.warning(f"Low healthy percentage: {healthy_percentage:.1%}")
            return True
        
        return False
    
    def trigger_automated_rollback(self):
        """Trigger automated rollback procedure"""
        logger.critical("🚨 TRIGGERING AUTOMATED ROLLBACK")
        
        try:
            # Set environment variable for rollback reason
            os.environ['ROLLBACK_REASON'] = 'Automated rollback triggered by health monitor'
            
            # Execute rollback script
            script_path = os.path.join(os.path.dirname(__file__), 'automated_rollback.sh')
            result = subprocess.run(
                ['/bin/bash', script_path, '--force'],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Automated rollback completed successfully")
                return True
            else:
                logger.error(f"❌ Automated rollback failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Automated rollback timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to execute automated rollback: {e}")
            return False
    
    def generate_health_report(self, system_health: SystemHealth) -> str:
        """Generate human-readable health report"""
        status_emoji = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.DEGRADED: "⚠️",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.CRITICAL: "🚨"
        }
        
        report = f"""
🏥 COUNSEL AI HEALTH REPORT
{'='*50}
Overall Status: {status_emoji[system_health.overall_status]} {system_health.overall_status.value.upper()}
Timestamp: {system_health.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

📊 METRICS:
- Healthy Endpoints: {system_health.healthy_endpoints}/{system_health.total_endpoints} ({system_health.healthy_endpoints/system_health.total_endpoints:.1%})
- Average Response Time: {system_health.average_response_time:.0f}ms
- Error Rate: {system_health.error_rate:.1%}

🔍 ENDPOINT STATUS:
"""
        
        for result in system_health.endpoint_results:
            status_icon = "✅" if result.healthy else "❌"
            report += f"{status_icon} {result.endpoint:<40} {result.status_code:>3} {result.response_time_ms:>6.0f}ms\n"
        
        if system_health.alerts:
            report += f"\n🚨 ALERTS:\n"
            for alert in system_health.alerts:
                report += f"- {alert}\n"
        
        return report
    
    async def continuous_monitoring(self, interval_seconds: int = 60):
        """Run continuous health monitoring"""
        logger.info(f"🔄 Starting continuous monitoring (interval: {interval_seconds}s)")
        
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while True:
            try:
                # Run health check
                system_health = await self.run_comprehensive_health_check()
                
                # Generate and log report
                report = self.generate_health_report(system_health)
                logger.info(report)
                
                # Publish metrics
                self.publish_metrics_to_cloudwatch(system_health)
                
                # Check if rollback should be triggered
                if self.should_trigger_rollback(system_health):
                    consecutive_failures += 1
                    logger.warning(f"Health check failure {consecutive_failures}/{max_consecutive_failures}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.critical("Maximum consecutive failures reached - triggering rollback")
                        if self.trigger_automated_rollback():
                            # Reset counter after successful rollback
                            consecutive_failures = 0
                        else:
                            logger.critical("Automated rollback failed - manual intervention required")
                            break
                else:
                    # Reset failure counter on successful health check
                    consecutive_failures = 0
                
                # Wait for next check
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)


async def main():
    """Main function for health monitoring"""
    monitor = HealthMonitor()
    
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            # Run single health check
            system_health = await monitor.run_comprehensive_health_check()
            report = monitor.generate_health_report(system_health)
            print(report)
            
            # Exit with appropriate code
            if system_health.overall_status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                sys.exit(1)
            else:
                sys.exit(0)
        elif sys.argv[1] == "--continuous":
            # Run continuous monitoring
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            await monitor.continuous_monitoring(interval)
        else:
            print("Usage: python health_monitor.py [--once|--continuous [interval]]")
            sys.exit(1)
    else:
        # Default: run single health check
        system_health = await monitor.run_comprehensive_health_check()
        report = monitor.generate_health_report(system_health)
        print(report)


if __name__ == "__main__":
    asyncio.run(main())
