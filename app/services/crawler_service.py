import asyncio
import logging
from typing import List, Dict, Optional, Any
import httpx
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin, urlparse
import time
from datetime import datetime, timedelta
import json

from app.config import settings
from app.models.document import Document
from app.models.legal_case import LegalCase
from app.database import SessionLocal
from app.services.document_service import DocumentService
from app.crawlers.kenya_law_crawler import KenyaLawCrawler
from app.crawlers.parliament_crawler import ParliamentCrawler

logger = logging.getLogger(__name__)

class CrawlerService:
    def __init__(self):
        self.session = None
        self.document_service = DocumentService()
        self.kenya_law_crawler = KenyaLawCrawler()
        self.parliament_crawler = ParliamentCrawler()
        self.is_running = False
        self.crawl_tasks = []
        
    async def start_periodic_crawling(self):
        """Start periodic crawling tasks"""
        if self.is_running:
            logger.warning("Crawling is already running")
            return
            
        self.is_running = True
        logger.info("Starting periodic crawling")
        
        # Start crawling tasks
        self.crawl_tasks = [
            asyncio.create_task(self._periodic_kenya_law_crawl()),
            asyncio.create_task(self._periodic_parliament_crawl())
        ]
        
    async def stop_periodic_crawling(self):
        """Stop periodic crawling tasks"""
        if not self.is_running:
            return
            
        self.is_running = False
        logger.info("Stopping periodic crawling")
        
        # Cancel all running tasks
        for task in self.crawl_tasks:
            if not task.done():
                task.cancel()
                
        # Wait for tasks to complete
        await asyncio.gather(*self.crawl_tasks, return_exceptions=True)
        self.crawl_tasks = []
        
    async def _periodic_kenya_law_crawl(self):
        """Periodically crawl Kenya Law resources"""
        while self.is_running:
            try:
                logger.info("Starting Kenya Law crawling cycle")
                
                # Crawl different sections
                await self.kenya_law_crawler.crawl_judgments()
                await asyncio.sleep(60)  # Wait between sections
                
                await self.kenya_law_crawler.crawl_legislation()
                await asyncio.sleep(60)
                
                await self.kenya_law_crawler.crawl_gazettes()
                await asyncio.sleep(60)
                
                logger.info("Kenya Law crawling cycle completed")
                
                # Wait 24 hours before next cycle
                await asyncio.sleep(24 * 60 * 60)
                
            except asyncio.CancelledError:
                logger.info("Kenya Law crawling cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Kenya Law crawling: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
                
    async def _periodic_parliament_crawl(self):
        """Periodically crawl Parliament resources"""
        while self.is_running:
            try:
                logger.info("Starting Parliament crawling cycle")
                
                await self.parliament_crawler.crawl_hansard()
                await asyncio.sleep(60)
                
                await self.parliament_crawler.crawl_bills()
                await asyncio.sleep(60)
                
                logger.info("Parliament crawling cycle completed")
                
                # Wait 24 hours before next cycle
                await asyncio.sleep(24 * 60 * 60)
                
            except asyncio.CancelledError:
                logger.info("Parliament crawling cancelled")
                break
            except Exception as e:
                logger.error(f"Error in Parliament crawling: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
                
    async def crawl_specific_url(self, url: str, source: str = "manual") -> Optional[Dict[str, Any]]:
        """Crawl a specific URL and extract content"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Extract text content using trafilatura
                text_content = trafilatura.extract(response.text)
                
                if not text_content:
                    logger.warning(f"No text content extracted from {url}")
                    return None
                
                # Parse HTML for additional metadata
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.find('title')
                title_text = title.text.strip() if title else "Untitled"
                
                # Extract metadata
                metadata = {
                    'url': url,
                    'title': title_text,
                    'content': text_content,
                    'source': source,
                    'crawled_at': datetime.utcnow().isoformat(),
                    'content_length': len(text_content),
                    'word_count': len(text_content.split())
                }
                
                # Save to database
                await self.document_service.create_document_from_crawl(metadata)
                
                return metadata
                
        except Exception as e:
            logger.error(f"Error crawling URL {url}: {e}")
            return None
            
    async def get_crawl_status(self) -> Dict[str, Any]:
        """Get current crawling status"""
        db = SessionLocal()
        try:
            # Get recent crawl statistics
            recent_docs = db.query(Document).filter(
                Document.created_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            total_docs = db.query(Document).count()
            
            return {
                'is_running': self.is_running,
                'active_tasks': len(self.crawl_tasks),
                'recent_documents': recent_docs,
                'total_documents': total_docs,
                'last_update': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting crawl status: {e}")
            return {
                'is_running': self.is_running,
                'error': str(e)
            }
        finally:
            db.close()
            
    async def search_and_crawl(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for legal documents and crawl them"""
        results = []
        
        try:
            # Search Kenya Law
            kenya_results = await self.kenya_law_crawler.search_documents(query, max_results // 2)
            results.extend(kenya_results)
            
            # Search Parliament
            parliament_results = await self.parliament_crawler.search_documents(query, max_results // 2)
            results.extend(parliament_results)
            
            # Crawl each result
            crawled_results = []
            for result in results[:max_results]:
                crawled_data = await self.crawl_specific_url(result['url'], result['source'])
                if crawled_data:
                    crawled_results.append(crawled_data)
                    
                # Rate limiting
                await asyncio.sleep(settings.CRAWLER_DELAY)
                
            return crawled_results
            
        except Exception as e:
            logger.error(f"Error in search and crawl: {e}")
            return []
