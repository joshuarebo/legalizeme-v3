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
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

from app.config import settings

logger = logging.getLogger(__name__)

class AWSVectorService:
    """AWS OpenSearch-based vector service for production deployment"""
    
    def __init__(self):
        self.opensearch_client = None
        self.bedrock_client = None
        self.index_name = settings.OPENSEARCH_INDEX
        self._initialized = False
        self._use_opensearch = True  # Flag to enable/disable OpenSearch
        
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

            # Initialize OpenSearch connection
            if self._use_opensearch:
                try:
                    # Get AWS credentials for OpenSearch authentication
                    session = boto3.Session(
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_REGION
                    )
                    credentials = session.get_credentials()

                    awsauth = AWS4Auth(
                        credentials.access_key,
                        credentials.secret_key,
                        settings.AWS_REGION,
                        'es',
                        session_token=credentials.token
                    )

                    # Create OpenSearch client
                    self.opensearch_client = OpenSearch(
                        hosts=[{
                            'host': settings.OPENSEARCH_ENDPOINT,
                            'port': settings.OPENSEARCH_PORT
                        }],
                        http_auth=awsauth,
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection,
                        timeout=30
                    )

                    # Test connection
                    info = self.opensearch_client.info()
                    logger.info(f"Connected to OpenSearch: {info.get('version', {}).get('number', 'unknown')}")

                except Exception as os_error:
                    logger.error(f"Failed to connect to OpenSearch: {os_error}")
                    logger.warning("Falling back to in-memory vector store")
                    self._use_opensearch = False

            # Fallback to in-memory store if OpenSearch not available
            if not self._use_opensearch:
                self.vector_store = {}
                self.document_store = {}
                logger.info("Using in-memory vector store (fallback mode)")

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
                logger.error(f"Failed to generate embeddings for document {doc_id}")
                return False

            metadata = metadata or {}

            if self._use_opensearch and self.opensearch_client:
                try:
                    # Index document to OpenSearch
                    document = {
                        'embedding': embeddings,
                        'content': text,
                        'title': metadata.get('title', 'Untitled'),
                        'source_url': metadata.get('source_url', ''),
                        'document_type': metadata.get('document_type', 'legal_document'),
                        'legal_area': metadata.get('legal_area', 'General'),
                        'court': metadata.get('court'),
                        'publication_date': metadata.get('publication_date'),
                        'summary': metadata.get('summary', text[:500]),
                        'metadata': metadata,
                        'created_at': datetime.utcnow().isoformat()
                    }

                    response = self.opensearch_client.index(
                        index=self.index_name,
                        id=doc_id,
                        body=document,
                        refresh=True  # Make document immediately searchable
                    )

                    logger.info(f"Indexed document {doc_id} to OpenSearch: {response.get('result', 'unknown')}")
                    return response.get('result') in ['created', 'updated']

                except Exception as os_error:
                    logger.error(f"OpenSearch indexing failed for {doc_id}: {os_error}")
                    # Fall back to in-memory if OpenSearch fails
                    self._use_opensearch = False

            # Fallback to in-memory storage
            if not self._use_opensearch:
                if not hasattr(self, 'vector_store'):
                    self.vector_store = {}
                    self.document_store = {}

                self.vector_store[doc_id] = embeddings
                self.document_store[doc_id] = {
                    'text': text,
                    'metadata': metadata,
                    'created_at': datetime.utcnow().isoformat()
                }
                logger.info(f"Added document {doc_id} to in-memory store")
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
                logger.error("Failed to generate query embeddings")
                return []

            if self._use_opensearch and self.opensearch_client:
                try:
                    # Use k-NN search in OpenSearch
                    search_query = {
                        "size": limit,
                        "query": {
                            "knn": {
                                "embedding": {
                                    "vector": query_embeddings,
                                    "k": limit
                                }
                            }
                        },
                        "_source": ["title", "content", "source_url", "legal_area", "document_type", "court", "publication_date", "summary", "metadata"]
                    }

                    response = self.opensearch_client.search(
                        index=self.index_name,
                        body=search_query
                    )

                    # Format results
                    results = []
                    for hit in response.get('hits', {}).get('hits', []):
                        score = hit.get('_score', 0)
                        # Convert OpenSearch score to similarity (0-1 range)
                        # k-NN scores are already normalized
                        similarity = min(score / 2.0, 1.0) if score > 0 else 0

                        if similarity >= threshold:
                            source = hit.get('_source', {})
                            results.append({
                                'doc_id': hit.get('_id'),
                                'similarity': similarity,
                                'score': score,
                                'document': {
                                    'text': source.get('content', ''),
                                    'metadata': {
                                        'title': source.get('title', ''),
                                        'source_url': source.get('source_url', ''),
                                        'legal_area': source.get('legal_area', ''),
                                        'document_type': source.get('document_type', ''),
                                        'court': source.get('court'),
                                        'publication_date': source.get('publication_date'),
                                        'summary': source.get('summary', ''),
                                        **source.get('metadata', {})
                                    }
                                }
                            })

                    logger.info(f"OpenSearch k-NN search returned {len(results)} results")
                    return results

                except Exception as os_error:
                    logger.error(f"OpenSearch search failed: {os_error}")
                    # Fall back to in-memory search
                    self._use_opensearch = False

            # Fallback to in-memory similarity search
            if not self._use_opensearch:
                if not hasattr(self, 'vector_store'):
                    logger.warning("No vector store available")
                    return []

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
                logger.info(f"In-memory search returned {len(similarities[:limit])} results")
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
            if self._use_opensearch and self.opensearch_client:
                try:
                    response = self.opensearch_client.delete(
                        index=self.index_name,
                        id=doc_id
                    )
                    logger.info(f"Deleted document {doc_id} from OpenSearch")
                    return response.get('result') == 'deleted'
                except Exception as os_error:
                    logger.error(f"OpenSearch delete failed: {os_error}")
                    self._use_opensearch = False

            # Fallback to in-memory delete
            if not self._use_opensearch:
                if hasattr(self, 'vector_store') and doc_id in self.vector_store:
                    del self.vector_store[doc_id]
                if hasattr(self, 'document_store') and doc_id in self.document_store:
                    del self.document_store[doc_id]
                logger.info(f"Deleted document {doc_id} from in-memory store")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        if not self._initialized:
            await self.initialize()

        try:
            if self._use_opensearch and self.opensearch_client:
                try:
                    count_response = self.opensearch_client.count(index=self.index_name)
                    stats_response = self.opensearch_client.indices.stats(index=self.index_name)

                    return {
                        'total_documents': count_response.get('count', 0),
                        'index_name': self.index_name,
                        'service_type': 'AWS OpenSearch',
                        'size_bytes': stats_response.get('_all', {}).get('total', {}).get('store', {}).get('size_in_bytes', 0),
                        'using_opensearch': True
                    }
                except Exception as os_error:
                    logger.error(f"Failed to get OpenSearch stats: {os_error}")
                    self._use_opensearch = False

            # Fallback to in-memory stats
            if not self._use_opensearch:
                return {
                    'total_documents': len(getattr(self, 'document_store', {})),
                    'total_vectors': len(getattr(self, 'vector_store', {})),
                    'index_name': self.index_name,
                    'service_type': 'In-Memory Vector Store (Fallback)',
                    'using_opensearch': False
                }

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                'total_documents': 0,
                'index_name': self.index_name,
                'service_type': 'Error',
                'error': str(e)
            }

# Global instance
aws_vector_service = AWSVectorService()
