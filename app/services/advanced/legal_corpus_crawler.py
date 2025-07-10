import logging
import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import re
from datetime import datetime
import aiohttp
from urllib.parse import urljoin, urlparse
import time

# Optional imports
try:
    from trafilatura import extract, fetch_url
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

try:
    from newspaper import Article
    HAS_NEWSPAPER = True
except ImportError:
    HAS_NEWSPAPER = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from app.config import settings
from app.services.advanced.legal_rag import LegalRAGService
from app.services.advanced.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

class LegalCorpusCrawler:
    """Advanced crawler for building legal knowledge base"""
    
    def __init__(self, rag_service: LegalRAGService = None, doc_processor: DocumentProcessor = None):
        self.rag_service = rag_service or LegalRAGService()
        self.doc_processor = doc_processor or DocumentProcessor()
        
        # Kenyan legal sources
        self.legal_sources = {
            "kenya_law_judgments": [
                "https://new.kenyalaw.org/judgments/",
                "https://new.kenyalaw.org/judgments/court-class/superior-courts/",
                "https://new.kenyalaw.org/judgments/court-class/subordinate-courts/",
                "https://new.kenyalaw.org/judgments/court-class/small-claims-court/",
                "https://new.kenyalaw.org/judgments/court-class/civil-and-human-rights-tribunals/",
                "https://new.kenyalaw.org/judgments/court-class/commercial-tribunals/",
                "https://new.kenyalaw.org/judgments/court-class/environment-and-land-tribunals/",
                "https://new.kenyalaw.org/judgments/court-class/intellectual-property-tribunals/",
                "https://new.kenyalaw.org/judgments/court-class/regional-and-international-courts/",
                "https://new.kenyalaw.org/judgments/court-class/tribunals/"
            ],
            "kenya_law_legislation": [
                "https://new.kenyalaw.org/legislation/",
                "https://new.kenyalaw.org/akn/ke/act/2010/constitution/eng@2010-09-03",
                "https://new.kenyalaw.org/taxonomy/collections/collections-treaties",
                "https://new.kenyalaw.org/taxonomy/foreign-legislation/foreign-legislation-east-african-community-eac",
                "https://new.kenyalaw.org/legislation/counties"
            ],
            "kenya_law_publications": [
                "https://new.kenyalaw.org/taxonomy/publications/",
                "https://new.kenyalaw.org/taxonomy/publications/publications-commission-reports",
                "https://new.kenyalaw.org/taxonomy/publications/publications-case-digests",
                "https://new.kenyalaw.org/taxonomy/publications/publications-bench-bulletin",
                "https://new.kenyalaw.org/taxonomy/publications/publications-journals",
                "https://new.kenyalaw.org/taxonomy/publications/publications-kenya-law-news",
                "https://new.kenyalaw.org/taxonomy/publications/publications-law-related-articles",
                "https://new.kenyalaw.org/taxonomy/publications/publications-weekly-newsletter"
            ],
            "kenya_law_other": [
                "https://new.kenyalaw.org/causelists/",
                "https://new.kenyalaw.org/gazettes/",
                "https://new.kenyalaw.org/bills/"
            ],
            "parliament": [
                "http://www.parliament.go.ke/the-national-assembly/committees",
                "http://parliament.go.ke/2025-2026-budget-documents",
                "http://parliament.go.ke/"
            ]
        }
        
        # Crawling configuration
        self.max_concurrent_requests = 5
        self.request_delay = 2.0  # seconds between requests
        self.max_retries = 3
        self.timeout = 30
        self.max_pages_per_source = 50
        
        # Content filtering
        self.min_content_length = 500
        self.max_content_length = 100000
        
        # Statistics
        self.stats = {
            "total_urls_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "documents_ingested": 0,
            "errors": []
        }
        
        self._session = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the crawler"""
        if self._initialized:
            return
        
        try:
            logger.info("Initializing Legal Corpus Crawler...")
            
            # Initialize HTTP session
            connector = aiohttp.TCPConnector(limit=self.max_concurrent_requests)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'LegalizeMe-Crawler/1.0 (Educational Legal Research)'
                }
            )
            
            # Initialize services
            await self.rag_service.initialize()
            await self.doc_processor.initialize()
            
            self._initialized = True
            logger.info("Legal Corpus Crawler initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Legal Corpus Crawler: {e}")
            raise
    
    async def crawl_all_sources(self, max_documents: int = 1000) -> Dict[str, Any]:
        """Crawl all legal sources and build corpus"""
        if not self._initialized:
            await self.initialize()
        
        try:
            logger.info(f"Starting comprehensive legal corpus crawl (max {max_documents} documents)")
            
            all_documents = []
            documents_per_category = max_documents // len(self.legal_sources)
            
            # Crawl each category
            for category, urls in self.legal_sources.items():
                logger.info(f"Crawling category: {category}")
                
                category_docs = await self._crawl_category(
                    category, urls, documents_per_category
                )
                all_documents.extend(category_docs)
                
                # Rate limiting between categories
                await asyncio.sleep(self.request_delay)
            
            # Ingest documents into RAG system
            ingestion_results = await self._ingest_documents(all_documents)
            
            # Save corpus to local files
            await self._save_corpus_locally(all_documents)
            
            final_stats = {
                **self.stats,
                "total_documents_crawled": len(all_documents),
                "ingestion_results": ingestion_results,
                "crawl_completed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Corpus crawl completed: {final_stats}")
            return final_stats
            
        except Exception as e:
            logger.error(f"Error in comprehensive crawl: {e}")
            return {"error": str(e), "stats": self.stats}
        finally:
            if self._session:
                await self._session.close()
    
    async def _crawl_category(self, category: str, urls: List[str], max_docs: int) -> List[Dict[str, Any]]:
        """Crawl a specific category of legal sources"""
        documents = []
        
        try:
            # Create semaphore for concurrent requests
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            # Crawl each URL in the category
            tasks = []
            for url in urls:
                if len(documents) >= max_docs:
                    break
                
                task = self._crawl_url_with_semaphore(semaphore, url, category)
                tasks.append(task)
            
            # Execute tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Crawl task failed: {result}")
                    self.stats["failed_extractions"] += 1
                elif result and isinstance(result, list):
                    documents.extend(result)
                    if len(documents) >= max_docs:
                        documents = documents[:max_docs]
                        break
            
            logger.info(f"Category {category}: crawled {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error crawling category {category}: {e}")
            return []
    
    async def _crawl_url_with_semaphore(self, semaphore: asyncio.Semaphore, url: str, category: str) -> List[Dict[str, Any]]:
        """Crawl a single URL with semaphore control"""
        async with semaphore:
            return await self._crawl_single_url(url, category)
    
    async def _crawl_single_url(self, url: str, category: str) -> List[Dict[str, Any]]:
        """Crawl a single URL and extract documents"""
        documents = []
        
        try:
            self.stats["total_urls_processed"] += 1
            
            # Fetch page content
            content = await self._fetch_page_content(url)
            if not content:
                return []
            
            # Extract document links from the page
            document_links = self._extract_document_links(content, url)
            
            # Process each document link
            for doc_url in document_links[:self.max_pages_per_source]:
                try:
                    doc_content = await self._fetch_page_content(doc_url)
                    if doc_content:
                        # Extract and clean text
                        extracted_text = self._extract_text_content(doc_content)
                        
                        if self._is_valid_content(extracted_text):
                            # Create document metadata
                            doc_metadata = self._create_document_metadata(
                                doc_url, extracted_text, category
                            )
                            documents.append(doc_metadata)
                            self.stats["successful_extractions"] += 1
                        
                    # Rate limiting
                    await asyncio.sleep(self.request_delay)
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc_url}: {e}")
                    self.stats["failed_extractions"] += 1
                    self.stats["errors"].append(f"Document {doc_url}: {str(e)}")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error crawling URL {url}: {e}")
            self.stats["failed_extractions"] += 1
            self.stats["errors"].append(f"URL {url}: {str(e)}")
            return []
    
    async def _fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch content from a URL"""
        for attempt in range(self.max_retries):
            try:
                async with self._session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def _extract_document_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract document links from HTML content"""
        links = []
        
        try:
            if not HAS_BS4:
                logger.warning("BeautifulSoup not available, limited link extraction")
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for various types of document links
            link_selectors = [
                'a[href*="/judgment"]',
                'a[href*="/case"]',
                'a[href*="/act"]',
                'a[href*="/bill"]',
                'a[href*="/legislation"]',
                'a[href*="/gazette"]',
                'a[href*="/publication"]',
                'a[href$=".pdf"]',
                'a[href$=".doc"]',
                'a[href$=".docx"]'
            ]
            
            for selector in link_selectors:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        if self._is_valid_document_url(full_url):
                            links.append(full_url)
            
            # Remove duplicates and limit
            return list(set(links))[:self.max_pages_per_source]
            
        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            return []
    
    def _extract_text_content(self, html_content: str) -> str:
        """Extract clean text content from HTML"""
        try:
            # Try trafilatura first (best for content extraction)
            if HAS_TRAFILATURA:
                extracted = extract(html_content)
                if extracted and len(extracted.strip()) > self.min_content_length:
                    return extracted
            
            # Fallback to BeautifulSoup
            if HAS_BS4:
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text
            
            # Basic fallback - strip HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text content: {e}")
            return ""
    
    def _is_valid_document_url(self, url: str) -> bool:
        """Check if URL is a valid document URL"""
        try:
            parsed = urlparse(url)
            
            # Must be from trusted domains
            trusted_domains = ['kenyalaw.org', 'parliament.go.ke']
            if not any(domain in parsed.netloc for domain in trusted_domains):
                return False
            
            # Should not be navigation or search pages
            invalid_patterns = [
                '/search', '/login', '/register', '/contact',
                '/about', '/help', '/sitemap', '/rss'
            ]
            
            if any(pattern in url.lower() for pattern in invalid_patterns):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _is_valid_content(self, content: str) -> bool:
        """Check if content is valid for ingestion"""
        if not content or not content.strip():
            return False
        
        content_length = len(content)
        if content_length < self.min_content_length or content_length > self.max_content_length:
            return False
        
        # Check for legal content indicators
        legal_indicators = [
            'section', 'article', 'act', 'law', 'court', 'judgment',
            'legal', 'constitution', 'statute', 'regulation', 'kenya'
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for indicator in legal_indicators if indicator in content_lower)
        
        return indicator_count >= 2  # Must have at least 2 legal indicators
    
    def _create_document_metadata(self, url: str, content: str, category: str) -> Dict[str, Any]:
        """Create document metadata"""
        # Extract title from content
        title = self._extract_title(content, url)
        
        # Determine document type
        doc_type = self._determine_document_type(content, url)
        
        return {
            "title": title,
            "content": content,
            "url": url,
            "source": "legal_corpus_crawler",
            "document_type": doc_type,
            "category": category,
            "word_count": len(content.split()),
            "crawled_at": datetime.utcnow().isoformat(),
            "jurisdiction": "kenya"
        }
    
    def _extract_title(self, content: str, url: str) -> str:
        """Extract title from content or URL"""
        try:
            # Try to find title in first few lines
            lines = content.split('\n')[:10]
            for line in lines:
                line = line.strip()
                if len(line) > 10 and len(line) < 200:
                    # Check if it looks like a title
                    if any(keyword in line.lower() for keyword in ['act', 'case', 'judgment', 'constitution']):
                        return line
            
            # Fallback to URL-based title
            path = urlparse(url).path
            title = path.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            return title if title else "Legal Document"
            
        except Exception:
            return "Legal Document"
    
    def _determine_document_type(self, content: str, url: str) -> str:
        """Determine document type from content and URL"""
        content_lower = content.lower()
        url_lower = url.lower()
        
        if 'constitution' in content_lower or 'constitution' in url_lower:
            return 'constitution'
        elif any(term in content_lower for term in ['judgment', 'ruling', 'court']) or 'judgment' in url_lower:
            return 'judgment'
        elif any(term in content_lower for term in ['act', 'statute']) or 'act' in url_lower:
            return 'legislation'
        elif 'gazette' in content_lower or 'gazette' in url_lower:
            return 'gazette'
        elif 'bill' in url_lower:
            return 'bill'
        else:
            return 'legal_document'

    async def _ingest_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest documents into RAG system"""
        results = {
            "total_documents": len(documents),
            "successful_ingestions": 0,
            "failed_ingestions": 0,
            "errors": []
        }

        try:
            for doc in documents:
                # Create temporary document object
                temp_doc = type('Document', (), {
                    'id': abs(hash(doc['url'])),  # Use positive integer ID
                    'title': doc['title'],
                    'content': doc['content'],
                    'source': doc['source'],
                    'document_type': doc['document_type'],
                    'url': doc['url'],
                    'category': doc['category'],
                    'jurisdiction': doc.get('jurisdiction', 'kenya'),
                    'created_at': datetime.utcnow(),
                    'word_count': doc['word_count'],
                    'tags': [],
                    'subcategory': None,
                    'language': 'en',
                    'readability_score': None,
                    'embedding': None,
                    'embedding_model': None,
                    'is_processed': False,
                    'is_indexed': False,
                    'processing_status': 'pending',
                    'error_message': None,
                    'updated_at': None,
                    'last_indexed': None,
                    'relevance_score': None
                })()

                # Ingest document
                success = await self.rag_service.ingest_document(temp_doc)
                if success:
                    results["successful_ingestions"] += 1
                    self.stats["documents_ingested"] += 1
                else:
                    results["failed_ingestions"] += 1
                    results["errors"].append(f"Failed to ingest {doc['title']}")

            return results

        except Exception as e:
            logger.error(f"Error ingesting documents: {e}")
            results["error"] = str(e)
            return results

    async def _save_corpus_locally(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Save corpus to local files"""
        results = {
            "total_documents": len(documents),
            "saved_documents": 0,
            "failed_saves": 0
        }

        try:
            # Create corpus directory
            corpus_dir = Path("data/legal_corpus")
            corpus_dir.mkdir(exist_ok=True, parents=True)

            # Create category subdirectories
            categories = set(doc['category'] for doc in documents)
            for category in categories:
                category_dir = corpus_dir / category.replace("/", "_")
                category_dir.mkdir(exist_ok=True)

            # Save each document
            for doc in documents:
                try:
                    # Create safe filename
                    safe_title = re.sub(r'[^\w\s-]', '', doc['title'])
                    safe_title = re.sub(r'[-\s]+', '_', safe_title).strip('-_')

                    # Limit filename length
                    if len(safe_title) > 100:
                        safe_title = safe_title[:100]

                    # Create category path
                    category_path = corpus_dir / doc['category'].replace("/", "_")

                    # Create file path
                    file_path = category_path / f"{safe_title}.txt"

                    # Save content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(doc['content'])

                    # Save metadata
                    metadata_path = category_path / f"{safe_title}_metadata.json"
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        # Create metadata without content (to save space)
                        metadata = {k: v for k, v in doc.items() if k != 'content'}
                        json.dump(metadata, f, indent=2)

                    results["saved_documents"] += 1

                except Exception as e:
                    logger.error(f"Error saving document {doc.get('title', 'unknown')}: {e}")
                    results["failed_saves"] += 1

            return results

        except Exception as e:
            logger.error(f"Error saving corpus: {e}")
            results["error"] = str(e)
            return results

    async def crawl_specific_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Crawl a specific URL and extract content"""
        if not self._initialized:
            await self.initialize()

        try:
            # Create session if needed
            if not self._session:
                connector = aiohttp.TCPConnector(limit=1)
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'LegalizeMe-Crawler/1.0 (Educational Legal Research)'
                    }
                )

            # Fetch content
            content = await self._fetch_page_content(url)
            if not content:
                return None

            # Extract text
            extracted_text = self._extract_text_content(content)
            if not self._is_valid_content(extracted_text):
                return None

            # Determine category
            category = self._determine_category(url)

            # Create document metadata
            doc_metadata = self._create_document_metadata(url, extracted_text, category)

            # Ingest document
            temp_doc = type('Document', (), {
                'id': abs(hash(url)),  # Use positive integer ID
                'title': doc_metadata['title'],
                'content': doc_metadata['content'],
                'source': doc_metadata['source'],
                'document_type': doc_metadata['document_type'],
                'url': doc_metadata['url'],
                'category': doc_metadata['category'],
                'jurisdiction': doc_metadata.get('jurisdiction', 'kenya'),
                'created_at': datetime.utcnow(),
                'word_count': doc_metadata['word_count'],
                'tags': [],
                'subcategory': None,
                'language': 'en',
                'readability_score': None,
                'embedding': None,
                'embedding_model': None,
                'is_processed': False,
                'is_indexed': False,
                'processing_status': 'pending',
                'error_message': None,
                'updated_at': None,
                'last_indexed': None,
                'relevance_score': None
            })()

            await self.rag_service.ingest_document(temp_doc)

            return doc_metadata

        except Exception as e:
            logger.error(f"Error crawling specific URL {url}: {e}")
            return None
        finally:
            if self._session:
                await self._session.close()
                self._session = None

    def _determine_category(self, url: str) -> str:
        """Determine category from URL"""
        url_lower = url.lower()

        for category, urls in self.legal_sources.items():
            for base_url in urls:
                if url_lower.startswith(base_url.lower()):
                    return category

        # Fallback categorization
        if 'judgment' in url_lower:
            return 'kenya_law_judgments'
        elif 'legislation' in url_lower or 'act' in url_lower:
            return 'kenya_law_legislation'
        elif 'publication' in url_lower:
            return 'kenya_law_publications'
        elif 'parliament' in url_lower:
            return 'parliament'
        else:
            return 'kenya_law_other'

    async def search_and_crawl(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for legal documents and crawl them"""
        if not self._initialized:
            await self.initialize()

        try:
            # Create session if needed
            if not self._session:
                connector = aiohttp.TCPConnector(limit=self.max_concurrent_requests)
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'LegalizeMe-Crawler/1.0 (Educational Legal Research)'
                    }
                )

            # Search Kenya Law
            search_url = f"https://new.kenyalaw.org/search/?q={query}"
            content = await self._fetch_page_content(search_url)

            if not content:
                return []

            # Extract search result links
            result_links = self._extract_document_links(content, search_url)

            # Crawl each result
            documents = []
            for url in result_links[:max_results]:
                doc = await self.crawl_specific_url(url)
                if doc:
                    documents.append(doc)

                # Rate limiting
                await asyncio.sleep(self.request_delay)

            return documents

        except Exception as e:
            logger.error(f"Error in search and crawl for '{query}': {e}")
            return []
        finally:
            if self._session:
                await self._session.close()
                self._session = None

    def get_stats(self) -> Dict[str, Any]:
        """Get crawler statistics"""
        return {
            **self.stats,
            "initialized": self._initialized,
            "has_trafilatura": HAS_TRAFILATURA,
            "has_newspaper": HAS_NEWSPAPER,
            "has_bs4": HAS_BS4
        }
