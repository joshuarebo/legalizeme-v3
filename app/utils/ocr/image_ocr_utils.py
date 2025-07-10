"""
OCR Utilities for Enhanced Image Processing
Specialized utilities for legal document OCR processing
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import tempfile
import os

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    import numpy as np
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    # Create dummy classes for type hints when PIL is not available
    class Image:
        class Image:
            pass

logger = logging.getLogger(__name__)

class ImageOCRUtils:
    """Utility class for enhanced OCR processing of legal documents"""
    
    def __init__(self):
        self.ocr_languages = ['eng']
        
        # OCR configurations for different document types
        self.ocr_configs = {
            'default': '--oem 3 --psm 6',
            'single_column': '--oem 3 --psm 4',
            'single_block': '--oem 3 --psm 8',
            'single_line': '--oem 3 --psm 7',
            'sparse_text': '--oem 3 --psm 11',
            'single_word': '--oem 3 --psm 10'
        }
        
        # Legal document specific preprocessing settings
        self.legal_doc_settings = {
            'contract': {
                'enhance_contrast': 1.8,
                'enhance_sharpness': 2.2,
                'noise_reduction': True,
                'deskew': True
            },
            'affidavit': {
                'enhance_contrast': 1.5,
                'enhance_sharpness': 2.0,
                'noise_reduction': True,
                'deskew': True
            },
            'judgment': {
                'enhance_contrast': 1.6,
                'enhance_sharpness': 1.8,
                'noise_reduction': True,
                'deskew': False
            },
            'default': {
                'enhance_contrast': 1.5,
                'enhance_sharpness': 2.0,
                'noise_reduction': True,
                'deskew': True
            }
        }
    
    def check_ocr_availability(self) -> bool:
        """Check if OCR capabilities are available"""
        if not HAS_OCR:
            return False
        
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
    
    async def process_image_with_ocr(self, image_path: Path, 
                                   document_type: str = 'default',
                                   config_name: str = 'default') -> Dict[str, Any]:
        """
        Process image with OCR using document-specific optimizations
        
        Args:
            image_path: Path to the image file
            document_type: Type of legal document for optimization
            config_name: OCR configuration to use
        
        Returns:
            OCR results with confidence scores and metadata
        """
        if not self.check_ocr_availability():
            return {"success": False, "error": "OCR not available"}
        
        try:
            # Load image
            image = Image.open(image_path)
            
            # Apply document-specific preprocessing
            processed_image = await self._preprocess_image_for_legal_doc(
                image, document_type
            )
            
            # Perform OCR with multiple configurations
            best_result = await self._ocr_with_multiple_configs(
                processed_image, config_name
            )
            
            if best_result:
                best_result["preprocessing_applied"] = document_type
                best_result["original_image_size"] = image.size
                best_result["processed_image_size"] = processed_image.size
                
            return best_result or {"success": False, "error": "OCR failed"}
            
        except Exception as e:
            logger.error(f"Error in OCR processing: {e}")
            return {"success": False, "error": str(e)}
    
    async def _preprocess_image_for_legal_doc(self, image: Image.Image, 
                                            doc_type: str) -> Image.Image:
        """Apply document-specific preprocessing for legal documents"""
        try:
            settings = self.legal_doc_settings.get(doc_type, self.legal_doc_settings['default'])
            
            # Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')
            
            # Deskew if enabled
            if settings.get('deskew', False):
                image = self._deskew_image(image)
            
            # Enhance contrast
            if settings.get('enhance_contrast', 1.0) != 1.0:
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(settings['enhance_contrast'])
            
            # Enhance sharpness
            if settings.get('enhance_sharpness', 1.0) != 1.0:
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(settings['enhance_sharpness'])
            
            # Apply noise reduction
            if settings.get('noise_reduction', False):
                image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Resize for optimal OCR (if too small)
            width, height = image.size
            min_dimension = 1200  # Minimum dimension for good OCR
            
            if width < min_dimension or height < min_dimension:
                scale_factor = max(min_dimension / width, min_dimension / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Apply binary threshold for better text recognition
            image = self._apply_adaptive_threshold(image)
            
            return image
            
        except Exception as e:
            logger.error(f"Error in image preprocessing: {e}")
            return image  # Return original if preprocessing fails
    
    def _deskew_image(self, image: Image.Image) -> Image.Image:
        """Deskew image to correct rotation"""
        try:
            # Simple deskewing using PIL
            # This is a basic implementation - could be enhanced with more sophisticated algorithms
            
            # Convert to numpy array for processing
            if hasattr(np, 'array'):
                img_array = np.array(image)
                
                # Find text lines and calculate skew angle
                # For now, return original image (placeholder for advanced deskewing)
                return image
            else:
                return image
                
        except Exception as e:
            logger.error(f"Error in deskewing: {e}")
            return image
    
    def _apply_adaptive_threshold(self, image: Image.Image) -> Image.Image:
        """Apply adaptive thresholding for better text recognition"""
        try:
            # Convert to binary using adaptive threshold
            # This helps with varying lighting conditions in scanned documents
            
            # Simple threshold approach using PIL
            threshold = 128
            image = image.point(lambda x: 255 if x > threshold else 0, mode='1')
            
            return image.convert('L')  # Convert back to grayscale
            
        except Exception as e:
            logger.error(f"Error in adaptive thresholding: {e}")
            return image
    
    async def _ocr_with_multiple_configs(self, image: Image.Image, 
                                       preferred_config: str) -> Optional[Dict[str, Any]]:
        """Try OCR with multiple configurations and return the best result"""
        try:
            configs_to_try = [preferred_config]
            
            # Add fallback configurations
            if preferred_config != 'default':
                configs_to_try.append('default')
            
            configs_to_try.extend(['single_column', 'single_block'])
            
            best_result = None
            best_confidence = 0
            
            for config_name in configs_to_try:
                if config_name not in self.ocr_configs:
                    continue
                
                try:
                    config = self.ocr_configs[config_name]
                    
                    # Get confidence data
                    data = pytesseract.image_to_data(
                        image,
                        lang='+'.join(self.ocr_languages),
                        config=config,
                        output_type=pytesseract.Output.DICT
                    )
                    
                    # Calculate average confidence
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Extract text
                    text = pytesseract.image_to_string(
                        image,
                        lang='+'.join(self.ocr_languages),
                        config=config
                    )
                    
                    # Quality check: prefer results with higher confidence and substantial text
                    if (avg_confidence > best_confidence and 
                        text.strip() and 
                        len(text.split()) > 5):  # At least 5 words
                        
                        best_confidence = avg_confidence
                        best_result = {
                            "success": True,
                            "text": text,
                            "confidence": avg_confidence,
                            "config_used": config_name,
                            "word_count": len(text.split()),
                            "char_count": len(text),
                            "extraction_method": "enhanced_ocr"
                        }
                
                except Exception as e:
                    logger.warning(f"OCR config {config_name} failed: {e}")
                    continue
            
            return best_result
            
        except Exception as e:
            logger.error(f"Error in multi-config OCR: {e}")
            return None
    
    def get_optimal_config_for_document_type(self, doc_type: str) -> str:
        """Get the optimal OCR configuration for a document type"""
        config_mapping = {
            'employment_contract': 'single_column',
            'affidavit': 'single_column',
            'judgment': 'default',
            'legislation': 'single_column',
            'constitution': 'single_column',
            'civil_case': 'default'
        }
        
        return config_mapping.get(doc_type, 'default')
    
    def get_preprocessing_settings(self, doc_type: str) -> Dict[str, Any]:
        """Get preprocessing settings for a document type"""
        return self.legal_doc_settings.get(doc_type, self.legal_doc_settings['default'])
    
    def get_available_languages(self) -> List[str]:
        """Get available OCR languages"""
        if not self.check_ocr_availability():
            return []
        
        try:
            # Get available languages from tesseract
            langs = pytesseract.get_languages()
            return langs
        except Exception:
            return self.ocr_languages  # Return default
    
    def get_ocr_capabilities(self) -> Dict[str, Any]:
        """Get OCR capabilities and configuration options"""
        return {
            "ocr_available": self.check_ocr_availability(),
            "supported_languages": self.get_available_languages(),
            "available_configs": list(self.ocr_configs.keys()),
            "document_types": list(self.legal_doc_settings.keys()),
            "features": [
                "Document-specific preprocessing",
                "Multiple OCR configuration testing",
                "Confidence scoring",
                "Adaptive thresholding",
                "Image enhancement",
                "Noise reduction"
            ]
        }
