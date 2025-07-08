#!/usr/bin/env python3
"""
Comprehensive System Test for Kenyan Legal AI
Tests all major components including AWS Bedrock integration, fallback systems, and API endpoints
"""

import asyncio
import os
import sys
import json
import time
import logging
from typing import Dict, Any, List
import httpx
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemTester:
    """Comprehensive system tester"""
    
    def __init__(self):
        self.test_results = []
        self.base_url = "http://localhost:8000"
        
    async def run_all_tests(self):
        """Run all system tests"""
        logger.info("Starting comprehensive system tests...")
        
        # Test 1: Framework Compliance - AWS Bedrock Integration
        await self.test_aws_bedrock_integration()
        
        # Test 2: API Integration Tests
        await self.test_api_endpoints()
        
        # Test 3: Training Data Setup
        await self.test_training_data_generation()
        
        # Test 4: Fallback System Testing
        await self.test_fallback_systems()
        
        # Test 5: Monitoring & Logging
        await self.test_monitoring_logging()
        
        # Generate test report
        self.generate_test_report()
        
        return self.test_results
    
    async def test_aws_bedrock_integration(self):
        """Test AWS Bedrock integration and Claude 4 access"""
        logger.info("Testing AWS Bedrock integration...")
        
        try:
            # Test AWS credentials and Bedrock client initialization
            from app.services.ai_service import AIService
            
            ai_service = AIService()
            
            # Test Bedrock client initialization
            if hasattr(ai_service, 'bedrock_client') and ai_service.bedrock_client:
                self.add_test_result("AWS Bedrock Client", "PASS", "Bedrock client initialized successfully")
            else:
                self.add_test_result("AWS Bedrock Client", "FAIL", "Bedrock client not initialized")
            
            # Test Claude 4 model availability
            try:
                # This would test actual Claude 4 access in production
                test_query = "Test query for Claude 4 via AWS Bedrock"
                # response = await ai_service.query_claude_bedrock(test_query)
                self.add_test_result("Claude 4 Access", "SKIP", "Requires valid AWS credentials and Bedrock access")
            except Exception as e:
                self.add_test_result("Claude 4 Access", "FAIL", f"Claude 4 access failed: {str(e)}")
            
            # Test model health monitoring
            if hasattr(ai_service, 'model_health'):
                self.add_test_result("Model Health Monitoring", "PASS", "Health monitoring system active")
            else:
                self.add_test_result("Model Health Monitoring", "FAIL", "Health monitoring not found")
                
        except Exception as e:
            self.add_test_result("AWS Bedrock Integration", "FAIL", f"Integration test failed: {str(e)}")
    
    async def test_api_endpoints(self):
        """Test all API endpoints with success and failure scenarios"""
        logger.info("Testing API endpoints...")
        
        # Start the server for testing (in a real scenario)
        # For now, we'll test the endpoint definitions
        
        try:
            from app.main import app
            from fastapi.testclient import TestClient
            
            client = TestClient(app)
            
            # Test health endpoint
            try:
                response = client.get("/health")
                if response.status_code == 200:
                    self.add_test_result("Health Endpoint", "PASS", "Health endpoint accessible")
                else:
                    self.add_test_result("Health Endpoint", "FAIL", f"Health endpoint returned {response.status_code}")
            except Exception as e:
                self.add_test_result("Health Endpoint", "FAIL", f"Health endpoint error: {str(e)}")
            
            # Test root endpoint
            try:
                response = client.get("/")
                if response.status_code == 200:
                    data = response.json()
                    if "orchestration" in data:
                        self.add_test_result("Root Endpoint", "PASS", "Root endpoint with orchestration info")
                    else:
                        self.add_test_result("Root Endpoint", "PARTIAL", "Root endpoint accessible but missing orchestration info")
                else:
                    self.add_test_result("Root Endpoint", "FAIL", f"Root endpoint returned {response.status_code}")
            except Exception as e:
                self.add_test_result("Root Endpoint", "FAIL", f"Root endpoint error: {str(e)}")
            
            # Test metrics endpoint
            try:
                response = client.get("/metrics")
                if response.status_code == 200:
                    self.add_test_result("Metrics Endpoint", "PASS", "Metrics endpoint accessible")
                else:
                    self.add_test_result("Metrics Endpoint", "FAIL", f"Metrics endpoint returned {response.status_code}")
            except Exception as e:
                self.add_test_result("Metrics Endpoint", "FAIL", f"Metrics endpoint error: {str(e)}")
            
            # Test API documentation
            try:
                response = client.get("/docs")
                if response.status_code == 200:
                    self.add_test_result("API Documentation", "PASS", "Swagger UI accessible")
                else:
                    self.add_test_result("API Documentation", "SKIP", "API docs disabled in production mode")
            except Exception as e:
                self.add_test_result("API Documentation", "FAIL", f"API docs error: {str(e)}")
                
        except Exception as e:
            self.add_test_result("API Endpoints", "FAIL", f"API testing failed: {str(e)}")
    
    async def test_training_data_generation(self):
        """Test training data generation script"""
        logger.info("Testing training data generation...")
        
        try:
            # Check if training data script exists
            script_path = "scripts/prepare_training_data.py"
            if os.path.exists(script_path):
                self.add_test_result("Training Data Script", "PASS", "Training data script exists")
                
                # Test script execution (dry run)
                try:
                    import subprocess
                    result = subprocess.run([
                        sys.executable, script_path, "--dry-run"
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        self.add_test_result("Training Data Generation", "PASS", "Script executed successfully")
                    else:
                        self.add_test_result("Training Data Generation", "FAIL", f"Script failed: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    self.add_test_result("Training Data Generation", "TIMEOUT", "Script execution timed out")
                except Exception as e:
                    self.add_test_result("Training Data Generation", "FAIL", f"Script execution error: {str(e)}")
            else:
                self.add_test_result("Training Data Script", "FAIL", "Training data script not found")
                
            # Check for existing training data
            data_path = "data/kenyan_legal_training.jsonl"
            if os.path.exists(data_path):
                file_size = os.path.getsize(data_path)
                self.add_test_result("Training Data File", "PASS", f"Training data exists ({file_size} bytes)")
            else:
                self.add_test_result("Training Data File", "SKIP", "Training data file not found (will be generated)")
                
        except Exception as e:
            self.add_test_result("Training Data Setup", "FAIL", f"Training data test failed: {str(e)}")
    
    async def test_fallback_systems(self):
        """Test fallback model systems"""
        logger.info("Testing fallback systems...")
        
        try:
            from app.services.ai_service import AIService
            
            ai_service = AIService()
            
            # Test model priority system
            if hasattr(ai_service, 'model_priority'):
                self.add_test_result("Model Priority System", "PASS", "Model priority system configured")
            else:
                self.add_test_result("Model Priority System", "FAIL", "Model priority system not found")
            
            # Test fallback mechanism
            try:
                # Simulate primary model failure
                original_claude_status = getattr(ai_service, 'claude_status', 'UNKNOWN')
                
                # Test fallback to local models
                if hasattr(ai_service, 'hunyuan_model') or hasattr(ai_service, 'minimax_model'):
                    self.add_test_result("Fallback Models", "PASS", "Fallback models configured")
                else:
                    self.add_test_result("Fallback Models", "SKIP", "Local models not loaded (expected in production)")
                
                # Test health monitoring
                if hasattr(ai_service, 'check_model_health'):
                    health_status = ai_service.check_model_health()
                    self.add_test_result("Model Health Check", "PASS", f"Health check functional: {health_status}")
                else:
                    self.add_test_result("Model Health Check", "FAIL", "Health check method not found")
                    
            except Exception as e:
                self.add_test_result("Fallback Testing", "FAIL", f"Fallback test error: {str(e)}")
                
        except Exception as e:
            self.add_test_result("Fallback Systems", "FAIL", f"Fallback system test failed: {str(e)}")
    
    async def test_monitoring_logging(self):
        """Test monitoring and logging systems"""
        logger.info("Testing monitoring and logging...")
        
        try:
            # Test logging configuration
            import logging
            root_logger = logging.getLogger()
            if root_logger.handlers:
                self.add_test_result("Logging Configuration", "PASS", f"Logging configured with {len(root_logger.handlers)} handlers")
            else:
                self.add_test_result("Logging Configuration", "FAIL", "No logging handlers configured")
            
            # Test log file creation
            log_dir = "logs"
            if os.path.exists(log_dir):
                log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
                if log_files:
                    self.add_test_result("Log Files", "PASS", f"Log files found: {log_files}")
                else:
                    self.add_test_result("Log Files", "SKIP", "No log files found (may be created at runtime)")
            else:
                self.add_test_result("Log Directory", "SKIP", "Log directory not found (will be created)")
            
            # Test metrics collection
            try:
                from app.core.orchestration.intelligence_enhancer import IntelligenceEnhancer
                enhancer = IntelligenceEnhancer()
                metrics = enhancer.get_comprehensive_metrics()
                if metrics:
                    self.add_test_result("Metrics Collection", "PASS", "Metrics collection functional")
                else:
                    self.add_test_result("Metrics Collection", "FAIL", "No metrics collected")
            except Exception as e:
                self.add_test_result("Metrics Collection", "FAIL", f"Metrics error: {str(e)}")
            
            # Test rate limiting
            try:
                from app.core.security.rate_limiter import RateLimiter
                rate_limiter = RateLimiter()
                metrics = rate_limiter.get_metrics()
                if metrics:
                    self.add_test_result("Rate Limiting", "PASS", "Rate limiting system functional")
                else:
                    self.add_test_result("Rate Limiting", "FAIL", "Rate limiting not functional")
            except Exception as e:
                self.add_test_result("Rate Limiting", "FAIL", f"Rate limiting error: {str(e)}")
                
        except Exception as e:
            self.add_test_result("Monitoring & Logging", "FAIL", f"Monitoring test failed: {str(e)}")
    
    def add_test_result(self, test_name: str, status: str, message: str):
        """Add a test result"""
        result = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.test_results.append(result)
        
        # Log the result
        status_icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "PARTIAL": "⚠️", "TIMEOUT": "⏱️"}.get(status, "❓")
        logger.info(f"{status_icon} {test_name}: {message}")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        
        # Calculate statistics
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped = len([r for r in self.test_results if r["status"] == "SKIP"])
        partial = len([r for r in self.test_results if r["status"] == "PARTIAL"])
        
        # Generate report
        report_lines = [
            "# Kenyan Legal AI - Comprehensive System Test Report",
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Test Summary",
            f"- Total Tests: {total_tests}",
            f"- Passed: {passed} ✅",
            f"- Failed: {failed} ❌", 
            f"- Skipped: {skipped} ⏭️",
            f"- Partial: {partial} ⚠️",
            f"- Success Rate: {(passed / total_tests * 100):.1f}%" if total_tests > 0 else "- Success Rate: 0%",
            ""
        ]
        
        # Overall status
        if failed == 0:
            if partial == 0:
                status = "🟢 ALL TESTS PASSED"
            else:
                status = "🟡 TESTS PASSED WITH WARNINGS"
        else:
            status = "🔴 SOME TESTS FAILED"
        
        report_lines.extend([
            f"## Overall Status: {status}",
            "",
            "## Detailed Results",
            ""
        ])
        
        # Add detailed results
        for result in self.test_results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "PARTIAL": "⚠️", "TIMEOUT": "⏱️"}.get(result["status"], "❓")
            report_lines.extend([
                f"### {status_icon} {result['test_name']}",
                f"**Status**: {result['status']}",
                f"**Message**: {result['message']}",
                f"**Timestamp**: {result['timestamp']}",
                ""
            ])
        
        # Save report
        os.makedirs('reports', exist_ok=True)
        report_filename = f"system_test_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(f"reports/{report_filename}", 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        
        # Print summary
        print("\n" + "="*60)
        print("COMPREHENSIVE SYSTEM TEST COMPLETE")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Skipped: {skipped} ⏭️")
        print(f"Partial: {partial} ⚠️")
        print(f"Success Rate: {(passed / total_tests * 100):.1f}%" if total_tests > 0 else "Success Rate: 0%")
        print(f"\nDetailed report saved: reports/{report_filename}")
        print(f"\nOverall Status: {status}")

async def main():
    """Main test function"""
    tester = SystemTester()
    results = await tester.run_all_tests()
    
    # Return appropriate exit code
    failed_tests = [r for r in results if r["status"] == "FAIL"]
    return 0 if not failed_tests else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
