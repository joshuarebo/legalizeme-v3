"""
Document Indexing Service
Bridge between crawlers and OpenSearch vector store
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

from app.services.aws_embedding_service import aws_embedding_service
from app.services.aws_vector_service import aws_vector_service

logger = logging.getLogger(__name__)

class DocumentIndexingService:
    """Index crawled documents to OpenSearch with embeddings"""

    def __init__(self):
        self.embedding_service = aws_embedding_service
        self.vector_service = aws_vector_service
        self._initialized = False

    async def initialize(self):
        """Initialize required services"""
        if self._initialized:
            return

        try:
            await self.embedding_service.initialize()
            await self.vector_service.initialize()
            self._initialized = True
            logger.info("Document Indexing Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Document Indexing Service: {e}")
            raise

    async def index_crawled_document(self, crawl_result: Dict[str, Any]) -> bool:
        """
        Index a crawled document to OpenSearch

        Args:
            crawl_result: Dict with keys:
                - title: Document title
                - content: Full text content
                - url: Source URL
                - document_type: 'judgment', 'legislation', etc.
                - metadata: Dict with court, date, etc.

        Returns:
            True if indexed successfully
        """
        try:
            if not self._initialized:
                await self.initialize()

            # Extract fields
            title = crawl_result.get('title', 'Untitled')
            content = crawl_result.get('content', '')
            url = crawl_result.get('url', '')
            doc_type = crawl_result.get('document_type', 'legal_document')
            metadata = crawl_result.get('metadata', {})

            # Validate content
            if not content or len(content.strip()) < 50:
                logger.warning(f"Skipping document with insufficient content: {title[:50]}")
                return False

            # Generate document ID from URL
            if url:
                doc_id = hashlib.md5(url.encode()).hexdigest()
            else:
                doc_id = f"doc_{int(datetime.utcnow().timestamp() * 1000)}"

            # Prepare text for embedding (title + content preview)
            text_to_embed = f"{title}\n\n{content[:2000]}"  # First 2000 chars

            # Extract additional metadata
            legal_area = metadata.get('legal_area', 'General')
            court = metadata.get('court')
            publication_date = metadata.get('publication_date') or metadata.get('date')
            summary = metadata.get('summary', content[:500])

            # Add to vector store (which now uses OpenSearch)
            success = await self.vector_service.add_document(
                doc_id=doc_id,
                text=text_to_embed,
                metadata={
                    'title': title,
                    'source_url': url,
                    'document_type': doc_type,
                    'legal_area': legal_area,
                    'court': court,
                    'publication_date': publication_date,
                    'summary': summary,
                    'full_content': content,
                    **metadata
                }
            )

            if success:
                logger.info(f"✓ Indexed: {title[:60]}... ({doc_id[:8]})")
            else:
                logger.error(f"✗ Failed to index: {title[:60]}")

            return success

        except Exception as e:
            logger.error(f"Error indexing document: {e}", exc_info=True)
            return False

    async def index_batch(self, crawl_results: list[Dict[str, Any]]) -> Dict[str, int]:
        """
        Index multiple documents in batch

        Args:
            crawl_results: List of crawl result dictionaries

        Returns:
            Dict with 'indexed', 'failed', 'total' counts
        """
        if not self._initialized:
            await self.initialize()

        indexed = 0
        failed = 0

        for result in crawl_results:
            success = await self.index_crawled_document(result)
            if success:
                indexed += 1
            else:
                failed += 1

        logger.info(f"Batch indexing complete: {indexed} indexed, {failed} failed, {len(crawl_results)} total")

        return {
            'indexed': indexed,
            'failed': failed,
            'total': len(crawl_results)
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        if not self._initialized:
            await self.initialize()

        return await self.vector_service.get_collection_stats()

# Global instance
document_indexing_service = DocumentIndexingService()
