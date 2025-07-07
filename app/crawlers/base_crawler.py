import asyncio
import logging
from typing import List, Dict, Optional, Any
import httpx
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin, urlparse, parse_qs
import time
from datetime import datetime, timedelta
import json
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)

class BaseCrawler(ABC):
    """Base class for web crawlers"""
    
    def __init__(self, base_url: str, name: str):
        self.base_url = base_url
        self.name = name
        self.session = None
        self.crawl_delay = settings.CRAWLER_DELAY
        self.max_concurrent_requests = settings.MAX_CONCURRENT_REQUESTS
        self.last_request_time = 0
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Common headers to avoid being blocked
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Rate limiting
        self.rate_limit_requests = 100
        self.rate_limit_window = 3600  # 1 hour
        self.request_times = []
    
    async def _ensure_session(self):
        """Ensure HTTP session is available"""
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers=self.headers,
                follow_redirects=True
            )
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        
        # Clean old requests
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < self.rate_limit_window
        ]
        
        # Check if we're hitting rate limits
        if len(self.request_times) >= self.rate_limit_requests:
            sleep_time = self.rate_limit_window - (current_time - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
        
        # Ensure minimum delay between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.crawl_delay:
            await asyncio.sleep(self.crawl_delay - time_since_last)
        
        self.last_request_time = time.time()
        self.request_times.append(self.last_request_time)
    
    async def _make_request(self, url: str, retries: int = 3) -> Optional[httpx.Response]:
        """Make HTTP request with rate limiting and retries"""
        await self._ensure_session()
        
        async with self.semaphore:
            await self._rate_limit()
            
            for attempt in range(retries + 1):
                try:
                    logger.debug(f"Making request to {url} (attempt {attempt + 1})")
                    response = await self.session.get(url)
                    
                    if response.status_code == 200:
                        return response
                    elif response.status_code == 429:
                        # Rate limited, wait longer
                        wait_time = (2 ** attempt) * self.crawl_delay
                        logger.warning(f"Rate limited, waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status_code in [404, 403]:
                        logger.warning(f"Request failed with status {response.status_code}: {url}")
                        return None
                    else:
                        logger.warning(f"Request failed with status {response.status_code}: {url}")
                        if attempt < retries:
                            await asyncio.sleep(self.crawl_delay * (attempt + 1))
                        continue
                        
                except httpx.TimeoutException:
                    logger.warning(f"Request timeout for {url} (attempt {attempt + 1})")
                    if attempt < retries:
                        await asyncio.sleep(self.crawl_delay * (attempt + 1))
                    continue
                except Exception as e:
                    logger.error(f"Request error for {url}: {e}")
                    if attempt < retries:
                        await asyncio.sleep(self.crawl_delay * (attempt + 1))
                    continue
            
            return None
    
    def _extract_text_content(self, html: str) -> Optional[str]:
        """Extract clean text content from HTML"""
        try:
            # Try trafilatura first (better for article content)
            text = trafilatura.extract(html)
            if text and len(text.strip()) > 100:
                return text
            
            # Fallback to BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text if len(text.strip()) > 50 else None
            
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return None
    
    def _extract_metadata(self, html: str, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            metadata = {
                'url': url,
                'title': '',
                'description': '',
                'keywords': [],
                'published_date': '',
                'author': '',
                'source': self.name
            }
            
            # Title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
            
            # Meta description
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                metadata['description'] = desc_tag.get('content', '').strip()
            
            # Meta keywords
            keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_tag:
                keywords = keywords_tag.get('content', '').strip()
                metadata['keywords'] = [k.strip() for k in keywords.split(',') if k.strip()]
            
            # Author
            author_tag = soup.find('meta', attrs={'name': 'author'})
            if author_tag:
                metadata['author'] = author_tag.get('content', '').strip()
            
            # Published date
            date_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="date"]',
                'meta[name="publish_date"]',
                'time[datetime]',
                '.date',
                '.published',
                '.publish-date'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    if date_elem.name == 'meta':
                        date_text = date_elem.get('content', '')
                    elif date_elem.name == 'time':
                        date_text = date_elem.get('datetime', '') or date_elem.get_text()
                    else:
                        date_text = date_elem.get_text()
                    
                    if date_text:
                        metadata['published_date'] = date_text.strip()
                        break
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and within scope"""
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(self.base_url)
            
            # Check if it's from the same domain
            if parsed.netloc != base_parsed.netloc:
                return False
            
            # Check for common non-content URLs
            excluded_patterns = [
                '/css/', '/js/', '/images/', '/img/', '/static/',
                '/assets/', '/media/', '/admin/', '/login/', '/logout/',
                '.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg',
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar'
            ]
            
            for pattern in excluded_patterns:
                if pattern in url.lower():
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract valid links from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(base_url, href)
                
                if self._is_valid_url(full_url):
                    links.append(full_url)
            
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return []
    
    async def crawl_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Crawl a single page and extract content"""
        try:
            logger.info(f"Crawling page: {url}")
            
            response = await self._make_request(url)
            if not response:
                return None
            
            html = response.text
            
            # Extract content
            text_content = self._extract_text_content(html)
            if not text_content:
                logger.warning(f"No text content extracted from {url}")
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(html, url)
            
            # Extract links
            links = self._extract_links(html, url)
            
            return {
                'url': url,
                'title': metadata.get('title', ''),
                'content': text_content,
                'metadata': metadata,
                'links': links,
                'crawled_at': datetime.utcnow().isoformat(),
                'source': self.name,
                'content_length': len(text_content),
                'word_count': len(text_content.split())
            }
            
        except Exception as e:
            logger.error(f"Error crawling page {url}: {e}")
            return None
    
    async def crawl_multiple_pages(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Crawl multiple pages concurrently"""
        try:
            tasks = [self.crawl_page(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None results and exceptions
            valid_results = []
            for result in results:
                if isinstance(result, dict):
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Crawling error: {result}")
            
            return valid_results
            
        except Exception as e:
            logger.error(f"Error crawling multiple pages: {e}")
            return []
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None
    
    @abstractmethod
    async def crawl_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl documents from the source"""
        pass
    
    @abstractmethod
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for documents"""
        pass
    
    @abstractmethod
    async def get_document_urls(self, limit: int = 100) -> List[str]:
        """Get list of document URLs to crawl"""
        pass
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.session:
            try:
                asyncio.create_task(self.close())
            except Exception:
                pass
