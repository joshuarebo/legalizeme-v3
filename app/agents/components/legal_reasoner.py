"""
Legal Reasoner Component - Context-aware legal reasoning and analysis
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .base_component import BaseComponent, ComponentResult, ComponentStatus, ComponentError
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

class ReasoningMode(Enum):
    """Different reasoning modes"""
    ANALYTICAL = "analytical"      # Step-by-step legal analysis
    COMPARATIVE = "comparative"    # Compare multiple legal positions
    PRECEDENTIAL = "precedential"  # Focus on precedents and case law
    STATUTORY = "statutory"        # Focus on statutory interpretation
    PRACTICAL = "practical"        # Focus on practical implications

@dataclass
class ReasoningStrategy:
    """Configuration for legal reasoning strategy"""
    name: str
    mode: ReasoningMode
    depth_level: str = "standard"  # "quick", "standard", "deep"
    include_precedents: bool = True
    include_counterarguments: bool = True
    include_practical_implications: bool = True
    confidence_threshold: float = 0.7
    max_reasoning_steps: int = 10

class LegalReasoner(BaseComponent):
    """
    Context-aware legal reasoning component that provides
    structured legal analysis and reasoning chains
    """
    
    def __init__(self, context_manager=None, ai_service=None):
        super().__init__("LegalReasoner", context_manager)
        self.ai_service = ai_service or AIService()
        
        # Reasoning strategies
        self.strategies = {
            "quick_analysis": ReasoningStrategy(
                name="quick_analysis",
                mode=ReasoningMode.ANALYTICAL,
                depth_level="quick",
                include_precedents=False,
                include_counterarguments=False,
                max_reasoning_steps=5
            ),
            "comprehensive_analysis": ReasoningStrategy(
                name="comprehensive_analysis",
                mode=ReasoningMode.ANALYTICAL,
                depth_level="deep",
                include_precedents=True,
                include_counterarguments=True,
                include_practical_implications=True,
                max_reasoning_steps=15
            ),
            "statutory_interpretation": ReasoningStrategy(
                name="statutory_interpretation",
                mode=ReasoningMode.STATUTORY,
                depth_level="standard",
                include_precedents=True,
                confidence_threshold=0.8
            ),
            "case_comparison": ReasoningStrategy(
                name="case_comparison",
                mode=ReasoningMode.COMPARATIVE,
                depth_level="standard",
                include_precedents=True,
                include_counterarguments=True
            ),
            "practical_guidance": ReasoningStrategy(
                name="practical_guidance",
                mode=ReasoningMode.PRACTICAL,
                depth_level="standard",
                include_practical_implications=True,
                confidence_threshold=0.6
            )
        }
    
    async def _initialize_component(self):
        """Initialize AI service"""
        # AI service is typically initialized elsewhere
        pass
    
    async def _validate_input(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate reasoning input"""
        required_fields = ["query", "summary"]
        
        for field in required_fields:
            if field not in input_data:
                return {"valid": False, "error": f"Field '{field}' is required for legal reasoning"}
        
        query = input_data["query"]
        summary = input_data["summary"]
        
        if not isinstance(query, str) or len(query.strip()) == 0:
            return {"valid": False, "error": "Query must be a non-empty string"}
        
        if not isinstance(summary, str) or len(summary.strip()) == 0:
            return {"valid": False, "error": "Summary must be a non-empty string"}
        
        return {"valid": True}
    
    async def _execute_component(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute context-aware legal reasoning"""
        
        query = input_data["query"]
        summary = input_data["summary"]
        citations = input_data.get("citations", [])
        key_insights = input_data.get("key_insights", [])
        
        # Select reasoning strategy based on context
        strategy = self._select_reasoning_strategy(context, input_data)
        
        # Analyze the legal question
        question_analysis = await self._analyze_legal_question(query, context, strategy)
        
        # Generate reasoning chain
        reasoning_chain = await self._generate_reasoning_chain(
            query, summary, citations, key_insights, question_analysis, strategy, context
        )
        
        # Identify legal principles
        legal_principles = self._identify_legal_principles(reasoning_chain, context)
        
        # Generate counterarguments if required
        counterarguments = []
        if strategy.include_counterarguments:
            counterarguments = await self._generate_counterarguments(
                reasoning_chain, question_analysis, strategy, context
            )
        
        # Assess practical implications
        practical_implications = []
        if strategy.include_practical_implications:
            practical_implications = await self._assess_practical_implications(
                reasoning_chain, question_analysis, strategy, context
            )
        
        # Calculate reasoning confidence
        reasoning_confidence = self._calculate_reasoning_confidence(
            reasoning_chain, legal_principles, strategy
        )
        
        return {
            "reasoning_chain": reasoning_chain,
            "legal_principles": legal_principles,
            "counterarguments": counterarguments,
            "practical_implications": practical_implications,
            "question_analysis": question_analysis,
            "reasoning_confidence": reasoning_confidence,
            "strategy_used": strategy.name,
            "reasoning_mode": strategy.mode.value
        }
    
    def _select_reasoning_strategy(self, context: Dict[str, Any], input_data: Dict[str, Any]) -> ReasoningStrategy:
        """Select appropriate reasoning strategy based on context"""
        
        # Check for explicit strategy in input
        if "reasoning_strategy" in input_data and input_data["reasoning_strategy"] in self.strategies:
            return self.strategies[input_data["reasoning_strategy"]]
        
        # Analyze context for strategy selection
        query_complexity = context.get("query_complexity", {})
        urgency_analysis = context.get("urgency_analysis", {})
        detected_domains = context.get("detected_domains", [])
        routing_rules = context.get("routing_rules", {})
        
        # High urgency -> quick analysis
        if urgency_analysis.get("level") == "high":
            return self.strategies["quick_analysis"]
        
        # Statutory focus -> statutory interpretation
        if "statutory_lookup" in routing_rules:
            return self.strategies["statutory_interpretation"]
        
        # Case law focus -> case comparison
        if "case_law_research" in routing_rules:
            return self.strategies["case_comparison"]
        
        # Practical questions -> practical guidance
        query_lower = input_data.get("query", "").lower()
        practical_indicators = ["how to", "what should", "next steps", "procedure", "process"]
        if any(indicator in query_lower for indicator in practical_indicators):
            return self.strategies["practical_guidance"]
        
        # High complexity -> comprehensive analysis
        if query_complexity.get("level") == "high":
            return self.strategies["comprehensive_analysis"]
        
        # Default to comprehensive analysis
        return self.strategies["comprehensive_analysis"]
    
    async def _analyze_legal_question(
        self,
        query: str,
        context: Dict[str, Any],
        strategy: ReasoningStrategy
    ) -> Dict[str, Any]:
        """Analyze the legal question to understand its structure and requirements"""
        
        prompt = f"""
Analyze the following legal question for Kenyan jurisdiction:

Question: {query}

Provide a structured analysis including:
1. Legal issue identification
2. Applicable areas of law
3. Key legal concepts involved
4. Type of legal question (interpretation, application, procedure, etc.)
5. Complexity level and reasoning requirements
6. Potential legal sources to consider

Analysis:"""
        
        try:
            result = await self.ai_service._generate_with_fallback(prompt, "legal_analysis")
            analysis_text = result.get("response", "")
            
            # Parse the analysis into structured format
            return self._parse_question_analysis(analysis_text, query, context)
            
        except Exception as e:
            logger.warning(f"Failed to analyze legal question: {e}")
            return self._create_fallback_analysis(query, context)
    
    def _parse_question_analysis(self, analysis_text: str, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI-generated analysis into structured format"""
        
        # Simple parsing - in production, this could be more sophisticated
        analysis = {
            "legal_issues": [],
            "applicable_law_areas": context.get("detected_domains", []),
            "key_concepts": [],
            "question_type": "general",
            "complexity_level": context.get("query_complexity", {}).get("level", "medium"),
            "analysis_text": analysis_text
        }
        
        # Extract key information from analysis text
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if "legal issue" in line.lower():
                current_section = "legal_issues"
            elif "applicable" in line.lower() and "law" in line.lower():
                current_section = "applicable_law_areas"
            elif "key concept" in line.lower():
                current_section = "key_concepts"
            elif "type" in line.lower() and "question" in line.lower():
                current_section = "question_type"
            elif line.startswith("-") or line.startswith("•"):
                if current_section and current_section != "question_type":
                    analysis[current_section].append(line[1:].strip())
        
        return analysis
    
    def _create_fallback_analysis(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback analysis when AI analysis fails"""
        
        return {
            "legal_issues": ["General legal inquiry"],
            "applicable_law_areas": context.get("detected_domains", ["general"]),
            "key_concepts": [],
            "question_type": "general",
            "complexity_level": context.get("query_complexity", {}).get("level", "medium"),
            "analysis_text": f"Analysis of query: {query}"
        }
    
    async def _generate_reasoning_chain(
        self,
        query: str,
        summary: str,
        citations: List[Dict[str, Any]],
        key_insights: List[str],
        question_analysis: Dict[str, Any],
        strategy: ReasoningStrategy,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate structured legal reasoning chain"""
        
        # Build context for reasoning
        reasoning_context = self._build_reasoning_context(
            summary, citations, key_insights, question_analysis, context
        )
        
        prompt = f"""
Provide step-by-step legal reasoning for the following question under Kenyan law:

Question: {query}

Legal Context:
{reasoning_context}

Question Analysis:
{question_analysis.get('analysis_text', '')}

Instructions:
1. Use {strategy.mode.value} reasoning approach
2. Provide {strategy.depth_level} level analysis
3. Create maximum {strategy.max_reasoning_steps} reasoning steps
4. {"Include relevant precedents and case law" if strategy.include_precedents else "Focus on statutory provisions"}
5. Each step should build logically on the previous steps
6. Cite specific legal provisions where applicable

Reasoning Steps:"""
        
        try:
            result = await self.ai_service._generate_with_fallback(prompt, "legal_reasoning")
            reasoning_text = result.get("response", "")
            
            # Parse reasoning into steps
            return self._parse_reasoning_steps(reasoning_text)
            
        except Exception as e:
            logger.warning(f"Failed to generate reasoning chain: {e}")
            return self._create_fallback_reasoning(query, question_analysis)
    
    def _build_reasoning_context(
        self,
        summary: str,
        citations: List[Dict[str, Any]],
        key_insights: List[str],
        question_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build comprehensive context for reasoning"""
        
        context_parts = []
        
        # Add summary
        if summary:
            context_parts.append(f"Document Summary:\n{summary}")
        
        # Add key insights
        if key_insights:
            insights_text = "\n".join(f"- {insight}" for insight in key_insights[:5])
            context_parts.append(f"Key Legal Insights:\n{insights_text}")
        
        # Add relevant citations
        if citations:
            citations_text = "\n".join([
                f"- {cite.get('formal_citation', cite.get('title', 'Unknown'))}"
                for cite in citations[:3]
            ])
            context_parts.append(f"Relevant Legal Sources:\n{citations_text}")
        
        # Add domain context
        domain_context = context.get("domain_context", {})
        primary_sources = domain_context.get("primary_sources", [])
        if primary_sources:
            sources_text = "\n".join(f"- {source}" for source in primary_sources[:3])
            context_parts.append(f"Primary Legal Sources:\n{sources_text}")
        
        return "\n\n".join(context_parts)

    def _parse_reasoning_steps(self, reasoning_text: str) -> List[str]:
        """Parse AI-generated reasoning into structured steps"""

        steps = []
        lines = reasoning_text.split('\n')

        current_step = ""
        step_indicators = ["step", "1.", "2.", "3.", "4.", "5.", "first", "second", "third", "therefore", "consequently"]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line starts a new step
            line_lower = line.lower()
            is_new_step = any(line_lower.startswith(indicator) for indicator in step_indicators)

            if is_new_step and current_step:
                # Save previous step
                steps.append(current_step.strip())
                current_step = line
            else:
                # Continue current step
                if current_step:
                    current_step += " " + line
                else:
                    current_step = line

        # Add final step
        if current_step:
            steps.append(current_step.strip())

        # Clean up steps
        cleaned_steps = []
        for step in steps:
            if len(step) > 20:  # Avoid very short steps
                # Remove step numbering for cleaner presentation
                cleaned_step = step
                for indicator in ["step 1:", "step 2:", "step 3:", "1.", "2.", "3."]:
                    if cleaned_step.lower().startswith(indicator):
                        cleaned_step = cleaned_step[len(indicator):].strip()
                        break
                cleaned_steps.append(cleaned_step)

        return cleaned_steps[:10]  # Limit to 10 steps

    def _create_fallback_reasoning(self, query: str, question_analysis: Dict[str, Any]) -> List[str]:
        """Create fallback reasoning when AI reasoning fails"""

        return [
            f"Legal question identified: {query}",
            f"Applicable law areas: {', '.join(question_analysis.get('applicable_law_areas', ['general']))}",
            "Analysis requires review of relevant statutory provisions",
            "Consider applicable case law and precedents",
            "Apply legal principles to the specific facts",
            "Determine legal position and implications"
        ]

    def _identify_legal_principles(self, reasoning_chain: List[str], context: Dict[str, Any]) -> List[str]:
        """Identify key legal principles from the reasoning chain"""

        principles = []

        # Keywords that indicate legal principles
        principle_indicators = [
            "principle", "rule", "doctrine", "test", "standard", "requirement",
            "burden of proof", "due process", "natural justice", "constitutional",
            "fundamental right", "legal duty", "obligation", "liability"
        ]

        for step in reasoning_chain:
            step_lower = step.lower()

            # Look for principle indicators
            for indicator in principle_indicators:
                if indicator in step_lower:
                    # Extract the sentence containing the principle
                    sentences = step.split('. ')
                    for sentence in sentences:
                        if indicator in sentence.lower():
                            principles.append(sentence.strip())
                            break
                    break

        # Remove duplicates and limit
        unique_principles = list(dict.fromkeys(principles))
        return unique_principles[:5]

    async def _generate_counterarguments(
        self,
        reasoning_chain: List[str],
        question_analysis: Dict[str, Any],
        strategy: ReasoningStrategy,
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate potential counterarguments to the reasoning"""

        reasoning_summary = "\n".join(reasoning_chain)

        prompt = f"""
Based on the following legal reasoning, identify potential counterarguments or alternative interpretations:

Legal Reasoning:
{reasoning_summary}

Legal Context: {question_analysis.get('analysis_text', '')}

Provide 3-5 potential counterarguments or alternative legal positions that could challenge this reasoning. Focus on:
1. Alternative statutory interpretations
2. Different case law applications
3. Policy considerations
4. Factual distinctions

Counterarguments:"""

        try:
            result = await self.ai_service._generate_with_fallback(prompt, "legal_counterarguments")
            counterarguments_text = result.get("response", "")

            # Parse counterarguments
            return self._parse_counterarguments(counterarguments_text)

        except Exception as e:
            logger.warning(f"Failed to generate counterarguments: {e}")
            return ["Alternative interpretations may exist", "Consider different factual scenarios"]

    def _parse_counterarguments(self, counterarguments_text: str) -> List[str]:
        """Parse AI-generated counterarguments"""

        counterarguments = []
        lines = counterarguments_text.split('\n')

        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('1.') or line.startswith('2.')):
                # Clean up formatting
                cleaned = line[1:].strip() if line.startswith(('-', '•')) else line[2:].strip()
                if len(cleaned) > 20:
                    counterarguments.append(cleaned)

        return counterarguments[:5]

    async def _assess_practical_implications(
        self,
        reasoning_chain: List[str],
        question_analysis: Dict[str, Any],
        strategy: ReasoningStrategy,
        context: Dict[str, Any]
    ) -> List[str]:
        """Assess practical implications of the legal reasoning"""

        reasoning_summary = "\n".join(reasoning_chain)

        prompt = f"""
Based on the following legal reasoning, identify practical implications and next steps:

Legal Reasoning:
{reasoning_summary}

Provide practical implications including:
1. Immediate actions required
2. Compliance considerations
3. Risk assessment
4. Procedural next steps
5. Documentation requirements

Practical Implications:"""

        try:
            result = await self.ai_service._generate_with_fallback(prompt, "practical_implications")
            implications_text = result.get("response", "")

            # Parse implications
            return self._parse_practical_implications(implications_text)

        except Exception as e:
            logger.warning(f"Failed to assess practical implications: {e}")
            return ["Consider practical implementation", "Review compliance requirements"]

    def _parse_practical_implications(self, implications_text: str) -> List[str]:
        """Parse AI-generated practical implications"""

        implications = []
        lines = implications_text.split('\n')

        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or
                        line.startswith('1.') or line.startswith('2.') or
                        any(word in line.lower() for word in ['should', 'must', 'consider', 'ensure'])):
                # Clean up formatting
                if line.startswith(('-', '•')):
                    cleaned = line[1:].strip()
                elif line[0].isdigit():
                    cleaned = line[2:].strip()
                else:
                    cleaned = line

                if len(cleaned) > 15:
                    implications.append(cleaned)

        return implications[:7]

    def _calculate_reasoning_confidence(
        self,
        reasoning_chain: List[str],
        legal_principles: List[str],
        strategy: ReasoningStrategy
    ) -> float:
        """Calculate confidence in the legal reasoning"""

        # Base confidence factors
        chain_length_factor = min(len(reasoning_chain) / 5, 1.0)  # Optimal around 5 steps
        principles_factor = min(len(legal_principles) / 3, 1.0)   # Optimal around 3 principles

        # Quality indicators in reasoning
        quality_indicators = [
            "section", "act", "case", "court", "held", "established",
            "according to", "under the", "pursuant to", "therefore", "consequently"
        ]

        quality_score = 0
        total_words = 0

        for step in reasoning_chain:
            words = step.lower().split()
            total_words += len(words)
            quality_score += sum(1 for word in words if word in quality_indicators)

        quality_factor = min(quality_score / max(total_words / 20, 1), 1.0) if total_words > 0 else 0

        # Combine factors
        confidence = 0.3 + (chain_length_factor * 0.3) + (principles_factor * 0.2) + (quality_factor * 0.2)

        return min(1.0, max(0.0, confidence))

    async def _calculate_confidence(self, output_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate overall confidence in the reasoning component output"""

        reasoning_chain = output_data.get("reasoning_chain", [])
        legal_principles = output_data.get("legal_principles", [])
        reasoning_confidence = output_data.get("reasoning_confidence", 0.0)

        # Use the calculated reasoning confidence as base
        base_confidence = reasoning_confidence

        # Adjust based on completeness
        completeness_factor = 1.0
        if not reasoning_chain:
            completeness_factor -= 0.3
        if not legal_principles:
            completeness_factor -= 0.2

        # Adjust based on context complexity
        query_complexity = context.get("query_complexity", {})
        if query_complexity.get("level") == "high" and len(reasoning_chain) < 5:
            completeness_factor -= 0.1

        final_confidence = base_confidence * completeness_factor
        return min(1.0, max(0.0, final_confidence))
