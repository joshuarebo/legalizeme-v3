"""
KENYAN LEGAL PROMPT OPTIMIZER
============================
Specialized prompt templates for different Kenyan legal areas with pre-computed context.
Designed for maximum accuracy and speed in legal responses.
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class LegalArea(Enum):
    """Kenyan legal practice areas"""
    EMPLOYMENT = "employment"
    COMPANY = "company"
    CONSTITUTIONAL = "constitutional"
    LAND = "land"
    FAMILY = "family"
    DATA_PROTECTION = "data_protection"
    CRIMINAL = "criminal"
    GENERAL = "general"

@dataclass
class PromptTemplate:
    """Optimized prompt template for specific legal area"""
    area: LegalArea
    system_context: str
    legal_framework: str
    response_format: str
    examples: List[str]
    keywords: List[str]

class KenyanLegalPromptOptimizer:
    """
    Optimized prompt engineering for Kenyan legal queries
    with pre-computed context and specialized templates
    """
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.legal_sources = self._initialize_legal_sources()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the prompt optimizer"""
        if self._initialized:
            return
        
        try:
            # Pre-compute common legal contexts
            await self._precompute_contexts()
            self._initialized = True
            logger.info("Kenyan Legal Prompt Optimizer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize prompt optimizer: {e}")
            self._initialized = True
    
    def optimize_prompt(
        self, 
        query: str, 
        legal_area: Optional[str] = None,
        query_type: str = "legal_query",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate optimized prompt for Kenyan legal query
        
        Args:
            query: User's legal question
            legal_area: Specific legal area (auto-detected if None)
            query_type: Type of query (legal_query, research, analysis)
            context: Additional context
            
        Returns:
            Optimized prompt string
        """
        try:
            # Detect legal area if not provided
            if not legal_area:
                legal_area = self._detect_legal_area(query)
            
            # Get appropriate template
            template = self.templates.get(legal_area, self.templates[LegalArea.GENERAL])
            
            # Build optimized prompt
            optimized_prompt = self._build_prompt(query, template, query_type, context)
            
            logger.debug(f"Optimized prompt for {legal_area}: {len(optimized_prompt)} chars")
            return optimized_prompt
            
        except Exception as e:
            logger.error(f"Error optimizing prompt: {e}")
            return self._fallback_prompt(query)
    
    def _initialize_templates(self) -> Dict[LegalArea, PromptTemplate]:
        """Initialize specialized prompt templates for each legal area"""
        return {
            LegalArea.EMPLOYMENT: PromptTemplate(
                area=LegalArea.EMPLOYMENT,
                system_context="""You are a Kenyan employment law expert with deep knowledge of:
- Employment Act 2007
- Labour Relations Act 2007
- Work Injury Benefits Act 2007
- Occupational Safety and Health Act 2007
- National Social Security Fund Act
- National Hospital Insurance Fund Act""",
                legal_framework="""KENYAN EMPLOYMENT LAW FRAMEWORK:

KEY LEGISLATION:
• Employment Act 2007 - Core employment rights and obligations
• Labour Relations Act 2007 - Trade unions, collective bargaining, disputes
• Work Injury Benefits Act 2007 - Workplace injury compensation
• Occupational Safety and Health Act 2007 - Workplace safety standards

EMPLOYMENT RIGHTS:
• Minimum wage: KES 15,201 per month (2024)
• Maximum working hours: 52 hours per week
• Annual leave: 21 working days minimum
• Maternity leave: 3 months (fully paid)
• Paternity leave: 2 weeks
• Sick leave: 7 days per year (full pay), 7 days (half pay)

TERMINATION PROCEDURES:
• Notice periods: 28 days (monthly paid), 7 days (others)
• Severance pay: 15 days per year of service
• Unfair dismissal protection
• Disciplinary procedures required

INSTITUTIONS:
• Employment and Labour Relations Court
• Ministry of Labour and Social Protection
• National Labour Board""",
                response_format="""Provide comprehensive guidance including:
1. Direct answer to the employment question
2. Relevant legal provisions and sections
3. Practical steps and procedures
4. Compliance requirements
5. Potential consequences of non-compliance
6. Recommended next actions""",
                examples=[
                    "Employment contract requirements under Employment Act 2007",
                    "Termination procedures and severance pay calculations",
                    "Maternity and paternity leave entitlements"
                ],
                keywords=["employment", "job", "work", "salary", "termination", "contract", "leave"]
            ),
            
            LegalArea.COMPANY: PromptTemplate(
                area=LegalArea.COMPANY,
                system_context="""You are a Kenyan company law expert with comprehensive knowledge of:
- Companies Act 2015
- Business Registration Service Act 2015
- Capital Markets Act
- Competition Act 2010
- Public Procurement and Asset Disposal Act 2015""",
                legal_framework="""KENYAN COMPANY LAW FRAMEWORK:

KEY LEGISLATION:
• Companies Act 2015 - Primary company law
• Business Registration Service Act 2015 - Registration procedures
• Capital Markets Act - Public companies and securities
• Competition Act 2010 - Anti-competitive practices

COMPANY TYPES:
• Private company limited by shares
• Public company limited by shares
• Company limited by guarantee
• Unlimited company

REGISTRATION PROCESS:
1. Name reservation (KES 1,000)
2. Prepare incorporation documents
3. Submit to Registrar of Companies
4. Pay registration fees (KES 10,000-20,000)
5. Obtain Certificate of Incorporation
6. Register for taxes (PIN, VAT)

DIRECTOR DUTIES:
• Fiduciary duty to company
• Duty of care and skill
• Avoid conflicts of interest
• Maintain proper records
• File annual returns

COMPLIANCE REQUIREMENTS:
• Annual returns filing
• Financial statements preparation
• Tax compliance (Corporate tax 30%)
• Statutory meetings""",
                response_format="""Provide detailed guidance covering:
1. Specific answer to company law question
2. Relevant Companies Act 2015 provisions
3. Step-by-step procedures
4. Required documents and fees
5. Compliance obligations
6. Penalties for non-compliance
7. Professional advice recommendations""",
                examples=[
                    "Company registration process and requirements",
                    "Director duties and liabilities under Companies Act 2015",
                    "Annual compliance requirements for private companies"
                ],
                keywords=["company", "business", "registration", "director", "shareholder", "incorporation"]
            ),

            LegalArea.GENERAL: PromptTemplate(
                area=LegalArea.GENERAL,
                system_context="""You are a Kenyan legal expert with comprehensive knowledge of Kenyan law across all practice areas including employment, company, constitutional, land, and family law.""",
                legal_framework="""KENYAN LEGAL SYSTEM OVERVIEW:

KEY LEGISLATION:
• Constitution of Kenya 2010 - Supreme law
• Employment Act 2007 - Employment matters
• Companies Act 2015 - Business and corporate law
• Land Act 2012 - Land and property matters
• Data Protection Act 2019 - Privacy and data rights

LEGAL INSTITUTIONS:
• Supreme Court of Kenya
• Court of Appeal
• High Court
• Specialized courts (Employment, Environment & Land, Family)
• Kenya Law Reform Commission""",
                response_format="""Provide comprehensive legal guidance including:
1. Direct answer to the legal question
2. Relevant Kenyan legal provisions
3. Practical steps and compliance requirements
4. Professional advice recommendations""",
                examples=[
                    "General legal inquiries about Kenyan law",
                    "Cross-cutting legal issues",
                    "Legal procedure questions"
                ],
                keywords=["law", "legal", "kenya", "rights", "procedure"]
            ),

            LegalArea.CONSTITUTIONAL: PromptTemplate(
                area=LegalArea.CONSTITUTIONAL,
                system_context="""You are a Kenyan constitutional law expert with expertise in:
- Constitution of Kenya 2010
- Bill of Rights (Chapter 4)
- Devolution and county governments
- Judicial system and access to justice
- Human rights jurisprudence""",
                legal_framework="""KENYAN CONSTITUTIONAL FRAMEWORK:

CONSTITUTION OF KENYA 2010:
• Supreme law of Kenya
• Bill of Rights (Articles 19-59)
• Devolved government structure
• Separation of powers

FUNDAMENTAL RIGHTS AND FREEDOMS:
• Right to life (Article 26)
• Freedom of expression (Article 33)
• Freedom of association (Article 36)
• Right to education (Article 43)
• Right to health (Article 43)
• Right to housing (Article 43)
• Right to fair trial (Article 50)

ENFORCEMENT MECHANISMS:
• High Court jurisdiction
• Constitutional petitions
• Kenya National Commission on Human Rights
• Commission on Administrative Justice (Ombudsman)

DEVOLUTION:
• 47 county governments
• Concurrent and exclusive functions
• County assemblies and governors""",
                response_format="""Provide constitutional analysis including:
1. Constitutional provisions applicable
2. Bill of Rights protections
3. Enforcement mechanisms available
4. Relevant court procedures
5. Precedent cases if applicable
6. Remedies and reliefs available""",
                examples=[
                    "Freedom of expression protections under Article 33",
                    "Right to fair trial guarantees in criminal proceedings",
                    "Access to information under Article 35"
                ],
                keywords=["constitution", "rights", "freedom", "bill of rights", "constitutional"]
            )
        }
    
    def _initialize_legal_sources(self) -> Dict[str, List[str]]:
        """Initialize authoritative Kenyan legal sources"""
        return {
            "primary_legislation": [
                "Constitution of Kenya 2010",
                "Employment Act 2007",
                "Companies Act 2015",
                "Land Act 2012",
                "Data Protection Act 2019"
            ],
            "institutions": [
                "Kenya Law (www.kenyalaw.org)",
                "Parliament of Kenya",
                "Judiciary of Kenya",
                "Kenya National Commission on Human Rights"
            ],
            "courts": [
                "Supreme Court of Kenya",
                "Court of Appeal",
                "High Court",
                "Employment and Labour Relations Court",
                "Environment and Land Court"
            ]
        }
    
    def _detect_legal_area(self, query: str) -> LegalArea:
        """Detect legal area from query content"""
        query_lower = query.lower()
        
        # Employment keywords
        if any(word in query_lower for word in ["employment", "job", "work", "salary", "termination", "contract", "leave"]):
            return LegalArea.EMPLOYMENT
        
        # Company keywords
        if any(word in query_lower for word in ["company", "business", "registration", "director", "incorporation"]):
            return LegalArea.COMPANY
        
        # Constitutional keywords
        if any(word in query_lower for word in ["constitution", "rights", "freedom", "bill of rights"]):
            return LegalArea.CONSTITUTIONAL
        
        # Land keywords
        if any(word in query_lower for word in ["land", "property", "title", "ownership"]):
            return LegalArea.LAND
        
        # Family keywords
        if any(word in query_lower for word in ["marriage", "divorce", "custody", "family"]):
            return LegalArea.FAMILY
        
        return LegalArea.GENERAL

    def _build_prompt(
        self,
        query: str,
        template: PromptTemplate,
        query_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build optimized prompt using template"""

        # Add context-specific instructions
        context_instructions = ""
        if context:
            if context.get("urgent"):
                context_instructions += "URGENT: Provide immediate practical guidance. "
            if context.get("jurisdiction"):
                context_instructions += f"Focus on {context['jurisdiction']} jurisdiction. "

        # Build the complete prompt
        prompt = f"""{template.system_context}

{template.legal_framework}

{context_instructions}

QUERY TYPE: {query_type.upper()}
USER QUESTION: {query}

{template.response_format}

IMPORTANT GUIDELINES:
• Cite specific legal provisions and section numbers
• Provide practical, actionable advice
• Recommend professional legal consultation for complex matters
• Include relevant deadlines and time limits
• Mention applicable fees and costs
• Reference authoritative sources (Kenya Law, Parliament, Courts)

Please provide a comprehensive response following the above framework."""

        return prompt

    def _fallback_prompt(self, query: str) -> str:
        """Fallback prompt for general queries"""
        return f"""As a Kenyan legal expert, please provide comprehensive guidance on: {query}

Please include:
1. Relevant Kenyan laws and regulations
2. Practical steps and procedures
3. Compliance requirements
4. Professional advice recommendations

Focus on Kenyan jurisdiction and current legal framework."""

    async def _precompute_contexts(self):
        """Pre-compute common legal contexts for faster responses"""
        try:
            # This could be expanded to pre-compute embeddings or other expensive operations
            logger.info("Pre-computed legal contexts for optimization")
        except Exception as e:
            logger.error(f"Error pre-computing contexts: {e}")

    def get_template_for_area(self, legal_area: str) -> Optional[PromptTemplate]:
        """Get template for specific legal area"""
        try:
            area_enum = LegalArea(legal_area.lower())
            return self.templates.get(area_enum)
        except ValueError:
            return self.templates.get(LegalArea.GENERAL)

    def get_available_areas(self) -> List[str]:
        """Get list of available legal areas"""
        return [area.value for area in LegalArea]

    def optimize_for_speed(self, query: str) -> str:
        """Generate speed-optimized prompt for direct queries"""
        legal_area = self._detect_legal_area(query)
        template = self.templates.get(legal_area, self.templates[LegalArea.GENERAL])

        # Simplified prompt for speed
        speed_prompt = f"""{template.system_context}

QUICK RESPONSE REQUIRED for: {query}

Provide concise, accurate guidance including:
1. Direct answer
2. Key legal provision
3. Next steps

Keep response focused and practical."""

        return speed_prompt

# Global prompt optimizer instance
kenyan_legal_prompt_optimizer = KenyanLegalPromptOptimizer()
