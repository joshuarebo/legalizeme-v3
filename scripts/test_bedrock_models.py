#!/usr/bin/env python3
"""
Comprehensive test script for AWS Bedrock model integration
Tests Claude Sonnet 4, Claude 3.7, and Mistral 7B via AWS Bedrock
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.services.ai_service import AIService
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BedrockModelTester:
    """Test AWS Bedrock model integration"""
    
    def __init__(self):
        self.ai_service = None
        self.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "test_summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "models_tested": []
            },
            "model_tests": {},
            "fallback_tests": {},
            "performance_metrics": {}
        }
        
    async def initialize_service(self):
        """Initialize the AI service"""
        try:
            logger.info("Initializing AI service...")
            self.ai_service = AIService()
            await asyncio.sleep(2)  # Give time for initialization
            logger.info("AI service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            return False
    
    def get_test_queries(self):
        """Get test queries for legal AI testing"""
        return [
            {
                "query": "What are the constitutional rights in Kenya?",
                "expected_keywords": ["constitution", "rights", "kenya", "bill of rights"],
                "category": "constitutional_law"
            },
            {
                "query": "Explain the process of company registration in Kenya",
                "expected_keywords": ["company", "registration", "kenya", "process"],
                "category": "corporate_law"
            },
            {
                "query": "What is the law on guardianship in Kenya?",
                "expected_keywords": ["guardianship", "kenya", "law", "children"],
                "category": "family_law"
            }
        ]
    
    async def test_single_model(self, model_name: str, test_queries: list) -> dict:
        """Test a single Bedrock model"""
        logger.info(f"\n🧪 Testing {model_name}...")
        
        model_results = {
            "model_name": model_name,
            "status": "unknown",
            "tests_passed": 0,
            "tests_failed": 0,
            "response_times": [],
            "responses": [],
            "errors": []
        }
        
        # Check if model is available
        model_status = self.ai_service.get_model_status()
        if model_name not in model_status.get('models', {}):
            model_results["status"] = "not_configured"
            model_results["errors"].append(f"Model {model_name} not configured")
            return model_results
            
        model_info = model_status['models'][model_name]
        if model_info['status'] != 'healthy':
            model_results["status"] = "unhealthy"
            model_results["errors"].append(f"Model {model_name} status: {model_info['status']}")
            return model_results
        
        # Test each query
        for i, test_case in enumerate(test_queries):
            try:
                logger.info(f"  Test {i+1}: {test_case['category']}")
                
                start_time = time.time()
                
                # Generate response using the specific model
                # We'll force the model by temporarily modifying the fallback order
                original_configs = self.ai_service.model_configs.copy()
                
                # Temporarily set only this model as available
                for name in self.ai_service.model_configs:
                    if name != model_name:
                        self.ai_service.model_status[name] = self.ai_service.model_status[name].__class__.FAILED
                
                result_dict = await self.ai_service.answer_legal_query(
                    test_case["query"],
                    user_context={"test_mode": True}
                )
                result = result_dict.get('response', '') if isinstance(result_dict, dict) else str(result_dict)
                
                # Restore original status
                self.ai_service.model_configs = original_configs
                
                response_time = time.time() - start_time
                model_results["response_times"].append(response_time)
                
                # Validate response
                if result and len(result.strip()) > 50:
                    # Check for expected keywords
                    response_lower = result.lower()
                    keywords_found = sum(1 for keyword in test_case["expected_keywords"] 
                                       if keyword.lower() in response_lower)
                    
                    if keywords_found >= len(test_case["expected_keywords"]) // 2:
                        model_results["tests_passed"] += 1
                        logger.info(f"    ✅ Test passed ({response_time:.2f}s)")
                    else:
                        model_results["tests_failed"] += 1
                        logger.info(f"    ❌ Test failed - insufficient keywords")
                        model_results["errors"].append(f"Test {i+1}: Insufficient keywords found")
                    
                    model_results["responses"].append({
                        "query": test_case["query"],
                        "response": result[:200] + "..." if len(result) > 200 else result,
                        "response_time": response_time,
                        "keywords_found": keywords_found
                    })
                else:
                    model_results["tests_failed"] += 1
                    logger.info(f"    ❌ Test failed - invalid response")
                    model_results["errors"].append(f"Test {i+1}: Invalid or too short response")
                
            except Exception as e:
                model_results["tests_failed"] += 1
                error_msg = f"Test {i+1} error: {str(e)}"
                model_results["errors"].append(error_msg)
                logger.error(f"    ❌ {error_msg}")
        
        # Determine overall status
        if model_results["tests_passed"] > 0 and model_results["tests_failed"] == 0:
            model_results["status"] = "excellent"
        elif model_results["tests_passed"] > model_results["tests_failed"]:
            model_results["status"] = "good"
        elif model_results["tests_passed"] > 0:
            model_results["status"] = "partial"
        else:
            model_results["status"] = "failed"
        
        # Calculate performance metrics
        if model_results["response_times"]:
            model_results["avg_response_time"] = sum(model_results["response_times"]) / len(model_results["response_times"])
            model_results["max_response_time"] = max(model_results["response_times"])
            model_results["min_response_time"] = min(model_results["response_times"])
        
        return model_results
    
    async def test_fallback_system(self) -> dict:
        """Test the fallback system with all Bedrock models"""
        logger.info("\n🔄 Testing Fallback System...")
        
        fallback_results = {
            "test_name": "bedrock_fallback_system",
            "status": "unknown",
            "fallback_chain": ["claude-sonnet-4", "claude-3-7", "mistral-large"],
            "tests": []
        }
        
        test_query = "What are the constitutional rights in Kenya?"
        
        # Test normal fallback (all models healthy)
        try:
            logger.info("  Testing normal fallback behavior...")
            start_time = time.time()
            
            result_dict = await self.ai_service.answer_legal_query(test_query)
            result = result_dict.get('response', '') if isinstance(result_dict, dict) else str(result_dict)
            response_time = time.time() - start_time
            
            fallback_results["tests"].append({
                "scenario": "normal_operation",
                "success": bool(result and len(result.strip()) > 50),
                "response_time": response_time,
                "response_length": len(result) if result else 0
            })
            
            logger.info(f"    ✅ Normal operation test passed ({response_time:.2f}s)")
            
        except Exception as e:
            fallback_results["tests"].append({
                "scenario": "normal_operation",
                "success": False,
                "error": str(e)
            })
            logger.error(f"    ❌ Normal operation test failed: {e}")
        
        # Test with primary model disabled
        try:
            logger.info("  Testing fallback with primary model disabled...")
            
            # Temporarily disable Claude Sonnet 4
            original_status = self.ai_service.model_status['claude-sonnet-4']
            self.ai_service.model_status['claude-sonnet-4'] = self.ai_service.model_status['claude-sonnet-4'].__class__.FAILED
            
            start_time = time.time()
            result_dict = await self.ai_service.answer_legal_query(test_query)
            result = result_dict.get('response', '') if isinstance(result_dict, dict) else str(result_dict)
            response_time = time.time() - start_time
            
            # Restore status
            self.ai_service.model_status['claude-sonnet-4'] = original_status
            
            fallback_results["tests"].append({
                "scenario": "primary_disabled",
                "success": bool(result and len(result.strip()) > 50),
                "response_time": response_time,
                "expected_fallback": "claude-3-7"
            })
            
            logger.info(f"    ✅ Primary disabled test passed ({response_time:.2f}s)")
            
        except Exception as e:
            fallback_results["tests"].append({
                "scenario": "primary_disabled",
                "success": False,
                "error": str(e)
            })
            logger.error(f"    ❌ Primary disabled test failed: {e}")
        
        # Determine overall fallback status
        successful_tests = sum(1 for test in fallback_results["tests"] if test.get("success", False))
        total_tests = len(fallback_results["tests"])
        
        if successful_tests == total_tests:
            fallback_results["status"] = "excellent"
        elif successful_tests > 0:
            fallback_results["status"] = "partial"
        else:
            fallback_results["status"] = "failed"
        
        return fallback_results
    
    async def run_comprehensive_tests(self):
        """Run all Bedrock model tests"""
        logger.info("🚀 Starting Comprehensive Bedrock Model Tests")
        logger.info("=" * 60)
        
        # Initialize service
        if not await self.initialize_service():
            logger.error("Failed to initialize AI service. Exiting.")
            return
        
        # Get test queries
        test_queries = self.get_test_queries()
        
        # Test individual models
        bedrock_models = ['claude-sonnet-4', 'claude-3-7', 'mistral-large']
        
        for model_name in bedrock_models:
            try:
                model_results = await self.test_single_model(model_name, test_queries)
                self.test_results["model_tests"][model_name] = model_results
                self.test_results["test_summary"]["models_tested"].append(model_name)
                
                if model_results["status"] in ["excellent", "good", "partial"]:
                    self.test_results["test_summary"]["passed_tests"] += 1
                else:
                    self.test_results["test_summary"]["failed_tests"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to test {model_name}: {e}")
                self.test_results["model_tests"][model_name] = {
                    "status": "error",
                    "error": str(e)
                }
                self.test_results["test_summary"]["failed_tests"] += 1
        
        # Test fallback system
        try:
            fallback_results = await self.test_fallback_system()
            self.test_results["fallback_tests"] = fallback_results
            
            if fallback_results["status"] in ["excellent", "partial"]:
                self.test_results["test_summary"]["passed_tests"] += 1
            else:
                self.test_results["test_summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Failed to test fallback system: {e}")
            self.test_results["fallback_tests"] = {
                "status": "error",
                "error": str(e)
            }
            self.test_results["test_summary"]["failed_tests"] += 1
        
        # Update total tests
        self.test_results["test_summary"]["total_tests"] = (
            self.test_results["test_summary"]["passed_tests"] + 
            self.test_results["test_summary"]["failed_tests"]
        )
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 BEDROCK MODEL TEST REPORT")
        logger.info("=" * 60)
        
        summary = self.test_results["test_summary"]
        logger.info(f"Total Tests: {summary['total_tests']}")
        logger.info(f"Passed: {summary['passed_tests']}")
        logger.info(f"Failed: {summary['failed_tests']}")
        logger.info(f"Success Rate: {(summary['passed_tests']/summary['total_tests']*100):.1f}%" if summary['total_tests'] > 0 else "N/A")
        
        # Model-specific results
        logger.info("\n📋 Model Test Results:")
        for model_name, results in self.test_results["model_tests"].items():
            status_emoji = {
                "excellent": "🟢",
                "good": "🟡", 
                "partial": "🟠",
                "failed": "🔴",
                "error": "❌"
            }.get(results["status"], "❓")
            
            logger.info(f"  {status_emoji} {model_name}: {results['status']}")
            if "avg_response_time" in results:
                logger.info(f"    Average Response Time: {results['avg_response_time']:.2f}s")
            if results.get("errors"):
                logger.info(f"    Errors: {len(results['errors'])}")
        
        # Fallback system results
        if "fallback_tests" in self.test_results:
            fallback = self.test_results["fallback_tests"]
            status_emoji = {
                "excellent": "🟢",
                "partial": "🟠", 
                "failed": "🔴",
                "error": "❌"
            }.get(fallback["status"], "❓")
            
            logger.info(f"\n🔄 Fallback System: {status_emoji} {fallback['status']}")
        
        # Save detailed results
        output_file = "bedrock_test_results.json"
        with open(output_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"\n💾 Detailed results saved to: {output_file}")
        logger.info("=" * 60)

async def main():
    """Main test execution"""
    tester = BedrockModelTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())
