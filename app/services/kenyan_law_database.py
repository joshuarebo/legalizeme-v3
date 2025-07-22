"""
Comprehensive Kenyan Law Database Integration
Advanced legal corpus management, citation database, and automated compliance checking.
"""

import asyncio
import aiohttp
import sqlite3
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import hashlib
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

@dataclass
class LegalDocument:
    """Legal document structure"""
    document_id: str
    title: str
    source: str
    document_type: str  # "act", "case_law", "regulation", "template"
    url: str
    content: str
    sections: Dict[str, str]
    citations: List[str]
    keywords: List[str]
    jurisdiction: str
    date_published: Optional[str]
    last_updated: str
    relevance_score: float

@dataclass
class LegalCitation:
    """Legal citation structure"""
    citation_id: str
    source_document: str
    section: str
    title: str
    content: str
    legal_area: str  # "employment", "property", "commercial", "constitutional"
    authority_level: str  # "primary", "secondary", "precedent"
    confidence_score: float
    usage_count: int

@dataclass
class ComplianceRule:
    """Compliance rule structure"""
    rule_id: str
    legal_basis: str
    document_type: str
    requirement: str
    validation_pattern: str
    severity: str  # "mandatory", "recommended", "optional"
    penalty_description: str
    auto_fix_available: bool

class KenyanLawDatabase:
    """Comprehensive Kenyan Law Database with advanced search and compliance checking"""
    
    def __init__(self, db_path: str = "kenyan_law.db"):
        self.db_path = Path(db_path)
        self.session = None
        self.legal_documents = {}
        self.citation_index = {}
        self.compliance_rules = {}
        self.search_index = {}
        
        # Initialize database
        self._init_database()

        # Load existing data and generate compliance rules
        asyncio.create_task(self._initialize_data())
    
    def _init_database(self):
        """Initialize SQLite database for legal documents"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Legal documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS legal_documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    url TEXT,
                    content TEXT,
                    sections TEXT,  -- JSON
                    citations TEXT,  -- JSON
                    keywords TEXT,  -- JSON
                    jurisdiction TEXT DEFAULT 'kenya',
                    date_published TEXT,
                    last_updated TEXT NOT NULL,
                    relevance_score REAL DEFAULT 0.0
                )
            ''')
            
            # Legal citations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS legal_citations (
                    citation_id TEXT PRIMARY KEY,
                    source_document TEXT NOT NULL,
                    section TEXT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    legal_area TEXT NOT NULL,
                    authority_level TEXT NOT NULL,
                    confidence_score REAL DEFAULT 0.0,
                    usage_count INTEGER DEFAULT 0,
                    FOREIGN KEY (source_document) REFERENCES legal_documents (document_id)
                )
            ''')
            
            # Compliance rules table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS compliance_rules (
                    rule_id TEXT PRIMARY KEY,
                    legal_basis TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    requirement TEXT NOT NULL,
                    validation_pattern TEXT,
                    severity TEXT NOT NULL,
                    penalty_description TEXT,
                    auto_fix_available BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Search index table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_index (
                    term TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    context TEXT,
                    PRIMARY KEY (term, document_id),
                    FOREIGN KEY (document_id) REFERENCES legal_documents (document_id)
                )
            ''')
            
            # Create indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON legal_documents(document_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_citations_area ON legal_citations(legal_area)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rules_type ON compliance_rules(document_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_term ON search_index(term)')
            
            conn.commit()
            conn.close()
            
            logger.info("Kenyan Law Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def _initialize_data(self):
        """Initialize data including loading existing data and generating compliance rules"""
        await self._load_existing_data()

        # Generate compliance rules if not already present
        if not self.compliance_rules:
            await self._generate_compliance_rules()
            logger.info("Generated compliance rules during initialization")

    async def _load_existing_data(self):
        """Load existing data from database into memory"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load legal documents
            cursor.execute('SELECT * FROM legal_documents')
            for row in cursor.fetchall():
                doc = LegalDocument(
                    document_id=row[0], title=row[1], source=row[2],
                    document_type=row[3], url=row[4], content=row[5],
                    sections=json.loads(row[6]) if row[6] else {},
                    citations=json.loads(row[7]) if row[7] else [],
                    keywords=json.loads(row[8]) if row[8] else [],
                    jurisdiction=row[9], date_published=row[10],
                    last_updated=row[11], relevance_score=row[12]
                )
                self.legal_documents[doc.document_id] = doc
            
            # Load citations
            cursor.execute('SELECT * FROM legal_citations')
            for row in cursor.fetchall():
                citation = LegalCitation(
                    citation_id=row[0], source_document=row[1], section=row[2],
                    title=row[3], content=row[4], legal_area=row[5],
                    authority_level=row[6], confidence_score=row[7], usage_count=row[8]
                )
                self.citation_index[citation.citation_id] = citation
            
            # Load compliance rules
            cursor.execute('SELECT * FROM compliance_rules')
            for row in cursor.fetchall():
                rule = ComplianceRule(
                    rule_id=row[0], legal_basis=row[1], document_type=row[2],
                    requirement=row[3], validation_pattern=row[4], severity=row[5],
                    penalty_description=row[6], auto_fix_available=bool(row[7])
                )
                self.compliance_rules[rule.rule_id] = rule
            
            conn.close()
            
            logger.info(f"Loaded {len(self.legal_documents)} documents, "
                       f"{len(self.citation_index)} citations, "
                       f"{len(self.compliance_rules)} compliance rules")
            
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    async def crawl_kenya_law_portal(self, max_documents: int = 100) -> Dict[str, Any]:
        """Enhanced crawler for Kenya Law portal"""
        try:
            async with aiohttp.ClientSession() as session:
                self.session = session
                
                crawl_results = {
                    "documents_crawled": 0,
                    "citations_extracted": 0,
                    "templates_found": 0,
                    "errors": []
                }
                
                # Crawl different sections
                sections_to_crawl = [
                    {
                        "name": "Employment Act 2007",
                        "url": "https://new.kenyalaw.org/akn/ke/act/2007/11/eng@2010-05-01",
                        "type": "act"
                    },
                    {
                        "name": "Constitution of Kenya 2010",
                        "url": "https://new.kenyalaw.org/akn/ke/act/2010/constitution/eng@2010-09-03",
                        "type": "constitution"
                    },
                    {
                        "name": "Companies Act 2015",
                        "url": "https://new.kenyalaw.org/akn/ke/act/2015/17/eng@2015-09-11",
                        "type": "act"
                    },
                    {
                        "name": "Landlord and Tenant Act",
                        "url": "https://new.kenyalaw.org/akn/ke/act/cap/301/eng@2012-12-31",
                        "type": "act"
                    }
                ]
                
                for section in sections_to_crawl:
                    try:
                        result = await self._crawl_legal_document(
                            section["url"], section["name"], section["type"]
                        )
                        
                        if result:
                            crawl_results["documents_crawled"] += 1
                            crawl_results["citations_extracted"] += len(result.citations)
                            
                            # Store in database
                            await self._store_legal_document(result)
                            
                    except Exception as e:
                        error_msg = f"Error crawling {section['name']}: {e}"
                        crawl_results["errors"].append(error_msg)
                        logger.error(error_msg)
                
                # Crawl case law for templates
                template_results = await self._crawl_case_law_templates()
                crawl_results["templates_found"] = template_results
                
                # Build search index
                await self._build_search_index()
                
                # Generate compliance rules
                await self._generate_compliance_rules()
                
                return crawl_results
                
        except Exception as e:
            logger.error(f"Error in Kenya Law portal crawl: {e}")
            return {"error": str(e)}
    
    async def _crawl_legal_document(self, url: str, title: str, doc_type: str) -> Optional[LegalDocument]:
        """Crawl a specific legal document"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract content
                content = self._extract_document_content(soup)
                
                # Extract sections
                sections = self._extract_document_sections(soup, doc_type)
                
                # Extract citations
                citations = self._extract_document_citations(content)
                
                # Extract keywords
                keywords = self._extract_keywords(content, title)
                
                # Generate document ID
                doc_id = hashlib.md5(f"{title}_{url}".encode()).hexdigest()
                
                document = LegalDocument(
                    document_id=doc_id,
                    title=title,
                    source="Kenya Law Portal",
                    document_type=doc_type,
                    url=url,
                    content=content,
                    sections=sections,
                    citations=citations,
                    keywords=keywords,
                    jurisdiction="kenya",
                    date_published=None,
                    last_updated=datetime.utcnow().isoformat(),
                    relevance_score=self._calculate_relevance_score(content, doc_type)
                )
                
                return document
                
        except Exception as e:
            logger.error(f"Error crawling document {url}: {e}")
            return None
    
    def _extract_document_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from legal document"""
        # Remove navigation, headers, footers
        for element in soup.find_all(['nav', 'header', 'footer', 'script', 'style']):
            element.decompose()
        
        # Find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        
        if main_content:
            return main_content.get_text(separator=' ', strip=True)
        else:
            return soup.get_text(separator=' ', strip=True)
    
    def _extract_document_sections(self, soup: BeautifulSoup, doc_type: str) -> Dict[str, str]:
        """Extract sections from legal document"""
        sections = {}
        
        if doc_type == "act":
            # Look for section headers
            section_pattern = re.compile(r'section\s+(\d+)', re.IGNORECASE)
            
            # Find all section headers
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                header_text = header.get_text(strip=True)
                match = section_pattern.search(header_text)
                
                if match:
                    section_num = match.group(1)
                    
                    # Extract section content
                    section_content = []
                    current = header.next_sibling
                    
                    while current and current.name not in ['h1', 'h2', 'h3', 'h4']:
                        if hasattr(current, 'get_text'):
                            text = current.get_text(strip=True)
                            if text:
                                section_content.append(text)
                        current = current.next_sibling
                    
                    sections[f"section_{section_num}"] = ' '.join(section_content)
        
        return sections
    
    def _extract_document_citations(self, content: str) -> List[str]:
        """Extract legal citations from document content"""
        citations = []
        
        # Citation patterns
        patterns = [
            r'Employment Act\s*(?:2007|Cap\s*226)(?:,?\s*Section\s*(\d+))?',
            r'Constitution(?:\s*of\s*Kenya)?\s*(?:2010)?(?:,?\s*Article\s*(\d+))?',
            r'Companies Act\s*(?:2015)?(?:,?\s*Section\s*(\d+))?',
            r'Landlord(?:\s*and\s*|\s*&\s*)Tenant Act(?:\s*Cap\s*301)?(?:,?\s*Section\s*(\d+))?'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                citations.append(match.group(0))
        
        return list(set(citations))  # Remove duplicates
    
    def _extract_keywords(self, content: str, title: str) -> List[str]:
        """Extract relevant keywords from document"""
        # Legal keywords
        legal_terms = [
            'employment', 'contract', 'termination', 'notice', 'salary', 'wage',
            'probation', 'leave', 'benefits', 'overtime', 'dismissal', 'severance',
            'landlord', 'tenant', 'rent', 'lease', 'deposit', 'maintenance',
            'company', 'director', 'shareholder', 'registration', 'compliance'
        ]
        
        keywords = []
        content_lower = content.lower()
        title_lower = title.lower()
        
        for term in legal_terms:
            if term in content_lower or term in title_lower:
                keywords.append(term)
        
        return keywords
    
    def _calculate_relevance_score(self, content: str, doc_type: str) -> float:
        """Calculate relevance score for document"""
        base_score = 0.5
        
        # Higher score for acts and constitution
        if doc_type in ['act', 'constitution']:
            base_score += 0.3
        
        # Higher score for employment-related content
        employment_terms = ['employment', 'employee', 'employer', 'contract', 'work']
        for term in employment_terms:
            if term.lower() in content.lower():
                base_score += 0.05
        
        return min(base_score, 1.0)

    async def _crawl_case_law_templates(self) -> int:
        """Crawl case law for document templates"""
        templates_found = 0

        # Mock case law template extraction
        # In production, this would search actual case law databases
        mock_templates = [
            {
                "title": "Employment Contract Template from Case XYZ vs ABC Ltd",
                "content": "Standard employment contract clauses extracted from case law",
                "type": "employment_contract_template"
            },
            {
                "title": "Lease Agreement Template from Landlord vs Tenant Case",
                "content": "Standard lease agreement clauses from legal precedent",
                "type": "lease_agreement_template"
            }
        ]

        for template in mock_templates:
            doc_id = hashlib.md5(template["title"].encode()).hexdigest()

            document = LegalDocument(
                document_id=doc_id,
                title=template["title"],
                source="Kenya Law Case Law",
                document_type="template",
                url="",
                content=template["content"],
                sections={},
                citations=[],
                keywords=["template", "contract"],
                jurisdiction="kenya",
                date_published=None,
                last_updated=datetime.utcnow().isoformat(),
                relevance_score=0.8
            )

            await self._store_legal_document(document)
            templates_found += 1

        return templates_found

    async def _store_legal_document(self, document: LegalDocument):
        """Store legal document in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO legal_documents
                (document_id, title, source, document_type, url, content, sections,
                 citations, keywords, jurisdiction, date_published, last_updated, relevance_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                document.document_id, document.title, document.source, document.document_type,
                document.url, document.content, json.dumps(document.sections),
                json.dumps(document.citations), json.dumps(document.keywords),
                document.jurisdiction, document.date_published, document.last_updated,
                document.relevance_score
            ))

            conn.commit()
            conn.close()

            # Store in memory
            self.legal_documents[document.document_id] = document

            logger.info(f"Stored legal document: {document.title}")

        except Exception as e:
            logger.error(f"Error storing document {document.document_id}: {e}")

    async def _build_search_index(self):
        """Build search index for fast document retrieval"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Clear existing index
            cursor.execute('DELETE FROM search_index')

            for doc_id, document in self.legal_documents.items():
                # Index title and content
                text_to_index = f"{document.title} {document.content}"

                # Extract terms
                terms = self._extract_search_terms(text_to_index)

                for term, frequency in terms.items():
                    cursor.execute('''
                        INSERT INTO search_index (term, document_id, frequency, context)
                        VALUES (?, ?, ?, ?)
                    ''', (term, doc_id, frequency, self._get_term_context(text_to_index, term)))

            conn.commit()
            conn.close()

            logger.info("Search index built successfully")

        except Exception as e:
            logger.error(f"Error building search index: {e}")

    def _extract_search_terms(self, text: str) -> Dict[str, int]:
        """Extract search terms with frequency"""
        # Simple tokenization and frequency counting
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter out common words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

        term_freq = {}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                term_freq[word] = term_freq.get(word, 0) + 1

        return term_freq

    def _get_term_context(self, text: str, term: str) -> str:
        """Get context around a search term"""
        # Find term in text and extract surrounding context
        pattern = re.compile(rf'\b{re.escape(term)}\b', re.IGNORECASE)
        match = pattern.search(text)

        if match:
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            return text[start:end].strip()

        return ""

    async def _generate_compliance_rules(self):
        """Generate compliance rules from legal documents"""
        try:
            # Employment Act compliance rules
            employment_rules = [
                {
                    "rule_id": "emp_act_section_9",
                    "legal_basis": "Employment Act 2007, Section 9",
                    "document_type": "employment_contract",
                    "requirement": "Written particulars of employment must be provided",
                    "validation_pattern": r"(position|job\s+title|duties|responsibilities)",
                    "severity": "mandatory",
                    "penalty_description": "Contract may be deemed invalid",
                    "auto_fix_available": True
                },
                {
                    "rule_id": "emp_act_section_35",
                    "legal_basis": "Employment Act 2007, Section 35",
                    "document_type": "employment_contract",
                    "requirement": "Notice period for termination must be specified",
                    "validation_pattern": r"(notice\s+period|termination\s+notice)",
                    "severity": "mandatory",
                    "penalty_description": "Termination disputes may arise",
                    "auto_fix_available": True
                },
                {
                    "rule_id": "min_wage_compliance",
                    "legal_basis": "Minimum Wage Regulations 2024",
                    "document_type": "employment_contract",
                    "requirement": "Salary must meet minimum wage requirements (KES 15,000 general, KES 13,500 agricultural)",
                    "validation_pattern": r"salary|wage|remuneration",
                    "severity": "mandatory",
                    "penalty_description": "Legal penalties, back pay required, contract may be invalid",
                    "auto_fix_available": True
                },
                {
                    "rule_id": "working_hours_compliance",
                    "legal_basis": "Employment Act 2007, Section 56",
                    "document_type": "employment_contract",
                    "requirement": "Working hours must not exceed 52 hours per week",
                    "validation_pattern": r"(working\s+hours|hours\s+of\s+work|work\s+schedule)",
                    "severity": "mandatory",
                    "penalty_description": "Overtime pay required, labor violations",
                    "auto_fix_available": True
                },
                {
                    "rule_id": "annual_leave_compliance",
                    "legal_basis": "Employment Act 2007, Section 28",
                    "document_type": "employment_contract",
                    "requirement": "Annual leave must be minimum 21 days per year",
                    "validation_pattern": r"(annual\s+leave|vacation|holiday)",
                    "severity": "mandatory",
                    "penalty_description": "Employee entitled to additional leave compensation",
                    "auto_fix_available": True
                }
            ]

            # Store compliance rules
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for rule_data in employment_rules:
                rule = ComplianceRule(**rule_data)

                cursor.execute('''
                    INSERT OR REPLACE INTO compliance_rules
                    (rule_id, legal_basis, document_type, requirement, validation_pattern,
                     severity, penalty_description, auto_fix_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule.rule_id, rule.legal_basis, rule.document_type, rule.requirement,
                    rule.validation_pattern, rule.severity, rule.penalty_description,
                    rule.auto_fix_available
                ))

                self.compliance_rules[rule.rule_id] = rule

            conn.commit()
            conn.close()

            logger.info(f"Generated {len(employment_rules)} compliance rules")

        except Exception as e:
            logger.error(f"Error generating compliance rules: {e}")

    async def search_legal_documents(self, query: str, document_type: Optional[str] = None,
                                   limit: int = 10) -> List[Dict[str, Any]]:
        """Advanced search for legal documents"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build search query
            search_terms = query.lower().split()

            if document_type:
                cursor.execute('''
                    SELECT d.*, SUM(s.frequency) as relevance
                    FROM legal_documents d
                    JOIN search_index s ON d.document_id = s.document_id
                    WHERE d.document_type = ? AND s.term IN ({})
                    GROUP BY d.document_id
                    ORDER BY relevance DESC, d.relevance_score DESC
                    LIMIT ?
                '''.format(','.join('?' * len(search_terms))),
                [document_type] + search_terms + [limit])
            else:
                cursor.execute('''
                    SELECT d.*, SUM(s.frequency) as relevance
                    FROM legal_documents d
                    JOIN search_index s ON d.document_id = s.document_id
                    WHERE s.term IN ({})
                    GROUP BY d.document_id
                    ORDER BY relevance DESC, d.relevance_score DESC
                    LIMIT ?
                '''.format(','.join('?' * len(search_terms))),
                search_terms + [limit])

            results = []
            for row in cursor.fetchall():
                results.append({
                    'document_id': row[0],
                    'title': row[1],
                    'source': row[2],
                    'document_type': row[3],
                    'url': row[4],
                    'content_preview': row[5][:200] + '...' if len(row[5]) > 200 else row[5],
                    'relevance_score': row[12],
                    'search_relevance': row[13] if len(row) > 13 else 0
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error searching legal documents: {e}")
            return []

    async def check_document_compliance(self, document_content: str,
                                      document_type: str, document_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Automated compliance checking against Kenyan law"""
        try:
            compliance_results = {
                'overall_compliance': True,
                'compliance_score': 1.0,
                'violations': [],
                'warnings': [],
                'recommendations': [],
                'auto_fixes_available': []
            }

            # Get relevant compliance rules
            relevant_rules = [rule for rule in self.compliance_rules.values()
                            if rule.document_type == document_type]

            violations_count = 0
            warnings_count = 0

            for rule in relevant_rules:
                violation_found = False

                # Special handling for minimum wage compliance
                if rule.rule_id == "min_wage_compliance" and document_data:
                    violation_found = await self._check_minimum_wage_compliance(document_data, compliance_results)
                    if violation_found:
                        violations_count += 1

                # Special handling for working hours compliance
                elif rule.rule_id == "working_hours_compliance" and document_data:
                    violation_found = await self._check_working_hours_compliance(document_data, compliance_results)
                    if violation_found:
                        violations_count += 1

                # Special handling for annual leave compliance
                elif rule.rule_id == "annual_leave_compliance" and document_data:
                    violation_found = await self._check_annual_leave_compliance(document_data, compliance_results)
                    if violation_found:
                        violations_count += 1

                # Standard pattern matching for other rules
                elif rule.validation_pattern:
                    pattern_match = re.search(rule.validation_pattern, document_content, re.IGNORECASE)

                    if not pattern_match:
                        if rule.severity == "mandatory":
                            compliance_results['violations'].append({
                                'rule_id': rule.rule_id,
                                'legal_basis': rule.legal_basis,
                                'requirement': rule.requirement,
                                'penalty': rule.penalty_description,
                                'auto_fix_available': rule.auto_fix_available
                            })
                            violations_count += 1

                            if rule.auto_fix_available:
                                compliance_results['auto_fixes_available'].append({
                                    'rule_id': rule.rule_id,
                                    'fix_description': f"Auto-inject clause for {rule.requirement}"
                                })

                        elif rule.severity == "recommended":
                            compliance_results['warnings'].append({
                                'rule_id': rule.rule_id,
                                'legal_basis': rule.legal_basis,
                                'requirement': rule.requirement,
                                'recommendation': f"Consider adding: {rule.requirement}"
                            })
                            warnings_count += 1

            # Calculate compliance score
            total_mandatory_rules = len([r for r in relevant_rules if r.severity == "mandatory"])
            if total_mandatory_rules > 0:
                compliance_results['compliance_score'] = max(0, 1.0 - (violations_count / total_mandatory_rules))

            compliance_results['overall_compliance'] = violations_count == 0

            # Generate recommendations
            if violations_count > 0:
                compliance_results['recommendations'].append(
                    f"Address {violations_count} mandatory compliance violations"
                )

            if warnings_count > 0:
                compliance_results['recommendations'].append(
                    f"Consider addressing {warnings_count} recommended improvements"
                )

            return compliance_results

        except Exception as e:
            logger.error(f"Error checking document compliance: {e}")
            return {
                'overall_compliance': False,
                'compliance_score': 0.0,
                'error': str(e)
            }

    async def _check_minimum_wage_compliance(self, document_data: Dict[str, Any],
                                           compliance_results: Dict[str, Any]) -> bool:
        """Check minimum wage compliance with current Kenyan regulations"""
        try:
            # Current Kenyan minimum wages (2024)
            MINIMUM_WAGES = {
                "general": 15000,      # General workers
                "agricultural": 13500,  # Agricultural workers
                "domestic": 15000,     # Domestic workers
                "security": 15000      # Security workers
            }

            salary = document_data.get("salary", 0)
            position = document_data.get("position", "").lower()

            # Determine wage category based on position
            wage_category = "general"
            if any(term in position for term in ["farm", "agricultural", "agriculture"]):
                wage_category = "agricultural"
            elif any(term in position for term in ["domestic", "house", "maid"]):
                wage_category = "domestic"
            elif any(term in position for term in ["security", "guard", "watchman"]):
                wage_category = "security"

            minimum_wage = MINIMUM_WAGES[wage_category]

            if salary < minimum_wage:
                shortfall = minimum_wage - salary
                compliance_results['violations'].append({
                    'rule_id': 'min_wage_compliance',
                    'legal_basis': 'Minimum Wage Regulations 2024',
                    'requirement': f'Salary must be at least KES {minimum_wage:,} for {wage_category} workers',
                    'penalty': f'Legal penalties, back pay of KES {shortfall:,} required, contract may be invalid',
                    'auto_fix_available': True,
                    'violation_details': {
                        'current_salary': salary,
                        'minimum_required': minimum_wage,
                        'shortfall': shortfall,
                        'wage_category': wage_category
                    }
                })

                compliance_results['auto_fixes_available'].append({
                    'rule_id': 'min_wage_compliance',
                    'fix_description': f'Increase salary to KES {minimum_wage:,} to meet minimum wage requirements',
                    'suggested_value': minimum_wage
                })

                return True  # Violation found

            return False  # No violation

        except Exception as e:
            logger.error(f"Error checking minimum wage compliance: {e}")
            return False

    async def _check_working_hours_compliance(self, document_data: Dict[str, Any],
                                            compliance_results: Dict[str, Any]) -> bool:
        """Check working hours compliance with Employment Act 2007"""
        try:
            working_hours = document_data.get("working_hours", "")

            # Extract hours per week if specified
            hours_per_week = None

            # Try to extract hours from common formats
            if "40" in working_hours and "week" in working_hours.lower():
                hours_per_week = 40
            elif "45" in working_hours and "week" in working_hours.lower():
                hours_per_week = 45
            elif "48" in working_hours and "week" in working_hours.lower():
                hours_per_week = 48
            elif "8:00" in working_hours and "5:00" in working_hours and "monday" in working_hours.lower():
                # Standard 8-5, Monday-Friday = 45 hours
                hours_per_week = 45

            # Check if exceeds 52 hours per week (Employment Act limit)
            if hours_per_week and hours_per_week > 52:
                compliance_results['violations'].append({
                    'rule_id': 'working_hours_compliance',
                    'legal_basis': 'Employment Act 2007, Section 56',
                    'requirement': 'Working hours must not exceed 52 hours per week',
                    'penalty': 'Overtime pay required for excess hours, labor law violations',
                    'auto_fix_available': True,
                    'violation_details': {
                        'specified_hours': hours_per_week,
                        'maximum_allowed': 52,
                        'excess_hours': hours_per_week - 52
                    }
                })

                compliance_results['auto_fixes_available'].append({
                    'rule_id': 'working_hours_compliance',
                    'fix_description': 'Reduce working hours to 52 hours per week maximum',
                    'suggested_value': '8:00 AM to 5:00 PM, Monday to Friday (45 hours/week)'
                })

                return True  # Violation found

            return False  # No violation

        except Exception as e:
            logger.error(f"Error checking working hours compliance: {e}")
            return False

    async def _check_annual_leave_compliance(self, document_data: Dict[str, Any],
                                           compliance_results: Dict[str, Any]) -> bool:
        """Check annual leave compliance with Employment Act 2007"""
        try:
            annual_leave = document_data.get("annual_leave", 0)

            # Minimum 21 days per year under Employment Act 2007
            if annual_leave < 21:
                shortfall = 21 - annual_leave
                compliance_results['violations'].append({
                    'rule_id': 'annual_leave_compliance',
                    'legal_basis': 'Employment Act 2007, Section 28',
                    'requirement': 'Annual leave must be minimum 21 days per year',
                    'penalty': f'Employee entitled to additional {shortfall} days leave compensation',
                    'auto_fix_available': True,
                    'violation_details': {
                        'specified_leave': annual_leave,
                        'minimum_required': 21,
                        'shortfall': shortfall
                    }
                })

                compliance_results['auto_fixes_available'].append({
                    'rule_id': 'annual_leave_compliance',
                    'fix_description': 'Increase annual leave to 21 days minimum',
                    'suggested_value': 21
                })

                return True  # Violation found

            return False  # No violation

        except Exception as e:
            logger.error(f"Error checking annual leave compliance: {e}")
            return False

# Global instance
kenyan_law_db = KenyanLawDatabase()
