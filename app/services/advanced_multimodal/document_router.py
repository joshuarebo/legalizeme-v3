"""
Document Router for Multi-Modal Legal Document Processing
Handles intelligent routing of documents to appropriate processors
"""

import logging
import asyncio
import re
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import mimetypes
from datetime import datetime

from .document_processor import MultiModalDocumentProcessor

logger = logging.getLogger(__name__)

class DocumentRouter:
    """Intelligent document router for multi-modal processing"""
    
    def __init__(self):
        self.processor = MultiModalDocumentProcessor()
        
        # File type mappings
        self.mime_type_mappings = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',
            'text/plain': 'text',
            'image/png': 'image',
            'image/jpeg': 'image',
            'image/jpg': 'image',
            'image/tiff': 'image',
            'image/bmp': 'image'
        }
        
        # Processing strategies based on document type
        self.processing_strategies = {
            'pdf': self._process_pdf_document,
            'docx': self._process_docx_document,
            'doc': self._process_doc_document,
            'text': self._process_text_document,
            'image': self._process_image_document
        }
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize the document router"""
        if self._initialized:
            return
        
        try:
            await self.processor.initialize()
            self._initialized = True
            logger.info("Document Router initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Document Router: {e}")
            raise
    
    async def process_document(self, file_path: Union[str, Path], 
                             processing_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entry point for document processing
        
        Args:
            file_path: Path to the document file
            processing_options: Optional processing configuration
        
        Returns:
            Comprehensive processing results
        """
        if not self._initialized:
            await self.initialize()
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "error": "File not found"}
        
        try:
            # Detect file type
            file_type = await self._detect_file_type(file_path)
            
            if file_type not in self.processing_strategies:
                return {"success": False, "error": f"Unsupported file type: {file_type}"}
            
            # Route to appropriate processor
            processing_strategy = self.processing_strategies[file_type]
            result = await processing_strategy(file_path, processing_options or {})
            
            # Add routing metadata
            result["routing_info"] = {
                "file_type": file_type,
                "file_size": file_path.stat().st_size,
                "processing_timestamp": datetime.now().isoformat(),
                "processor_used": "MultiModalDocumentProcessor"
            }
            
            # Perform post-processing analysis
            if result.get("success") and result.get("text"):
                post_analysis = await self._perform_post_processing_analysis(
                    result["text"], file_type, processing_options
                )
                result.update(post_analysis)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            return {"success": False, "error": str(e)}
    
    async def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type using multiple methods"""
        try:
            # First, try MIME type detection
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type in self.mime_type_mappings:
                return self.mime_type_mappings[mime_type]
            
            # Fallback to file extension
            extension = file_path.suffix.lower()
            extension_mappings = {
                '.pdf': 'pdf',
                '.docx': 'docx',
                '.doc': 'doc',
                '.txt': 'text',
                '.png': 'image',
                '.jpg': 'image',
                '.jpeg': 'image',
                '.tiff': 'image',
                '.bmp': 'image'
            }
            
            if extension in extension_mappings:
                return extension_mappings[extension]
            
            # Final fallback - try to read file header
            with open(file_path, 'rb') as f:
                header = f.read(8)
                
            # PDF signature
            if header.startswith(b'%PDF'):
                return 'pdf'
            
            # PNG signature
            if header.startswith(b'\x89PNG'):
                return 'image'
            
            # JPEG signature
            if header.startswith(b'\xff\xd8\xff'):
                return 'image'
            
            # Default to text if nothing else matches
            return 'text'
            
        except Exception as e:
            logger.error(f"Error detecting file type: {e}")
            return 'unknown'
    
    async def _process_pdf_document(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF documents with enhanced extraction"""
        try:
            # Extract text using enhanced PDF processor
            result = await self.processor.extract_text_from_pdf(file_path)
            
            if not result.get("success"):
                return result
            
            # Detect document type
            doc_type = await self.processor.detect_document_type(result["text"])
            result["document_type"] = doc_type
            
            # Generate summary if requested
            if options.get("generate_summary", True):
                summary_model = options.get("summary_model", "claude-sonnet-4")
                summary_result = await self.processor.summarize_text(
                    result["text"], 
                    model=summary_model
                )
                
                if summary_result.get("success"):
                    result["summary_data"] = summary_result
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF document: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_image_document(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process image documents with OCR"""
        try:
            # Perform OCR
            result = await self.processor.ocr_image_to_text(file_path)
            
            if not result.get("success"):
                return result
            
            # Detect document type
            doc_type = await self.processor.detect_document_type(result["text"])
            result["document_type"] = doc_type
            
            # Generate summary if requested and text is substantial
            if options.get("generate_summary", True) and len(result["text"].split()) > 50:
                summary_model = options.get("summary_model", "claude-sonnet-4")
                summary_result = await self.processor.summarize_text(
                    result["text"], 
                    model=summary_model
                )
                
                if summary_result.get("success"):
                    result["summary_data"] = summary_result
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image document: {e}")
            return {"success": False, "error": str(e)}
    
    async def _process_docx_document(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process DOCX documents (placeholder for future implementation)"""
        # For now, return a placeholder response
        return {
            "success": False, 
            "error": "DOCX processing not yet implemented in multi-modal router"
        }
    
    async def _process_doc_document(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process DOC documents (placeholder for future implementation)"""
        return {
            "success": False, 
            "error": "DOC processing not yet implemented in multi-modal router"
        }
    
    async def _process_text_document(self, file_path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
        """Process plain text documents"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Detect document type
            doc_type = await self.processor.detect_document_type(text)
            
            result = {
                "success": True,
                "text": text,
                "document_type": doc_type,
                "word_count": len(text.split()),
                "char_count": len(text),
                "extraction_method": "direct_text_read"
            }
            
            # Generate summary if requested
            if options.get("generate_summary", True):
                summary_model = options.get("summary_model", "claude-sonnet-4")
                summary_result = await self.processor.summarize_text(
                    text, 
                    model=summary_model
                )
                
                if summary_result.get("success"):
                    result["summary_data"] = summary_result
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing text document: {e}")
            return {"success": False, "error": str(e)}
    
    async def _perform_post_processing_analysis(self, text: str, file_type: str, 
                                              options: Dict[str, Any]) -> Dict[str, Any]:
        """Perform additional analysis after document processing"""
        analysis = {}
        
        try:
            # Text quality assessment
            analysis["text_quality"] = {
                "word_count": len(text.split()),
                "char_count": len(text),
                "avg_word_length": sum(len(word) for word in text.split()) / len(text.split()) if text.split() else 0,
                "has_special_chars": bool(re.search(r'[^\w\s]', text)),
                "estimated_reading_time": len(text.split()) / 200  # Assuming 200 WPM
            }
            
            # Legal document indicators
            legal_indicators = [
                'whereas', 'therefore', 'hereby', 'pursuant', 'notwithstanding',
                'plaintiff', 'defendant', 'court', 'judge', 'magistrate',
                'section', 'article', 'clause', 'provision', 'act'
            ]
            
            legal_score = sum(1 for indicator in legal_indicators if indicator in text.lower())
            analysis["legal_document_score"] = min(legal_score / len(legal_indicators), 1.0)
            
            # Processing recommendations
            recommendations = []
            
            if analysis["text_quality"]["word_count"] < 100:
                recommendations.append("Document appears to be very short - consider manual review")
            
            if analysis["legal_document_score"] > 0.3:
                recommendations.append("High legal content detected - consider legal expert review")
            
            if file_type == "image" and "confidence" in analysis:
                if analysis["confidence"] < 70:
                    recommendations.append("Low OCR confidence - consider manual verification")
            
            analysis["processing_recommendations"] = recommendations
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in post-processing analysis: {e}")
            return {"analysis_error": str(e)}
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats"""
        return list(self.processing_strategies.keys())
    
    def get_router_capabilities(self) -> Dict[str, Any]:
        """Get router capabilities"""
        return {
            "supported_formats": self.get_supported_formats(),
            "processor_capabilities": self.processor.get_capabilities(),
            "features": [
                "Intelligent file type detection",
                "Multi-modal document processing",
                "Document type classification",
                "Automated summarization",
                "Entity extraction",
                "Quality assessment",
                "Processing recommendations"
            ]
        }
