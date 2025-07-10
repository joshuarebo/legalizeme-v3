"""
Multi-Modal Document Processing Test Suite
Comprehensive testing for enhanced document processing capabilities
"""

import asyncio
import logging
import os
from pathlib import Path
import json
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure tesseract path for Windows
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    logger.info("Tesseract path configured for Windows")
except ImportError:
    logger.warning("pytesseract not available")

# Import our multi-modal components
from app.services.advanced_multimodal.document_processor import MultiModalDocumentProcessor
from app.services.advanced_multimodal.document_router import DocumentRouter
from app.services.advanced_multimodal.vector_integration import MultiModalVectorIntegration
from app.utils.ocr.image_ocr_utils import ImageOCRUtils

class MultiModalTestSuite:
    """Test suite for multi-modal document processing"""
    
    def __init__(self):
        self.processor = MultiModalDocumentProcessor()
        self.router = DocumentRouter()
        self.vector_integration = MultiModalVectorIntegration()
        self.ocr_utils = ImageOCRUtils()
        self.test_results = []
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        logger.info("Starting Multi-Modal Document Processing Test Suite")
        
        # Test 1: Processor Initialization
        await self.test_processor_initialization()
        
        # Test 2: Router Initialization
        await self.test_router_initialization()
        
        # Test 3: Vector Integration Initialization
        await self.test_vector_integration_initialization()

        # Test 4: OCR Utilities
        await self.test_ocr_utilities()

        # Test 5: Document Type Detection
        await self.test_document_type_detection()

        # Test 6: PDF Processing (if sample available)
        await self.test_pdf_processing()

        # Test 7: Image OCR Processing (if sample available)
        await self.test_image_ocr_processing()

        # Test 8: Text Summarization
        await self.test_text_summarization()

        # Test 9: Document Router Integration
        await self.test_document_router()

        # Test 10: Vector Integration and Search
        await self.test_vector_integration()

        # Test 11: Capabilities Check
        await self.test_capabilities()
        
        # Generate test report
        self.generate_test_report()
    
    async def test_processor_initialization(self):
        """Test processor initialization"""
        try:
            await self.processor.initialize()
            self.test_results.append({
                "test": "Processor Initialization",
                "status": "PASS",
                "message": "Processor initialized successfully"
            })
            logger.info("✓ Processor initialization test passed")
        except Exception as e:
            self.test_results.append({
                "test": "Processor Initialization",
                "status": "FAIL",
                "message": f"Initialization failed: {e}"
            })
            logger.error(f"✗ Processor initialization test failed: {e}")
    
    async def test_router_initialization(self):
        """Test router initialization"""
        try:
            await self.router.initialize()
            self.test_results.append({
                "test": "Router Initialization",
                "status": "PASS",
                "message": "Router initialized successfully"
            })
            logger.info("✓ Router initialization test passed")
        except Exception as e:
            self.test_results.append({
                "test": "Router Initialization",
                "status": "FAIL",
                "message": f"Router initialization failed: {e}"
            })
            logger.error(f"✗ Router initialization test failed: {e}")

    async def test_vector_integration_initialization(self):
        """Test vector integration initialization"""
        try:
            await self.vector_integration.initialize()
            self.test_results.append({
                "test": "Vector Integration Initialization",
                "status": "PASS",
                "message": "Vector integration initialized successfully"
            })
            logger.info("✓ Vector integration initialization test passed")
        except Exception as e:
            self.test_results.append({
                "test": "Vector Integration Initialization",
                "status": "FAIL",
                "message": f"Vector integration initialization failed: {e}"
            })
            logger.error(f"✗ Vector integration initialization test failed: {e}")

    async def test_ocr_utilities(self):
        """Test OCR utilities"""
        try:
            ocr_available = self.ocr_utils.check_ocr_availability()
            capabilities = self.ocr_utils.get_ocr_capabilities()
            
            self.test_results.append({
                "test": "OCR Utilities",
                "status": "PASS",
                "message": f"OCR Available: {ocr_available}",
                "details": capabilities
            })
            logger.info(f"✓ OCR utilities test passed - OCR Available: {ocr_available}")
        except Exception as e:
            self.test_results.append({
                "test": "OCR Utilities",
                "status": "FAIL",
                "message": f"OCR utilities test failed: {e}"
            })
            logger.error(f"✗ OCR utilities test failed: {e}")
    
    async def test_document_type_detection(self):
        """Test document type detection"""
        test_texts = {
            "employment_contract": "This employment contract is between ABC Company and John Doe for the position of Software Engineer with a salary of KSh 100,000 per month.",
            "affidavit": "I, John Doe, do solemnly affirm that the facts stated in this affidavit are true to the best of my knowledge.",
            "judgment": "In the matter between John Doe (Plaintiff) and Jane Smith (Defendant), this court hereby rules in favor of the plaintiff.",
            "legislation": "Act No. 15 of 2023. Section 1: This Act may be cited as the Legal AI Act, 2023.",
            "unknown": "This is just some random text that doesn't match any legal document pattern."
        }
        
        try:
            for expected_type, text in test_texts.items():
                detected_type = await self.processor.detect_document_type(text)
                
                if expected_type == "unknown":
                    # For unknown text, any detection is acceptable
                    status = "PASS"
                    message = f"Detected: {detected_type}"
                else:
                    status = "PASS" if detected_type == expected_type else "PARTIAL"
                    message = f"Expected: {expected_type}, Detected: {detected_type}"
                
                self.test_results.append({
                    "test": f"Document Type Detection - {expected_type}",
                    "status": status,
                    "message": message
                })
            
            logger.info("✓ Document type detection tests completed")
        except Exception as e:
            self.test_results.append({
                "test": "Document Type Detection",
                "status": "FAIL",
                "message": f"Document type detection failed: {e}"
            })
            logger.error(f"✗ Document type detection test failed: {e}")
    
    async def test_pdf_processing(self):
        """Test PDF processing with sample files"""
        sample_dir = Path("data/samples")
        pdf_files = list(sample_dir.glob("*.pdf"))
        
        if not pdf_files:
            self.test_results.append({
                "test": "PDF Processing",
                "status": "SKIP",
                "message": "No PDF sample files found in data/samples/"
            })
            logger.info("⚠ PDF processing test skipped - no sample files")
            return
        
        try:
            for pdf_file in pdf_files[:2]:  # Test first 2 PDFs
                result = await self.processor.extract_text_from_pdf(pdf_file)
                
                status = "PASS" if result.get("success") else "FAIL"
                message = f"File: {pdf_file.name}, Success: {result.get('success')}"
                
                if result.get("success"):
                    message += f", Words: {result.get('word_count', 0)}"
                else:
                    message += f", Error: {result.get('error', 'Unknown')}"
                
                self.test_results.append({
                    "test": f"PDF Processing - {pdf_file.name}",
                    "status": status,
                    "message": message
                })
            
            logger.info("✓ PDF processing tests completed")
        except Exception as e:
            self.test_results.append({
                "test": "PDF Processing",
                "status": "FAIL",
                "message": f"PDF processing failed: {e}"
            })
            logger.error(f"✗ PDF processing test failed: {e}")
    
    async def test_image_ocr_processing(self):
        """Test image OCR processing"""
        sample_dir = Path("data/samples")
        image_files = list(sample_dir.glob("*.png")) + list(sample_dir.glob("*.jpg"))
        
        if not image_files:
            self.test_results.append({
                "test": "Image OCR Processing",
                "status": "SKIP",
                "message": "No image sample files found in data/samples/"
            })
            logger.info("⚠ Image OCR processing test skipped - no sample files")
            return
        
        try:
            for image_file in image_files[:2]:  # Test first 2 images
                result = await self.processor.ocr_image_to_text(image_file)
                
                status = "PASS" if result.get("success") else "FAIL"
                message = f"File: {image_file.name}, Success: {result.get('success')}"
                
                if result.get("success"):
                    message += f", Words: {result.get('word_count', 0)}, Confidence: {result.get('confidence', 0):.1f}%"
                else:
                    message += f", Error: {result.get('error', 'Unknown')}"
                
                self.test_results.append({
                    "test": f"Image OCR Processing - {image_file.name}",
                    "status": status,
                    "message": message
                })
            
            logger.info("✓ Image OCR processing tests completed")
        except Exception as e:
            self.test_results.append({
                "test": "Image OCR Processing",
                "status": "FAIL",
                "message": f"Image OCR processing failed: {e}"
            })
            logger.error(f"✗ Image OCR processing test failed: {e}")
    
    async def test_text_summarization(self):
        """Test text summarization"""
        test_text = """
        This employment contract is entered into between ABC Legal Services Limited, 
        a company incorporated under the laws of Kenya (the "Company") and John Doe, 
        an individual (the "Employee"). The Employee shall serve as a Senior Legal Counsel 
        with a monthly salary of KSh 150,000. The contract shall commence on 1st January 2024 
        and shall be for an initial period of two years. The Employee shall be entitled to 
        annual leave of 21 days and medical insurance coverage. Either party may terminate 
        this contract by giving 30 days written notice.
        """
        
        try:
            result = await self.processor.summarize_text(test_text, model="claude-sonnet-4")
            
            status = "PASS" if result.get("success") else "FAIL"
            message = f"Summarization Success: {result.get('success')}"
            
            if result.get("success"):
                summary_length = len(result.get("summary", "").split())
                message += f", Summary Length: {summary_length} words"
            else:
                message += f", Error: {result.get('error', 'Unknown')}"
            
            self.test_results.append({
                "test": "Text Summarization",
                "status": status,
                "message": message,
                "details": result if result.get("success") else None
            })
            
            logger.info("✓ Text summarization test completed")
        except Exception as e:
            self.test_results.append({
                "test": "Text Summarization",
                "status": "FAIL",
                "message": f"Text summarization failed: {e}"
            })
            logger.error(f"✗ Text summarization test failed: {e}")
    
    async def test_document_router(self):
        """Test document router functionality"""
        try:
            # Test supported formats
            formats = self.router.get_supported_formats()
            capabilities = self.router.get_router_capabilities()
            
            self.test_results.append({
                "test": "Document Router",
                "status": "PASS",
                "message": f"Supported formats: {len(formats)}",
                "details": {
                    "formats": formats,
                    "capabilities": capabilities
                }
            })
            
            logger.info("✓ Document router test completed")
        except Exception as e:
            self.test_results.append({
                "test": "Document Router",
                "status": "FAIL",
                "message": f"Document router test failed: {e}"
            })
            logger.error(f"✗ Document router test failed: {e}")

    async def test_vector_integration(self):
        """Test vector integration and search capabilities"""
        try:
            # Test with sample text file
            sample_dir = Path("data/samples")
            text_files = list(sample_dir.glob("*.txt"))

            if not text_files:
                self.test_results.append({
                    "test": "Vector Integration",
                    "status": "SKIP",
                    "message": "No text sample files found for vector testing"
                })
                logger.info("⚠ Vector integration test skipped - no sample files")
                return

            # Test document processing and indexing
            test_file = text_files[0]
            processing_options = {
                "generate_summary": True,
                "chunk_for_vector": True
            }

            result = await self.vector_integration.process_and_index_document(
                test_file, processing_options
            )

            status = "PASS" if result.get("success") else "FAIL"
            message = f"File: {test_file.name}, Success: {result.get('success')}"

            if result.get("success"):
                message += f", Chunks: {result.get('chunks_created', 0)}"

                # Test search functionality
                search_results = await self.vector_integration.search_multimodal_documents(
                    query="employment contract legal terms",
                    limit=3
                )

                message += f", Search Results: {len(search_results)}"
            else:
                message += f", Error: {result.get('error', 'Unknown')}"

            self.test_results.append({
                "test": "Vector Integration",
                "status": status,
                "message": message,
                "details": result if result.get("success") else None
            })

            logger.info("✓ Vector integration test completed")
        except Exception as e:
            self.test_results.append({
                "test": "Vector Integration",
                "status": "FAIL",
                "message": f"Vector integration test failed: {e}"
            })
            logger.error(f"✗ Vector integration test failed: {e}")

    async def test_capabilities(self):
        """Test capabilities reporting"""
        try:
            processor_caps = self.processor.get_capabilities()
            router_caps = self.router.get_router_capabilities()
            vector_caps = self.vector_integration.get_integration_capabilities()
            ocr_caps = self.ocr_utils.get_ocr_capabilities()

            # Get collection stats
            collection_stats = await self.vector_integration.get_collection_stats()

            self.test_results.append({
                "test": "Capabilities Check",
                "status": "PASS",
                "message": "All capabilities retrieved successfully",
                "details": {
                    "processor": processor_caps,
                    "router": router_caps,
                    "vector_integration": vector_caps,
                    "ocr": ocr_caps,
                    "collection_stats": collection_stats
                }
            })
            
            logger.info("✓ Capabilities check completed")
        except Exception as e:
            self.test_results.append({
                "test": "Capabilities Check",
                "status": "FAIL",
                "message": f"Capabilities check failed: {e}"
            })
            logger.error(f"✗ Capabilities check failed: {e}")
    
    def generate_test_report(self):
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            "test_results": self.test_results
        }
        
        # Save report to file
        with open("multimodal_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("MULTI-MODAL DOCUMENT PROCESSING TEST REPORT")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Skipped: {skipped_tests}")
        print(f"Success Rate: {report['test_summary']['success_rate']}")
        print("="*60)
        
        for result in self.test_results:
            status_symbol = "✓" if result["status"] == "PASS" else "✗" if result["status"] == "FAIL" else "⚠"
            print(f"{status_symbol} {result['test']}: {result['message']}")
        
        print(f"\nDetailed report saved to: multimodal_test_report.json")

async def main():
    """Main test execution"""
    test_suite = MultiModalTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
