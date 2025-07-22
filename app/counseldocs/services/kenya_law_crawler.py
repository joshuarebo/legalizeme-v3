"""
Kenya Law Crawler Service for CounselDocs
Comprehensive crawler for Kenya Law portal and related legal sources.
Extracts legal content, PDFs, and citations for compliance analysis.
"""

import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json
import hashlib

import aiohttp
import boto3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import PyPDF2
import tempfile
import os

from app.config import settings

logger = logging.getLogger(__name__)

class KenyaLawCrawler:
    """
    Comprehensive crawler for Kenya Law portal and legal sources.
    Extracts judgments, legislation, constitution, and other legal documents.
    """
    
    # Kenya Law URLs to crawl
    KENYA_LAW_URLS = [
        # Judgments
        "https://new.kenyalaw.org/judgments/",
        "https://new.kenyalaw.org/judgments/court-class/superior-courts/",
        "https://new.kenyalaw.org/judgments/court-class/subordinate-courts/",
        "https://new.kenyalaw.org/judgments/court-class/small-claims-court/",
        "https://new.kenyalaw.org/judgments/court-class/civil-and-human-rights-tribunals/",
        "https://new.kenyalaw.org/judgments/court-class/commercial-tribunals/",
        "https://new.kenyalaw.org/judgments/court-class/environment-and-land-tribunals/",
        "https://new.kenyalaw.org/judgments/court-class/intellectual-property-tribunals/",
        "https://new.kenyalaw.org/judgments/court-class/regional-and-international-courts/",
        "https://new.kenyalaw.org/judgments/court-class/tribunals/",
        
        # Constitution and Legislation
        "https://new.kenyalaw.org/akn/ke/act/2010/constitution/eng@2010-09-03",
        "https://new.kenyalaw.org/legislation/",
        "https://new.kenyalaw.org/legislation/counties",
        
        # Treaties and International
        "https://new.kenyalaw.org/taxonomy/collections/collections-treaties",
        "https://new.kenyalaw.org/taxonomy/foreign-legislation/foreign-legislation-east-african-community-eac",
        
        # Legal Documents
        "https://new.kenyalaw.org/causelists/",
        "https://new.kenyalaw.org/gazettes/",
        "https://new.kenyalaw.org/bills/",
        
        # Publications
        "https://new.kenyalaw.org/taxonomy/publications/publications-commission-reports",
        "https://new.kenyalaw.org/taxonomy/publications/publications-case-digests",
        "https://new.kenyalaw.org/taxonomy/publications/publications-bench-bulletin",
        "https://new.kenyalaw.org/taxonomy/publications/publications-journals",
        "https://new.kenyalaw.org/taxonomy/publications/publications-kenya-law-news",
        "https://new.kenyalaw.org/taxonomy/publications/publications-law-related-articles",
        "https://new.kenyalaw.org/taxonomy/publications/publications-weekly-newsletter",
        
        # Parliament
        "http://www.parliament.go.ke/the-national-assembly/committees",
        "http://parliament.go.ke/2025-2026-budget-documents"
    ]
    
    def __init__(self):
        """Initialize crawler with AWS services"""
        self.session = None
        self.crawled_urls: Set[str] = set()
        self.legal_documents: List[Dict[str, Any]] = []
        self.citations_database: Dict[str, Any] = {}
        
        # AWS S3 for storing crawled content
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Bedrock for embeddings
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        self.s3_bucket = "counseldocs-legal-corpus"
        self._ensure_s3_bucket()
    
    def _ensure_s3_bucket(self):
        """Ensure S3 bucket exists for legal corpus storage"""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except Exception:
            try:
                # For us-east-1, don't specify LocationConstraint
                if settings.AWS_REGION == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=self.s3_bucket)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.s3_bucket,
                        CreateBucketConfiguration={'LocationConstraint': settings.AWS_REGION}
                    )
                logger.info(f"Created S3 bucket: {self.s3_bucket}")
            except Exception as e:
                logger.error(f"Failed to create S3 bucket: {e}")
    
    async def crawl_all_sources(self) -> Dict[str, Any]:
        """
        Crawl all Kenya Law sources and extract legal content.
        
        Returns:
            Dict with crawling results and statistics
        """
        start_time = datetime.utcnow()
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'CounselDocs Legal Crawler 1.0'}
        ) as session:
            self.session = session
            
            crawl_results = {
                'documents_found': 0,
                'pdfs_processed': 0,
                'citations_extracted': 0,
                'errors': [],
                'crawled_urls': [],
                'processing_time': 0
            }
            
            # Crawl each source
            for url in self.KENYA_LAW_URLS:
                try:
                    logger.info(f"Crawling: {url}")
                    result = await self._crawl_url(url)
                    
                    crawl_results['documents_found'] += result.get('documents_found', 0)
                    crawl_results['pdfs_processed'] += result.get('pdfs_processed', 0)
                    crawl_results['citations_extracted'] += result.get('citations_extracted', 0)
                    crawl_results['crawled_urls'].append(url)
                    
                    # Small delay to be respectful
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    error_msg = f"Failed to crawl {url}: {str(e)}"
                    logger.error(error_msg)
                    crawl_results['errors'].append(error_msg)
            
            # Process and store results
            await self._process_and_store_results()
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            crawl_results['processing_time'] = processing_time
            
            logger.info(f"Crawling completed in {processing_time:.2f}s")
            return crawl_results
    
    async def _crawl_url(self, url: str) -> Dict[str, Any]:
        """Crawl a specific URL and extract legal content"""
        
        if url in self.crawled_urls:
            return {'documents_found': 0, 'pdfs_processed': 0, 'citations_extracted': 0}
        
        self.crawled_urls.add(url)
        result = {'documents_found': 0, 'pdfs_processed': 0, 'citations_extracted': 0}
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return result
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract document links
                document_links = self._extract_document_links(soup, url)
                result['documents_found'] = len(document_links)
                
                # Process each document
                for link_info in document_links:
                    try:
                        doc_result = await self._process_document_link(link_info)
                        if doc_result.get('is_pdf'):
                            result['pdfs_processed'] += 1
                        result['citations_extracted'] += doc_result.get('citations_count', 0)
                    except Exception as e:
                        logger.error(f"Failed to process document {link_info['url']}: {e}")
                
                # Extract citations from page content
                page_citations = self._extract_citations_from_content(content, url)
                result['citations_extracted'] += len(page_citations)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to crawl {url}: {e}")
            return result
    
    def _extract_document_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract document links from page"""
        
        links = []
        
        # Look for PDF links
        pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
        for link in pdf_links:
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                links.append({
                    'url': full_url,
                    'text': link.get_text(strip=True),
                    'type': 'pdf'
                })
        
        # Look for document pages
        doc_links = soup.find_all('a', href=re.compile(r'/(act|judgment|bill|gazette)/', re.I))
        for link in doc_links:
            href = link.get('href')
            if href and href not in [l['url'] for l in links]:
                full_url = urljoin(base_url, href)
                links.append({
                    'url': full_url,
                    'text': link.get_text(strip=True),
                    'type': 'document'
                })
        
        return links[:50]  # Limit to prevent overwhelming
    
    async def _process_document_link(self, link_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual document link"""
        
        result = {'is_pdf': False, 'citations_count': 0, 'content_extracted': False}
        
        try:
            async with self.session.get(link_info['url']) as response:
                if response.status != 200:
                    return result
                
                content_type = response.headers.get('content-type', '').lower()
                
                if 'pdf' in content_type or link_info['type'] == 'pdf':
                    # Process PDF
                    pdf_content = await response.read()
                    pdf_result = await self._process_pdf_content(pdf_content, link_info['url'])
                    result.update(pdf_result)
                    result['is_pdf'] = True
                    
                else:
                    # Process HTML document
                    html_content = await response.text()
                    html_result = await self._process_html_document(html_content, link_info['url'])
                    result.update(html_result)
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to process document {link_info['url']}: {e}")
            return result
    
    async def _process_pdf_content(self, pdf_content: bytes, url: str) -> Dict[str, Any]:
        """Extract text and citations from PDF"""
        
        result = {'citations_count': 0, 'content_extracted': False}
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file.flush()
                
                # Extract text from PDF
                with open(temp_file.name, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    text_content = ""
                    
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
                
                if text_content.strip():
                    # Extract citations
                    citations = self._extract_citations_from_content(text_content, url)
                    result['citations_count'] = len(citations)
                    
                    # Store document
                    await self._store_legal_document({
                        'url': url,
                        'content': text_content,
                        'type': 'pdf',
                        'citations': citations,
                        'extracted_at': datetime.utcnow().isoformat()
                    })
                    
                    result['content_extracted'] = True
                
                # Cleanup
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.error(f"PDF processing failed for {url}: {e}")

        return result

    async def _process_html_document(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract content and citations from HTML document"""

        result = {'citations_count': 0, 'content_extracted': False}

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Extract text content
            text_content = soup.get_text()

            # Clean up text
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text_content = '\n'.join(chunk for chunk in chunks if chunk)

            if text_content.strip():
                # Extract citations
                citations = self._extract_citations_from_content(text_content, url)
                result['citations_count'] = len(citations)

                # Store document
                await self._store_legal_document({
                    'url': url,
                    'content': text_content,
                    'type': 'html',
                    'citations': citations,
                    'extracted_at': datetime.utcnow().isoformat()
                })

                result['content_extracted'] = True

        except Exception as e:
            logger.error(f"HTML processing failed for {url}: {e}")

        return result

    def _extract_citations_from_content(self, content: str, source_url: str) -> List[Dict[str, Any]]:
        """Extract legal citations from content"""

        citations = []

        # Citation patterns for Kenyan law
        citation_patterns = [
            # Acts and Statutes
            r'([A-Z][a-zA-Z\s]+Act,?\s*(?:No\.?\s*\d+\s*of\s*)?\d{4})',
            r'(Constitution of Kenya,?\s*\d{4})',
            r'(Employment Act,?\s*\d{4})',
            r'(Companies Act,?\s*\d{4})',

            # Case citations
            r'([A-Z][a-zA-Z\s]+v\.?\s+[A-Z][a-zA-Z\s]+\s*\[\d{4}\])',
            r'([A-Z][a-zA-Z\s]+v\.?\s+[A-Z][a-zA-Z\s]+\s*\(\d{4}\))',

            # Section references
            r'(Section\s+\d+[a-z]?(?:\(\d+\))?(?:\([a-z]\))?)',
            r'(Article\s+\d+[a-z]?(?:\(\d+\))?(?:\([a-z]\))?)',

            # Legal Notice references
            r'(Legal Notice No\.?\s*\d+\s*of\s*\d{4})',

            # Gazette references
            r'(Kenya Gazette\s+(?:Supplement\s+)?No\.?\s*\d+)',
        ]

        for pattern in citation_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                citation_text = match.group(1).strip()

                # Create citation entry
                citation = {
                    'text': citation_text,
                    'source_url': source_url,
                    'type': self._classify_citation(citation_text),
                    'position': match.start(),
                    'confidence': self._calculate_citation_confidence(citation_text),
                    'extracted_at': datetime.utcnow().isoformat()
                }

                citations.append(citation)

        # Remove duplicates
        unique_citations = []
        seen_texts = set()
        for citation in citations:
            if citation['text'] not in seen_texts:
                unique_citations.append(citation)
                seen_texts.add(citation['text'])

        return unique_citations

    def _classify_citation(self, citation_text: str) -> str:
        """Classify the type of legal citation"""

        citation_lower = citation_text.lower()

        if 'constitution' in citation_lower:
            return 'constitution'
        elif 'act' in citation_lower:
            return 'act'
        elif 'section' in citation_lower:
            return 'section'
        elif 'article' in citation_lower:
            return 'article'
        elif 'v.' in citation_lower or ' v ' in citation_lower:
            return 'case'
        elif 'legal notice' in citation_lower:
            return 'legal_notice'
        elif 'gazette' in citation_lower:
            return 'gazette'
        else:
            return 'other'

    def _calculate_citation_confidence(self, citation_text: str) -> float:
        """Calculate confidence score for citation accuracy"""

        confidence = 0.5  # Base confidence

        # Increase confidence for specific patterns
        if re.search(r'\d{4}', citation_text):  # Contains year
            confidence += 0.2
        if re.search(r'No\.?\s*\d+', citation_text):  # Contains number
            confidence += 0.2
        if len(citation_text.split()) >= 3:  # Reasonable length
            confidence += 0.1

        # Known important acts
        important_acts = ['employment act', 'constitution', 'companies act', 'civil procedure']
        if any(act in citation_text.lower() for act in important_acts):
            confidence += 0.2

        return min(confidence, 1.0)

# Global instance
kenya_law_crawler = KenyaLawCrawler()
