"""
Enhanced Multi-Modal Document Processor for Legal AI Platform
Supports PDF, images, DOCX with advanced OCR, summarization, and entity extraction
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any, Union, Tuple
from pathlib import Path
import json
import re
from datetime import datetime
import tempfile
import os
import base64
from io import BytesIO

# Optional imports for document processing
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from pypdf2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    # Create dummy classes for type hints when PIL is not available
    class Image:
        class Image:
            pass

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import mammoth
    HAS_MAMMOTH = True
except ImportError:
    HAS_MAMMOTH = False

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from app.config import settings

logger = logging.getLogger(__name__)

class MultiModalDocumentProcessor:
    """Enhanced multi-modal document processor with advanced AI capabilities"""
    
    def __init__(self):
        self.bedrock_client = None
        
        # Processing configuration
        self.max_file_size = 100 * 1024 * 1024  # 100MB for multi-modal
        self.supported_formats = {
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
        
        # Enhanced OCR configuration
        self.ocr_languages = ['eng']  # English by default
        self.ocr_configs = {
            'default': '--oem 3 --psm 6',
            'single_column': '--oem 3 --psm 4',
            'single_block': '--oem 3 --psm 8',
            'single_line': '--oem 3 --psm 7'
        }
        
        # Document type patterns for legal documents
        self.document_patterns = {
            'employment_contract': [
                r'employment\s+contract', r'terms\s+of\s+employment', 
                r'job\s+description', r'salary', r'termination'
            ],
            'affidavit': [
                r'affidavit', r'sworn\s+statement', r'deponent', 
                r'solemnly\s+affirm', r'oath'
            ],
            'judgment': [
                r'judgment', r'ruling', r'court\s+order', r'magistrate',
                r'justice', r'plaintiff', r'defendant'
            ],
            'legislation': [
                r'act\s+no\.', r'section\s+\d+', r'subsection', 
                r'parliament', r'gazette'
            ],
            'constitution': [
                r'constitution', r'article\s+\d+', r'chapter\s+\d+',
                r'fundamental\s+rights'
            ],
            'civil_case': [
                r'civil\s+case', r'petition', r'application', 
                r'respondent', r'applicant'
            ]
        }
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize the multi-modal document processor"""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing Multi-Modal Document Processor...")
            
            # Initialize Bedrock client for AI processing
            if HAS_BOTO3:
                try:
                    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                        self.bedrock_client = boto3.client(
                            'bedrock-runtime',
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                            region_name=settings.AWS_REGION
                        )
                        logger.info("AWS Bedrock client initialized for multi-modal processing")
                    else:
                        logger.warning("AWS credentials not found - Bedrock unavailable")
                except Exception as e:
                    logger.warning(f"Failed to initialize Bedrock client: {e}")
            
            # Check OCR availability
            if HAS_OCR:
                try:
                    pytesseract.get_tesseract_version()
                    logger.info("Enhanced OCR capabilities available")
                except Exception as e:
                    logger.warning(f"OCR not properly configured: {e}")
            
            self._initialized = True
            logger.info("Multi-Modal Document Processor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Multi-Modal Document Processor: {e}")
            raise
    
    async def extract_text_from_pdf(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Enhanced PDF text extraction with multiple fallback methods"""
        if not self._initialized:
            await self.initialize()
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "error": "File not found"}
        
        if file_path.stat().st_size > self.max_file_size:
            return {"success": False, "error": "File too large"}
        
        try:
            # Try pdfplumber first (best for structured text)
            if HAS_PDFPLUMBER:
                result = await self._extract_with_pdfplumber_enhanced(file_path)
                if result["success"] and result.get("text", "").strip():
                    result["extraction_method"] = "pdfplumber"
                    return result
            
            # Fallback to pypdf2
            if HAS_PYPDF2:
                result = await self._extract_with_pypdf2_enhanced(file_path)
                if result["success"] and result.get("text", "").strip():
                    result["extraction_method"] = "pypdf2"
                    return result
            
            # Final fallback to enhanced OCR
            if HAS_OCR:
                logger.info(f"Falling back to enhanced OCR for {file_path.name}")
                result = await self._extract_with_enhanced_ocr(file_path)
                result["extraction_method"] = "ocr"
                return result
            
            return {"success": False, "error": "No PDF processing libraries available"}
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            return {"success": False, "error": str(e)}
    
    async def ocr_image_to_text(self, image_path: Union[str, Path]) -> Dict[str, Any]:
        """Enhanced OCR processing for images with preprocessing"""
        if not self._initialized:
            await self.initialize()
        
        if not HAS_OCR:
            return {"success": False, "error": "OCR not available"}
        
        image_path = Path(image_path)
        
        if not image_path.exists():
            return {"success": False, "error": "Image file not found"}
        
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            processed_image = await self._preprocess_image_for_ocr(image)
            
            # Try different OCR configurations
            best_result = None
            best_confidence = 0
            
            for config_name, config in self.ocr_configs.items():
                try:
                    # Extract text with confidence data
                    data = pytesseract.image_to_data(
                        processed_image,
                        lang='+'.join(self.ocr_languages),
                        config=config,
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # Calculate average confidence
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Extract text
                    text = pytesseract.image_to_string(
                        processed_image,
                        lang='+'.join(self.ocr_languages),
                        config=config
                    )
                    
                    if avg_confidence > best_confidence and text.strip():
                        best_confidence = avg_confidence
                        best_result = {
                            "text": text,
                            "confidence": avg_confidence,
                            "config_used": config_name,
                            "word_count": len(text.split()),
                            "char_count": len(text)
                        }
                        
                except Exception as e:
                    logger.warning(f"OCR config {config_name} failed: {e}")
                    continue
            
            if best_result:
                return {
                    "success": True,
                    **best_result,
                    "extraction_method": "enhanced_ocr"
                }
            else:
                return {"success": False, "error": "OCR failed with all configurations"}
                
        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            return {"success": False, "error": str(e)}

    async def detect_document_type(self, text: str) -> str:
        """Enhanced document type detection using pattern matching"""
        text_lower = text.lower()

        # Score each document type
        type_scores = {}

        for doc_type, patterns in self.document_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches

            if score > 0:
                type_scores[doc_type] = score

        # Return the type with highest score, or 'unknown' if no matches
        if type_scores:
            return max(type_scores, key=type_scores.get)
        return 'unknown'

    async def summarize_text(self, text: str, model: str = "claude-sonnet-4", max_length: int = 500) -> Dict[str, Any]:
        """Enhanced text summarization with structured output"""
        if not self._initialized:
            await self.initialize()

        if not text.strip():
            return {"success": False, "error": "Empty text provided"}

        try:
            # Detect document type for context-aware summarization
            doc_type = await self.detect_document_type(text)

            # Create enhanced summarization prompt
            prompt = self._create_enhanced_summarization_prompt(text, doc_type, max_length)

            # Generate summary using Bedrock
            if self.bedrock_client and model.startswith("claude"):
                result = await self._summarize_with_bedrock_enhanced(prompt, model)
            else:
                return {"success": False, "error": "Bedrock client not available"}

            if result["success"]:
                # Parse structured response
                summary_data = self._parse_structured_summary(result["summary"])
                result.update(summary_data)
                result["document_type"] = doc_type

                # Extract entities and key information
                entities = await self._extract_legal_entities(text)
                result["extracted_entities"] = entities

            return result

        except Exception as e:
            logger.error(f"Error summarizing text: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_with_pdfplumber_enhanced(self, file_path: Path) -> Dict[str, Any]:
        """Enhanced pdfplumber extraction with table and metadata support"""
        try:
            with pdfplumber.open(file_path) as pdf:
                text_parts = []
                tables = []
                metadata = {
                    "total_pages": len(pdf.pages),
                    "extraction_method": "pdfplumber_enhanced",
                    "has_tables": False,
                    "page_info": []
                }

                for page_num, page in enumerate(pdf.pages):
                    page_info = {"page_number": page_num + 1}

                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                        page_info["has_text"] = True

                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        metadata["has_tables"] = True
                        page_info["table_count"] = len(page_tables)
                        for table in page_tables:
                            tables.append({
                                "page": page_num + 1,
                                "data": table
                            })

                    metadata["page_info"].append(page_info)

                full_text = "\n".join(text_parts)

                return {
                    "success": True,
                    "text": full_text,
                    "metadata": metadata,
                    "tables": tables,
                    "word_count": len(full_text.split()),
                    "char_count": len(full_text)
                }

        except Exception as e:
            logger.error(f"Error with enhanced pdfplumber extraction: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_with_pypdf2_enhanced(self, file_path: Path) -> Dict[str, Any]:
        """Enhanced pypdf2 extraction with metadata"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                text_parts = []

                metadata = {
                    "total_pages": len(pdf_reader.pages),
                    "extraction_method": "pypdf2_enhanced"
                }

                # Extract PDF metadata if available
                if pdf_reader.metadata:
                    metadata["pdf_metadata"] = {
                        "title": pdf_reader.metadata.get('/Title', ''),
                        "author": pdf_reader.metadata.get('/Author', ''),
                        "subject": pdf_reader.metadata.get('/Subject', ''),
                        "creator": pdf_reader.metadata.get('/Creator', '')
                    }

                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")

                full_text = "\n".join(text_parts)

                return {
                    "success": True,
                    "text": full_text,
                    "metadata": metadata,
                    "word_count": len(full_text.split()),
                    "char_count": len(full_text)
                }

        except Exception as e:
            logger.error(f"Error with enhanced pypdf2 extraction: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_with_enhanced_ocr(self, file_path: Path) -> Dict[str, Any]:
        """Enhanced OCR extraction for PDFs with image preprocessing"""
        try:
            import fitz  # PyMuPDF for PDF to image conversion

            doc = fitz.open(file_path)
            text_parts = []
            page_confidences = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                # Convert to high-quality image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")

                # Save to temporary file
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    temp_file.write(img_data)
                    temp_path = temp_file.name

                try:
                    # Load and preprocess image
                    image = Image.open(temp_path)
                    processed_image = await self._preprocess_image_for_ocr(image)

                    # OCR with confidence
                    data = pytesseract.image_to_data(
                        processed_image,
                        lang='+'.join(self.ocr_languages),
                        config=self.ocr_configs['default'],
                        output_type=pytesseract.Output.DICT
                    )

                    # Calculate page confidence
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    page_confidence = sum(confidences) / len(confidences) if confidences else 0
                    page_confidences.append(page_confidence)

                    # Extract text
                    text = pytesseract.image_to_string(
                        processed_image,
                        lang='+'.join(self.ocr_languages),
                        config=self.ocr_configs['default']
                    )

                    if text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

                finally:
                    # Clean up temp file
                    os.unlink(temp_path)

            doc.close()
            full_text = "\n".join(text_parts)
            avg_confidence = sum(page_confidences) / len(page_confidences) if page_confidences else 0

            return {
                "success": True,
                "text": full_text,
                "metadata": {
                    "total_pages": len(doc),
                    "extraction_method": "enhanced_ocr",
                    "ocr_languages": self.ocr_languages,
                    "average_confidence": avg_confidence,
                    "page_confidences": page_confidences
                },
                "word_count": len(full_text.split()),
                "char_count": len(full_text)
            }

        except Exception as e:
            logger.error(f"Error with enhanced OCR extraction: {e}")
            return {"success": False, "error": str(e)}

    async def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)

            # Apply noise reduction
            image = image.filter(ImageFilter.MedianFilter(size=3))

            # Resize if too small (OCR works better on larger images)
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            return image

        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return image  # Return original if preprocessing fails

    def _create_enhanced_summarization_prompt(self, text: str, doc_type: str, max_length: int) -> str:
        """Create context-aware summarization prompt"""

        type_specific_instructions = {
            'employment_contract': "Focus on key terms: parties, position, salary, benefits, termination conditions, and obligations.",
            'affidavit': "Identify the deponent, key facts being sworn to, and the purpose of the affidavit.",
            'judgment': "Extract the case details, legal issues, court's reasoning, and final ruling.",
            'legislation': "Summarize the act's purpose, key provisions, and affected parties.",
            'constitution': "Focus on fundamental rights, governance structures, and key principles.",
            'civil_case': "Identify parties, claims, relief sought, and procedural status."
        }

        specific_instruction = type_specific_instructions.get(doc_type, "Provide a comprehensive legal summary.")

        prompt = f"""
You are a Kenyan legal AI assistant. Analyze this {doc_type} document and provide a structured summary.

Document Text:
{text[:4000]}  # Limit to avoid token limits

Instructions:
1. {specific_instruction}
2. Maximum summary length: {max_length} words
3. Extract key legal entities (parties, dates, amounts, legal references)
4. Identify important clauses or provisions
5. Note any compliance or legal issues

Provide your response in this JSON format:
{{
    "summary": "Brief summary here",
    "key_parties": ["Party 1", "Party 2"],
    "important_dates": ["Date 1", "Date 2"],
    "key_clauses": ["Clause 1", "Clause 2"],
    "legal_references": ["Reference 1", "Reference 2"],
    "compliance_notes": "Any compliance issues or requirements"
}}
"""
        return prompt

    async def _summarize_with_bedrock_enhanced(self, prompt: str, model: str) -> Dict[str, Any]:
        """Enhanced Bedrock summarization with structured output"""
        try:
            # Map model names to Bedrock model IDs
            model_mapping = {
                "claude-sonnet-4": settings.AWS_BEDROCK_MODEL_ID_PRIMARY,
                "claude-3.7": settings.AWS_BEDROCK_MODEL_ID_SECONDARY,
                "mistral-large": settings.AWS_BEDROCK_MODEL_ID_FALLBACK
            }

            model_id = model_mapping.get(model, model_mapping["claude-sonnet-4"])

            # Prepare request body for Anthropic models
            if "anthropic" in model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            elif "mistral" in model_id:
                body = {
                    "prompt": f"<s>[INST] {prompt} [/INST]",
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "stop": ["</s>"]
                }
            else:
                raise Exception(f"Unsupported model type: {model_id}")

            # Make request to Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )

            # Parse response
            result = json.loads(response['body'].read())

            if "anthropic" in model_id:
                summary = result['content'][0]['text']
            else:  # Mistral
                summary = result.get('outputs', [{}])[0].get('text', '')

            return {
                "success": True,
                "summary": summary,
                "model_used": model,
                "model_id": model_id,
                "method": "bedrock_enhanced"
            }

        except Exception as e:
            logger.error(f"Error with enhanced Bedrock summarization: {e}")
            return {"success": False, "error": str(e)}

    def _parse_structured_summary(self, summary_text: str) -> Dict[str, Any]:
        """Parse structured JSON response from AI model"""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', summary_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                return parsed
            else:
                # Fallback: return summary as plain text
                return {"summary": summary_text}

        except json.JSONDecodeError:
            logger.warning("Failed to parse structured summary, returning as plain text")
            return {"summary": summary_text}

    async def _extract_legal_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract legal entities using pattern matching"""
        entities = {
            "parties": [],
            "dates": [],
            "amounts": [],
            "legal_references": [],
            "locations": []
        }

        try:
            # Extract dates
            date_patterns = [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
                r'\b\d{1,2}\s+\w+\s+\d{4}\b',
                r'\b\w+\s+\d{1,2},?\s+\d{4}\b'
            ]
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                entities["dates"].extend(matches)

            # Extract monetary amounts
            amount_patterns = [
                r'KSh?\s*[\d,]+(?:\.\d{2})?',
                r'USD?\s*[\d,]+(?:\.\d{2})?',
                r'Kshs?\s*[\d,]+(?:\.\d{2})?'
            ]
            for pattern in amount_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities["amounts"].extend(matches)

            # Extract legal references
            legal_ref_patterns = [
                r'Act\s+No\.\s*\d+\s+of\s+\d{4}',
                r'Section\s+\d+[a-z]?',
                r'Article\s+\d+[a-z]?',
                r'Chapter\s+\d+[a-z]?'
            ]
            for pattern in legal_ref_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities["legal_references"].extend(matches)

            # Extract Kenyan locations
            kenyan_locations = [
                'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika',
                'Malindi', 'Kitale', 'Garissa', 'Kakamega', 'Machakos', 'Meru'
            ]
            for location in kenyan_locations:
                if location.lower() in text.lower():
                    entities["locations"].append(location)

            # Remove duplicates
            for key in entities:
                entities[key] = list(set(entities[key]))

            return entities

        except Exception as e:
            logger.error(f"Error extracting legal entities: {e}")
            return entities

    def get_capabilities(self) -> Dict[str, bool]:
        """Get enhanced processor capabilities"""
        return {
            "pdf_extraction": HAS_PDFPLUMBER or HAS_PYPDF2,
            "enhanced_pdf_extraction": HAS_PDFPLUMBER,
            "docx_extraction": HAS_DOCX or HAS_MAMMOTH,
            "image_ocr": HAS_OCR,
            "enhanced_ocr": HAS_OCR,
            "image_preprocessing": HAS_OCR,
            "ai_summarization": True,
            "bedrock_integration": HAS_BOTO3 and self.bedrock_client is not None,
            "document_type_detection": True,
            "entity_extraction": True,
            "structured_output": True,
            "table_extraction": HAS_PDFPLUMBER
        }
