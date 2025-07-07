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

class ParliamentCrawler(BaseCrawler):
    """Crawler for Parliament of Kenya website (http://parliament.go.ke)"""
    
    def __init__(self):
        super().__init__(settings.PARLIAMENT_BASE_URL, "parliament")
        
        # Section-specific URLs
        self.sections = {
            'hansard': f"{self.base_url}/hansard/",
            'bills': f"{self.base_url}/bills/",
            'acts': f"{self.base_url}/acts/",
            'committees': f"{self.base_url}/committees/",
            'proceedings': f"{self.base_url}/proceedings/",
            'questions': f"{self.base_url}/questions/",
            'motions': f"{self.base_url}/motions/"
        }
        
        # Document type mappings
        self.document_types = {
            'hansard': 'hansard',
            'bills': 'bill',
            'acts': 'act',
            'committees': 'committee_report',
            'proceedings': 'proceeding',
            'questions': 'parliamentary_question',
            'motions': 'motion'
        }
    
    async def crawl_hansard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl Hansard records"""
        try:
            logger.info("Starting Hansard crawling...")
            
            # Get Hansard URLs
            hansard_urls = await self._get_hansard_urls(limit)
            
            # Crawl each Hansard record
            results = []
            for url in hansard_urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'hansard'
                    result['category'] = 'parliamentary_proceeding'
                    
                    # Extract Hansard-specific metadata
                    hansard_metadata = self._extract_hansard_metadata(result.get('content', ''))
                    result['metadata'].update(hansard_metadata)
                    
                    results.append(result)
            
            logger.info(f"Crawled {len(results)} Hansard records")
            return results
            
        except Exception as e:
            logger.error(f"Error crawling Hansard: {e}")
            return []
    
    async def crawl_bills(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl parliamentary bills"""
        try:
            logger.info("Starting bills crawling...")
            
            # Get bill URLs
            bill_urls = await self._get_bill_urls(limit)
            
            # Crawl each bill
            results = []
            for url in bill_urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'bill'
                    result['category'] = 'proposed_legislation'
                    
                    # Extract bill-specific metadata
                    bill_metadata = self._extract_bill_metadata(result.get('content', ''))
                    result['metadata'].update(bill_metadata)
                    
                    results.append(result)
            
            logger.info(f"Crawled {len(results)} bills")
            return results
            
        except Exception as e:
            logger.error(f"Error crawling bills: {e}")
            return []
    
    async def crawl_committee_reports(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl committee reports"""
        try:
            logger.info("Starting committee reports crawling...")
            
            # Get committee report URLs
            committee_urls = await self._get_committee_urls(limit)
            
            # Crawl each committee report
            results = []
            for url in committee_urls[:limit]:
                result = await self.crawl_page(url)
                if result:
                    result['document_type'] = 'committee_report'
                    result['category'] = 'parliamentary_report'
                    
                    # Extract committee-specific metadata
                    committee_metadata = self._extract_committee_metadata(result.get('content', ''))
                    result['metadata'].update(committee_metadata)
                    
                    results.append(result)
            
            logger.info(f"Crawled {len(results)} committee reports")
            return results
            
        except Exception as e:
            logger.error(f"Error crawling committee reports: {e}")
            return []
    
    async def _get_hansard_urls(self, limit: int) -> List[str]:
        """Get Hansard URLs from listing pages"""
        urls = []
        try:
            # Main Hansard page
            response = await self._make_request(self.sections['hansard'])
            if response:
                urls.extend(self._extract_hansard_urls_from_html(response.text))
            
            # Try different date ranges
            current_year = datetime.now().year
            for year in range(current_year, current_year - 3, -1):  # Last 3 years
                if len(urls) >= limit:
                    break
                    
                year_url = f"{self.sections['hansard']}{year}/"
                response = await self._make_request(year_url)
                if response:
                    urls.extend(self._extract_hansard_urls_from_html(response.text))
            
            return list(set(urls))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting Hansard URLs: {e}")
            return []
    
    async def _get_bill_urls(self, limit: int) -> List[str]:
        """Get bill URLs from listing pages"""
        urls = []
        try:
            # Main bills page
            response = await self._make_request(self.sections['bills'])
            if response:
                urls.extend(self._extract_bill_urls_from_html(response.text))
            
            # Try different categories
            categories = ['current', 'pending', 'passed', 'government', 'private']
            for category in categories:
                if len(urls) >= limit:
                    break
                    
                category_url = f"{self.sections['bills']}{category}/"
                response = await self._make_request(category_url)
                if response:
                    urls.extend(self._extract_bill_urls_from_html(response.text))
            
            return list(set(urls))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting bill URLs: {e}")
            return []
    
    async def _get_committee_urls(self, limit: int) -> List[str]:
        """Get committee URLs from listing pages"""
        urls = []
        try:
            # Main committees page
            response = await self._make_request(self.sections['committees'])
            if response:
                urls.extend(self._extract_committee_urls_from_html(response.text))
            
            # Try different committee types
            committee_types = ['standing', 'select', 'joint', 'special']
            for committee_type in committee_types:
                if len(urls) >= limit:
                    break
                    
                type_url = f"{self.sections['committees']}{committee_type}/"
                response = await self._make_request(type_url)
                if response:
                    urls.extend(self._extract_committee_urls_from_html(response.text))
            
            return list(set(urls))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting committee URLs: {e}")
            return []
    
    def _extract_hansard_urls_from_html(self, html: str) -> List[str]:
        """Extract Hansard URLs from HTML"""
        urls = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for Hansard links
            selectors = [
                'a[href*="/hansard/"]',
                'a[href*="/proceedings/"]',
                'a[href*="/sitting/"]',
                '.hansard-link a',
                '.proceeding-link a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if self._is_hansard_url(full_url):
                            urls.append(full_url)
            
            return list(set(urls))
            
        except Exception as e:
            logger.error(f"Error extracting Hansard URLs: {e}")
            return []
    
    def _extract_bill_urls_from_html(self, html: str) -> List[str]:
        """Extract bill URLs from HTML"""
        urls = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for bill links
            selectors = [
                'a[href*="/bills/"]',
                'a[href*="/bill/"]',
                '.bill-link a',
                '.legislation-link a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if self._is_bill_url(full_url):
                            urls.append(full_url)
            
            return list(set(urls))
            
        except Exception as e:
            logger.error(f"Error extracting bill URLs: {e}")
            return []
    
    def _extract_committee_urls_from_html(self, html: str) -> List[str]:
        """Extract committee URLs from HTML"""
        urls = []
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for committee links
            selectors = [
                'a[href*="/committees/"]',
                'a[href*="/committee/"]',
                'a[href*="/reports/"]',
                '.committee-link a',
                '.report-link a'
            ]
            
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        if self._is_committee_url(full_url):
                            urls.append(full_url)
            
            return list(set(urls))
            
        except Exception as e:
            logger.error(f"Error extracting committee URLs: {e}")
            return []
    
    def _is_hansard_url(self, url: str) -> bool:
        """Check if URL is a Hansard document"""
        patterns = [
            r'/hansard/[^/]+/?$',
            r'/proceedings/[^/]+/?$',
            r'/sitting/[^/]+/?$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _is_bill_url(self, url: str) -> bool:
        """Check if URL is a bill document"""
        patterns = [
            r'/bills?/[^/]+/?$',
            r'/bill/[^/]+/?$',
            r'/legislation/[^/]+/?$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _is_committee_url(self, url: str) -> bool:
        """Check if URL is a committee document"""
        patterns = [
            r'/committees?/[^/]+/?$',
            r'/committee/[^/]+/?$',
            r'/reports?/[^/]+/?$'
        ]
        
        for pattern in patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def _extract_hansard_metadata(self, content: str) -> Dict[str, Any]:
        """Extract Hansard-specific metadata"""
        metadata = {}
        
        try:
            # Extract sitting date
            date_pattern = r'(?:Sitting|Session)\s+(?:of|on)\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})'
            date_match = re.search(date_pattern, content, re.IGNORECASE)
            if date_match:
                metadata['sitting_date'] = date_match.group(1).strip()
            
            # Extract session number
            session_pattern = r'(?:Session|Parliament)\s+No\.?\s*(\d+)'
            session_match = re.search(session_pattern, content, re.IGNORECASE)
            if session_match:
                metadata['session_number'] = session_match.group(1)
            
            # Extract speakers
            speaker_pattern = r'(?:Hon\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            speaker_matches = re.findall(speaker_pattern, content)
            if speaker_matches:
                metadata['speakers'] = list(set(speaker_matches))
            
            # Extract topics/subjects
            topic_pattern = r'(?:MOTION|QUESTION|BILL|STATEMENT)\s+(?:ON|REGARDING|CONCERNING)\s+([A-Z][^.]+)'
            topic_matches = re.findall(topic_pattern, content, re.IGNORECASE)
            if topic_matches:
                metadata['topics'] = [topic.strip() for topic in topic_matches]
            
        except Exception as e:
            logger.error(f"Error extracting Hansard metadata: {e}")
        
        return metadata
    
    def _extract_bill_metadata(self, content: str) -> Dict[str, Any]:
        """Extract bill-specific metadata"""
        metadata = {}
        
        try:
            # Extract bill number
            bill_pattern = r'(?:Bill No\.?)\s*:?\s*(\d+)\s*of\s*(\d{4})'
            bill_match = re.search(bill_pattern, content, re.IGNORECASE)
            if bill_match:
                metadata['bill_number'] = bill_match.group(1)
                metadata['year'] = bill_match.group(2)
            
            # Extract sponsor
            sponsor_pattern = r'(?:Sponsored by|Introduced by|Moved by)\s+(?:Hon\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            sponsor_match = re.search(sponsor_pattern, content, re.IGNORECASE)
            if sponsor_match:
                metadata['sponsor'] = sponsor_match.group(1).strip()
            
            # Extract committee
            committee_pattern = r'(?:Committee on|Referred to)\s+([A-Z][^.]+Committee)'
            committee_match = re.search(committee_pattern, content, re.IGNORECASE)
            if committee_match:
                metadata['committee'] = committee_match.group(1).strip()
            
            # Extract status
            status_pattern = r'(?:Status|Stage)\s*:?\s*([A-Z][^.\n]+)'
            status_match = re.search(status_pattern, content, re.IGNORECASE)
            if status_match:
                metadata['status'] = status_match.group(1).strip()
            
            # Extract reading dates
            reading_pattern = r'(?:First|Second|Third)\s+Reading\s+on\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})'
            reading_matches = re.findall(reading_pattern, content, re.IGNORECASE)
            if reading_matches:
                metadata['reading_dates'] = reading_matches
            
        except Exception as e:
            logger.error(f"Error extracting bill metadata: {e}")
        
        return metadata
    
    def _extract_committee_metadata(self, content: str) -> Dict[str, Any]:
        """Extract committee-specific metadata"""
        metadata = {}
        
        try:
            # Extract committee name
            committee_pattern = r'(?:Committee on|Report of)\s+([A-Z][^.]+(?:Committee|Affairs))'
            committee_match = re.search(committee_pattern, content, re.IGNORECASE)
            if committee_match:
                metadata['committee_name'] = committee_match.group(1).strip()
            
            # Extract chairperson
            chair_pattern = r'(?:Chairperson|Chairman|Chairwoman)\s*:?\s*(?:Hon\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            chair_match = re.search(chair_pattern, content, re.IGNORECASE)
            if chair_match:
                metadata['chairperson'] = chair_match.group(1).strip()
            
            # Extract members
            member_pattern = r'(?:Members|Committee comprises)\s*:?\s*([^.]+)'
            member_match = re.search(member_pattern, content, re.IGNORECASE)
            if member_match:
                members_text = member_match.group(1)
                # Extract individual member names
                member_names = re.findall(r'(?:Hon\.|Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', members_text)
                if member_names:
                    metadata['members'] = member_names
            
            # Extract report date
            report_date_pattern = r'(?:Report dated|Presented on)\s+(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})'
            report_date_match = re.search(report_date_pattern, content, re.IGNORECASE)
            if report_date_match:
                metadata['report_date'] = report_date_match.group(1).strip()
            
            # Extract recommendations
            recommendations_pattern = r'(?:RECOMMENDATIONS|CONCLUSION)\s*:?\s*([^.]+(?:\.[^.]+)*)'
            recommendations_match = re.search(recommendations_pattern, content, re.IGNORECASE)
            if recommendations_match:
                metadata['recommendations'] = recommendations_match.group(1).strip()
            
        except Exception as e:
            logger.error(f"Error extracting committee metadata: {e}")
        
        return metadata
    
    async def crawl_documents(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Crawl documents from Parliament"""
        all_results = []
        
        try:
            # Crawl different types of documents
            section_limit = limit // 3  # Distribute across sections
            
            # Crawl Hansard
            hansard = await self.crawl_hansard(section_limit)
            all_results.extend(hansard)
            
            # Crawl bills
            bills = await self.crawl_bills(section_limit)
            all_results.extend(bills)
            
            # Crawl committee reports
            committee_reports = await self.crawl_committee_reports(section_limit)
            all_results.extend(committee_reports)
            
            return all_results[:limit]
            
        except Exception as e:
            logger.error(f"Error crawling Parliament documents: {e}")
            return []
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for documents on Parliament website"""
        try:
            # Parliament search URL (if available)
            search_url = f"{self.base_url}/search/"
            
            # Try to make search request
            response = await self._make_request(f"{search_url}?q={query}&limit={limit}")
            
            if response:
                # Extract search results
                search_results = self._extract_search_results(response.text)
                return search_results[:limit]
            
            return []
            
        except Exception as e:
            logger.error(f"Error searching Parliament: {e}")
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
            hansard_urls = await self._get_hansard_urls(limit // 3)
            bill_urls = await self._get_bill_urls(limit // 3)
            committee_urls = await self._get_committee_urls(limit // 3)
            
            urls.extend(hansard_urls)
            urls.extend(bill_urls)
            urls.extend(committee_urls)
            
            return list(set(urls))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting document URLs: {e}")
            return []
