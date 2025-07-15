"""
Enhanced Vector Integration for Multi-Modal Document Processing
Connects multi-modal processing to existing ChromaDB vector search with enhanced indexing
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import json
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

from app.config import settings
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from .document_processor import MultiModalDocumentProcessor
from .document_router import DocumentRouter

logger = logging.getLogger(__name__)

class MultiModalVectorIntegration:
    """Enhanced vector integration for multi-modal document processing"""
    
    def __init__(self):
        self.vector_service = VectorService()
        self.ai_service = AIService()
        self.document_processor = MultiModalDocumentProcessor()
        self.document_router = DocumentRouter()
        
        # Enhanced collection for multi-modal documents
        self.multimodal_collection = None
        self.collection_name = "multimodal_legal_documents"
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize the multi-modal vector integration"""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing Multi-Modal Vector Integration...")
            
            # Initialize base services
            await self.vector_service.initialize()
            await self.document_processor.initialize()
            await self.document_router.initialize()
            
            # Initialize enhanced ChromaDB collection for multi-modal documents
            if HAS_CHROMADB and self.vector_service.client:
                try:
                    self.multimodal_collection = self.vector_service.client.get_collection(
                        name=self.collection_name
                    )
                    logger.info(f"Retrieved existing multi-modal collection: {self.collection_name}")
                except Exception:
                    self.multimodal_collection = self.vector_service.client.create_collection(
                        name=self.collection_name,
                        metadata={
                            "description": "Multi-modal legal documents with enhanced processing",
                            "version": "1.0",
                            "features": "pdf_extraction,ocr_processing,document_classification,structured_summarization"
                        }
                    )
                    logger.info(f"Created new multi-modal collection: {self.collection_name}")
            
            self._initialized = True
            logger.info("Multi-Modal Vector Integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Multi-Modal Vector Integration: {e}")
            raise
    
    async def process_and_index_document(self, file_path: Union[str, Path], 
                                       processing_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process document with multi-modal capabilities and add to vector index
        
        Args:
            file_path: Path to document file
            processing_options: Processing configuration options
        
        Returns:
            Processing and indexing results
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Process document using multi-modal router
            processing_result = await self.document_router.process_document(
                file_path, processing_options or {}
            )
            
            if not processing_result.get("success"):
                return {
                    "success": False,
                    "error": f"Document processing failed: {processing_result.get('error', 'Unknown error')}"
                }
            
            # Extract processed information
            text_content = processing_result.get("text", "")
            document_type = processing_result.get("document_type", "unknown")
            summary_data = processing_result.get("summary_data", {})
            
            # Generate enhanced metadata
            enhanced_metadata = await self._create_enhanced_metadata(
                file_path, processing_result
            )
            
            # Generate embeddings for the full text
            embeddings = await self._generate_embeddings(text_content)
            
            if not embeddings:
                logger.warning(f"Failed to generate embeddings for {file_path}")
                embeddings = [0.0] * 384  # Fallback zero vector
            
            # Create document chunks for better retrieval
            chunks = await self._create_document_chunks(text_content, enhanced_metadata)
            
            # Add to multi-modal collection
            indexing_result = await self._add_to_multimodal_collection(
                file_path, text_content, embeddings, enhanced_metadata, chunks
            )
            
            # Also add to standard vector service for compatibility
            await self._add_to_standard_collection(file_path, text_content, enhanced_metadata)
            
            return {
                "success": True,
                "processing_result": processing_result,
                "indexing_result": indexing_result,
                "metadata": enhanced_metadata,
                "chunks_created": len(chunks),
                "embeddings_generated": len(embeddings) > 0
            }
            
        except Exception as e:
            logger.error(f"Error processing and indexing document {file_path}: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_multimodal_documents(self, query: str, 
                                        filters: Optional[Dict[str, Any]] = None,
                                        limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search multi-modal documents with enhanced filtering
        
        Args:
            query: Search query
            filters: Optional filters (document_type, extraction_method, etc.)
            limit: Maximum number of results
        
        Returns:
            List of matching documents with enhanced metadata
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            if not self.multimodal_collection:
                logger.warning("Multi-modal collection not available, falling back to standard search")
                return await self._fallback_search(query, filters, limit)
            
            # Build where clause for filtering
            where_clause = {}
            if filters:
                if filters.get('document_type'):
                    where_clause['document_type'] = filters['document_type']
                if filters.get('extraction_method'):
                    where_clause['extraction_method'] = filters['extraction_method']
                if filters.get('has_summary'):
                    where_clause['has_summary'] = filters['has_summary']
                if filters.get('confidence_threshold'):
                    where_clause['processing_confidence'] = {"$gte": filters['confidence_threshold']}
            
            # Search in multi-modal collection
            results = self.multimodal_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0.0,
                        "relevance_score": 1.0 - (results['distances'][0][i] if results['distances'] else 0.0)
                    }
                    formatted_results.append(result)
            
            logger.info(f"Multi-modal search returned {len(formatted_results)} results for query: {query}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in multi-modal document search: {e}")
            return await self._fallback_search(query, filters, limit)
    
    async def _create_enhanced_metadata(self, file_path: Path, processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced metadata for multi-modal documents"""
        try:
            file_path = Path(file_path)
            
            metadata = {
                # File information
                "filename": file_path.name,
                "file_extension": file_path.suffix.lower(),
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "processing_timestamp": datetime.now().isoformat(),
                
                # Processing information
                "document_type": processing_result.get("document_type", "unknown"),
                "extraction_method": processing_result.get("extraction_method", "unknown"),
                "word_count": processing_result.get("word_count", 0),
                "char_count": processing_result.get("char_count", 0),
                
                # Quality metrics
                "processing_confidence": processing_result.get("confidence", 0.0),
                "has_summary": bool(processing_result.get("summary_data")),
                "has_entities": bool(processing_result.get("summary_data", {}).get("extracted_entities")),
                
                # Multi-modal specific
                "is_multimodal": True,
                "processor_version": "1.0",
                "capabilities_used": []
            }
            
            # Add routing information
            routing_info = processing_result.get("routing_info", {})
            metadata.update({
                "file_type": routing_info.get("file_type", "unknown"),
                "processor_used": routing_info.get("processor_used", "unknown")
            })
            
            # Add summary data if available
            summary_data = processing_result.get("summary_data", {})
            if summary_data:
                metadata.update({
                    "summary_length": len(summary_data.get("summary", "").split()),
                    "entities_count": len(summary_data.get("extracted_entities", {}).get("parties", [])),
                    "model_used": summary_data.get("model_used", "unknown")
                })
            
            # Add text quality information
            text_quality = processing_result.get("text_quality", {})
            if text_quality:
                metadata.update({
                    "avg_word_length": float(text_quality.get("avg_word_length", 0.0)),
                    "legal_document_score": float(processing_result.get("legal_document_score", 0.0))
                })

            # Ensure all metadata values are scalar (ChromaDB requirement)
            cleaned_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (list, dict)):
                    # Convert complex types to strings
                    cleaned_metadata[key] = str(value)
                elif isinstance(value, bool):
                    cleaned_metadata[key] = value
                elif isinstance(value, (int, float)):
                    cleaned_metadata[key] = value
                else:
                    cleaned_metadata[key] = str(value)

            return cleaned_metadata
            
        except Exception as e:
            logger.error(f"Error creating enhanced metadata: {e}")
            return {"error": str(e), "processing_timestamp": datetime.now().isoformat()}
    
    async def _generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generate embeddings using AI service"""
        try:
            if hasattr(self.ai_service, 'generate_embeddings'):
                embeddings = await self.ai_service.generate_embeddings(text)
                return embeddings if embeddings else None
            else:
                # Fallback to document processor
                return await self.document_processor.generate_embeddings(text)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return None
    
    async def _create_document_chunks(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create document chunks for better retrieval"""
        try:
            # Simple chunking strategy - can be enhanced
            chunk_size = 1000
            overlap = 200
            
            chunks = []
            words = text.split()
            
            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                if chunk_text.strip():
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": len(chunks),
                        "chunk_size": len(chunk_text),
                        "chunk_word_count": len(chunk_words),
                        "is_chunk": True
                    })
                    
                    chunks.append({
                        "text": chunk_text,
                        "metadata": chunk_metadata
                    })
            
            return chunks

        except Exception as e:
            logger.error(f"Error creating document chunks: {e}")
            return [{"text": text, "metadata": metadata}]  # Fallback to single chunk

    async def _add_to_multimodal_collection(self, file_path: Path, text: str,
                                          embeddings: List[float], metadata: Dict[str, Any],
                                          chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add document and chunks to multi-modal collection"""
        try:
            if not self.multimodal_collection:
                return {"success": False, "error": "Multi-modal collection not available"}

            # Add main document
            doc_id = f"multimodal_{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            self.multimodal_collection.add(
                documents=[text],
                embeddings=[embeddings],
                metadatas=[metadata],
                ids=[doc_id]
            )

            # Add chunks
            chunk_ids = []
            chunk_texts = []
            chunk_embeddings = []
            chunk_metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunk_embedding = await self._generate_embeddings(chunk["text"])

                if chunk_embedding:
                    chunk_ids.append(chunk_id)
                    chunk_texts.append(chunk["text"])
                    chunk_embeddings.append(chunk_embedding)
                    chunk_metadatas.append(chunk["metadata"])

            if chunk_ids:
                self.multimodal_collection.add(
                    documents=chunk_texts,
                    embeddings=chunk_embeddings,
                    metadatas=chunk_metadatas,
                    ids=chunk_ids
                )

            return {
                "success": True,
                "document_id": doc_id,
                "chunks_added": len(chunk_ids),
                "collection": self.collection_name
            }

        except Exception as e:
            logger.error(f"Error adding to multi-modal collection: {e}")
            return {"success": False, "error": str(e)}

    async def _add_to_standard_collection(self, file_path: Path, text: str,
                                        metadata: Dict[str, Any]) -> bool:
        """Add document to standard vector collection for compatibility"""
        try:
            # Create a simplified document object for standard collection
            from app.models.document import Document

            # Create temporary document object (not saved to DB)
            temp_doc = Document(
                title=metadata.get("filename", "Unknown"),
                content=text,
                source="multimodal_processing",
                document_type=metadata.get("document_type", "unknown"),
                word_count=metadata.get("word_count", 0),
                created_at=datetime.now()
            )

            # Add to standard vector service
            return await self.vector_service.add_document(temp_doc)

        except Exception as e:
            logger.error(f"Error adding to standard collection: {e}")
            return False

    async def _fallback_search(self, query: str, filters: Optional[Dict[str, Any]],
                             limit: int) -> List[Dict[str, Any]]:
        """Fallback search using standard vector service"""
        try:
            # Convert filters to standard format
            standard_filters = {}
            if filters:
                if filters.get('document_type'):
                    standard_filters['document_type'] = filters['document_type']

            # Search using standard vector service
            results = await self.vector_service.search_similar_documents(
                query, limit, standard_filters
            )

            # Format results to match multi-modal format
            formatted_results = []
            for doc in results:
                result = {
                    "content": doc.content,
                    "metadata": {
                        "title": doc.title,
                        "document_type": doc.document_type,
                        "source": doc.source,
                        "word_count": doc.word_count or 0,
                        "is_fallback": True
                    },
                    "distance": 0.5,  # Default distance
                    "relevance_score": 0.5
                }
                formatted_results.append(result)

            return formatted_results

        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the multi-modal collection"""
        try:
            if not self._initialized:
                await self.initialize()

            stats = {
                "multimodal_collection_available": self.multimodal_collection is not None,
                "standard_collection_available": self.vector_service.collection is not None,
                "total_documents": 0,
                "total_chunks": 0,
                "document_types": {},
                "extraction_methods": {}
            }

            if self.multimodal_collection:
                # Get collection count
                try:
                    collection_data = self.multimodal_collection.get()
                    if collection_data and collection_data.get('metadatas'):
                        metadatas = collection_data['metadatas']

                        stats["total_documents"] = len([m for m in metadatas if not m.get('is_chunk', False)])
                        stats["total_chunks"] = len([m for m in metadatas if m.get('is_chunk', False)])

                        # Count document types
                        for metadata in metadatas:
                            if not metadata.get('is_chunk', False):
                                doc_type = metadata.get('document_type', 'unknown')
                                stats["document_types"][doc_type] = stats["document_types"].get(doc_type, 0) + 1

                                extraction_method = metadata.get('extraction_method', 'unknown')
                                stats["extraction_methods"][extraction_method] = stats["extraction_methods"].get(extraction_method, 0) + 1

                except Exception as e:
                    logger.warning(f"Could not get detailed collection stats: {e}")

            return stats

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    async def delete_document(self, document_id: str) -> bool:
        """Delete document and its chunks from multi-modal collection"""
        try:
            if not self.multimodal_collection:
                return False

            # Get all IDs that start with the document ID
            collection_data = self.multimodal_collection.get()
            if collection_data and collection_data.get('ids'):
                ids_to_delete = [
                    id for id in collection_data['ids']
                    if id.startswith(document_id)
                ]

                if ids_to_delete:
                    self.multimodal_collection.delete(ids=ids_to_delete)
                    logger.info(f"Deleted {len(ids_to_delete)} items for document {document_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    def get_integration_capabilities(self) -> Dict[str, Any]:
        """Get integration capabilities and status"""
        return {
            "multimodal_processing": True,
            "vector_indexing": HAS_CHROMADB,
            "enhanced_search": self.multimodal_collection is not None,
            "document_chunking": True,
            "metadata_enhancement": True,
            "fallback_search": True,
            "supported_formats": ["pdf", "image", "text", "docx"],
            "features": [
                "Multi-modal document processing",
                "Enhanced metadata extraction",
                "Document chunking for better retrieval",
                "Confidence-based filtering",
                "Document type classification",
                "Extraction method tracking",
                "Structured summarization integration"
            ]
        }
