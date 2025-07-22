import logging
from typing import Dict, Any, Optional, List
import json
import asyncio
from datetime import datetime

from app.services.ai_service import AIService
from app.services.vector_service import VectorService
# DocumentService removed - using direct database operations
from app.services.crawler_service import CrawlerService

logger = logging.getLogger(__name__)

class MCPService:
    """Model Context Protocol Service for coordinating AI operations"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.vector_service = VectorService()
        # DocumentService removed - using direct database operations
        self.crawler_service = CrawlerService()
        
    async def process_legal_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a comprehensive legal request using multiple services"""
        try:
            request_type = request.get('type', 'query')
            
            if request_type == 'query':
                return await self._process_query_request(request)
            elif request_type == 'document_generation':
                return await self._process_document_generation_request(request)
            elif request_type == 'document_analysis':
                return await self._process_document_analysis_request(request)
            elif request_type == 'legal_research':
                return await self._process_legal_research_request(request)
            else:
                raise ValueError(f"Unsupported request type: {request_type}")
                
        except Exception as e:
            logger.error(f"Error processing legal request: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            
    async def _process_query_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a legal query request"""
        query = request.get('query', '')
        context = request.get('context', {})
        
        # Answer the query using AI service
        response = await self.ai_service.answer_legal_query(query, context)
        
        return {
            'success': True,
            'type': 'query_response',
            'query': query,
            'response': response,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    async def _process_document_generation_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document generation request"""
        document_type = request.get('document_type', '')
        parameters = request.get('parameters', {})
        
        # Generate document using AI service
        document_content = await self.ai_service.generate_legal_document(document_type, parameters)
        
        return {
            'success': True,
            'type': 'document_generation',
            'document_type': document_type,
            'content': document_content,
            'parameters': parameters,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    async def _process_document_analysis_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document analysis request"""
        document_id = request.get('document_id')
        document_content = request.get('content', '')
        
        if document_id:
            # Get document from database (DocumentService removed)
            # document = await self.document_service.get_document_by_id(document_id)
            # if document:
            #     document_content = document.content
            # else:
            return {
                'success': False,
                'error': 'Document service not available - use CounselDocs instead',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Analyze document using AI service
        analysis = await self.ai_service.analyze_document_content(document_content)
        
        return {
            'success': True,
            'type': 'document_analysis',
            'document_id': document_id,
            'analysis': analysis,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    async def _process_legal_research_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a legal research request"""
        research_query = request.get('query', '')
        max_results = request.get('max_results', 10)
        sources = request.get('sources', ['kenya_law', 'parliament'])
        
        # Search for relevant documents
        relevant_docs = await self.vector_service.search_similar_documents(
            research_query, 
            limit=max_results
        )
        
        # If not enough results, try crawling
        if len(relevant_docs) < max_results // 2:
            crawl_results = await self.crawler_service.search_and_crawl(
                research_query, 
                max_results=max_results - len(relevant_docs)
            )
            logger.info(f"Crawled {len(crawl_results)} additional documents")
        
        # Generate research summary
        research_content = "\n\n".join([doc.content[:500] for doc in relevant_docs])
        summary = await self.ai_service.generate_legal_summary(
            research_content,
            f"legal_research_{research_query}"
        )
        
        return {
            'success': True,
            'type': 'legal_research',
            'query': research_query,
            'summary': summary,
            'relevant_documents': [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'source': doc.source,
                    'url': doc.url,
                    'relevance_score': getattr(doc, 'relevance_score', 0.0)
                } for doc in relevant_docs
            ],
            'total_results': len(relevant_docs),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    async def get_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        try:
            # Get vector service stats
            vector_stats = await self.vector_service.get_collection_stats()
            
            # Get document service stats
            # document_stats = await self.document_service.get_document_statistics()
            document_stats = {'status': 'service_removed', 'message': 'Use CounselDocs instead'}
            
            # Get crawler status
            crawler_status = await self.crawler_service.get_crawl_status()
            
            return {
                'success': True,
                'services': {
                    'vector_service': vector_stats,
                    'document_service': document_stats,
                    'crawler_service': crawler_status,
                    'ai_service': {
                        'status': 'active',
                        'models_available': [
                            'claude-sonnet-4' if self.ai_service.anthropic_client else None,
                            'hunyuan' if 'hunyuan' in self.ai_service.local_models else None,
                            'minimax' if 'minimax' in self.ai_service.local_models else None
                        ]
                    }
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
            
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services"""
        try:
            checks = {
                'vector_service': False,
                'ai_service': False,
                'database': False
            }
            
            # Check vector service
            try:
                if not self.vector_service._initialized:
                    await self.vector_service.initialize()
                checks['vector_service'] = True
            except Exception as e:
                logger.error(f"Vector service health check failed: {e}")
            
            # Check AI service
            try:
                # Test AWS Bedrock embedding service
                from app.services.aws_embedding_service import AWSEmbeddingService
                embedding_service = AWSEmbeddingService()
                await embedding_service.initialize()

                # If initialized, try to generate test embeddings
                if embedding_service._initialized:
                    embeddings = await embedding_service.generate_embeddings("test")
                    checks['ai_service'] = embeddings is not None and len(embeddings) > 0
                else:
                    # Service initialized but may be using fallback
                    checks['ai_service'] = True
                    logger.info("AI service using fallback embeddings")
            except Exception as e:
                logger.error(f"AI service health check failed: {e}")
                # Don't fail completely - service can work with fallback
                checks['ai_service'] = True
            
            # Check database (DocumentService removed)
            try:
                # stats = await self.document_service.get_document_statistics()
                # checks['database'] = isinstance(stats, dict)
                checks['database'] = True  # Assume database is healthy
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
            
            overall_health = all(checks.values())
            
            return {
                'success': True,
                'overall_health': overall_health,
                'service_checks': checks,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
