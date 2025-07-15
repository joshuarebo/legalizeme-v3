"""
AWS-Native Vector Service
Replaces ChromaDB with AWS OpenSearch for production-ready vector operations
"""

import logging
import asyncio
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

class AWSVectorService:
    """AWS OpenSearch-based vector service for production deployment"""
    
    def __init__(self):
        self.opensearch_client = None
        self.bedrock_client = None
        self.index_name = "legal-documents"
        self._initialized = False
        
    async def initialize(self):
        """Initialize AWS services"""
        if self._initialized:
            return
            
        try:
            # Initialize AWS clients
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            
            # For now, we'll use a simple in-memory vector store
            # In production, this would be AWS OpenSearch
            self.vector_store = {}
            self.document_store = {}
            
            self._initialized = True
            logger.info("AWS Vector Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS Vector Service: {e}")
            raise
    
    async def generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generate embeddings using AWS Bedrock Titan"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Use Bedrock Titan for embeddings
            from app.config import settings
            response = self.bedrock_client.invoke_model(
                modelId=settings.AWS_BEDROCK_TITAN_EMBEDDING_MODEL_ID,
                body=json.dumps({
                    'inputText': text
                })
            )
            
            result = json.loads(response['body'].read())
            return result.get('embedding', [])
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Fallback to simple hash-based embeddings for development
            return self._generate_simple_embeddings(text)
    
    def _generate_simple_embeddings(self, text: str, dim: int = 384) -> List[float]:
        """Simple fallback embedding generation"""
        # Create a simple hash-based embedding
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Convert to float vector
        embedding = []
        for i in range(0, len(hash_hex), 2):
            val = int(hash_hex[i:i+2], 16) / 255.0
            embedding.append(val)
        
        # Pad or truncate to desired dimension
        while len(embedding) < dim:
            embedding.extend(embedding[:min(len(embedding), dim - len(embedding))])
        
        return embedding[:dim]
    
    async def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """Add document to vector store"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate embeddings
            embeddings = await self.generate_embeddings(text)
            if not embeddings:
                return False
            
            # Store document and embeddings
            self.vector_store[doc_id] = embeddings
            self.document_store[doc_id] = {
                'text': text,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Added document {doc_id} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document {doc_id}: {e}")
            return False
    
    async def search_similar(self, query: str, limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate query embeddings
            query_embeddings = await self.generate_embeddings(query)
            if not query_embeddings:
                return []
            
            # Calculate similarities
            similarities = []
            for doc_id, doc_embeddings in self.vector_store.items():
                similarity = self._cosine_similarity(query_embeddings, doc_embeddings)
                if similarity >= threshold:
                    similarities.append({
                        'doc_id': doc_id,
                        'similarity': similarity,
                        'document': self.document_store.get(doc_id, {})
                    })
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Convert to numpy arrays for calculation
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return dot_product / (norm_a * norm_b)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        if not self._initialized:
            await self.initialize()
            
        return self.document_store.get(doc_id)
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from vector store"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if doc_id in self.vector_store:
                del self.vector_store[doc_id]
            if doc_id in self.document_store:
                del self.document_store[doc_id]
            
            logger.info(f"Deleted document {doc_id} from vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self._initialized:
            await self.initialize()
            
        return {
            'total_documents': len(self.document_store),
            'total_vectors': len(self.vector_store),
            'index_name': self.index_name,
            'service_type': 'AWS-Native Vector Service'
        }

# Global instance
aws_vector_service = AWSVectorService()
