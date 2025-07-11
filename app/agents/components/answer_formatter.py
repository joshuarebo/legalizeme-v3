"""
Answer Formatter Component - Context-aware response formatting
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .base_component import BaseComponent, ComponentResult, ComponentStatus, ComponentError

logger = logging.getLogger(__name__)

@dataclass
class FormattingStrategy:
    """Configuration for answer formatting strategy"""
    name: str
    structure: List[str]  # Ordered list of sections
    max_length: int = 2000
    include_confidence: bool = True
    include_citations: bool = True
    include_disclaimer: bool = True
    use_markdown: bool = True
    professional_tone: bool = True

class AnswerFormatter(BaseComponent):
    """
    Context-aware answer formatter that creates professional,
    well-structured legal responses based on context requirements
    """
    
    def __init__(self, context_manager=None):
        super().__init__("AnswerFormatter", context_manager)
        
        # Formatting strategies
        self.strategies = {
            "standard": FormattingStrategy(
                name="standard",
                structure=["executive_summary", "legal_analysis", "relevant_law", "citations", "recommendations"],
                max_length=1500,
                include_confidence=True,
                include_citations=True,
                include_disclaimer=True
            ),
            "comprehensive": FormattingStrategy(
                name="comprehensive",
                structure=["executive_summary", "legal_analysis", "reasoning_chain", "legal_principles", 
                          "counterarguments", "practical_implications", "relevant_law", "citations", 
                          "recommendations", "confidence_assessment"],
                max_length=2500,
                include_confidence=True,
                include_citations=True,
                include_disclaimer=True
            ),
            "concise": FormattingStrategy(
                name="concise",
                structure=["executive_summary", "key_points", "citations"],
                max_length=800,
                include_confidence=True,
                include_citations=True,
                include_disclaimer=False
            ),
            "technical": FormattingStrategy(
                name="technical",
                structure=["legal_analysis", "statutory_provisions", "case_law", "reasoning_chain", 
                          "legal_principles", "citations", "technical_recommendations"],
                max_length=2000,
                include_confidence=True,
                include_citations=True,
                professional_tone=True
            ),
            "practical": FormattingStrategy(
                name="practical",
                structure=["executive_summary", "immediate_actions", "compliance_requirements", 
                          "risk_assessment", "next_steps", "citations"],
                max_length=1200,
                include_confidence=False,
                include_citations=True,
                include_disclaimer=True
            )
        }
        
        # Standard disclaimers
        self.disclaimers = {
            "general": "This response provides general legal information and should not be considered as legal advice. For specific legal matters, please consult with a qualified legal practitioner.",
            "urgent": "This is general legal information. For urgent legal matters, please seek immediate professional legal advice.",
            "complex": "This analysis covers complex legal matters. Professional legal consultation is strongly recommended for specific applications."
        }
    
    async def _initialize_component(self):
        """Initialize the formatter"""
        pass  # No special initialization needed
    
    async def _validate_input(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate formatting input"""
        required_fields = ["query"]
        
        for field in required_fields:
            if field not in input_data:
                return {"valid": False, "error": f"Field '{field}' is required for answer formatting"}
        
        # At least one content field should be present
        content_fields = ["summary", "reasoning_chain", "legal_principles", "answer"]
        if not any(field in input_data for field in content_fields):
            return {"valid": False, "error": "At least one content field (summary, reasoning_chain, legal_principles, or answer) is required"}
        
        return {"valid": True}
    
    async def _execute_component(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute context-aware answer formatting"""
        
        # Select formatting strategy based on context
        strategy = self._select_formatting_strategy(context, input_data)
        
        # Extract all available content
        content_data = self._extract_content_data(input_data)
        
        # Build structured sections
        sections = await self._build_sections(content_data, strategy, context)
        
        # Format the final answer
        formatted_answer = self._format_final_answer(sections, strategy, context)
        
        # Add metadata and quality indicators
        formatting_metadata = self._generate_formatting_metadata(sections, strategy, content_data)
        
        return {
            "formatted_answer": formatted_answer,
            "sections": sections,
            "strategy_used": strategy.name,
            "word_count": len(formatted_answer.split()),
            "formatting_metadata": formatting_metadata,
            "quality_indicators": self._assess_quality_indicators(formatted_answer, strategy)
        }
    
    def _select_formatting_strategy(self, context: Dict[str, Any], input_data: Dict[str, Any]) -> FormattingStrategy:
        """Select appropriate formatting strategy based on context"""
        
        # Check for explicit strategy in input
        if "formatting_strategy" in input_data and input_data["formatting_strategy"] in self.strategies:
            return self.strategies[input_data["formatting_strategy"]]
        
        # Analyze context for strategy selection
        query_complexity = context.get("query_complexity", {})
        urgency_analysis = context.get("urgency_analysis", {})
        response_context = context.get("response_context", {})
        
        # Check response context preferences
        formatting_prefs = response_context.get("formatting", {})
        if "structure" in formatting_prefs:
            preferred_structure = formatting_prefs["structure"]
            if preferred_structure == "comprehensive":
                return self.strategies["comprehensive"]
            elif preferred_structure == "concise":
                return self.strategies["concise"]
        
        # High urgency -> concise format
        if urgency_analysis.get("level") == "high":
            return self.strategies["concise"]
        
        # High complexity -> comprehensive format
        if query_complexity.get("level") == "high":
            return self.strategies["comprehensive"]
        
        # Practical questions -> practical format
        query_lower = input_data.get("query", "").lower()
        practical_indicators = ["how to", "what should", "next steps", "procedure", "process"]
        if any(indicator in query_lower for indicator in practical_indicators):
            return self.strategies["practical"]
        
        # Technical/legal analysis -> technical format
        if any(domain in ["employment", "contract"] for domain in context.get("detected_domains", [])):
            return self.strategies["technical"]
        
        # Default to standard format
        return self.strategies["standard"]
    
    def _extract_content_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and organize all available content data"""
        
        return {
            "query": input_data.get("query", ""),
            "summary": input_data.get("summary", ""),
            "reasoning_chain": input_data.get("reasoning_chain", []),
            "legal_principles": input_data.get("legal_principles", []),
            "counterarguments": input_data.get("counterarguments", []),
            "practical_implications": input_data.get("practical_implications", []),
            "citations": input_data.get("citations", []),
            "key_insights": input_data.get("key_insights", []),
            "confidence": input_data.get("confidence", 0.0),
            "reasoning_confidence": input_data.get("reasoning_confidence", 0.0),
            "answer": input_data.get("answer", ""),
            "strategy_used": input_data.get("strategy_used", ""),
            "documents_processed": input_data.get("documents_processed", 0)
        }
    
    async def _build_sections(
        self,
        content_data: Dict[str, Any],
        strategy: FormattingStrategy,
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Build structured sections based on strategy"""
        
        sections = {}
        
        for section_name in strategy.structure:
            section_content = await self._build_section(section_name, content_data, strategy, context)
            if section_content:
                sections[section_name] = section_content
        
        return sections
    
    async def _build_section(
        self,
        section_name: str,
        content_data: Dict[str, Any],
        strategy: FormattingStrategy,
        context: Dict[str, Any]
    ) -> str:
        """Build a specific section"""
        
        if section_name == "executive_summary":
            return self._build_executive_summary(content_data, strategy)
        
        elif section_name == "legal_analysis":
            return self._build_legal_analysis(content_data, strategy)
        
        elif section_name == "reasoning_chain":
            return self._build_reasoning_chain(content_data, strategy)
        
        elif section_name == "legal_principles":
            return self._build_legal_principles(content_data, strategy)
        
        elif section_name == "counterarguments":
            return self._build_counterarguments(content_data, strategy)
        
        elif section_name == "practical_implications":
            return self._build_practical_implications(content_data, strategy)
        
        elif section_name == "relevant_law":
            return self._build_relevant_law(content_data, strategy, context)
        
        elif section_name == "citations":
            return self._build_citations(content_data, strategy)
        
        elif section_name == "recommendations":
            return self._build_recommendations(content_data, strategy)
        
        elif section_name == "confidence_assessment":
            return self._build_confidence_assessment(content_data, strategy)
        
        elif section_name == "key_points":
            return self._build_key_points(content_data, strategy)
        
        elif section_name == "immediate_actions":
            return self._build_immediate_actions(content_data, strategy)
        
        elif section_name == "compliance_requirements":
            return self._build_compliance_requirements(content_data, strategy)
        
        elif section_name == "risk_assessment":
            return self._build_risk_assessment(content_data, strategy)
        
        elif section_name == "next_steps":
            return self._build_next_steps(content_data, strategy)
        
        elif section_name == "statutory_provisions":
            return self._build_statutory_provisions(content_data, strategy, context)
        
        elif section_name == "case_law":
            return self._build_case_law(content_data, strategy)
        
        elif section_name == "technical_recommendations":
            return self._build_technical_recommendations(content_data, strategy)
        
        return ""
    
    def _build_executive_summary(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build executive summary section"""
        
        summary = content_data.get("summary", "")
        answer = content_data.get("answer", "")
        
        # Use existing summary or answer as base
        base_content = summary or answer
        
        if not base_content:
            return ""
        
        # Truncate if too long for executive summary
        if len(base_content) > 300:
            sentences = base_content.split('. ')
            truncated = '. '.join(sentences[:3]) + '.'
            return truncated
        
        return base_content
    
    def _build_legal_analysis(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build legal analysis section"""
        
        summary = content_data.get("summary", "")
        reasoning_chain = content_data.get("reasoning_chain", [])
        
        analysis_parts = []
        
        if summary:
            analysis_parts.append(summary)
        
        if reasoning_chain:
            reasoning_text = "\n\n".join([f"• {step}" for step in reasoning_chain[:5]])
            analysis_parts.append(f"**Legal Reasoning:**\n{reasoning_text}")
        
        return "\n\n".join(analysis_parts)
    
    def _build_reasoning_chain(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build reasoning chain section"""
        
        reasoning_chain = content_data.get("reasoning_chain", [])
        
        if not reasoning_chain:
            return ""
        
        formatted_steps = []
        for i, step in enumerate(reasoning_chain, 1):
            formatted_steps.append(f"{i}. {step}")
        
        return "\n\n".join(formatted_steps)
    
    def _build_legal_principles(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build legal principles section"""
        
        principles = content_data.get("legal_principles", [])
        
        if not principles:
            return ""
        
        formatted_principles = []
        for principle in principles:
            formatted_principles.append(f"• {principle}")
        
        return "\n".join(formatted_principles)

    def _build_counterarguments(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build counterarguments section"""

        counterarguments = content_data.get("counterarguments", [])

        if not counterarguments:
            return ""

        formatted_args = []
        for arg in counterarguments:
            formatted_args.append(f"• {arg}")

        return "\n".join(formatted_args)

    def _build_practical_implications(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build practical implications section"""

        implications = content_data.get("practical_implications", [])

        if not implications:
            return ""

        formatted_implications = []
        for implication in implications:
            formatted_implications.append(f"• {implication}")

        return "\n".join(formatted_implications)

    def _build_relevant_law(self, content_data: Dict[str, Any], strategy: FormattingStrategy, context: Dict[str, Any]) -> str:
        """Build relevant law section"""

        # Extract relevant law from context
        domain_context = context.get("domain_context", {})
        primary_sources = domain_context.get("primary_sources", [])
        detected_domains = context.get("detected_domains", [])

        law_parts = []

        # Add primary sources relevant to detected domains
        if primary_sources and detected_domains:
            relevant_sources = []
            for source in primary_sources:
                source_lower = source.lower()
                for domain in detected_domains:
                    if domain in source_lower:
                        relevant_sources.append(source)
                        break

            if relevant_sources:
                law_parts.append("**Primary Legal Sources:**")
                for source in relevant_sources[:3]:
                    law_parts.append(f"• {source}")

        # Add legal concepts if available
        legal_concepts = domain_context.get("legal_concepts", [])
        if legal_concepts:
            law_parts.append("**Key Legal Concepts:**")
            for concept in legal_concepts[:3]:
                law_parts.append(f"• {concept}")

        return "\n".join(law_parts)

    def _build_citations(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build citations section"""

        citations = content_data.get("citations", [])

        if not citations:
            return ""

        formatted_citations = []
        for i, citation in enumerate(citations, 1):
            if isinstance(citation, dict):
                formal_citation = citation.get("formal_citation", citation.get("title", "Unknown"))
                url = citation.get("url")

                if url:
                    formatted_citations.append(f"{i}. {formal_citation} - {url}")
                else:
                    formatted_citations.append(f"{i}. {formal_citation}")
            else:
                formatted_citations.append(f"{i}. {citation}")

        return "\n".join(formatted_citations)

    def _build_recommendations(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build recommendations section"""

        practical_implications = content_data.get("practical_implications", [])

        if not practical_implications:
            return "Consider consulting with a qualified legal practitioner for specific guidance on this matter."

        # Filter implications that sound like recommendations
        recommendations = []
        for implication in practical_implications:
            if any(word in implication.lower() for word in ["should", "must", "consider", "ensure", "recommend"]):
                recommendations.append(f"• {implication}")

        if not recommendations:
            recommendations = [f"• {impl}" for impl in practical_implications[:3]]

        return "\n".join(recommendations)

    def _build_confidence_assessment(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build confidence assessment section"""

        confidence = content_data.get("confidence", 0.0)
        reasoning_confidence = content_data.get("reasoning_confidence", 0.0)

        # Use the higher of the two confidence scores
        overall_confidence = max(confidence, reasoning_confidence)

        confidence_level = "High" if overall_confidence >= 0.8 else "Medium" if overall_confidence >= 0.6 else "Low"
        confidence_percentage = f"{overall_confidence * 100:.0f}%"

        assessment = f"**Confidence Level:** {confidence_level} ({confidence_percentage})\n\n"

        # Add explanation based on confidence level
        if overall_confidence >= 0.8:
            assessment += "This analysis is based on clear legal principles and well-established sources."
        elif overall_confidence >= 0.6:
            assessment += "This analysis is reasonably well-supported, though some aspects may require further clarification."
        else:
            assessment += "This analysis has limitations and should be verified with additional legal research."

        return assessment

    def _build_key_points(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build key points section (for concise format)"""

        key_insights = content_data.get("key_insights", [])
        legal_principles = content_data.get("legal_principles", [])

        key_points = []

        # Add key insights
        for insight in key_insights[:3]:
            key_points.append(f"• {insight}")

        # Add legal principles if no insights
        if not key_points:
            for principle in legal_principles[:3]:
                key_points.append(f"• {principle}")

        return "\n".join(key_points)

    def _build_immediate_actions(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build immediate actions section"""

        implications = content_data.get("practical_implications", [])

        # Filter for immediate/urgent actions
        immediate_actions = []
        for implication in implications:
            if any(word in implication.lower() for word in ["immediate", "urgent", "must", "shall", "now"]):
                immediate_actions.append(f"• {implication}")

        if not immediate_actions and implications:
            # Take first few implications as immediate actions
            immediate_actions = [f"• {impl}" for impl in implications[:2]]

        return "\n".join(immediate_actions)

    def _build_compliance_requirements(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build compliance requirements section"""

        implications = content_data.get("practical_implications", [])

        # Filter for compliance-related items
        compliance_items = []
        for implication in implications:
            if any(word in implication.lower() for word in ["comply", "requirement", "regulation", "standard"]):
                compliance_items.append(f"• {implication}")

        if not compliance_items:
            return "• Review applicable legal requirements\n• Ensure compliance with relevant regulations"

        return "\n".join(compliance_items)

    def _build_risk_assessment(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build risk assessment section"""

        counterarguments = content_data.get("counterarguments", [])
        confidence = content_data.get("confidence", 0.0)

        risk_items = []

        # Add risks based on counterarguments
        for arg in counterarguments[:2]:
            risk_items.append(f"• Risk: {arg}")

        # Add confidence-based risk assessment
        if confidence < 0.7:
            risk_items.append("• Risk: Legal position may be subject to different interpretations")

        if not risk_items:
            risk_items = ["• Consider potential legal challenges", "• Review for compliance gaps"]

        return "\n".join(risk_items)

    def _build_next_steps(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build next steps section"""

        implications = content_data.get("practical_implications", [])

        # Filter for action-oriented items
        next_steps = []
        for implication in implications:
            if any(word in implication.lower() for word in ["next", "follow", "proceed", "contact", "file"]):
                next_steps.append(f"• {implication}")

        if not next_steps:
            next_steps = [
                "• Consult with a qualified legal practitioner",
                "• Review relevant documentation",
                "• Consider implementation timeline"
            ]

        return "\n".join(next_steps)

    def _build_statutory_provisions(self, content_data: Dict[str, Any], strategy: FormattingStrategy, context: Dict[str, Any]) -> str:
        """Build statutory provisions section"""

        # Extract from citations that are statutory
        citations = content_data.get("citations", [])
        statutory_citations = []

        for citation in citations:
            if isinstance(citation, dict):
                doc_type = citation.get("document_type", "")
                title = citation.get("title", "")
                if "act" in doc_type.lower() or "act" in title.lower():
                    formal_citation = citation.get("formal_citation", title)
                    statutory_citations.append(f"• {formal_citation}")

        if not statutory_citations:
            # Use domain context
            domain_context = context.get("domain_context", {})
            primary_sources = domain_context.get("primary_sources", [])
            detected_domains = context.get("detected_domains", [])

            for source in primary_sources[:3]:
                if any(domain in source.lower() for domain in detected_domains):
                    statutory_citations.append(f"• {source}")

        return "\n".join(statutory_citations)

    def _build_case_law(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build case law section"""

        # Extract from citations that are cases
        citations = content_data.get("citations", [])
        case_citations = []

        for citation in citations:
            if isinstance(citation, dict):
                doc_type = citation.get("document_type", "")
                title = citation.get("title", "")
                if "case" in doc_type.lower() or any(word in title.lower() for word in ["v.", "vs.", "case"]):
                    formal_citation = citation.get("formal_citation", title)
                    case_citations.append(f"• {formal_citation}")

        return "\n".join(case_citations)

    def _build_technical_recommendations(self, content_data: Dict[str, Any], strategy: FormattingStrategy) -> str:
        """Build technical recommendations section"""

        implications = content_data.get("practical_implications", [])
        legal_principles = content_data.get("legal_principles", [])

        tech_recommendations = []

        # Add principle-based recommendations
        for principle in legal_principles[:2]:
            tech_recommendations.append(f"• Apply principle: {principle}")

        # Add technical implications
        for implication in implications[:3]:
            if any(word in implication.lower() for word in ["technical", "procedure", "process", "documentation"]):
                tech_recommendations.append(f"• {implication}")

        if not tech_recommendations:
            tech_recommendations = [
                "• Ensure technical compliance with legal requirements",
                "• Document all relevant procedures and decisions"
            ]

        return "\n".join(tech_recommendations)

    def _format_final_answer(
        self,
        sections: Dict[str, str],
        strategy: FormattingStrategy,
        context: Dict[str, Any]
    ) -> str:
        """Format the final answer with all sections"""

        answer_parts = []

        # Add sections in the order specified by strategy
        for section_name in strategy.structure:
            if section_name in sections and sections[section_name]:
                # Format section header
                header = self._format_section_header(section_name, strategy)
                content = sections[section_name]

                if strategy.use_markdown:
                    answer_parts.append(f"{header}\n{content}")
                else:
                    answer_parts.append(f"{header}\n{content}")

        # Join sections
        formatted_answer = "\n\n".join(answer_parts)

        # Add disclaimer if required
        if strategy.include_disclaimer:
            disclaimer = self._select_disclaimer(context)
            formatted_answer += f"\n\n**Disclaimer:** {disclaimer}"

        # Ensure length limit
        if len(formatted_answer) > strategy.max_length:
            formatted_answer = self._truncate_answer(formatted_answer, strategy.max_length)

        return formatted_answer

    def _format_section_header(self, section_name: str, strategy: FormattingStrategy) -> str:
        """Format section header based on strategy"""

        # Header mapping
        header_map = {
            "executive_summary": "## Executive Summary",
            "legal_analysis": "## Legal Analysis",
            "reasoning_chain": "## Legal Reasoning",
            "legal_principles": "## Legal Principles",
            "counterarguments": "## Alternative Considerations",
            "practical_implications": "## Practical Implications",
            "relevant_law": "## Relevant Law",
            "citations": "## Citations",
            "recommendations": "## Recommendations",
            "confidence_assessment": "## Confidence Assessment",
            "key_points": "## Key Points",
            "immediate_actions": "## Immediate Actions",
            "compliance_requirements": "## Compliance Requirements",
            "risk_assessment": "## Risk Assessment",
            "next_steps": "## Next Steps",
            "statutory_provisions": "## Statutory Provisions",
            "case_law": "## Case Law",
            "technical_recommendations": "## Technical Recommendations"
        }

        if strategy.use_markdown:
            return header_map.get(section_name, f"## {section_name.replace('_', ' ').title()}")
        else:
            header = header_map.get(section_name, section_name.replace('_', ' ').title())
            return header.replace("## ", "").upper()

    def _select_disclaimer(self, context: Dict[str, Any]) -> str:
        """Select appropriate disclaimer based on context"""

        urgency_analysis = context.get("urgency_analysis", {})
        query_complexity = context.get("query_complexity", {})

        if urgency_analysis.get("level") == "high":
            return self.disclaimers["urgent"]
        elif query_complexity.get("level") == "high":
            return self.disclaimers["complex"]
        else:
            return self.disclaimers["general"]

    def _truncate_answer(self, answer: str, max_length: int) -> str:
        """Truncate answer while preserving structure"""

        if len(answer) <= max_length:
            return answer

        # Try to truncate at section boundaries
        sections = answer.split("\n\n")
        truncated_sections = []
        current_length = 0

        for section in sections:
            if current_length + len(section) + 2 <= max_length:  # +2 for \n\n
                truncated_sections.append(section)
                current_length += len(section) + 2
            else:
                # Try to fit a partial section
                remaining_space = max_length - current_length - 50  # Leave space for truncation notice
                if remaining_space > 100:
                    partial_section = section[:remaining_space] + "..."
                    truncated_sections.append(partial_section)
                break

        truncated_answer = "\n\n".join(truncated_sections)

        # Add truncation notice if needed
        if len(truncated_answer) < len(answer):
            truncated_answer += "\n\n*[Response truncated due to length limits]*"

        return truncated_answer

    def _generate_formatting_metadata(
        self,
        sections: Dict[str, str],
        strategy: FormattingStrategy,
        content_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate metadata about the formatting process"""

        return {
            "sections_included": list(sections.keys()),
            "sections_count": len(sections),
            "strategy_name": strategy.name,
            "includes_citations": strategy.include_citations and bool(content_data.get("citations")),
            "includes_confidence": strategy.include_confidence,
            "includes_disclaimer": strategy.include_disclaimer,
            "uses_markdown": strategy.use_markdown,
            "content_sources": {
                "has_summary": bool(content_data.get("summary")),
                "has_reasoning": bool(content_data.get("reasoning_chain")),
                "has_principles": bool(content_data.get("legal_principles")),
                "has_citations": bool(content_data.get("citations")),
                "has_implications": bool(content_data.get("practical_implications"))
            }
        }

    def _assess_quality_indicators(self, formatted_answer: str, strategy: FormattingStrategy) -> Dict[str, Any]:
        """Assess quality indicators of the formatted answer"""

        word_count = len(formatted_answer.split())
        char_count = len(formatted_answer)

        # Count sections
        section_count = formatted_answer.count("##") if strategy.use_markdown else formatted_answer.count("\n\n")

        # Check for key quality indicators
        has_citations = "citations" in formatted_answer.lower() or any(char in formatted_answer for char in ["1.", "2.", "3."])
        has_legal_terms = any(term in formatted_answer.lower() for term in ["section", "act", "law", "court", "legal"])
        has_structure = section_count >= 3

        # Calculate quality score
        quality_factors = [
            word_count >= 200,  # Sufficient length
            word_count <= strategy.max_length,  # Within limits
            has_citations,  # Includes citations
            has_legal_terms,  # Uses legal terminology
            has_structure,  # Well-structured
            section_count >= len(strategy.structure) * 0.6  # Most sections included
        ]

        quality_score = sum(quality_factors) / len(quality_factors)

        return {
            "word_count": word_count,
            "character_count": char_count,
            "section_count": section_count,
            "has_citations": has_citations,
            "has_legal_terms": has_legal_terms,
            "has_structure": has_structure,
            "quality_score": quality_score,
            "quality_level": "High" if quality_score >= 0.8 else "Medium" if quality_score >= 0.6 else "Low"
        }

    async def _calculate_confidence(self, output_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate confidence based on formatting quality"""

        quality_indicators = output_data.get("quality_indicators", {})
        formatting_metadata = output_data.get("formatting_metadata", {})

        # Base confidence on quality score
        quality_score = quality_indicators.get("quality_score", 0.5)

        # Adjust based on completeness
        sections_included = formatting_metadata.get("sections_count", 0)
        content_sources = formatting_metadata.get("content_sources", {})

        # Bonus for having multiple content sources
        content_diversity = sum(1 for has_content in content_sources.values() if has_content)
        diversity_bonus = min(content_diversity / 5, 0.2)  # Up to 20% bonus

        # Penalty for very short responses
        word_count = quality_indicators.get("word_count", 0)
        length_penalty = 0.1 if word_count < 100 else 0.0

        confidence = quality_score + diversity_bonus - length_penalty
        return min(1.0, max(0.0, confidence))
