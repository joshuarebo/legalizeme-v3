"""
AWS-Native Embedding Service
Replaces sentence-transformers with AWS Bedrock Titan embeddings
"""

import logging
import asyncio
import json
from typing import List, Dict, Optional, Any
import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)

class AWSEmbeddingService:
    """AWS Bedrock-based embedding service"""
    
    def __init__(self):
        self.bedrock_client = None
        self._initialized = False
        self.model_id = settings.AWS_BEDROCK_TITAN_EMBEDDING_MODEL_ID
        
    async def initialize(self):
        """Initialize AWS Bedrock client"""
        if self._initialized:
            return

        try:
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info("AWS Embedding Service initialized successfully")
            else:
                logger.warning("AWS credentials not found - using fallback embeddings")

            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize AWS Embedding Service: {e}")
            # Continue without Bedrock for development
            self._initialized = True
    
    async def generate_embeddings(self, text: str) -> Optional[List[float]]:
        """Generate embeddings using AWS Bedrock Titan"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if self.bedrock_client:
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps({
                        'inputText': text[:8000]  # Titan has input limits
                    })
                )
                
                result = json.loads(response['body'].read())
                return result.get('embedding', [])
            else:
                # Fallback for development
                return self._generate_fallback_embeddings(text)
                
        except Exception as e:
            logger.warning(f"Bedrock embedding failed, using fallback: {e}")
            return self._generate_fallback_embeddings(text)
    
    def _generate_fallback_embeddings(self, text: str, dim: int = 1536) -> List[float]:
        """Generate fallback embeddings using simple hashing"""
        import hashlib
        import math
        
        # Create multiple hash values for better distribution
        hashes = []
        for i in range(4):
            hash_input = f"{text}_{i}".encode()
            hash_obj = hashlib.sha256(hash_input)
            hash_hex = hash_obj.hexdigest()
            hashes.append(hash_hex)
        
        # Convert to float vector
        embedding = []
        combined_hash = ''.join(hashes)
        
        for i in range(0, len(combined_hash), 2):
            if len(embedding) >= dim:
                break
            val = int(combined_hash[i:i+2], 16) / 255.0
            # Apply sine transformation for better distribution
            val = math.sin(val * math.pi)
            embedding.append(val)
        
        # Pad to desired dimension
        while len(embedding) < dim:
            embedding.append(0.0)
        
        # Normalize vector
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x/norm for x in embedding]
        
        return embedding[:dim]
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts"""
        if not self._initialized:
            await self.initialize()
            
        embeddings = []
        for text in texts:
            embedding = await self.generate_embeddings(text)
            embeddings.append(embedding)
        
        return embeddings
    
    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate embeddings for both texts
            emb1 = await self.generate_embeddings(text1)
            emb2 = await self.generate_embeddings(text2)
            
            if not emb1 or not emb2:
                return 0.0
            
            # Calculate cosine similarity
            return self._cosine_similarity(emb1, emb2)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            # Ensure vectors are same length
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]
            
            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # Calculate magnitudes
            mag1 = math.sqrt(sum(a * a for a in vec1))
            mag2 = math.sqrt(sum(b * b for b in vec2))
            
            if mag1 == 0 or mag2 == 0:
                return 0.0
            
            return dot_product / (mag1 * mag2)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    async def find_most_similar(self, query: str, candidates: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """Find most similar texts from candidates"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate query embedding
            query_emb = await self.generate_embeddings(query)
            if not query_emb:
                return []
            
            # Calculate similarities
            similarities = []
            for i, candidate in enumerate(candidates):
                candidate_emb = await self.generate_embeddings(candidate)
                if candidate_emb:
                    similarity = self._cosine_similarity(query_emb, candidate_emb)
                    similarities.append({
                        'index': i,
                        'text': candidate,
                        'similarity': similarity
                    })
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar texts: {e}")
            return []
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            'service_name': 'AWS Embedding Service',
            'model_id': self.model_id,
            'initialized': self._initialized,
            'has_bedrock': self.bedrock_client is not None,
            'fallback_available': True
        }

# Global instance
aws_embedding_service = AWSEmbeddingService()
