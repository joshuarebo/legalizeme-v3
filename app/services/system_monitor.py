"""
Advanced System Monitoring & Analytics Service
Comprehensive monitoring for production legal AI system with performance metrics,
error tracking, and compliance monitoring.
"""

import asyncio
import logging
import time
import psutil
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    response_time_avg: float
    error_rate: float
    ai_model_usage: Dict[str, int]
    document_generation_count: int
    analysis_count: int
    compliance_score_avg: float

@dataclass
class APIMetrics:
    """API endpoint performance metrics"""
    endpoint: str
    method: str
    total_requests: int
    success_count: int
    error_count: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    last_24h_requests: int
    error_rate: float

@dataclass
class LegalComplianceMetrics:
    """Legal compliance and document quality metrics"""
    total_documents_analyzed: int
    avg_compliance_score: float
    kenyan_law_citations_found: int
    compliance_issues_detected: int
    high_risk_documents: int
    auto_clauses_injected: int
    template_usage_stats: Dict[str, int]

class SystemMonitor:
    """Advanced system monitoring and analytics service"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1440)  # 24 hours of minute-by-minute data
        self.api_metrics = defaultdict(lambda: {
            'total_requests': 0,
            'success_count': 0,
            'error_count': 0,
            'response_times': deque(maxlen=100),
            'last_24h': deque(maxlen=1440)
        })
        self.legal_metrics = {
            'total_documents_analyzed': 0,
            'compliance_scores': deque(maxlen=1000),
            'citations_found': 0,
            'compliance_issues': 0,
            'high_risk_documents': 0,
            'auto_clauses_injected': 0,
            'template_usage': defaultdict(int)
        }
        self.alerts = deque(maxlen=100)
        self.monitoring_active = False
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start continuous system monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Check for alerts
                self._check_system_alerts(metrics)
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # System resource metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network connections (approximate)
            connections = len(psutil.net_connections())
            
            # Calculate API metrics
            avg_response_time = self._calculate_avg_response_time()
            error_rate = self._calculate_error_rate()
            
            # AI model usage stats
            ai_model_usage = self._get_ai_model_usage()
            
            # Document processing stats
            doc_gen_count = self._get_document_generation_count()
            analysis_count = self._get_analysis_count()
            
            # Compliance metrics
            compliance_avg = self._calculate_avg_compliance_score()
            
            return SystemMetrics(
                timestamp=datetime.utcnow().isoformat() + "Z",
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                active_connections=connections,
                response_time_avg=avg_response_time,
                error_rate=error_rate,
                ai_model_usage=ai_model_usage,
                document_generation_count=doc_gen_count,
                analysis_count=analysis_count,
                compliance_score_avg=compliance_avg
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.utcnow().isoformat() + "Z",
                cpu_usage=0.0, memory_usage=0.0, disk_usage=0.0,
                active_connections=0, response_time_avg=0.0, error_rate=0.0,
                ai_model_usage={}, document_generation_count=0,
                analysis_count=0, compliance_score_avg=0.0
            )
    
    def record_api_request(self, endpoint: str, method: str, response_time: float, success: bool):
        """Record API request metrics"""
        key = f"{method}:{endpoint}"
        metrics = self.api_metrics[key]
        
        metrics['total_requests'] += 1
        if success:
            metrics['success_count'] += 1
        else:
            metrics['error_count'] += 1
        
        metrics['response_times'].append(response_time)
        metrics['last_24h'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'response_time': response_time,
            'success': success
        })
    
    def record_document_analysis(self, compliance_score: float, citations_found: int, 
                                issues_detected: int, high_risk: bool):
        """Record document analysis metrics"""
        self.legal_metrics['total_documents_analyzed'] += 1
        self.legal_metrics['compliance_scores'].append(compliance_score)
        self.legal_metrics['citations_found'] += citations_found
        self.legal_metrics['compliance_issues'] += issues_detected
        
        if high_risk:
            self.legal_metrics['high_risk_documents'] += 1
    
    def record_document_generation(self, template_id: str, auto_clauses_count: int):
        """Record document generation metrics"""
        self.legal_metrics['template_usage'][template_id] += 1
        self.legal_metrics['auto_clauses_injected'] += auto_clauses_count
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        if not self.metrics_history:
            return {"status": "unknown", "message": "No metrics available"}
        
        latest = self.metrics_history[-1]
        
        # Determine health status
        health_issues = []
        if latest.cpu_usage > 80:
            health_issues.append("High CPU usage")
        if latest.memory_usage > 85:
            health_issues.append("High memory usage")
        if latest.error_rate > 0.05:  # 5% error rate
            health_issues.append("High error rate")
        if latest.response_time_avg > 30:  # 30 seconds
            health_issues.append("Slow response times")
        
        if not health_issues:
            status = "healthy"
        elif len(health_issues) <= 2:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "timestamp": latest.timestamp,
            "issues": health_issues,
            "metrics": asdict(latest),
            "uptime": self._calculate_uptime(),
            "total_requests_24h": self._get_total_requests_24h()
        }
    
    def get_api_analytics(self) -> Dict[str, Any]:
        """Get API endpoint analytics"""
        analytics = {}
        
        for endpoint_key, metrics in self.api_metrics.items():
            if metrics['total_requests'] > 0:
                response_times = list(metrics['response_times'])
                
                analytics[endpoint_key] = {
                    'total_requests': metrics['total_requests'],
                    'success_count': metrics['success_count'],
                    'error_count': metrics['error_count'],
                    'success_rate': metrics['success_count'] / metrics['total_requests'],
                    'error_rate': metrics['error_count'] / metrics['total_requests'],
                    'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                    'max_response_time': max(response_times) if response_times else 0,
                    'min_response_time': min(response_times) if response_times else 0,
                    'last_24h_requests': len([r for r in metrics['last_24h'] 
                                            if self._is_within_24h(r['timestamp'])])
                }
        
        return analytics
    
    def get_legal_compliance_analytics(self) -> Dict[str, Any]:
        """Get legal compliance and document quality analytics"""
        compliance_scores = list(self.legal_metrics['compliance_scores'])
        
        return {
            'total_documents_analyzed': self.legal_metrics['total_documents_analyzed'],
            'avg_compliance_score': sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0,
            'compliance_distribution': self._get_compliance_distribution(compliance_scores),
            'kenyan_law_citations_found': self.legal_metrics['citations_found'],
            'compliance_issues_detected': self.legal_metrics['compliance_issues'],
            'high_risk_documents': self.legal_metrics['high_risk_documents'],
            'auto_clauses_injected': self.legal_metrics['auto_clauses_injected'],
            'template_usage_stats': dict(self.legal_metrics['template_usage']),
            'quality_trends': self._get_quality_trends()
        }
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time across all endpoints"""
        total_time = 0
        total_requests = 0
        
        for metrics in self.api_metrics.values():
            if metrics['response_times']:
                total_time += sum(metrics['response_times'])
                total_requests += len(metrics['response_times'])
        
        return total_time / total_requests if total_requests > 0 else 0
    
    def _calculate_error_rate(self) -> float:
        """Calculate overall error rate"""
        total_requests = sum(m['total_requests'] for m in self.api_metrics.values())
        total_errors = sum(m['error_count'] for m in self.api_metrics.values())
        
        return total_errors / total_requests if total_requests > 0 else 0
    
    def _get_ai_model_usage(self) -> Dict[str, int]:
        """Get AI model usage statistics"""
        # This would integrate with actual AI service metrics
        return {
            "claude-sonnet-4": 150,
            "claude-3-7-sonnet": 45,
            "mistral-large": 12
        }
    
    def _get_document_generation_count(self) -> int:
        """Get document generation count for current period"""
        return sum(self.legal_metrics['template_usage'].values())
    
    def _get_analysis_count(self) -> int:
        """Get document analysis count for current period"""
        return self.legal_metrics['total_documents_analyzed']
    
    def _calculate_avg_compliance_score(self) -> float:
        """Calculate average compliance score"""
        scores = list(self.legal_metrics['compliance_scores'])
        return sum(scores) / len(scores) if scores else 0
    
    def _check_system_alerts(self, metrics: SystemMetrics):
        """Check for system alerts and warnings"""
        alerts = []
        
        if metrics.cpu_usage > 90:
            alerts.append({
                'level': 'critical',
                'message': f'CPU usage critical: {metrics.cpu_usage:.1f}%',
                'timestamp': metrics.timestamp
            })
        elif metrics.cpu_usage > 80:
            alerts.append({
                'level': 'warning',
                'message': f'CPU usage high: {metrics.cpu_usage:.1f}%',
                'timestamp': metrics.timestamp
            })
        
        if metrics.memory_usage > 90:
            alerts.append({
                'level': 'critical',
                'message': f'Memory usage critical: {metrics.memory_usage:.1f}%',
                'timestamp': metrics.timestamp
            })
        
        if metrics.error_rate > 0.1:  # 10% error rate
            alerts.append({
                'level': 'critical',
                'message': f'Error rate critical: {metrics.error_rate:.1%}',
                'timestamp': metrics.timestamp
            })
        
        if metrics.response_time_avg > 60:  # 60 seconds
            alerts.append({
                'level': 'warning',
                'message': f'Response time slow: {metrics.response_time_avg:.1f}s',
                'timestamp': metrics.timestamp
            })
        
        for alert in alerts:
            self.alerts.append(alert)
            logger.warning(f"System Alert [{alert['level']}]: {alert['message']}")

# Global instance
system_monitor = SystemMonitor()
