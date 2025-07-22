"""
Compliance Analyzer Service for CounselDocs
Analyzes documents for Kenya Law compliance with key areas and recommendations.
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from .kenya_law_crawler import kenya_law_crawler

logger = logging.getLogger(__name__)

class ComplianceAnalyzer:
    """
    Analyzes documents for compliance with Kenyan law.
    Provides key areas for attention, recommendations, and citations.
    """
    
    def __init__(self):
        """Initialize compliance analyzer with AWS Bedrock"""
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Use Titan Text Premier for analysis
        self.analysis_model_id = settings.AWS_BEDROCK_TITAN_TEXT_PREMIER_MODEL_ID
        
        # Compliance frameworks for different document types
        self.compliance_frameworks = {
            'employment_contract': {
                'name': 'Employment Act 2007 Compliance',
                'key_areas': [
                    'Written particulars of employment',
                    'Minimum wage compliance',
                    'Working hours and overtime',
                    'Annual leave entitlements',
                    'Notice periods for termination',
                    'Termination procedures',
                    'Dispute resolution mechanisms',
                    'Health and safety provisions'
                ],
                'legal_basis': 'Employment Act 2007, Constitution of Kenya 2010'
            },
            'service_agreement': {
                'name': 'Contract Law Compliance',
                'key_areas': [
                    'Offer and acceptance clarity',
                    'Consideration adequacy',
                    'Legal capacity of parties',
                    'Lawful object and purpose',
                    'Payment terms and conditions',
                    'Intellectual property rights',
                    'Termination clauses',
                    'Dispute resolution'
                ],
                'legal_basis': 'Law of Contract Act, Constitution of Kenya 2010'
            },
            'lease_agreement': {
                'name': 'Landlord and Tenant Act Compliance',
                'key_areas': [
                    'Rent control compliance',
                    'Security deposit regulations',
                    'Maintenance responsibilities',
                    'Notice periods for termination',
                    'Tenant rights protection',
                    'Property condition standards',
                    'Dispute resolution procedures'
                ],
                'legal_basis': 'Landlord and Tenant (Shops, Hotels and Catering Establishments) Act'
            },
            'general': {
                'name': 'General Legal Compliance',
                'key_areas': [
                    'Constitutional compliance',
                    'Legal capacity and authority',
                    'Lawful purpose and object',
                    'Proper execution requirements',
                    'Governing law provisions',
                    'Jurisdiction clauses',
                    'Force majeure provisions'
                ],
                'legal_basis': 'Constitution of Kenya 2010, Various Acts'
            }
        }
    
    async def analyze_document_compliance(
        self, 
        document_content: str, 
        document_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze document for Kenya Law compliance.
        
        Args:
            document_content: Extracted document text
            document_type: Type of document (employment_contract, etc.)
            user_id: User identifier for caching
            
        Returns:
            Comprehensive compliance analysis
        """
        start_time = datetime.utcnow()
        
        try:
            # Detect document type if not provided
            if not document_type:
                document_type = await self._detect_document_type(document_content)
            
            # Get compliance framework
            framework = self.compliance_frameworks.get(document_type, self.compliance_frameworks['general'])
            
            # Extract key areas requiring attention
            key_areas = await self._identify_key_areas(document_content, framework)
            
            # Generate compliance analysis
            compliance_analysis = await self._analyze_compliance(document_content, framework, key_areas)
            
            # Get relevant citations
            citations = await self._get_relevant_citations(document_content, document_type)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                document_content, framework, compliance_analysis, key_areas
            )
            
            # Calculate overall compliance score
            compliance_score = self._calculate_compliance_score(compliance_analysis, key_areas)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(compliance_analysis, citations)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'success': True,
                'document_type_detected': document_type,
                'compliance_framework': framework['name'],
                'legal_basis': framework['legal_basis'],
                'compliance_score': compliance_score,
                'confidence_score': confidence_score,
                'key_areas': key_areas,
                'compliance_analysis': compliance_analysis,
                'recommendations': recommendations,
                'citations': citations,
                'processing_time_seconds': processing_time,
                'analyzed_at': start_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Compliance analysis failed: {str(e)}")
            return {
                'success': False,
                'error': f"Analysis failed: {str(e)}",
                'error_type': 'analysis_error'
            }
    
    async def _detect_document_type(self, content: str) -> str:
        """Detect document type from content"""
        
        content_lower = content.lower()
        
        # Employment-related keywords
        employment_keywords = ['employment', 'employee', 'employer', 'salary', 'wages', 'job', 'position', 'work']
        if any(keyword in content_lower for keyword in employment_keywords):
            return 'employment_contract'
        
        # Service agreement keywords
        service_keywords = ['service', 'consultant', 'contractor', 'professional services', 'deliverables']
        if any(keyword in content_lower for keyword in service_keywords):
            return 'service_agreement'
        
        # Lease agreement keywords
        lease_keywords = ['lease', 'rent', 'tenant', 'landlord', 'premises', 'property']
        if any(keyword in content_lower for keyword in lease_keywords):
            return 'lease_agreement'
        
        return 'general'
    
    async def _identify_key_areas(self, content: str, framework: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify key areas requiring attention in the document"""
        
        key_areas = []
        
        for area in framework['key_areas']:
            # Analyze each key area
            area_analysis = await self._analyze_key_area(content, area, framework)
            key_areas.append(area_analysis)
        
        # Sort by priority (issues first)
        key_areas.sort(key=lambda x: (x['status'] != 'issue', x['importance']))
        
        return key_areas
    
    async def _analyze_key_area(self, content: str, area: str, framework: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a specific key area"""
        
        prompt = f"""
        Analyze the following legal document for compliance with Kenyan law regarding: {area}
        
        Legal Framework: {framework['legal_basis']}
        
        Document Content:
        {content[:3000]}  # Limit content for analysis
        
        Please analyze:
        1. Is this area properly addressed in the document?
        2. What specific issues or gaps exist?
        3. How critical is this area (scale 1-5)?
        4. What immediate attention is needed?
        
        Respond in JSON format:
        {{
            "area": "{area}",
            "status": "compliant|issue|missing",
            "importance": 1-5,
            "description": "Brief description of findings",
            "issues": ["list of specific issues"],
            "attention_required": "What the user should focus on"
        }}
        """
        
        try:
            response = await self._call_bedrock_model(prompt)
            
            # Parse JSON response
            try:
                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    'area': area,
                    'status': 'unknown',
                    'importance': 3,
                    'description': 'Analysis could not be parsed',
                    'issues': ['Unable to analyze this area'],
                    'attention_required': f'Manual review required for {area}'
                }
                
        except Exception as e:
            logger.error(f"Key area analysis failed for {area}: {e}")
            return {
                'area': area,
                'status': 'error',
                'importance': 3,
                'description': f'Analysis failed: {str(e)}',
                'issues': ['Analysis error occurred'],
                'attention_required': f'Manual review required for {area}'
            }
    
    async def _analyze_compliance(
        self, 
        content: str, 
        framework: Dict[str, Any], 
        key_areas: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform comprehensive compliance analysis"""
        
        # Summarize key area issues
        issues = []
        for area in key_areas:
            if area['status'] in ['issue', 'missing']:
                issues.extend(area.get('issues', []))
        
        prompt = f"""
        Perform a comprehensive legal compliance analysis for this document under Kenyan law.
        
        Legal Framework: {framework['legal_basis']}
        Document Type: {framework['name']}
        
        Key Issues Identified:
        {json.dumps(issues, indent=2)}
        
        Document Content:
        {content[:4000]}  # Limit for analysis
        
        Provide a detailed compliance analysis covering:
        1. Overall compliance status
        2. Critical legal gaps
        3. Risk assessment
        4. Regulatory compliance
        5. Enforceability concerns
        
        Respond in JSON format with detailed analysis.
        """
        
        try:
            response = await self._call_bedrock_model(prompt)
            
            # Try to parse as JSON, fallback to structured text
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    'overall_status': 'requires_review',
                    'analysis_text': response,
                    'critical_gaps': issues[:5],  # Top 5 issues
                    'risk_level': 'medium'
                }
                
        except Exception as e:
            logger.error(f"Compliance analysis failed: {e}")
            return {
                'overall_status': 'analysis_failed',
                'error': str(e),
                'risk_level': 'unknown'
            }

    async def _get_relevant_citations(self, content: str, document_type: str) -> List[Dict[str, Any]]:
        """Get relevant Kenya Law citations for the document"""

        try:
            # Use Kenya Law crawler to find relevant citations
            citations = await kenya_law_crawler.get_citations_for_analysis(content)

            # Add document-type specific citations
            type_specific_citations = self._get_type_specific_citations(document_type)
            citations.extend(type_specific_citations)

            # Remove duplicates and sort by relevance
            unique_citations = []
            seen_texts = set()

            for citation in citations:
                citation_text = citation.get('text', '')
                if citation_text not in seen_texts:
                    unique_citations.append(citation)
                    seen_texts.add(citation_text)

            return unique_citations[:10]  # Top 10 most relevant

        except Exception as e:
            logger.error(f"Citation extraction failed: {e}")
            return self._get_type_specific_citations(document_type)

    def _get_type_specific_citations(self, document_type: str) -> List[Dict[str, Any]]:
        """Get standard citations for document type"""

        citations_map = {
            'employment_contract': [
                {
                    'text': 'Employment Act 2007',
                    'type': 'act',
                    'confidence': 0.95,
                    'source_url': 'https://new.kenyalaw.org/akn/ke/act/2007/11/eng@2012-12-31',
                    'relevance': 'Primary legislation for employment matters'
                },
                {
                    'text': 'Constitution of Kenya 2010, Article 41',
                    'type': 'constitution',
                    'confidence': 0.90,
                    'source_url': 'https://new.kenyalaw.org/akn/ke/act/2010/constitution/eng@2010-09-03',
                    'relevance': 'Fundamental rights of workers'
                }
            ],
            'court_document': [
                {
                    'text': 'Civil Procedure Rules 2010',
                    'type': 'rules',
                    'confidence': 0.95,
                    'source_url': 'https://new.kenyalaw.org/akn/ke/act/ln/2010/151/eng@2022-12-31',
                    'relevance': 'Court procedure requirements'
                },
                {
                    'text': 'Civil Procedure Act',
                    'type': 'act',
                    'confidence': 0.90,
                    'source_url': 'https://new.kenyalaw.org/legislation/',
                    'relevance': 'Civil court procedures'
                }
            ],
            'contract': [
                {
                    'text': 'Law of Contract Act',
                    'type': 'act',
                    'confidence': 0.90,
                    'source_url': 'https://new.kenyalaw.org/legislation/',
                    'relevance': 'Contract formation and enforcement'
                }
            ]
        }

        return citations_map.get(document_type, [])

    async def _generate_recommendations(
        self,
        content: str,
        framework: Dict[str, Any],
        compliance_analysis: Dict[str, Any],
        key_areas: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate specific recommendations for compliance"""

        recommendations = []

        # Generate recommendations for each key area with issues
        for area in key_areas:
            if area['status'] in ['issue', 'missing']:
                recommendation = await self._generate_area_recommendation(area, framework)
                recommendations.append(recommendation)

        # Add general recommendations based on document type
        general_recs = self._get_general_recommendations(framework)
        recommendations.extend(general_recs)

        # Sort by priority
        recommendations.sort(key=lambda x: -x.get('priority', 0))

        return recommendations[:15]  # Top 15 recommendations

    async def _generate_area_recommendation(self, area: Dict[str, Any], framework: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendation for specific area"""

        prompt = f"""
        Generate a specific recommendation for this legal compliance issue:

        Area: {area['area']}
        Issues: {area.get('issues', [])}
        Legal Framework: {framework['legal_basis']}

        Provide:
        1. Specific action to take
        2. Legal requirement to address
        3. Priority level (1-5)
        4. Implementation steps

        Respond as JSON:
        {{
            "area": "{area['area']}",
            "recommendation": "specific action",
            "legal_requirement": "what law requires",
            "priority": 1-5,
            "implementation_steps": ["step 1", "step 2"],
            "risk_if_ignored": "consequences"
        }}
        """

        try:
            response = await self._call_bedrock_model(prompt)

            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    'area': area['area'],
                    'recommendation': f"Address issues in {area['area']}",
                    'legal_requirement': framework['legal_basis'],
                    'priority': area.get('importance', 3),
                    'implementation_steps': ['Review and update document'],
                    'risk_if_ignored': 'Legal non-compliance'
                }

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return {
                'area': area['area'],
                'recommendation': f"Address issues in {area['area']}",
                'legal_requirement': framework['legal_basis'],
                'priority': area.get('importance', 3),
                'implementation_steps': ['Review and update document'],
                'risk_if_ignored': 'Legal non-compliance'
            }

    def _get_general_recommendations(self, framework: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get general recommendations for document type"""

        return [
            {
                'area': 'Legal Review',
                'recommendation': 'Have document reviewed by qualified legal counsel',
                'legal_requirement': 'Best practice for legal documents',
                'priority': 4,
                'implementation_steps': [
                    'Engage qualified lawyer',
                    'Review all terms and conditions',
                    'Ensure compliance with current law'
                ],
                'risk_if_ignored': 'Potential legal vulnerabilities'
            },
            {
                'area': 'Regular Updates',
                'recommendation': 'Review document annually for legal changes',
                'legal_requirement': 'Ongoing compliance maintenance',
                'priority': 3,
                'implementation_steps': [
                    'Set annual review schedule',
                    'Monitor legal developments',
                    'Update as needed'
                ],
                'risk_if_ignored': 'Outdated legal provisions'
            }
        ]

    def _calculate_compliance_score(self, analysis: Dict[str, Any], key_areas: List[Dict[str, Any]]) -> float:
        """Calculate overall compliance score (0.0 to 1.0)"""

        if not key_areas:
            return 0.5  # Default if no analysis

        total_score = 0
        total_weight = 0

        for area in key_areas:
            importance = area.get('importance', 3)
            status = area.get('status', 'unknown')

            # Score based on status
            if status == 'compliant':
                score = 1.0
            elif status == 'issue':
                score = 0.3
            elif status == 'missing':
                score = 0.0
            else:
                score = 0.5

            total_score += score * importance
            total_weight += importance

        if total_weight == 0:
            return 0.5

        return total_score / total_weight

    def _calculate_confidence_score(self, analysis: Dict[str, Any], citations: List[Dict[str, Any]]) -> float:
        """Calculate confidence in analysis (0.0 to 1.0)"""

        base_confidence = 0.7  # Base confidence in AI analysis

        # Increase confidence based on citations found
        citation_boost = min(len(citations) * 0.05, 0.2)  # Up to 0.2 boost

        # Increase confidence if analysis was successful
        if analysis.get('overall_status') == 'analysis_failed':
            base_confidence = 0.3

        return min(base_confidence + citation_boost, 1.0)

    async def _call_bedrock_model(self, prompt: str) -> str:
        """Call AWS Bedrock Titan model for analysis"""

        try:
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 2048,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            })

            response = self.bedrock_client.invoke_model(
                modelId=self.analysis_model_id,
                body=body,
                contentType='application/json'
            )

            response_body = json.loads(response['body'].read())
            return response_body['results'][0]['outputText']

        except Exception as e:
            logger.error(f"Bedrock model call failed: {e}")
            raise Exception(f"AI analysis failed: {str(e)}")

# Global instance
compliance_analyzer = ComplianceAnalyzer()
