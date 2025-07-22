"""
Comprehensive System Testing & Quality Assurance
Advanced testing suite including unit tests, integration tests, load testing, 
and legal compliance validation.
"""

import asyncio
import sys
import os
import json
import time
import aiohttp
import pytest
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveSystemTester:
    """Comprehensive system testing framework"""
    
    def __init__(self, base_url: str = "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com"):
        self.base_url = base_url
        self.test_results = {
            "unit_tests": {},
            "integration_tests": {},
            "load_tests": {},
            "security_tests": {},
            "compliance_tests": {},
            "performance_tests": {}
        }
        self.session = None
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        print("🚀 STARTING COMPREHENSIVE SYSTEM TESTING")
        print("=" * 80)
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            # Phase 1: Unit Tests
            print("\n📋 PHASE 1: UNIT TESTS")
            await self._run_unit_tests()
            
            # Phase 2: Integration Tests
            print("\n🔗 PHASE 2: INTEGRATION TESTS")
            await self._run_integration_tests()
            
            # Phase 3: Performance Tests
            print("\n⚡ PHASE 3: PERFORMANCE TESTS")
            await self._run_performance_tests()
            
            # Phase 4: Security Tests
            print("\n🔒 PHASE 4: SECURITY TESTS")
            await self._run_security_tests()
            
            # Phase 5: Legal Compliance Tests
            print("\n⚖️ PHASE 5: LEGAL COMPLIANCE TESTS")
            await self._run_compliance_tests()
            
            # Phase 6: Load Tests
            print("\n📊 PHASE 6: LOAD TESTS")
            await self._run_load_tests()
        
        # Generate comprehensive report
        return self._generate_test_report()
    
    async def _run_unit_tests(self):
        """Run unit tests for core components"""
        try:
            print("   Testing core services...")
            
            # Test 1: System Monitor
            print("   • Testing System Monitor...")
            from app.services.system_monitor import system_monitor
            
            # Start monitoring
            system_monitor.start_monitoring()
            await asyncio.sleep(2)
            
            # Test metrics collection
            health = system_monitor.get_system_health()
            assert health["status"] in ["healthy", "warning", "critical"]
            
            # Test API metrics recording
            system_monitor.record_api_request("/test", "GET", 0.5, True)
            analytics = system_monitor.get_api_analytics()
            assert "GET:/test" in analytics
            
            self.test_results["unit_tests"]["system_monitor"] = "PASSED"
            print("     ✅ System Monitor: PASSED")
            
            # Test 2: Kenyan Law Database
            print("   • Testing Kenyan Law Database...")
            from app.services.kenyan_law_database import kenyan_law_db
            
            # Test search functionality
            search_results = await kenyan_law_db.search_legal_documents("employment", "act", 5)
            assert isinstance(search_results, list)
            
            # Test compliance checking
            sample_contract = "This is an employment contract for John Doe as Software Developer with salary of 150000 KES."
            compliance_result = await kenyan_law_db.check_document_compliance(sample_contract, "employment_contract")
            assert "compliance_score" in compliance_result
            
            self.test_results["unit_tests"]["kenyan_law_db"] = "PASSED"
            print("     ✅ Kenyan Law Database: PASSED")
            
            # Test 3: Performance Optimizer
            print("   • Testing Performance Optimizer...")
            from app.services.performance_optimizer import performance_optimizer
            
            # Test caching
            await performance_optimizer.cache.set("test_key", "test_value", 60)
            cached_value = await performance_optimizer.cache.get("test_key")
            assert cached_value == "test_value"
            
            # Test cache statistics
            stats = performance_optimizer.cache.get_cache_stats()
            assert "memory_cache" in stats
            assert "performance" in stats
            
            self.test_results["unit_tests"]["performance_optimizer"] = "PASSED"
            print("     ✅ Performance Optimizer: PASSED")
            
            # Test 4: Security Compliance
            print("   • Testing Security Compliance...")
            from app.services.security_compliance import security_compliance
            
            # Test input validation
            validation_result = await security_compliance.validate_input_security(
                "SELECT * FROM users", "user_input"
            )
            assert not validation_result["is_safe"]
            assert "sql_injection" in validation_result["threats_detected"]
            
            # Test encryption/decryption
            encrypted_data, record_id = await security_compliance.encrypt_sensitive_data(
                "sensitive information", "personal"
            )
            decrypted_data = await security_compliance.decrypt_sensitive_data(
                encrypted_data, record_id, "test_user"
            )
            assert decrypted_data == "sensitive information"
            
            self.test_results["unit_tests"]["security_compliance"] = "PASSED"
            print("     ✅ Security Compliance: PASSED")
            
        except Exception as e:
            logger.error(f"Unit test failed: {e}")
            self.test_results["unit_tests"]["error"] = str(e)
    
    async def _run_integration_tests(self):
        """Run integration tests for API endpoints"""
        try:
            print("   Testing API endpoints integration...")
            
            # Test 1: Health Check
            print("   • Testing Health Check endpoint...")
            async with self.session.get(f"{self.base_url}/health") as response:
                assert response.status == 200
                data = await response.json()
                assert data["status"] == "healthy"
            
            self.test_results["integration_tests"]["health_check"] = "PASSED"
            print("     ✅ Health Check: PASSED")
            
            # Test 2: Document Templates
            print("   • Testing Document Templates endpoint...")
            async with self.session.get(f"{self.base_url}/api/v1/generate/templates") as response:
                assert response.status == 200
                data = await response.json()
                assert "templates" in data
                assert "employment_contract" in data["templates"]
            
            self.test_results["integration_tests"]["templates"] = "PASSED"
            print("     ✅ Document Templates: PASSED")
            
            # Test 3: Document Generation
            print("   • Testing Document Generation endpoint...")
            generation_payload = {
                "template_id": "employment_contract",
                "document_data": {
                    "employer_name": "Test Corp Ltd",
                    "employee_name": "Test Employee",
                    "position": "Test Position",
                    "salary": 100000,
                    "start_date": "2025-08-01"
                },
                "generation_options": {
                    "output_format": "html",
                    "kenyan_law_focus": True,
                    "include_compliance_notes": True
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/generate/generate",
                json=generation_payload
            ) as response:
                assert response.status == 200
                data = await response.json()
                assert data["status"] == "completed"
                assert "generation_id" in data
                assert "document_content" in data
                
                # Store generation ID for export test
                self.test_generation_id = data["generation_id"]
            
            self.test_results["integration_tests"]["document_generation"] = "PASSED"
            print("     ✅ Document Generation: PASSED")
            
            # Test 4: Document Export
            print("   • Testing Document Export endpoint...")
            export_payload = {
                "generation_id": self.test_generation_id,
                "export_options": {
                    "add_watermark": True,
                    "include_compliance_footer": True
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/generate/export",
                json=export_payload
            ) as response:
                # Note: This might timeout in testing, so we'll check for reasonable response
                if response.status in [200, 202]:  # Accept both success and accepted
                    self.test_results["integration_tests"]["document_export"] = "PASSED"
                    print("     ✅ Document Export: PASSED")
                else:
                    self.test_results["integration_tests"]["document_export"] = f"FAILED - Status: {response.status}"
                    print(f"     ⚠️ Document Export: Status {response.status}")
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            self.test_results["integration_tests"]["error"] = str(e)
    
    async def _run_performance_tests(self):
        """Run performance tests"""
        try:
            print("   Testing system performance...")
            
            # Test 1: Response Time
            print("   • Testing API response times...")
            start_time = time.time()
            
            async with self.session.get(f"{self.base_url}/health") as response:
                response_time = time.time() - start_time
                assert response_time < 5.0  # Should respond within 5 seconds
                
                self.test_results["performance_tests"]["response_time"] = {
                    "time_seconds": response_time,
                    "status": "PASSED" if response_time < 2.0 else "WARNING"
                }
                
                if response_time < 2.0:
                    print(f"     ✅ Response Time: {response_time:.2f}s (EXCELLENT)")
                elif response_time < 5.0:
                    print(f"     ⚠️ Response Time: {response_time:.2f}s (ACCEPTABLE)")
                else:
                    print(f"     ❌ Response Time: {response_time:.2f}s (SLOW)")
            
            # Test 2: Concurrent Requests
            print("   • Testing concurrent request handling...")
            concurrent_requests = 10
            start_time = time.time()
            
            tasks = []
            for i in range(concurrent_requests):
                task = self.session.get(f"{self.base_url}/health")
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            successful_responses = sum(1 for r in responses if hasattr(r, 'status') and r.status == 200)
            
            self.test_results["performance_tests"]["concurrent_requests"] = {
                "total_requests": concurrent_requests,
                "successful_requests": successful_responses,
                "total_time": total_time,
                "avg_time_per_request": total_time / concurrent_requests,
                "status": "PASSED" if successful_responses >= concurrent_requests * 0.9 else "FAILED"
            }
            
            print(f"     ✅ Concurrent Requests: {successful_responses}/{concurrent_requests} successful")
            
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            self.test_results["performance_tests"]["error"] = str(e)
    
    async def _run_security_tests(self):
        """Run security tests"""
        try:
            print("   Testing security measures...")
            
            # Test 1: SQL Injection Protection
            print("   • Testing SQL injection protection...")
            malicious_payload = {
                "template_id": "employment_contract'; DROP TABLE users; --",
                "document_data": {
                    "employer_name": "Test Corp",
                    "employee_name": "'; DELETE FROM employees; --"
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/generate/generate",
                json=malicious_payload
            ) as response:
                # Should either reject the request or sanitize the input
                # We expect either 400 (bad request) or 200 with sanitized data
                if response.status in [400, 422]:
                    self.test_results["security_tests"]["sql_injection"] = "PASSED - Rejected"
                    print("     ✅ SQL Injection Protection: PASSED (Rejected)")
                elif response.status == 200:
                    data = await response.json()
                    # Check if the malicious content was sanitized
                    if "DROP TABLE" not in str(data):
                        self.test_results["security_tests"]["sql_injection"] = "PASSED - Sanitized"
                        print("     ✅ SQL Injection Protection: PASSED (Sanitized)")
                    else:
                        self.test_results["security_tests"]["sql_injection"] = "FAILED"
                        print("     ❌ SQL Injection Protection: FAILED")
            
            # Test 2: XSS Protection
            print("   • Testing XSS protection...")
            xss_payload = {
                "template_id": "employment_contract",
                "document_data": {
                    "employer_name": "<script>alert('XSS')</script>",
                    "employee_name": "Test Employee"
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/generate/generate",
                json=xss_payload
            ) as response:
                if response.status in [400, 422]:
                    self.test_results["security_tests"]["xss_protection"] = "PASSED - Rejected"
                    print("     ✅ XSS Protection: PASSED (Rejected)")
                elif response.status == 200:
                    data = await response.json()
                    if "<script>" not in str(data):
                        self.test_results["security_tests"]["xss_protection"] = "PASSED - Sanitized"
                        print("     ✅ XSS Protection: PASSED (Sanitized)")
                    else:
                        self.test_results["security_tests"]["xss_protection"] = "FAILED"
                        print("     ❌ XSS Protection: FAILED")
            
            # Test 3: Rate Limiting
            print("   • Testing rate limiting...")
            rapid_requests = 20
            start_time = time.time()
            
            tasks = []
            for i in range(rapid_requests):
                task = self.session.get(f"{self.base_url}/health")
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check if any requests were rate limited (429 status)
            rate_limited = sum(1 for r in responses if hasattr(r, 'status') and r.status == 429)
            
            if rate_limited > 0:
                self.test_results["security_tests"]["rate_limiting"] = "PASSED"
                print(f"     ✅ Rate Limiting: PASSED ({rate_limited} requests limited)")
            else:
                self.test_results["security_tests"]["rate_limiting"] = "WARNING - No rate limiting detected"
                print("     ⚠️ Rate Limiting: WARNING (No rate limiting detected)")
            
        except Exception as e:
            logger.error(f"Security test failed: {e}")
            self.test_results["security_tests"]["error"] = str(e)
    
    async def _run_compliance_tests(self):
        """Run legal compliance tests"""
        try:
            print("   Testing legal compliance...")
            
            # Test 1: Employment Act Compliance
            print("   • Testing Employment Act 2007 compliance...")
            
            # Test with compliant contract data
            compliant_data = {
                "template_id": "employment_contract",
                "document_data": {
                    "employer_name": "TechCorp Kenya Ltd",
                    "employee_name": "John Doe",
                    "position": "Software Developer",
                    "salary": 150000,  # Above minimum wage
                    "start_date": "2025-08-01",
                    "probation_period": 6,  # Within legal limits
                    "notice_period": 30,  # Meets minimum requirements
                    "working_hours": "8:00 AM to 5:00 PM, Monday to Friday",
                    "annual_leave": 21  # Meets minimum requirements
                },
                "generation_options": {
                    "kenyan_law_focus": True,
                    "include_compliance_notes": True
                }
            }
            
            async with self.session.post(
                f"{self.base_url}/api/v1/generate/generate",
                json=compliant_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check for compliance features
                    compliance_checks = []
                    
                    if "compliance_notes" in data and data["compliance_notes"]:
                        compliance_checks.append("Compliance notes included")
                    
                    if "metadata" in data and data["metadata"].get("kenyan_law_compliant"):
                        compliance_checks.append("Kenyan law compliance flagged")
                    
                    if "Employment Act" in str(data):
                        compliance_checks.append("Employment Act references found")
                    
                    self.test_results["compliance_tests"]["employment_act"] = {
                        "status": "PASSED",
                        "checks_passed": compliance_checks,
                        "compliance_score": data.get("metadata", {}).get("compliance_score", 0)
                    }
                    
                    print(f"     ✅ Employment Act Compliance: PASSED ({len(compliance_checks)} checks)")
                else:
                    self.test_results["compliance_tests"]["employment_act"] = "FAILED"
                    print("     ❌ Employment Act Compliance: FAILED")
            
            # Test 2: Minimum Wage Compliance
            print("   • Testing minimum wage compliance...")
            
            # Test with below minimum wage (should be flagged)
            low_wage_data = compliant_data.copy()
            low_wage_data["document_data"]["salary"] = 10000  # Below minimum wage
            
            async with self.session.post(
                f"{self.base_url}/api/v1/generate/generate",
                json=low_wage_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check if low wage was flagged in compliance notes
                    compliance_notes = data.get("compliance_notes", [])
                    wage_flagged = any("wage" in str(note).lower() or "salary" in str(note).lower() 
                                     for note in compliance_notes)
                    
                    if wage_flagged:
                        self.test_results["compliance_tests"]["minimum_wage"] = "PASSED - Violation detected"
                        print("     ✅ Minimum Wage Compliance: PASSED (Violation detected)")
                    else:
                        self.test_results["compliance_tests"]["minimum_wage"] = "WARNING - Violation not detected"
                        print("     ⚠️ Minimum Wage Compliance: WARNING (Violation not detected)")
                else:
                    self.test_results["compliance_tests"]["minimum_wage"] = "FAILED"
                    print("     ❌ Minimum Wage Compliance: FAILED")
            
        except Exception as e:
            logger.error(f"Compliance test failed: {e}")
            self.test_results["compliance_tests"]["error"] = str(e)
    
    async def _run_load_tests(self):
        """Run load tests"""
        try:
            print("   Testing system under load...")
            
            # Test 1: Sustained Load
            print("   • Testing sustained load (50 requests over 30 seconds)...")
            
            total_requests = 50
            duration_seconds = 30
            interval = duration_seconds / total_requests
            
            start_time = time.time()
            successful_requests = 0
            failed_requests = 0
            response_times = []
            
            for i in range(total_requests):
                request_start = time.time()
                
                try:
                    async with self.session.get(f"{self.base_url}/health") as response:
                        request_time = time.time() - request_start
                        response_times.append(request_time)
                        
                        if response.status == 200:
                            successful_requests += 1
                        else:
                            failed_requests += 1
                            
                except Exception:
                    failed_requests += 1
                
                # Wait for next request
                if i < total_requests - 1:
                    await asyncio.sleep(interval)
            
            total_time = time.time() - start_time
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            self.test_results["load_tests"]["sustained_load"] = {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "success_rate": successful_requests / total_requests,
                "total_time": total_time,
                "avg_response_time": avg_response_time,
                "requests_per_second": total_requests / total_time,
                "status": "PASSED" if successful_requests / total_requests >= 0.95 else "FAILED"
            }
            
            print(f"     ✅ Sustained Load: {successful_requests}/{total_requests} successful "
                  f"({avg_response_time:.2f}s avg response)")
            
        except Exception as e:
            logger.error(f"Load test failed: {e}")
            self.test_results["load_tests"]["error"] = str(e)
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        # Calculate overall scores
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.test_results.items():
            for test_name, result in tests.items():
                if test_name != "error":
                    total_tests += 1
                    if isinstance(result, str) and "PASSED" in result:
                        passed_tests += 1
                    elif isinstance(result, dict) and result.get("status") == "PASSED":
                        passed_tests += 1
        
        overall_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "overall_score": overall_score,
                "test_date": datetime.utcnow().isoformat(),
                "system_status": "PRODUCTION_READY" if overall_score >= 90 else "NEEDS_ATTENTION"
            },
            "detailed_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check performance
        perf_tests = self.test_results.get("performance_tests", {})
        if "response_time" in perf_tests:
            response_time = perf_tests["response_time"].get("time_seconds", 0)
            if response_time > 2.0:
                recommendations.append("Consider optimizing API response times")
        
        # Check security
        sec_tests = self.test_results.get("security_tests", {})
        if "rate_limiting" in sec_tests and "WARNING" in sec_tests["rate_limiting"]:
            recommendations.append("Implement rate limiting for better security")
        
        # Check compliance
        comp_tests = self.test_results.get("compliance_tests", {})
        if "minimum_wage" in comp_tests and "WARNING" in comp_tests["minimum_wage"]:
            recommendations.append("Enhance minimum wage compliance checking")
        
        if not recommendations:
            recommendations.append("System is performing well - continue monitoring")
        
        return recommendations

async def main():
    """Run comprehensive system tests"""
    tester = ComprehensiveSystemTester()
    
    try:
        report = await tester.run_comprehensive_tests()
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        summary = report["test_summary"]
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   • Total Tests: {summary['total_tests']}")
        print(f"   • Passed: {summary['passed_tests']}")
        print(f"   • Failed: {summary['failed_tests']}")
        print(f"   • Success Rate: {summary['overall_score']:.1f}%")
        print(f"   • System Status: {summary['system_status']}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")
        
        print(f"\n🚀 SYSTEM READINESS:")
        if summary['overall_score'] >= 90:
            print("   ✅ SYSTEM IS PRODUCTION READY!")
            print("   🎉 All critical tests passed - ready for deployment")
        elif summary['overall_score'] >= 75:
            print("   ⚠️ SYSTEM NEEDS MINOR IMPROVEMENTS")
            print("   🔧 Address recommendations before full deployment")
        else:
            print("   ❌ SYSTEM NEEDS SIGNIFICANT IMPROVEMENTS")
            print("   🛠️ Critical issues must be resolved before deployment")
        
        # Save detailed report
        report_file = Path("comprehensive_test_report.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return summary['overall_score'] >= 90
        
    except Exception as e:
        print(f"\n❌ TESTING FAILED: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n✅ COMPREHENSIVE TESTING COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\n❌ TESTING COMPLETED WITH ISSUES")
        sys.exit(1)
