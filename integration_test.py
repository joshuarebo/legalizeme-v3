#!/usr/bin/env python3
"""
Multi-Modal Legal Document Processing - Integration Test
End-to-end testing of the complete multi-modal processing pipeline
"""

import asyncio
import logging
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime
import requests
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure tesseract path for Windows
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    logger.info("Tesseract path configured for Windows")
except ImportError:
    logger.warning("pytesseract not available")

# Import our components
from app.services.advanced_multimodal import (
    MultiModalDocumentProcessor,
    DocumentRouter,
    MultiModalVectorIntegration
)

class IntegrationTestSuite:
    """Comprehensive integration test suite"""
    
    def __init__(self):
        self.processor = MultiModalDocumentProcessor()
        self.router = DocumentRouter()
        self.vector_integration = MultiModalVectorIntegration()
        self.test_results = []
        
        # Test configuration
        self.sample_dir = Path("data/samples")
        self.api_base_url = "http://localhost:8000"
        
    async def run_complete_integration_test(self):
        """Run complete end-to-end integration test"""
        logger.info("🚀 Starting Complete Integration Test Suite")
        logger.info("=" * 60)
        
        # Initialize all services
        await self._initialize_services()
        
        # Test 1: Document Processing Pipeline
        await self._test_document_processing_pipeline()
        
        # Test 2: Vector Integration Pipeline
        await self._test_vector_integration_pipeline()
        
        # Test 3: Search and Retrieval Pipeline
        await self._test_search_retrieval_pipeline()
        
        # Test 4: API Endpoints (if server is running)
        await self._test_api_endpoints()
        
        # Test 5: Performance Benchmarks
        await self._test_performance_benchmarks()
        
        # Test 6: Error Handling and Edge Cases
        await self._test_error_handling()
        
        # Generate comprehensive report
        self._generate_integration_report()
    
    async def _initialize_services(self):
        """Initialize all services"""
        try:
            logger.info("🔧 Initializing services...")
            await self.processor.initialize()
            await self.router.initialize()
            await self.vector_integration.initialize()
            
            self.test_results.append({
                "test": "Service Initialization",
                "status": "PASS",
                "message": "All services initialized successfully",
                "timestamp": datetime.now().isoformat()
            })
            logger.info("✅ All services initialized")
        except Exception as e:
            self.test_results.append({
                "test": "Service Initialization",
                "status": "FAIL",
                "message": f"Service initialization failed: {e}",
                "timestamp": datetime.now().isoformat()
            })
            logger.error(f"❌ Service initialization failed: {e}")
    
    async def _test_document_processing_pipeline(self):
        """Test complete document processing pipeline"""
        logger.info("📄 Testing Document Processing Pipeline...")
        
        test_files = [
            ("employment_contract_sample.pdf", "pdf"),
            ("scanned_affidavit.png", "image"),
            ("affidavit_sample.txt", "text")
        ]
        
        for filename, file_type in test_files:
            file_path = self.sample_dir / filename
            
            if not file_path.exists():
                self.test_results.append({
                    "test": f"Document Processing - {filename}",
                    "status": "SKIP",
                    "message": f"File not found: {filename}",
                    "timestamp": datetime.now().isoformat()
                })
                continue
            
            try:
                start_time = datetime.now()
                
                # Process document through router
                result = await self.router.process_document(
                    file_path,
                    {
                        "generate_summary": True,
                        "summary_model": "claude-sonnet-4",
                        "extract_entities": True
                    }
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Validate results
                success = result.get("success", False)
                document_type = result.get("document_type", "unknown")
                word_count = result.get("word_count", 0)
                
                status = "PASS" if success and word_count > 0 else "FAIL"
                message = f"Type: {document_type}, Words: {word_count}, Time: {processing_time:.2f}s"
                
                if result.get("summary_data"):
                    message += f", Summary: ✅"
                
                self.test_results.append({
                    "test": f"Document Processing - {filename}",
                    "status": status,
                    "message": message,
                    "details": {
                        "file_type": file_type,
                        "processing_time": processing_time,
                        "result": result
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"✅ {filename}: {message}")
                
            except Exception as e:
                self.test_results.append({
                    "test": f"Document Processing - {filename}",
                    "status": "FAIL",
                    "message": f"Processing failed: {e}",
                    "timestamp": datetime.now().isoformat()
                })
                logger.error(f"❌ {filename}: Processing failed: {e}")
    
    async def _test_vector_integration_pipeline(self):
        """Test vector integration and indexing"""
        logger.info("🔍 Testing Vector Integration Pipeline...")
        
        try:
            # Test document indexing
            test_file = self.sample_dir / "employment_contract_sample.txt"
            
            if test_file.exists():
                start_time = datetime.now()
                
                result = await self.vector_integration.process_and_index_document(
                    test_file,
                    {
                        "generate_summary": True,
                        "chunk_for_vector": True
                    }
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                success = result.get("success", False)
                chunks_created = result.get("chunks_created", 0)
                document_id = result.get("indexing_result", {}).get("document_id")
                
                status = "PASS" if success and chunks_created > 0 else "FAIL"
                message = f"Indexed: {success}, Chunks: {chunks_created}, Time: {processing_time:.2f}s"
                
                self.test_results.append({
                    "test": "Vector Integration - Indexing",
                    "status": status,
                    "message": message,
                    "details": {
                        "document_id": document_id,
                        "processing_time": processing_time,
                        "result": result
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"✅ Vector indexing: {message}")
            else:
                self.test_results.append({
                    "test": "Vector Integration - Indexing",
                    "status": "SKIP",
                    "message": "Test file not found",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            self.test_results.append({
                "test": "Vector Integration - Indexing",
                "status": "FAIL",
                "message": f"Vector indexing failed: {e}",
                "timestamp": datetime.now().isoformat()
            })
            logger.error(f"❌ Vector indexing failed: {e}")
    
    async def _test_search_retrieval_pipeline(self):
        """Test search and retrieval capabilities"""
        logger.info("🔎 Testing Search and Retrieval Pipeline...")
        
        test_queries = [
            "employment contract salary terms",
            "affidavit sworn statement",
            "legal document termination clause",
            "court judgment ruling"
        ]
        
        for query in test_queries:
            try:
                start_time = datetime.now()
                
                results = await self.vector_integration.search_multimodal_documents(
                    query=query,
                    filters={"document_type": None},
                    limit=5
                )
                
                search_time = (datetime.now() - start_time).total_seconds()
                
                result_count = len(results)
                avg_relevance = sum(r.get("relevance_score", 0) for r in results) / result_count if result_count > 0 else 0
                
                status = "PASS" if result_count > 0 else "PARTIAL"
                message = f"Results: {result_count}, Avg Relevance: {avg_relevance:.3f}, Time: {search_time:.2f}s"
                
                self.test_results.append({
                    "test": f"Search - '{query[:30]}...'",
                    "status": status,
                    "message": message,
                    "details": {
                        "query": query,
                        "result_count": result_count,
                        "search_time": search_time,
                        "results": results[:2]  # Include first 2 results
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"✅ Search '{query[:30]}...': {message}")
                
            except Exception as e:
                self.test_results.append({
                    "test": f"Search - '{query[:30]}...'",
                    "status": "FAIL",
                    "message": f"Search failed: {e}",
                    "timestamp": datetime.now().isoformat()
                })
                logger.error(f"❌ Search '{query[:30]}...' failed: {e}")
    
    async def _test_api_endpoints(self):
        """Test API endpoints if server is running"""
        logger.info("🌐 Testing API Endpoints...")
        
        # Test health endpoint
        try:
            response = requests.get(f"{self.api_base_url}/multimodal/health", timeout=5)
            
            if response.status_code == 200:
                self.test_results.append({
                    "test": "API Health Check",
                    "status": "PASS",
                    "message": f"Health endpoint responding: {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                })
                logger.info("✅ API health check passed")
            else:
                self.test_results.append({
                    "test": "API Health Check",
                    "status": "FAIL",
                    "message": f"Health endpoint error: {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                })
                
        except requests.exceptions.RequestException:
            self.test_results.append({
                "test": "API Health Check",
                "status": "SKIP",
                "message": "API server not running locally",
                "timestamp": datetime.now().isoformat()
            })
            logger.info("⚠️ API server not running - skipping endpoint tests")
    
    async def _test_performance_benchmarks(self):
        """Test performance benchmarks"""
        logger.info("⚡ Testing Performance Benchmarks...")
        
        try:
            # Test processing speed with different file types
            test_file = self.sample_dir / "employment_contract_sample.pdf"
            
            if test_file.exists():
                # Run multiple iterations for average
                times = []
                for i in range(3):
                    start_time = datetime.now()
                    result = await self.router.process_document(test_file)
                    processing_time = (datetime.now() - start_time).total_seconds()
                    times.append(processing_time)
                
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                # Performance thresholds
                pdf_threshold = 30.0  # 30 seconds for PDF processing
                status = "PASS" if avg_time < pdf_threshold else "FAIL"
                
                self.test_results.append({
                    "test": "Performance Benchmark - PDF",
                    "status": status,
                    "message": f"Avg: {avg_time:.2f}s, Min: {min_time:.2f}s, Max: {max_time:.2f}s",
                    "details": {
                        "average_time": avg_time,
                        "min_time": min_time,
                        "max_time": max_time,
                        "threshold": pdf_threshold,
                        "iterations": len(times)
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"✅ Performance benchmark: Avg {avg_time:.2f}s")
            else:
                self.test_results.append({
                    "test": "Performance Benchmark",
                    "status": "SKIP",
                    "message": "Test file not available",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            self.test_results.append({
                "test": "Performance Benchmark",
                "status": "FAIL",
                "message": f"Performance test failed: {e}",
                "timestamp": datetime.now().isoformat()
            })
            logger.error(f"❌ Performance benchmark failed: {e}")
    
    async def _test_error_handling(self):
        """Test error handling and edge cases"""
        logger.info("🛡️ Testing Error Handling...")
        
        # Test with non-existent file
        try:
            result = await self.router.process_document(Path("nonexistent.pdf"))
            
            if not result.get("success"):
                self.test_results.append({
                    "test": "Error Handling - Non-existent File",
                    "status": "PASS",
                    "message": "Correctly handled non-existent file",
                    "timestamp": datetime.now().isoformat()
                })
                logger.info("✅ Error handling: Non-existent file handled correctly")
            else:
                self.test_results.append({
                    "test": "Error Handling - Non-existent File",
                    "status": "FAIL",
                    "message": "Should have failed for non-existent file",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            self.test_results.append({
                "test": "Error Handling - Non-existent File",
                "status": "PASS",
                "message": f"Exception correctly raised: {type(e).__name__}",
                "timestamp": datetime.now().isoformat()
            })
            logger.info("✅ Error handling: Exception correctly raised")
    
    def _generate_integration_report(self):
        """Generate comprehensive integration test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "SKIP"])
        partial_tests = len([r for r in self.test_results if r["status"] == "PARTIAL"])
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        report = {
            "integration_test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "partial": partial_tests,
                "success_rate": f"{success_rate:.1f}%",
                "overall_status": "PASS" if success_rate >= 90 else "FAIL"
            },
            "test_categories": {
                "document_processing": len([r for r in self.test_results if "Document Processing" in r["test"]]),
                "vector_integration": len([r for r in self.test_results if "Vector Integration" in r["test"]]),
                "search_retrieval": len([r for r in self.test_results if "Search" in r["test"]]),
                "api_endpoints": len([r for r in self.test_results if "API" in r["test"]]),
                "performance": len([r for r in self.test_results if "Performance" in r["test"]]),
                "error_handling": len([r for r in self.test_results if "Error Handling" in r["test"]])
            },
            "detailed_results": self.test_results
        }
        
        # Save report
        with open("integration_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*80)
        print("🧪 MULTI-MODAL INTEGRATION TEST REPORT")
        print("="*80)
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Skipped: {skipped_tests}")
        print(f"🔶 Partial: {partial_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"🎯 Overall Status: {report['integration_test_summary']['overall_status']}")
        print("="*80)
        
        # Print test results
        for result in self.test_results:
            status_symbol = {
                "PASS": "✅",
                "FAIL": "❌", 
                "SKIP": "⚠️",
                "PARTIAL": "🔶"
            }.get(result["status"], "❓")
            
            print(f"{status_symbol} {result['test']}: {result['message']}")
        
        print(f"\n📄 Detailed report saved to: integration_test_report.json")
        
        if success_rate >= 90:
            print("\n🎉 INTEGRATION TESTS PASSED! System ready for production deployment.")
        else:
            print("\n⚠️ INTEGRATION TESTS NEED ATTENTION! Review failed tests before deployment.")

async def main():
    """Main integration test execution"""
    test_suite = IntegrationTestSuite()
    await test_suite.run_complete_integration_test()

if __name__ == "__main__":
    asyncio.run(main())
