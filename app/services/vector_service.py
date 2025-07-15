import logging
from typing import List, Dict, Optional, Any
import asyncio
from sqlalchemy.orm import Session
import json

# Optional imports - these are heavy dependencies that may not be available
# Use AWS-native vector service instead of ChromaDB
from app.services.aws_vector_service import aws_vector_service
HAS_CHROMADB = True  # Always available with AWS fallback

from app.config import settings
from app.models.document import Document
from app.database import SessionLocal

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.client = None
        self.collection_name = "legal_documents"
        self._initialized = False
        
    async def initialize(self):
        """Initialize AWS Vector Service"""
        if self._initialized:
            return

        try:
            # Use AWS Vector Service instead of ChromaDB
            await aws_vector_service.initialize()
            self.client = aws_vector_service
            logger.info("Vector service initialized with AWS backend")
            self._initialized = True

        except Exception as e:
            logger.error(f"Error initializing vector service: {e}")
            # Continue without vector service for development
            self._initialized = True
            
    async def add_document(self, document: Document) -> bool:
        """Add document to vector store"""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Prepare document for vector store
            doc_id = f"doc_{document.id}"
            
            # Create metadata
            metadata = {
                "title": document.title,
                "source": document.source,
                "document_type": document.document_type,
                "url": document.url or "",
                "word_count": document.word_count or 0,
                "created_at": document.created_at.isoformat() if document.created_at else "",
                "category": document.category or "",
                "tags": json.dumps(document.tags) if document.tags else "[]"
            }
            
            # Add to AWS vector service
            if self.client:
                await self.client.add_document(
                    doc_id=doc_id,
                    content=document.content,
                    metadata=metadata
                )
            
            # Update document status
            db = SessionLocal()
            try:
                db_doc = db.query(Document).filter(Document.id == document.id).first()
                if db_doc:
                    db_doc.is_indexed = True
                    db_doc.last_indexed = document.created_at
                    db.commit()
            finally:
                db.close()
                
            logger.info(f"Document added to vector store: {document.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document to vector store: {e}")
            return False
            
    async def search_similar_documents(self, query: str, limit: int = 5, filters: Dict = None) -> List[Document]:
        """Search for similar documents using vector similarity"""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Build where clause for filtering
            where_clause = {}
            if filters:
                if filters.get('source'):
                    where_clause['source'] = filters['source']
                if filters.get('document_type'):
                    where_clause['document_type'] = filters['document_type']
                    
            # Search using AWS vector service
            documents = []
            if self.client:
                results = await self.client.search_similar(
                    query=query,
                    limit=limit,
                    filters=filters
                )

                # Convert results to Document objects
                if results:
                    db = SessionLocal()
                    try:
                        for result in results:
                            doc_id = result.get('id', '').replace('doc_', '')
                            if doc_id.isdigit():
                                db_id = int(doc_id)
                                document = db.query(Document).filter(Document.id == db_id).first()
                                if document:
                                    document.relevance_score = result.get('score', 0.0)
                                    documents.append(document)
                    finally:
                        db.close()
                    
            return documents
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []
            
    async def get_document_by_vector_id(self, vector_id: str) -> Optional[Document]:
        """Get document by vector store ID"""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Extract database ID
            db_id = int(vector_id.replace('doc_', ''))
            
            # Get document from database
            db = SessionLocal()
            try:
                document = db.query(Document).filter(Document.id == db_id).first()
                return document
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting document by vector ID: {e}")
            return None
            
    async def update_document(self, document: Document) -> bool:
        """Update document in vector store"""
        try:
            if not self._initialized:
                await self.initialize()
                
            doc_id = f"doc_{document.id}"
            
            # Update metadata
            metadata = {
                "title": document.title,
                "source": document.source,
                "document_type": document.document_type,
                "url": document.url or "",
                "word_count": document.word_count or 0,
                "created_at": document.created_at.isoformat() if document.created_at else "",
                "category": document.category or "",
                "tags": json.dumps(document.tags) if document.tags else "[]"
            }
            
            # Update in AWS vector service
            if self.client:
                await self.client.update_document(
                    doc_id=doc_id,
                    content=document.content,
                    metadata=metadata
                )
            
            logger.info(f"Document updated in vector store: {document.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document in vector store: {e}")
            return False
            
    async def delete_document(self, document_id: int) -> bool:
        """Delete document from vector store"""
        try:
            if not self._initialized:
                await self.initialize()
                
            doc_id = f"doc_{document_id}"
            
            # Delete from AWS vector service
            if self.client:
                await self.client.delete_document(doc_id)
            
            logger.info(f"Document deleted from vector store: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document from vector store: {e}")
            return False
            
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            if not self._initialized:
                await self.initialize()
                
            # Get stats from AWS vector service
            if self.client:
                stats = await self.client.get_stats()
                return {
                    "total_documents": stats.get('count', 0),
                    "collection_name": self.collection_name,
                    "status": "active"
                }
            else:
                return {
                    "total_documents": 0,
                    "collection_name": self.collection_name,
                    "status": "inactive"
                }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
            
    async def rebuild_index(self) -> bool:
        """Rebuild vector index from database"""
        try:
            logger.info("Starting vector index rebuild...")
            
            if not self._initialized:
                await self.initialize()
                
            # Clear existing data in AWS vector service
            if self.client:
                await self.client.clear_all()
            
            # Get all processed documents
            db = SessionLocal()
            try:
                documents = db.query(Document).filter(
                    Document.is_processed == True
                ).all()
                
                logger.info(f"Found {len(documents)} documents to index")
                
                # Add documents in batches
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    
                    ids = [f"doc_{doc.id}" for doc in batch]
                    contents = [doc.content for doc in batch]
                    metadatas = []
                    
                    for doc in batch:
                        metadata = {
                            "title": doc.title,
                            "source": doc.source,
                            "document_type": doc.document_type,
                            "url": doc.url or "",
                            "word_count": doc.word_count or 0,
                            "created_at": doc.created_at.isoformat() if doc.created_at else "",
                            "category": doc.category or "",
                            "tags": json.dumps(doc.tags) if doc.tags else "[]"
                        }
                        metadatas.append(metadata)
                    
                    # Add batch to AWS vector service
                    if self.client:
                        for j, doc in enumerate(batch):
                            await self.client.add_document(
                                doc_id=ids[j],
                                content=contents[j],
                                metadata=metadatas[j]
                            )
                    
                    # Update document status
                    for doc in batch:
                        doc.is_indexed = True
                        doc.last_indexed = doc.created_at
                    
                    db.commit()
                    
                    logger.info(f"Processed batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
            finally:
                db.close()
                
            logger.info("Vector index rebuild completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding vector index: {e}")
            return False
