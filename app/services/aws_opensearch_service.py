"""
AWS OPENSEARCH RAG SERVICE
==========================
Production-grade RAG implementation using AWS OpenSearch for hybrid search,
advanced document indexing, and intelligent retrieval strategies.
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import boto3
import requests

logger = logging.getLogger(__name__)

# Optional OpenSearch imports
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
    OPENSEARCH_AVAILABLE = True
except ImportError:
    logger.warning("OpenSearch dependencies not available, using PostgreSQL fallback")
    OPENSEARCH_AVAILABLE = False
    AWS4Auth = None

from app.config import settings
from app.services.aws_embedding_service import aws_embedding_service
from app.services.llm_manager import llm_manager
from app.services.aws_opensearch_manager import aws_opensearch_manager

@dataclass
class SearchResult:
    """OpenSearch result with metadata"""
    document_id: str
    content: str
    score: float
    legal_area: str
    source_url: Optional[str]
    metadata: Dict[str, Any]
    highlights: List[str]

@dataclass
class HybridSearchResult:
    """Hybrid search result combining semantic and keyword search"""
    semantic_results: List[SearchResult]
    keyword_results: List[SearchResult]
    combined_results: List[SearchResult]
    total_found: int
    search_strategy: str

class AWSOpenSearchService:
    """
    AWS OpenSearch service for advanced RAG capabilities
    Implements hybrid search, document indexing, and intelligent retrieval
    """
    
    def __init__(self):
        self.client: Optional[OpenSearch] = None
        self.index_name = "kenyan-legal-docs"
        self.embedding_dimension = 1536  # AWS Titan embedding dimension
        self._initialized = False
        
        # OpenSearch configuration
        self.search_config = {
            "max_results": 20,
            "semantic_weight": 0.7,
            "keyword_weight": 0.3,
            "min_score": 0.1,
            "highlight_fields": ["content", "title", "summary"]
        }
    
    async def initialize(self):
        """Initialize AWS OpenSearch client with real AWS OpenSearch"""
        if self._initialized:
            return

        try:
            # Initialize OpenSearch manager
            await aws_opensearch_manager.initialize()

            # Initialize embedding service
            await aws_embedding_service.initialize()

            # Try to connect to real OpenSearch
            if OPENSEARCH_AVAILABLE and aws_opensearch_manager.domain_endpoint:
                await self._initialize_opensearch_client()
                logger.info("AWS OpenSearch Service initialized with real OpenSearch domain")
            else:
                logger.info("AWS OpenSearch Service initialized with PostgreSQL fallback")

            # Ensure fallback database is ready
            await self.create_index_if_not_exists()

            self._initialized = True
            logger.info("AWS OpenSearch Service ready for hybrid search")

        except Exception as e:
            logger.error(f"Failed to initialize AWS OpenSearch Service: {e}")
            # Continue with fallback to PostgreSQL
            self._initialized = True

    async def _initialize_opensearch_client(self):
        """Initialize real OpenSearch client"""
        try:
            if not AWS4Auth:
                logger.warning("AWS4Auth not available, skipping OpenSearch client initialization")
                return

            # Create AWS4Auth for authentication
            awsauth = AWS4Auth(
                settings.AWS_ACCESS_KEY_ID,
                settings.AWS_SECRET_ACCESS_KEY,
                settings.AWS_REGION,
                'es'
            )

            # Initialize OpenSearch client
            self.client = OpenSearch(
                hosts=[{
                    'host': aws_opensearch_manager.domain_endpoint,
                    'port': 443
                }],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )

            # Test connection
            cluster_health = self.client.cluster.health()
            logger.info(f"OpenSearch cluster health: {cluster_health['status']}")

            # Create index if it doesn't exist
            await self._create_opensearch_index()

        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {e}")
            self.client = None

    async def _create_opensearch_index(self):
        """Create OpenSearch index with proper mappings"""
        try:
            if not self.client:
                return

            index_mapping = {
                "mappings": {
                    "properties": {
                        "title": {"type": "text", "analyzer": "standard"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "summary": {"type": "text"},
                        "legal_area": {"type": "keyword"},
                        "source_url": {"type": "keyword"},
                        "document_type": {"type": "keyword"},
                        "jurisdiction": {"type": "keyword"},
                        "publication_date": {"type": "date"},
                        "keywords": {"type": "keyword"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.embedding_dimension
                        },
                        "created_at": {"type": "date"}
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "legal_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop"]
                            }
                        }
                    }
                }
            }

            if not self.client.indices.exists(index=self.index_name):
                self.client.indices.create(
                    index=self.index_name,
                    body=index_mapping
                )
                logger.info(f"Created OpenSearch index: {self.index_name}")
            else:
                logger.info(f"OpenSearch index already exists: {self.index_name}")

        except Exception as e:
            logger.error(f"Error creating OpenSearch index: {e}")
    
    async def create_index_if_not_exists(self):
        """Create OpenSearch index with proper mappings"""
        try:
            # In production OpenSearch, this would create the index
            # For now, we ensure our PostgreSQL tables support the functionality
            from app.database import get_db
            from sqlalchemy import text
            
            async for db in get_db():
                # Enhanced table for OpenSearch-like functionality
                create_enhanced_table = """
                CREATE TABLE IF NOT EXISTS legal_documents_enhanced (
                    id VARCHAR PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    embedding vector(1536),
                    legal_area VARCHAR(100),
                    source_url TEXT,
                    document_type VARCHAR(50),
                    jurisdiction VARCHAR(50) DEFAULT 'Kenya',
                    publication_date DATE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    keywords TEXT[],
                    metadata JSONB,
                    search_vector tsvector,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
                await db.execute(text(create_enhanced_table))
                
                # Create indexes for hybrid search
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_legal_docs_embedding ON legal_documents_enhanced USING ivfflat (embedding vector_cosine_ops);",
                    "CREATE INDEX IF NOT EXISTS idx_legal_docs_search_vector ON legal_documents_enhanced USING gin(search_vector);",
                    "CREATE INDEX IF NOT EXISTS idx_legal_docs_legal_area ON legal_documents_enhanced (legal_area);",
                    "CREATE INDEX IF NOT EXISTS idx_legal_docs_keywords ON legal_documents_enhanced USING gin(keywords);",
                    "CREATE INDEX IF NOT EXISTS idx_legal_docs_publication_date ON legal_documents_enhanced (publication_date);"
                ]
                
                for index_sql in indexes:
                    await db.execute(text(index_sql))
                
                await db.commit()
                logger.info("Enhanced legal documents table and indexes created")
                break
                
        except Exception as e:
            logger.error(f"Error creating enhanced index: {e}")
    
    async def index_document(
        self,
        document_id: str,
        title: str,
        content: str,
        legal_area: str,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Index a legal document with enhanced search capabilities
        
        Args:
            document_id: Unique document identifier
            title: Document title
            content: Document content
            legal_area: Legal practice area
            source_url: Source URL
            metadata: Additional metadata
            
        Returns:
            True if indexed successfully
        """
        try:
            if not self._initialized:
                await self.initialize()
                await self.create_index_if_not_exists()
            
            # Generate embedding
            full_text = f"{title}\n\n{content}"
            embedding = await aws_embedding_service.generate_embeddings(full_text)
            
            if not embedding:
                logger.warning(f"Failed to generate embedding for document {document_id}")
                return False
            
            # Extract keywords using simple NLP
            keywords = self._extract_keywords(content)
            
            # Generate summary
            summary = await self._generate_summary(content)
            
            # Store in enhanced PostgreSQL table
            from app.database import get_db
            from sqlalchemy import text
            
            async for db in get_db():
                insert_sql = """
                INSERT INTO legal_documents_enhanced 
                (id, title, content, summary, embedding, legal_area, source_url, 
                 keywords, metadata, search_vector, document_type, jurisdiction)
                VALUES 
                (:id, :title, :content, :summary, :embedding, :legal_area, :source_url,
                 :keywords, :metadata, to_tsvector('english', :title || ' ' || :content), 
                 'legal_document', 'Kenya')
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    summary = EXCLUDED.summary,
                    embedding = EXCLUDED.embedding,
                    legal_area = EXCLUDED.legal_area,
                    source_url = EXCLUDED.source_url,
                    keywords = EXCLUDED.keywords,
                    metadata = EXCLUDED.metadata,
                    search_vector = EXCLUDED.search_vector,
                    last_updated = CURRENT_TIMESTAMP;
                """
                
                await db.execute(text(insert_sql), {
                    'id': document_id,
                    'title': title,
                    'content': content,
                    'summary': summary,
                    'embedding': embedding,
                    'legal_area': legal_area,
                    'source_url': source_url,
                    'keywords': keywords,
                    'metadata': json.dumps(metadata or {})
                })
                
                await db.commit()
                logger.info(f"Indexed document: {document_id}")
                break
            
            return True
            
        except Exception as e:
            logger.error(f"Error indexing document {document_id}: {e}")
            return False
    
    async def hybrid_search(
        self,
        query: str,
        legal_area: Optional[str] = None,
        max_results: int = 10,
        semantic_weight: float = 0.7
    ) -> HybridSearchResult:
        """
        Perform hybrid search using real OpenSearch or PostgreSQL fallback

        Args:
            query: Search query
            legal_area: Filter by legal area
            max_results: Maximum results to return
            semantic_weight: Weight for semantic search (0-1)

        Returns:
            HybridSearchResult with combined results
        """
        try:
            if not self._initialized:
                await self.initialize()

            # Use real OpenSearch if available
            if self.client:
                return await self._opensearch_hybrid_search(
                    query, legal_area, max_results, semantic_weight
                )
            else:
                # Fallback to PostgreSQL
                return await self._postgresql_hybrid_search(
                    query, legal_area, max_results, semantic_weight
                )

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return HybridSearchResult(
                semantic_results=[],
                keyword_results=[],
                combined_results=[],
                total_found=0,
                search_strategy="error"
            )

    async def _opensearch_hybrid_search(
        self,
        query: str,
        legal_area: Optional[str],
        max_results: int,
        semantic_weight: float
    ) -> HybridSearchResult:
        """Perform hybrid search using real OpenSearch"""
        try:
            # Generate query embedding
            query_embedding = await aws_embedding_service.generate_embeddings(query)

            # Build OpenSearch query
            search_body = {
                "size": max_results,
                "query": {
                    "bool": {
                        "should": [
                            # Semantic search using k-NN
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_embedding,
                                        "k": max_results
                                    }
                                }
                            },
                            # Keyword search
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "content", "summary"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 150, "number_of_fragments": 3},
                        "title": {"fragment_size": 100, "number_of_fragments": 1}
                    }
                }
            }

            # Add legal area filter if specified
            if legal_area:
                search_body["query"]["bool"]["filter"] = [
                    {"term": {"legal_area": legal_area}}
                ]

            # Execute search
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.search(
                    index=self.index_name,
                    body=search_body
                )
            )

            # Process results
            search_results = []
            for hit in response['hits']['hits']:
                source = hit['_source']
                highlights = []

                if 'highlight' in hit:
                    for field, fragments in hit['highlight'].items():
                        highlights.extend(fragments)

                search_results.append(SearchResult(
                    document_id=hit['_id'],
                    content=source.get('content', ''),
                    score=hit['_score'],
                    legal_area=source.get('legal_area', 'general'),
                    source_url=source.get('source_url'),
                    metadata=source.get('metadata', {}),
                    highlights=highlights
                ))

            return HybridSearchResult(
                semantic_results=search_results,  # OpenSearch combines both
                keyword_results=[],
                combined_results=search_results,
                total_found=response['hits']['total']['value'],
                search_strategy="opensearch_hybrid"
            )

        except Exception as e:
            logger.error(f"Error in OpenSearch hybrid search: {e}")
            # Fallback to PostgreSQL
            return await self._postgresql_hybrid_search(
                query, legal_area, max_results, semantic_weight
            )

    async def _postgresql_hybrid_search(
        self,
        query: str,
        legal_area: Optional[str],
        max_results: int,
        semantic_weight: float
    ) -> HybridSearchResult:
        """Fallback hybrid search using PostgreSQL"""
        try:
            # Generate query embedding for semantic search
            query_embedding = await aws_embedding_service.generate_embeddings(query)

            # Perform semantic search
            semantic_results = await self._semantic_search(
                query_embedding, legal_area, max_results
            )

            # Perform keyword search
            keyword_results = await self._keyword_search(
                query, legal_area, max_results
            )

            # Combine and rank results
            combined_results = self._combine_search_results(
                semantic_results, keyword_results, semantic_weight
            )

            return HybridSearchResult(
                semantic_results=semantic_results,
                keyword_results=keyword_results,
                combined_results=combined_results[:max_results],
                total_found=len(combined_results),
                search_strategy="postgresql_hybrid_fallback"
            )

        except Exception as e:
            logger.error(f"Error in PostgreSQL hybrid search: {e}")
            return HybridSearchResult(
                semantic_results=[],
                keyword_results=[],
                combined_results=[],
                total_found=0,
                search_strategy="error"
            )
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content using simple NLP"""
        import re
        
        # Legal-specific keywords
        legal_terms = [
            'act', 'section', 'article', 'constitution', 'law', 'regulation',
            'statute', 'code', 'ordinance', 'bill', 'amendment', 'clause',
            'provision', 'subsection', 'paragraph', 'schedule', 'annex'
        ]
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        
        # Filter for legal terms and important words
        keywords = []
        for word in words:
            if word in legal_terms or len(word) > 6:
                if word not in keywords:
                    keywords.append(word)
        
        return keywords[:20]  # Limit to 20 keywords
    
    async def _generate_summary(self, content: str) -> str:
        """Generate document summary"""
        try:
            if len(content) < 500:
                return content[:200] + "..." if len(content) > 200 else content
            
            # Use LLM for summarization
            summary_prompt = f"""Provide a concise 2-3 sentence summary of this Kenyan legal document:

{content[:2000]}

Summary:"""
            
            response = await llm_manager.invoke_model(
                prompt=summary_prompt,
                model_preference="claude-3-7"  # Use faster model for summaries
            )
            
            if response.get("success"):
                return response.get("response_text", "")[:500]
            else:
                return content[:200] + "..."
                
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return content[:200] + "..."

    async def _semantic_search(
        self,
        query_embedding: List[float],
        legal_area: Optional[str],
        max_results: int
    ) -> List[SearchResult]:
        """Perform semantic search using embeddings"""
        try:
            from app.database import get_db
            from sqlalchemy import text

            # Build query with optional legal area filter
            where_clause = ""
            params = {
                'embedding': query_embedding,
                'limit': max_results
            }

            if legal_area:
                where_clause = "WHERE legal_area = :legal_area"
                params['legal_area'] = legal_area

            search_sql = f"""
            SELECT
                id, title, content, legal_area, source_url, metadata,
                summary, keywords,
                1 - (embedding <=> :embedding::vector) as similarity_score
            FROM legal_documents_enhanced
            {where_clause}
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit;
            """

            results = []
            async for db in get_db():
                result = await db.execute(text(search_sql), params)
                rows = result.fetchall()

                for row in rows:
                    # Generate highlights (simplified)
                    highlights = [row.summary[:200] + "..." if row.summary else row.content[:200] + "..."]

                    results.append(SearchResult(
                        document_id=row.id,
                        content=row.content,
                        score=float(row.similarity_score),
                        legal_area=row.legal_area,
                        source_url=row.source_url,
                        metadata=json.loads(row.metadata) if row.metadata else {},
                        highlights=highlights
                    ))
                break

            return results

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def _keyword_search(
        self,
        query: str,
        legal_area: Optional[str],
        max_results: int
    ) -> List[SearchResult]:
        """Perform keyword search using PostgreSQL full-text search"""
        try:
            from app.database import get_db
            from sqlalchemy import text

            # Build query with optional legal area filter
            where_clause = "WHERE search_vector @@ plainto_tsquery('english', :query)"
            params = {
                'query': query,
                'limit': max_results
            }

            if legal_area:
                where_clause += " AND legal_area = :legal_area"
                params['legal_area'] = legal_area

            search_sql = f"""
            SELECT
                id, title, content, legal_area, source_url, metadata,
                summary, keywords,
                ts_rank(search_vector, plainto_tsquery('english', :query)) as keyword_score,
                ts_headline('english', content, plainto_tsquery('english', :query),
                           'MaxWords=50, MinWords=20') as highlight
            FROM legal_documents_enhanced
            {where_clause}
            ORDER BY keyword_score DESC
            LIMIT :limit;
            """

            results = []
            async for db in get_db():
                result = await db.execute(text(search_sql), params)
                rows = result.fetchall()

                for row in rows:
                    highlights = [row.highlight] if hasattr(row, 'highlight') and row.highlight else []

                    results.append(SearchResult(
                        document_id=row.id,
                        content=row.content,
                        score=float(row.keyword_score),
                        legal_area=row.legal_area,
                        source_url=row.source_url,
                        metadata=json.loads(row.metadata) if row.metadata else {},
                        highlights=highlights
                    ))
                break

            return results

        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []

    def _combine_search_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        semantic_weight: float
    ) -> List[SearchResult]:
        """Combine and rank semantic and keyword search results"""
        try:
            # Create a map to combine results by document ID
            combined_map = {}

            # Add semantic results
            for result in semantic_results:
                combined_map[result.document_id] = result
                # Adjust score with semantic weight
                result.score = result.score * semantic_weight

            # Add keyword results
            keyword_weight = 1.0 - semantic_weight
            for result in keyword_results:
                if result.document_id in combined_map:
                    # Combine scores
                    existing = combined_map[result.document_id]
                    existing.score += result.score * keyword_weight
                    # Combine highlights
                    existing.highlights.extend(result.highlights)
                    existing.highlights = list(set(existing.highlights))  # Remove duplicates
                else:
                    # Add new result
                    result.score = result.score * keyword_weight
                    combined_map[result.document_id] = result

            # Sort by combined score
            combined_results = list(combined_map.values())
            combined_results.sort(key=lambda x: x.score, reverse=True)

            return combined_results

        except Exception as e:
            logger.error(f"Error combining search results: {e}")
            return semantic_results + keyword_results

    async def get_document_by_id(self, document_id: str) -> Optional[SearchResult]:
        """Get a specific document by ID"""
        try:
            from app.database import get_db
            from sqlalchemy import text

            search_sql = """
            SELECT id, title, content, legal_area, source_url, metadata, summary
            FROM legal_documents_enhanced
            WHERE id = :document_id;
            """

            async for db in get_db():
                result = await db.execute(text(search_sql), {'document_id': document_id})
                row = result.fetchone()

                if row:
                    return SearchResult(
                        document_id=row.id,
                        content=row.content,
                        score=1.0,
                        legal_area=row.legal_area,
                        source_url=row.source_url,
                        metadata=json.loads(row.metadata) if row.metadata else {},
                        highlights=[row.summary] if row.summary else []
                    )
                break

            return None

        except Exception as e:
            logger.error(f"Error getting document by ID: {e}")
            return None

    async def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics and statistics"""
        try:
            from app.database import get_db
            from sqlalchemy import text

            analytics_sql = """
            SELECT
                COUNT(*) as total_documents,
                COUNT(DISTINCT legal_area) as legal_areas,
                AVG(LENGTH(content)) as avg_content_length,
                legal_area,
                COUNT(*) as area_count
            FROM legal_documents_enhanced
            GROUP BY legal_area
            ORDER BY area_count DESC;
            """

            analytics = {
                "total_documents": 0,
                "legal_areas": 0,
                "avg_content_length": 0,
                "area_distribution": {},
                "search_config": self.search_config
            }

            async for db in get_db():
                result = await db.execute(text(analytics_sql))
                rows = result.fetchall()

                if rows:
                    analytics["total_documents"] = sum(row.area_count for row in rows)
                    analytics["legal_areas"] = len(rows)
                    analytics["avg_content_length"] = rows[0].avg_content_length if rows else 0

                    for row in rows:
                        analytics["area_distribution"][row.legal_area] = row.area_count
                break

            return analytics

        except Exception as e:
            logger.error(f"Error getting search analytics: {e}")
            return {"error": str(e)}

# Global AWS OpenSearch service instance
aws_opensearch_service = AWSOpenSearchService()
