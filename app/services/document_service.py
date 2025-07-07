import logging
from typing import List, Dict, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import asyncio
from datetime import datetime
import json

from app.models.document import Document
from app.models.legal_case import LegalCase
from app.database import SessionLocal, get_db
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from app.utils.pdf_parser import PDFParser
from app.utils.text_processor import TextProcessor

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        self.vector_service = VectorService()
        self.ai_service = AIService()
        self.pdf_parser = PDFParser()
        self.text_processor = TextProcessor()
        
    async def create_document_from_crawl(self, metadata: Dict[str, Any]) -> Optional[Document]:
        """Create a document from crawled metadata"""
        db = SessionLocal()
        try:
            # Check if document already exists
            existing_doc = db.query(Document).filter(
                Document.url == metadata['url']
            ).first()
            
            if existing_doc:
                logger.info(f"Document already exists: {metadata['url']}")
                return existing_doc
            
            # Create new document
            document = Document(
                title=metadata['title'],
                content=metadata['content'],
                url=metadata['url'],
                source=metadata['source'],
                document_type=metadata.get('document_type', 'unknown'),
                word_count=metadata.get('word_count', 0),
                language=metadata.get('language', 'en'),
                is_processed=False
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Process document asynchronously
            asyncio.create_task(self._process_document_async(document.id))
            
            return document
            
        except Exception as e:
            logger.error(f"Error creating document from crawl: {e}")
            db.rollback()
            return None
        finally:
            db.close()
            
    async def _process_document_async(self, document_id: int):
        """Process document asynchronously"""
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document not found: {document_id}")
                return
                
            # Update status
            document.processing_status = "processing"
            db.commit()
            
            # Generate embeddings
            embeddings = self.ai_service.generate_embeddings(document.content)
            if embeddings:
                document.embedding = embeddings
                document.embedding_model = "all-MiniLM-L6-v2"
                
            # Generate summary
            summary = await self.ai_service.generate_legal_summary(
                document.content[:2000],  # Limit content for summary
                f"kenyan_{document.source}"
            )
            document.summary = summary
            
            # Analyze content
            analysis = await self.ai_service.analyze_document_content(document.content)
            if analysis.get('analysis'):
                # Extract metadata from analysis
                document.tags = self._extract_tags_from_analysis(analysis['analysis'])
                
            # Calculate readability
            document.readability_score = self.text_processor.calculate_readability(document.content)
            
            # Update processing status
            document.is_processed = True
            document.processing_status = "completed"
            
            db.commit()
            
            # Add to vector store
            await self.vector_service.add_document(document)
            
            logger.info(f"Document processed successfully: {document.id}")
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            if document:
                document.processing_status = "failed"
                document.error_message = str(e)
                db.commit()
        finally:
            db.close()
            
    def _extract_tags_from_analysis(self, analysis: str) -> List[str]:
        """Extract tags from AI analysis"""
        try:
            # Simple tag extraction - could be enhanced with NLP
            tags = []
            keywords = ['contract', 'agreement', 'constitution', 'criminal', 'civil', 'property', 'employment']
            
            analysis_lower = analysis.lower()
            for keyword in keywords:
                if keyword in analysis_lower:
                    tags.append(keyword)
                    
            return tags
        except Exception as e:
            logger.error(f"Error extracting tags: {e}")
            return []
            
    async def search_documents(self, query: str, filters: Dict = None, limit: int = 10) -> List[Document]:
        """Search documents with optional filters"""
        db = SessionLocal()
        try:
            # Start with base query
            query_obj = db.query(Document).filter(Document.is_processed == True)
            
            # Apply filters
            if filters:
                if filters.get('source'):
                    query_obj = query_obj.filter(Document.source == filters['source'])
                if filters.get('document_type'):
                    query_obj = query_obj.filter(Document.document_type == filters['document_type'])
                if filters.get('category'):
                    query_obj = query_obj.filter(Document.category == filters['category'])
                    
            # Text search
            if query:
                query_obj = query_obj.filter(
                    func.to_tsvector('english', Document.content).match(query)
                )
                
            # Order by relevance and limit
            documents = query_obj.order_by(desc(Document.created_at)).limit(limit).all()
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
        finally:
            db.close()
            
    async def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """Get document by ID"""
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            return document
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None
        finally:
            db.close()
            
    async def get_documents_by_source(self, source: str, limit: int = 50) -> List[Document]:
        """Get documents by source"""
        db = SessionLocal()
        try:
            documents = db.query(Document).filter(
                Document.source == source
            ).order_by(desc(Document.created_at)).limit(limit).all()
            
            return documents
        except Exception as e:
            logger.error(f"Error getting documents by source: {e}")
            return []
        finally:
            db.close()
            
    async def get_document_statistics(self) -> Dict[str, Any]:
        """Get document statistics"""
        db = SessionLocal()
        try:
            stats = {
                'total_documents': db.query(Document).count(),
                'processed_documents': db.query(Document).filter(Document.is_processed == True).count(),
                'pending_documents': db.query(Document).filter(Document.processing_status == 'pending').count(),
                'failed_documents': db.query(Document).filter(Document.processing_status == 'failed').count(),
                'by_source': {},
                'by_type': {}
            }
            
            # Group by source
            source_stats = db.query(
                Document.source,
                func.count(Document.id).label('count')
            ).group_by(Document.source).all()
            
            stats['by_source'] = {source: count for source, count in source_stats}
            
            # Group by document type
            type_stats = db.query(
                Document.document_type,
                func.count(Document.id).label('count')
            ).group_by(Document.document_type).all()
            
            stats['by_type'] = {doc_type: count for doc_type, count in type_stats}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting document statistics: {e}")
            return {}
        finally:
            db.close()
            
    async def process_uploaded_file(self, file_content: bytes, filename: str, user_id: int) -> Optional[Document]:
        """Process uploaded file"""
        try:
            # Determine file type
            file_extension = filename.lower().split('.')[-1]
            
            # Extract text content
            if file_extension == 'pdf':
                text_content = self.pdf_parser.extract_text_from_bytes(file_content)
            elif file_extension in ['doc', 'docx']:
                text_content = self.pdf_parser.extract_text_from_docx_bytes(file_content)
            else:
                # Assume plain text
                text_content = file_content.decode('utf-8')
                
            if not text_content:
                logger.error(f"No text content extracted from {filename}")
                return None
                
            # Create document
            db = SessionLocal()
            try:
                document = Document(
                    title=filename,
                    content=text_content,
                    source="upload",
                    document_type="uploaded",
                    word_count=len(text_content.split()),
                    language="en",
                    is_processed=False
                )
                
                db.add(document)
                db.commit()
                db.refresh(document)
                
                # Process document asynchronously
                asyncio.create_task(self._process_document_async(document.id))
                
                return document
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}")
            return None
