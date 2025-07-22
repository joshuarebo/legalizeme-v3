"""
Kenyan Law Service for legal database integration, citation extraction, and compliance checking.
Integrates with Kenya Law portal and provides real legal intelligence.
"""

import asyncio
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import json

from app.schemas.api_responses import (
    KenyanLawCitation, 
    ComplianceAnalysis, 
    LegalRisk, 
    KeyFinding,
    DocumentIntelligence
)

logger = logging.getLogger(__name__)

class KenyanLawService:
    """Service for Kenyan law database integration and compliance checking"""
    
    def __init__(self):
        self.kenya_law_base_url = "https://new.kenyalaw.org"
        self.legal_acts_cache = {}
        self.citation_patterns = self._load_citation_patterns()
        self.compliance_rules = self._load_compliance_rules()
        
    def _load_citation_patterns(self) -> Dict[str, str]:
        """Load regex patterns for identifying Kenyan law citations"""
        return {
            "employment_act": r"Employment Act\s*(?:2007|Cap\s*226)(?:,?\s*Section\s*(\d+))?",
            "constitution": r"Constitution(?:\s*of\s*Kenya)?\s*(?:2010)?(?:,?\s*Article\s*(\d+))?",
            "companies_act": r"Companies Act\s*(?:2015)?(?:,?\s*Section\s*(\d+))?",
            "civil_procedure": r"Civil Procedure Act(?:\s*Cap\s*21)?(?:,?\s*Section\s*(\d+))?",
            "evidence_act": r"Evidence Act(?:\s*Cap\s*80)?(?:,?\s*Section\s*(\d+))?",
            "landlord_tenant": r"Landlord(?:\s*and\s*|\s*&\s*)Tenant Act(?:\s*Cap\s*301)?(?:,?\s*Section\s*(\d+))?",
            "general_section": r"Section\s*(\d+(?:\([a-z]\))?)",
            "general_article": r"Article\s*(\d+(?:\([a-z]\))?)"
        }
    
    def _load_compliance_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load compliance rules for different document types"""
        return {
            "employment_contract": {
                "required_clauses": [
                    "probation_period",
                    "notice_period", 
                    "termination_procedures",
                    "salary_details",
                    "working_hours"
                ],
                "employment_act_sections": {
                    "9": "Written particulars of employment",
                    "35": "Notice of termination",
                    "41": "Termination procedures",
                    "45": "Severance pay",
                    "56": "Working time"
                },
                "minimum_requirements": {
                    "notice_period_days": 30,
                    "probation_period_months": 6,
                    "minimum_wage_kes": 15000
                }
            },
            "lease_agreement": {
                "required_clauses": [
                    "rent_amount",
                    "lease_duration",
                    "deposit_amount",
                    "maintenance_responsibilities"
                ],
                "landlord_tenant_sections": {
                    "6": "Rent payment terms",
                    "12": "Landlord obligations",
                    "15": "Tenant obligations"
                }
            }
        }
    
    async def extract_kenyan_law_citations(self, content: str) -> List[KenyanLawCitation]:
        """Extract Kenyan law citations from document content"""
        citations = []
        
        try:
            for act_name, pattern in self.citation_patterns.items():
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    citation = await self._create_citation_from_match(
                        act_name, match, content
                    )
                    if citation:
                        citations.append(citation)
            
            # Remove duplicates and sort by confidence
            unique_citations = self._deduplicate_citations(citations)
            return sorted(unique_citations, key=lambda x: x.confidence, reverse=True)
            
        except Exception as e:
            logger.error(f"Error extracting citations: {e}")
            return []
    
    async def _create_citation_from_match(
        self, 
        act_name: str, 
        match: re.Match, 
        content: str
    ) -> Optional[KenyanLawCitation]:
        """Create a citation object from regex match"""
        try:
            full_match = match.group(0)
            section_number = match.group(1) if match.groups() else None
            
            # Map act names to formal titles and URLs
            act_mapping = {
                "employment_act": {
                    "source": "Employment Act 2007",
                    "base_url": "https://new.kenyalaw.org/akn/ke/act/2007/11/eng@2010-05-01",
                    "legal_area": "employment"
                },
                "constitution": {
                    "source": "Constitution of Kenya 2010", 
                    "base_url": "https://new.kenyalaw.org/akn/ke/act/2010/constitution/eng@2010-09-03",
                    "legal_area": "constitutional"
                },
                "companies_act": {
                    "source": "Companies Act 2015",
                    "base_url": "https://new.kenyalaw.org/akn/ke/act/2015/17/eng@2015-09-11",
                    "legal_area": "commercial"
                }
            }
            
            if act_name not in act_mapping:
                return None
                
            act_info = act_mapping[act_name]
            
            # Extract context around the citation
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(content), match.end() + 100)
            excerpt = content[start_pos:end_pos].strip()
            
            # Calculate confidence based on context
            confidence = self._calculate_citation_confidence(full_match, excerpt)
            
            section_title = await self._get_section_title(act_name, section_number)
            
            return KenyanLawCitation(
                source=act_info["source"],
                section=f"Section {section_number}" if section_number else "General Reference",
                title=section_title,
                relevance=self._determine_relevance(excerpt),
                url=f"{act_info['base_url']}#{section_number}" if section_number else act_info["base_url"],
                confidence=confidence,
                excerpt=excerpt,
                legal_area=act_info["legal_area"],
                citation_type="statute"
            )
            
        except Exception as e:
            logger.error(f"Error creating citation: {e}")
            return None
    
    async def _get_section_title(self, act_name: str, section_number: str) -> str:
        """Get the title of a specific section from cached legal data"""
        if not section_number:
            return "General Reference"
            
        # Predefined section titles for common acts
        section_titles = {
            "employment_act": {
                "9": "Written particulars of employment",
                "35": "Notice of termination", 
                "41": "Termination procedures",
                "45": "Severance pay",
                "56": "Working time",
                "5": "Basic employment terms"
            },
            "constitution": {
                "27": "Equality and freedom from discrimination",
                "41": "Labour relations",
                "47": "Fair administrative action"
            }
        }
        
        return section_titles.get(act_name, {}).get(section_number, f"Section {section_number}")
    
    def _calculate_citation_confidence(self, citation: str, context: str) -> float:
        """Calculate confidence score for a citation based on context"""
        base_confidence = 0.7
        
        # Increase confidence for specific section references
        if re.search(r"Section\s*\d+", citation):
            base_confidence += 0.15
            
        # Increase confidence for formal legal language in context
        legal_indicators = [
            "pursuant to", "in accordance with", "as provided", 
            "under the provisions", "subject to", "notwithstanding"
        ]
        
        for indicator in legal_indicators:
            if indicator.lower() in context.lower():
                base_confidence += 0.05
                break
                
        return min(base_confidence, 1.0)
    
    def _determine_relevance(self, excerpt: str) -> str:
        """Determine the relevance of a citation based on context"""
        if any(word in excerpt.lower() for word in ["termination", "notice", "dismissal"]):
            return "Termination procedures and notice requirements"
        elif any(word in excerpt.lower() for word in ["salary", "wage", "payment", "compensation"]):
            return "Salary and compensation provisions"
        elif any(word in excerpt.lower() for word in ["probation", "trial", "initial"]):
            return "Probationary period requirements"
        else:
            return "General employment law provisions"
    
    def _deduplicate_citations(self, citations: List[KenyanLawCitation]) -> List[KenyanLawCitation]:
        """Remove duplicate citations"""
        seen = set()
        unique_citations = []
        
        for citation in citations:
            key = (citation.source, citation.section)
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)
                
        return unique_citations
    
    async def check_employment_act_compliance(self, content: str, document_type: str) -> ComplianceAnalysis:
        """Check compliance with Employment Act 2007"""
        try:
            if document_type != "employment_contract":
                return ComplianceAnalysis(
                    overall_score=0.0,
                    kenyan_law_compliance=False,
                    compliance_details={},
                    missing_requirements=[],
                    recommendations=["Document type not supported for employment law compliance"],
                    critical_gaps=[]
                )
            
            rules = self.compliance_rules["employment_contract"]
            compliance_details = {}
            missing_requirements = []
            recommendations = []
            
            # Check for required clauses
            for clause in rules["required_clauses"]:
                if await self._check_clause_present(content, clause):
                    compliance_details[clause] = "compliant"
                else:
                    compliance_details[clause] = "missing"
                    missing_requirements.append(f"Missing {clause.replace('_', ' ')} clause")
            
            # Calculate overall score
            compliant_count = sum(1 for status in compliance_details.values() if status == "compliant")
            overall_score = compliant_count / len(rules["required_clauses"])
            
            # Generate recommendations
            if overall_score < 0.8:
                recommendations.extend([
                    "Review Employment Act 2007 Section 9 for written particulars requirements",
                    "Ensure all mandatory clauses are included",
                    "Consider legal review before finalization"
                ])
            
            # Identify critical gaps
            critical_gaps = []
            if overall_score < 0.5:
                critical_gaps.append("Major compliance deficiencies identified")
            if "termination_procedures" in missing_requirements:
                critical_gaps.append("Missing termination procedures - high legal risk")
            if "notice_period" in missing_requirements:
                critical_gaps.append("Notice period requirements not specified")

            return ComplianceAnalysis(
                overall_score=overall_score,
                kenyan_law_compliance=overall_score >= 0.8,
                compliance_details=compliance_details,
                missing_requirements=missing_requirements,
                recommendations=recommendations,
                critical_gaps=critical_gaps
            )
            
        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            return ComplianceAnalysis(
                overall_score=0.0,
                kenyan_law_compliance=False,
                compliance_details={},
                missing_requirements=[],
                recommendations=["Error occurred during compliance check"],
                critical_gaps=["Unable to assess compliance due to error"]
            )
    
    async def _check_clause_present(self, content: str, clause_type: str) -> bool:
        """Check if a specific clause type is present in the document"""
        clause_patterns = {
            "probation_period": r"probation(?:ary)?\s*period",
            "notice_period": r"notice\s*period|termination\s*notice",
            "termination_procedures": r"termination|dismissal|end(?:ing)?\s*(?:of\s*)?employment",
            "salary_details": r"salary|wage|remuneration|compensation",
            "working_hours": r"working\s*hours?|work(?:ing)?\s*time"
        }
        
        pattern = clause_patterns.get(clause_type, clause_type)
        return bool(re.search(pattern, content, re.IGNORECASE))

    async def extract_document_intelligence(self, content: str) -> DocumentIntelligence:
        """Extract intelligent document information using AI and pattern matching"""
        try:
            # Detect document type
            document_type = await self._detect_document_type(content)

            # Extract parties
            parties = await self._extract_parties(content)

            # Extract key dates
            key_dates = await self._extract_dates(content)

            # Extract financial terms
            financial_terms = await self._extract_financial_terms(content)

            # Extract critical clauses
            critical_clauses = await self._extract_critical_clauses(content, document_type)

            # Extract contract-specific information
            contract_duration = await self._extract_contract_duration(content)
            governing_law = await self._extract_governing_law(content)
            dispute_resolution = await self._extract_dispute_resolution(content)

            return DocumentIntelligence(
                document_type_detected=document_type,
                language="english",
                jurisdiction="kenya",
                parties_identified=parties,
                key_dates=key_dates,
                financial_terms=financial_terms,
                critical_clauses=critical_clauses,
                contract_duration=contract_duration,
                governing_law=governing_law,
                dispute_resolution=dispute_resolution
            )

        except Exception as e:
            logger.error(f"Error extracting document intelligence: {e}")
            return DocumentIntelligence(
                document_type_detected="unknown",
                language="english",
                jurisdiction="kenya",
                parties_identified=[],
                key_dates=[],
                financial_terms=[],
                critical_clauses=[]
            )

    async def _detect_document_type(self, content: str) -> str:
        """Detect the type of legal document"""
        content_lower = content.lower()

        if any(term in content_lower for term in ["employment", "employee", "employer", "job", "position"]):
            return "employment_contract"
        elif any(term in content_lower for term in ["lease", "rent", "tenant", "landlord", "premises"]):
            return "lease_agreement"
        elif any(term in content_lower for term in ["sale", "purchase", "buyer", "seller", "goods"]):
            return "sale_agreement"
        elif any(term in content_lower for term in ["service", "services", "provider", "client"]):
            return "service_agreement"
        elif any(term in content_lower for term in ["loan", "credit", "borrower", "lender"]):
            return "loan_agreement"
        else:
            return "general_contract"

    async def _extract_parties(self, content: str) -> List[str]:
        """Extract party names from the document"""
        parties = []

        # Pattern for company names (ending with Ltd, Limited, Inc, etc.)
        company_pattern = r'\b([A-Z][a-zA-Z\s&]+(?:Ltd|Limited|Inc|Corporation|Corp|Company|Co\.?))\b'
        companies = re.findall(company_pattern, content)
        parties.extend(companies[:5])  # Limit to first 5 matches

        # Pattern for individual names (Title + First + Last)
        name_pattern = r'\b(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b'
        individuals = re.findall(name_pattern, content)
        parties.extend(individuals[:3])  # Limit to first 3 matches

        return list(set(parties))  # Remove duplicates

    async def _extract_dates(self, content: str) -> List[str]:
        """Extract important dates from the document"""
        dates = []

        # Various date patterns
        date_patterns = [
            r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b',
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',
            r'\b(\d{4}-\d{2}-\d{2})\b',
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b'
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dates.extend(matches)

        return list(set(dates))[:10]  # Remove duplicates, limit to 10

    async def _extract_financial_terms(self, content: str) -> List[str]:
        """Extract financial terms and amounts"""
        financial_terms = []

        # Kenyan Shilling patterns
        kes_patterns = [
            r'KES\s*[\d,]+(?:\.\d{2})?',
            r'Kshs?\s*[\d,]+(?:\.\d{2})?',
            r'Kenya\s*Shillings?\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*Kenya\s*Shillings?'
        ]

        for pattern in kes_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            financial_terms.extend(matches)

        # Salary/wage patterns
        salary_patterns = [
            r'salary\s*of\s*[^\n]+',
            r'monthly\s*(?:salary|wage|pay)\s*[^\n]+',
            r'annual\s*(?:salary|wage|compensation)\s*[^\n]+'
        ]

        for pattern in salary_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            financial_terms.extend([match[:100] for match in matches])  # Truncate long matches

        return list(set(financial_terms))[:8]  # Remove duplicates, limit to 8

    async def _extract_critical_clauses(self, content: str, document_type: str) -> List[str]:
        """Extract critical clauses based on document type"""
        clauses = []

        if document_type == "employment_contract":
            clause_patterns = {
                "termination": r'termination[^.]*\.',
                "probation": r'probation(?:ary)?[^.]*\.',
                "confidentiality": r'confidential(?:ity)?[^.]*\.',
                "non_compete": r'non[- ]?compete[^.]*\.',
                "notice_period": r'notice\s*period[^.]*\.'
            }
        elif document_type == "lease_agreement":
            clause_patterns = {
                "rent_payment": r'rent[^.]*payment[^.]*\.',
                "maintenance": r'maintenance[^.]*\.',
                "deposit": r'deposit[^.]*\.',
                "termination": r'termination[^.]*\.'
            }
        else:
            clause_patterns = {
                "termination": r'termination[^.]*\.',
                "liability": r'liability[^.]*\.',
                "governing_law": r'governing\s*law[^.]*\.'
            }

        for clause_type, pattern in clause_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                clauses.append(clause_type)

        return clauses

    async def _extract_contract_duration(self, content: str) -> Optional[str]:
        """Extract contract duration information"""
        duration_patterns = [
            r'(?:term|duration|period)\s*(?:of|is|shall\s*be)\s*([^.]+)',
            r'(\d+\s*(?:year|month|day)s?)',
            r'from\s*[^.]*to\s*([^.]+)'
        ]

        for pattern in duration_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]  # Truncate if too long

        return None

    async def _extract_governing_law(self, content: str) -> Optional[str]:
        """Extract governing law clause"""
        law_patterns = [
            r'governed\s*by\s*(?:the\s*)?laws?\s*of\s*([^.]+)',
            r'subject\s*to\s*(?:the\s*)?laws?\s*of\s*([^.]+)',
            r'in\s*accordance\s*with\s*(?:the\s*)?laws?\s*of\s*([^.]+)'
        ]

        for pattern in law_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]

        return "Kenya" if "kenya" in content.lower() else None

    async def _extract_dispute_resolution(self, content: str) -> Optional[str]:
        """Extract dispute resolution mechanism"""
        dispute_patterns = [
            r'dispute(?:s)?\s*(?:shall\s*be|will\s*be|are\s*to\s*be)\s*([^.]+)',
            r'arbitration[^.]*',
            r'mediation[^.]*',
            r'court(?:s)?\s*of\s*([^.]+)'
        ]

        for pattern in dispute_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0).strip()[:150]  # Return full match, truncated

        return None
