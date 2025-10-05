import asyncio
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs
import re
from datetime import datetime, timedelta
import json

from app.crawlers.base_crawler import BaseCrawler
from app.config import settings

logger = logging.getLogger(__name__)

class KenyaLawCrawler(BaseCrawler):
    """Crawler for Kenya Law website (https://new.kenyalaw.org)"""
    
    def __init__(self):
        super().__init__(settings.KENYA_LAW_BASE_URL, "kenya_law")
        
        # Section-specific URLs
        self.sections = {
            'judgments': f"{self.base_url}/judgments/",
            'legislation': f"{self.base_url}/legislation/",
            'gazettes': f"{self.base_url}/gazettes/",
            'legislation_counties': f"{self.base_url}/legislation/counties",
            'bills': f"{self.base_url}/bills/",
            'causelists': f"{self.base_url}/causelists/",
            'publications': f"{self.base_url}/taxonomy/publications/",
            'superior_courts': f"{self.base_url}/judgments/court-class/superior-courts/",
            'subordinate_courts': f"{self.base_url}/judgments/court-class/subordinate-courts/",
            'small_claims_court': f"{self.base_url}/judgments/court-class/small-claims-court/",
            'civil_human_rights_tribunals': f"{self.base_url}/judgments/court-class/civil-and-human-rights-tribunals/",
            'commercial_tribunals': f"{self.base_url}/judgments/court-class/commercial-tribunals/",
            'environment_land_tribunals': f"{self.base_url}/judgments/court-class/environment-and-land-tribunals/",
            'intellectual_property_tribunals': f"{self.base_url}/judgments/court-class/intellectual-property-tribunals/",
            'regional_international_courts': f"{self.base_url}/judgments/court-class/regional-and-international-courts/",
            'tribunals': f"{self.base_url}/judgments/court-class/tribunals/"
        }
        
        # Document type mappings
        self.document_types = {
            'judgments': 'judgment',
            'legislation': 'legislation',
            'gazettes': 'gazette',
            'causelists': 'causelist',
            'publications': 'publication'
        }
    
    async def crawl_judgments(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl court judgments"""
        try:
            logger.info("Starting judgment crawling...")
            
            # Get judgment listing pages
            judgment_urls = await self._get_judgment_urls(limit)
            
            # Crawl each judgment
            results = []
            for url in judgment_urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'judgment'
                    result['category'] = 'legal_decision'
                    
                    # Extract judgment-specific metadata
                    judgment_metadata = self._extract_judgment_metadata(result.get('content', ''))
                    result['metadata'].update(judgment_metadata)
                    
                    results.append(result)
            
            logger.info(f"Crawled {len(results)} judgments")
            return results
            
        except Exception as e:
            logger.error(f"Error crawling judgments: {e}")
            return []
    
    async def crawl_legislation(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl legislation documents"""
        try:
            logger.info("Starting legislation crawling...")
            
            # Get legislation URLs
            legislation_urls = await self._get_legislation_urls(limit)
            
            # Crawl each legislation
            results = []
            for url in legislation_urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'legislation'
                    result['category'] = 'legal_statute'
                    
                    # Extract legislation-specific metadata
                    legislation_metadata = self._extract_legislation_metadata(result.get('content', ''))
                    result['metadata'].update(legislation_metadata)
                    
                    results.append(result)
            
            logger.info(f"Crawled {len(results)} legislation documents")
            return results
            
        except Exception as e:
            logger.error(f"Error crawling legislation: {e}")
            return []
    
    async def crawl_gazettes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl gazette documents"""
        try:
            logger.info("Starting gazette crawling...")
            
            # Get gazette URLs
            gazette_urls = await self._get_gazette_urls(limit)
            
            # Crawl each gazette
            results = []
            for url in gazette_urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'gazette'
                    result['category'] = 'government_notice'
                    
                    # Extract gazette-specific metadata
                    gazette_metadata = self._extract_gazette_metadata(result.get('content', ''))
                    result['metadata'].update(gazette_metadata)
                    
                    results.append(result)
            
            logger.info(f"Crawled {len(results)} gazette documents")
            return results
            
        except Exception as e:
            logger.error(f"Error crawling gazettes: {e}")
            return []
    
    async def _get_judgment_urls(self, limit: int) -> List[str]:
        """Get judgment URLs from listing pages"""
        urls = []
        try:
            # Main judgments page
            response = await self._make_request(self.sections['judgments'])
            if response:
                urls.extend(self._extract_judgment_urls_from_html(response.text))
            
            # Try pagination
            page = 1
            while len(urls) < limit and page <= 10:  # Limit to 10 pages
                page_url = f"{self.sections['judgments']}?page={page}"
                response = await self._make_request(page_url)
                if response:
                    page_urls = self._extract_judgment_urls_from_html(response.text)
                    if not page_urls:
                        break
                    urls.extend(page_urls)
                    page += 1
                else:
                    break
            
            return list(set(urls))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting judgment URLs: {e}")
            return []
    
    async def _get_legislation_urls(self, limit: int) -> List[str]:
        """Get legislation URLs from listing pages"""
        urls = []
        try:
            # Main legislation page
            response = await self._make_request(self.sections['legislation'])
            if response:
                urls.extend(self._extract_legislation_urls_from_html(response.text))
            
            # Try different categories
            categories = ['acts', 'bills', 'statutory-instruments', 'regulations']
            for category in categories:
                if len(urls) >= limit:
                    break
                    
                category_url = f"{self.sections['legislation']}{category}/"
                response = await self._make_request(category_url)
                if response:
                    urls.extend(self._extract_legislation_urls_from_html(response.text))
            
            return list(set(urls))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting legislation URLs: {e}")
            return []
    
    async def _get_gazette_urls(self, limit: int) -> List[str]:
        """Get gazette URLs from listing pages"""
        urls = []
        try:
            # Main gazettes page
            response = await self._make_request(self.sections['gazettes'])
            if response:
                urls.extend(self._extract_gazette_urls_from_html(response.text))
            
            # Try pagination
            page = 1
            while len(urls) < limit and page <= 5:  # Limit to 5 pages
                page_url = f"{self.sections['gazettes']}?page={page}"
                response = await self._make_request(page_url)
                if response:
                    page_urls = self._extract_gazette_urls_from_html(response.text)
                    if not page_urls:
                        break
                    urls.extend(page_urls)
                    page += 1
                else:
                    break
            
            return list(set(urls))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting gazette URLs: {e}")
            return []
    
    def _extract_judgment_urls_from_html(self, html: str) -> List[str]:
        """Extract judgment URLs from HTML"""
        urls = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for judgment links
            selectors = [
                'a[href*="/judgments/"]',
                'a[href*="/case/"]',
                'a[href*="/judgment/"]',
                '.judgment-link a',
                '.case-link a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if self._is_judgment_url(full_url):
                            urls.append(full_url)
            
            return list(set(urls))
            
        except Exception as e:
            logger.error(f"Error extracting judgment URLs: {e}")
            return []
    
    def _extract_legislation_urls_from_html(self, html: str) -> List[str]:
        """Extract legislation URLs from HTML"""
        urls = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for legislation links
            selectors = [
                'a[href*="/legislation/"]',
                'a[href*="/act/"]',
                'a[href*="/bill/"]',
                '.legislation-link a',
                '.act-link a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if self._is_legislation_url(full_url):
                            urls.append(full_url)
            
            return list(set(urls))
            
        except Exception as e:
            logger.error(f"Error extracting legislation URLs: {e}")
            return []
    
    def _extract_gazette_urls_from_html(self, html: str) -> List[str]:
        """Extract gazette URLs from HTML"""
        urls = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for gazette links
            selectors = [
                'a[href*="/gazettes/"]',
                'a[href*="/gazette/"]',
                '.gazette-link a',
                '.notice-link a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if self._is_gazette_url(full_url):
                            urls.append(full_url)
            
            return list(set(urls))
            
        except Exception as e:
            logger.error(f"Error extracting gazette URLs: {e}")
            return []
    
    def _is_judgment_url(self, url: str) -> bool:
        """Check if URL is a judgment document"""
        patterns = [
            r'/judgments?/[^/]+$',
            r'/case/[^/]+$',
            r'/judgment/[^/]+$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _is_legislation_url(self, url: str) -> bool:
        """Check if URL is a legislation document"""
        patterns = [
            r'/legislation/[^/]+$',
            r'/act/[^/]+$',
            r'/bill/[^/]+$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _is_gazette_url(self, url: str) -> bool:
        """Check if URL is a gazette document"""
        patterns = [
            r'/gazettes?/[^/]+$',
            r'/gazette/[^/]+$',
            r'/notice/[^/]+$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _extract_judgment_metadata(self, content: str) -> Dict[str, Any]:
        """Extract judgment-specific metadata"""
        metadata = {}
        
        try:
            # Extract case number
            case_pattern = r'(?:Case No\.?|Cause No\.?|Petition No\.?)\s*:?\s*([A-Z0-9\/\-\s]+)'
            case_match = re.search(case_pattern, content, re.IGNORECASE)
            if case_match:
                metadata['case_number'] = case_match.group(1).strip()
            
            # Extract court name
            court_pattern = r'(?:IN THE|BEFORE THE)\s+(.*?(?:COURT|TRIBUNAL))'
            court_match = re.search(court_pattern, content, re.IGNORECASE)
            if court_match:
                metadata['court_name'] = court_match.group(1).strip()
            
            # Extract judge names
            judge_pattern = r'(?:BEFORE|CORAM)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*,?\s*J\.?)'
            judge_matches = re.findall(judge_pattern, content, re.IGNORECASE)
            if judge_matches:
                metadata['judges'] = [judge.strip() for judge in judge_matches]
            
            # Extract parties
            parties_pattern = r'([A-Z][A-Z\s&]+)\s+(?:vs?\.?|V\.?)\s+([A-Z][A-Z\s&]+)'
            parties_match = re.search(parties_pattern, content)
            if parties_match:
                metadata['plaintiff'] = parties_match.group(1).strip()
                metadata['defendant'] = parties_match.group(2).strip()
            
            # Extract date
            date_pattern = r'(?:Delivered|Pronounced|Judgment delivered)\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})'
            date_match = re.search(date_pattern, content, re.IGNORECASE)
            if date_match:
                metadata['judgment_date'] = date_match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error extracting judgment metadata: {e}")
        
        return metadata
    
    def _extract_legislation_metadata(self, content: str) -> Dict[str, Any]:
        """Extract legislation-specific metadata"""
        metadata = {}
        
        try:
            # Extract act number
            act_pattern = r'(?:Act No\.?|Chapter)\s*:?\s*(\d+)\s*of\s*(\d{4})'
            act_match = re.search(act_pattern, content, re.IGNORECASE)
            if act_match:
                metadata['act_number'] = act_match.group(1)
                metadata['year'] = act_match.group(2)
            
            # Extract commencement date
            commencement_pattern = r'(?:Commencement|Effective)\s+(?:Date|from)\s*:?\s*(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})'
            commencement_match = re.search(commencement_pattern, content, re.IGNORECASE)
            if commencement_match:
                metadata['commencement_date'] = commencement_match.group(1).strip()
            
            # Extract assent date
            assent_pattern = r'(?:Assented to|Assent)\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})'
            assent_match = re.search(assent_pattern, content, re.IGNORECASE)
            if assent_match:
                metadata['assent_date'] = assent_match.group(1).strip()
            
            # Extract sections
            section_pattern = r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)'
            section_matches = re.findall(section_pattern, content, re.MULTILINE)
            if section_matches:
                metadata['sections'] = [
                    {'number': num, 'title': title.strip()} 
                    for num, title in section_matches[:20]  # Limit to first 20 sections
                ]
            
        except Exception as e:
            logger.error(f"Error extracting legislation metadata: {e}")
        
        return metadata
    
    def _extract_gazette_metadata(self, content: str) -> Dict[str, Any]:
        """Extract gazette-specific metadata"""
        metadata = {}
        
        try:
            # Extract gazette number
            gazette_pattern = r'(?:Gazette No\.?|Notice No\.?)\s*:?\s*(\d+)'
            gazette_match = re.search(gazette_pattern, content, re.IGNORECASE)
            if gazette_match:
                metadata['gazette_number'] = gazette_match.group(1)
            
            # Extract publication date
            pub_pattern = r'(?:Published|Dated)\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})'
            pub_match = re.search(pub_pattern, content, re.IGNORECASE)
            if pub_match:
                metadata['publication_date'] = pub_match.group(1).strip()
            
            # Extract notice type
            notice_pattern = r'(?:NOTICE|ANNOUNCEMENT|PROCLAMATION|ORDER)\s+(?:OF|FOR|TO)\s+([A-Z][^.\n]+)'
            notice_match = re.search(notice_pattern, content, re.IGNORECASE)
            if notice_match:
                metadata['notice_type'] = notice_match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error extracting gazette metadata: {e}")
        
        return metadata
    
    async def crawl_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl documents from Kenya Law"""
        all_results = []
        
        try:
            # Crawl different types of documents
            section_limit = limit // 3  # Distribute across sections
            
            # Crawl judgments
            judgments = await self.crawl_judgments(section_limit)
            all_results.extend(judgments)
            
            # Crawl legislation
            legislation = await self.crawl_legislation(section_limit)
            all_results.extend(legislation)
            
            # Crawl gazettes
            gazettes = await self.crawl_gazettes(section_limit)
            all_results.extend(gazettes)
            
            return all_results[:limit]
            
        except Exception as e:
            logger.error(f"Error crawling Kenya Law documents: {e}")
            return []
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for documents on Kenya Law"""
        try:
            # Kenya Law search URL (if available)
            search_url = f"{self.base_url}/search/"
            
            # Try to make search request
            response = await self._make_request(f"{search_url}?q={query}&limit={limit}")
            
            if response:
                # Extract search results
                search_results = self._extract_search_results(response.text)
                return search_results[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching Kenya Law: {e}")
            return []
    
    def _extract_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Extract search results from HTML"""
        results = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for search result items
            result_selectors = [
                '.search-result',
                '.result-item',
                '.document-item',
                '.search-item'
            ]
            
            for selector in result_selectors:
                items = soup.select(selector)
                for item in items:
                    result = self._extract_result_item(item)
                    if result:
                        results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
            return []
    
    def _extract_result_item(self, item) -> Optional[Dict[str, Any]]:
        """Extract individual search result item"""
        try:
            # Extract link
            link = item.find('a')
            if not link or not link.get('href'):
                return None
            
            url = urljoin(self.base_url, link['href'])
            
            # Extract title
            title = link.get_text().strip()
            
            # Extract description
            description = ""
            desc_elem = item.find('.description') or item.find('.snippet')
            if desc_elem:
                description = desc_elem.get_text().strip()
            
            return {
                'url': url,
                'title': title,
                'description': description,
                'source': self.name
            }
            
        except Exception as e:
            logger.error(f"Error extracting result item: {e}")
            return None
    
    async def get_document_urls(self, limit: int = 100) -> List[str]:
        """Get list of document URLs to crawl"""
        urls = []

        try:
            # Get URLs from different sections
            judgment_urls = await self._get_judgment_urls(limit // 3)
            legislation_urls = await self._get_legislation_urls(limit // 3)
            gazette_urls = await self._get_gazette_urls(limit // 3)

            urls.extend(judgment_urls)
            urls.extend(legislation_urls)
            urls.extend(gazette_urls)

            return list(set(urls))[:limit]

        except Exception as e:
            logger.error(f"Error getting document URLs: {e}")
            return []

    # Additional crawling methods for all Kenya Law sections

    async def crawl_superior_courts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Crawl superior court judgments"""
        try:
            logger.info("Starting superior courts crawling...")
            urls = await self._get_section_urls('superior_courts', limit)

            results = []
            for url in urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'judgment'
                    result['metadata']['court'] = 'Superior Court'
                    results.append(result)

            logger.info(f"Crawled {len(results)} superior court judgments")
            return results
        except Exception as e:
            logger.error(f"Error crawling superior courts: {e}")
            return []

    async def crawl_subordinate_courts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Crawl subordinate court judgments"""
        try:
            logger.info("Starting subordinate courts crawling...")
            urls = await self._get_section_urls('subordinate_courts', limit)

            results = []
            for url in urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'judgment'
                    result['metadata']['court'] = 'Subordinate Court'
                    results.append(result)

            logger.info(f"Crawled {len(results)} subordinate court judgments")
            return results
        except Exception as e:
            logger.error(f"Error crawling subordinate courts: {e}")
            return []

    async def crawl_tribunals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Crawl tribunal decisions"""
        try:
            logger.info("Starting tribunals crawling...")
            urls = await self._get_section_urls('tribunals', limit)

            results = []
            for url in urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'tribunal_decision'
                    result['metadata']['court'] = 'Tribunal'
                    results.append(result)

            logger.info(f"Crawled {len(results)} tribunal decisions")
            return results
        except Exception as e:
            logger.error(f"Error crawling tribunals: {e}")
            return []

    async def crawl_legislation_counties(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl county legislation"""
        try:
            logger.info("Starting county legislation crawling...")
            urls = await self._get_section_urls('legislation_counties', limit)

            results = []
            for url in urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'county_legislation'
                    results.append(result)

            logger.info(f"Crawled {len(results)} county legislation documents")
            return results
        except Exception as e:
            logger.error(f"Error crawling county legislation: {e}")
            return []

    async def crawl_bills(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl parliamentary bills"""
        try:
            logger.info("Starting bills crawling...")
            urls = await self._get_section_urls('bills', limit)

            results = []
            for url in urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'bill'
                    results.append(result)

            logger.info(f"Crawled {len(results)} bills")
            return results
        except Exception as e:
            logger.error(f"Error crawling bills: {e}")
            return []

    async def crawl_commercial_tribunals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl commercial tribunal decisions"""
        try:
            logger.info("Starting commercial tribunals crawling...")
            urls = await self._get_section_urls('commercial_tribunals', limit)

            results = []
            for url in urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'tribunal_decision'
                    result['metadata']['court'] = 'Commercial Tribunal'
                    results.append(result)

            logger.info(f"Crawled {len(results)} commercial tribunal decisions")
            return results
        except Exception as e:
            logger.error(f"Error crawling commercial tribunals: {e}")
            return []

    async def _get_section_urls(self, section: str, limit: int) -> List[str]:
        """Generic method to get URLs from any section"""
        try:
            section_url = self.sections.get(section)
            if not section_url:
                logger.error(f"Unknown section: {section}")
                return []

            # Fetch the section page
            soup = await self._fetch_page(section_url)
            if not soup:
                return []

            # Extract document links (adapt based on page structure)
            urls = []
            links = soup.find_all('a', href=True)

            for link in links:
                href = link['href']
                # Filter for document links (adjust pattern as needed)
                if any(pattern in href for pattern in ['/view/', '/download/', '/doc/', section]):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)
                        if len(urls) >= limit:
                            break

            logger.info(f"Found {len(urls)} URLs in {section}")
            return urls

        except Exception as e:
            logger.error(f"Error getting URLs from {section}: {e}")
            return []
