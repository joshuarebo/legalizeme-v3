"""
GAIA Evaluator for Legal Benchmarks
Evaluates agent responses against benchmark criteria
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class EvaluationMetric(Enum):
    """Types of evaluation metrics"""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    LEGAL_REASONING = "legal_reasoning"
    CITATION_QUALITY = "citation_quality"
    SYNTHESIS = "synthesis"
    POLICY_AWARENESS = "policy_awareness"

@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics"""
    accuracy: float = 0.0
    completeness: float = 0.0
    legal_reasoning: float = 0.0
    citation_quality: float = 0.0
    synthesis: float = 0.0
    policy_awareness: float = 0.0
    overall_score: float = 0.0

class GAIAEvaluator:
    """
    Evaluates LegalResearchAgent responses against GAIA-style
    benchmark criteria for legal AI systems
    """
    
    def __init__(self):
        self.legal_terms_patterns = self._compile_legal_patterns()
        self.citation_patterns = self._compile_citation_patterns()
    
    def _compile_legal_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for legal terminology detection"""
        return {
            "acts": re.compile(r'\b(?:act|Act)\s+(?:20\d{2}|19\d{2}|\(CAP\s+\d+\))', re.IGNORECASE),
            "sections": re.compile(r'\b(?:section|Section|s\.|s)\s+\d+', re.IGNORECASE),
            "cases": re.compile(r'\b(?:v\.|vs\.|versus)\s+\w+', re.IGNORECASE),
            "legal_concepts": re.compile(r'\b(?:breach|liability|duty|obligation|right|remedy|damages|contract|tort|negligence|fiduciary|statutory|common law)\b', re.IGNORECASE)
        }
    
    def _compile_citation_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for citation detection"""
        return {
            "kenyan_acts": re.compile(r'\b(?:Employment|Companies|Land|Constitution|Criminal|Civil)\s+Act\s+(?:20\d{2}|19\d{2})', re.IGNORECASE),
            "cap_references": re.compile(r'\(CAP\s+\d+\)', re.IGNORECASE),
            "section_references": re.compile(r'[Ss]ection\s+\d+(?:\(\d+\))?', re.IGNORECASE),
            "article_references": re.compile(r'[Aa]rticle\s+\d+', re.IGNORECASE)
        }
    
    async def evaluate_response(
        self,
        benchmark_case,
        agent_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate agent response against benchmark case"""
        
        response_text = self._extract_response_text(agent_response)
        ground_truth = benchmark_case.ground_truth
        evaluation_criteria = benchmark_case.evaluation_criteria
        
        # Perform individual evaluations
        accuracy_score = self._evaluate_accuracy(response_text, ground_truth, evaluation_criteria)
        completeness_score = self._evaluate_completeness(response_text, evaluation_criteria)
        reasoning_score = self._evaluate_legal_reasoning(response_text, evaluation_criteria)
        citation_score = self._evaluate_citation_quality(response_text, evaluation_criteria)
        
        # Advanced evaluations for Level 3 cases
        synthesis_score = 0.0
        policy_score = 0.0
        if benchmark_case.level >= 3:
            synthesis_score = self._evaluate_synthesis_quality(response_text, evaluation_criteria)
            policy_score = self._evaluate_policy_awareness(response_text, evaluation_criteria)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            accuracy_score, completeness_score, reasoning_score, 
            citation_score, synthesis_score, policy_score, benchmark_case.level
        )
        
        # Identify required elements
        required_elements_found, missing_elements = self._check_required_elements(
            response_text, evaluation_criteria
        )
        
        return {
            "overall_score": overall_score,
            "accuracy_score": accuracy_score,
            "completeness_score": completeness_score,
            "reasoning_score": reasoning_score,
            "citation_score": citation_score,
            "synthesis_score": synthesis_score,
            "policy_score": policy_score,
            "required_elements_found": required_elements_found,
            "missing_elements": missing_elements,
            "response_length": len(response_text),
            "legal_terms_count": self._count_legal_terms(response_text),
            "citations_count": self._count_citations(response_text)
        }
    
    def _extract_response_text(self, agent_response: Dict[str, Any]) -> str:
        """Extract text from agent response"""
        
        # Try different possible response fields
        text_fields = ["final_answer", "answer", "response", "formatted_answer", "summary"]
        
        for field in text_fields:
            if field in agent_response and agent_response[field]:
                return str(agent_response[field])
        
        # Fallback to string representation
        return str(agent_response)
    
    def _evaluate_accuracy(
        self,
        response_text: str,
        ground_truth: Dict[str, Any],
        evaluation_criteria: Dict[str, Any]
    ) -> float:
        """Evaluate accuracy of the response"""
        
        response_lower = response_text.lower()
        ground_truth_answer = ground_truth.get("answer", "").lower()
        
        # Check for exact answer match
        exact_match_score = 0.0
        if ground_truth_answer in response_lower:
            exact_match_score = 1.0
        
        # Check for acceptable variations
        variations_score = 0.0
        acceptable_variations = evaluation_criteria.get("acceptable_variations", [])
        for variation in acceptable_variations:
            if variation.lower() in response_lower:
                variations_score = 0.8
                break
        
        # Check for incorrect answers (penalty)
        incorrect_penalty = 0.0
        incorrect_answers = evaluation_criteria.get("incorrect_answers", [])
        for incorrect in incorrect_answers:
            if incorrect.lower() in response_lower:
                incorrect_penalty = 0.3
                break
        
        # Calculate accuracy score
        accuracy = max(exact_match_score, variations_score) - incorrect_penalty
        return max(0.0, min(1.0, accuracy))
    
    def _evaluate_completeness(
        self,
        response_text: str,
        evaluation_criteria: Dict[str, Any]
    ) -> float:
        """Evaluate completeness of the response"""
        
        required_elements = evaluation_criteria.get("required_elements", [])
        if not required_elements:
            return 0.8  # Default score if no specific requirements
        
        response_lower = response_text.lower()
        found_elements = 0
        
        for element in required_elements:
            if isinstance(element, str) and element.lower() in response_lower:
                found_elements += 1
            elif isinstance(element, list):
                # OR condition - any of the elements in the list
                if any(e.lower() in response_lower for e in element):
                    found_elements += 1
        
        completeness = found_elements / len(required_elements)
        return min(1.0, completeness)
    
    def _evaluate_legal_reasoning(
        self,
        response_text: str,
        evaluation_criteria: Dict[str, Any]
    ) -> float:
        """Evaluate quality of legal reasoning"""
        
        reasoning_score = 0.0
        
        # Check for analysis components
        analysis_components = evaluation_criteria.get("analysis_components", [])
        if analysis_components:
            found_components = 0
            response_lower = response_text.lower()
            
            for component in analysis_components:
                # Simple keyword matching for analysis components
                keywords = component.lower().split()
                if any(keyword in response_lower for keyword in keywords):
                    found_components += 1
            
            reasoning_score += (found_components / len(analysis_components)) * 0.5
        
        # Check for legal reasoning indicators
        legal_reasoning = evaluation_criteria.get("legal_reasoning", [])
        if legal_reasoning:
            found_reasoning = 0
            response_lower = response_text.lower()
            
            for reasoning_element in legal_reasoning:
                keywords = reasoning_element.lower().split()
                if any(keyword in response_lower for keyword in keywords):
                    found_reasoning += 1
            
            reasoning_score += (found_reasoning / len(legal_reasoning)) * 0.5
        
        # Bonus for structured reasoning
        if self._has_structured_reasoning(response_text):
            reasoning_score += 0.2
        
        return min(1.0, reasoning_score)
    
    def _evaluate_citation_quality(
        self,
        response_text: str,
        evaluation_criteria: Dict[str, Any]
    ) -> float:
        """Evaluate quality of legal citations"""
        
        citation_score = 0.0
        
        # Count different types of citations
        kenyan_acts = len(self.citation_patterns["kenyan_acts"].findall(response_text))
        cap_refs = len(self.citation_patterns["cap_references"].findall(response_text))
        section_refs = len(self.citation_patterns["section_references"].findall(response_text))
        article_refs = len(self.citation_patterns["article_references"].findall(response_text))
        
        total_citations = kenyan_acts + cap_refs + section_refs + article_refs
        
        # Base score for having citations
        if total_citations > 0:
            citation_score += 0.4
        
        # Bonus for specific citation types
        if kenyan_acts > 0:
            citation_score += 0.3
        if section_refs > 0:
            citation_score += 0.2
        if cap_refs > 0:
            citation_score += 0.1
        
        # Check for bonus points in evaluation criteria
        bonus_points = evaluation_criteria.get("bonus_points", [])
        if bonus_points:
            response_lower = response_text.lower()
            found_bonus = sum(1 for bonus in bonus_points if bonus.lower() in response_lower)
            citation_score += (found_bonus / len(bonus_points)) * 0.2
        
        return min(1.0, citation_score)
    
    def _evaluate_synthesis_quality(
        self,
        response_text: str,
        evaluation_criteria: Dict[str, Any]
    ) -> float:
        """Evaluate synthesis quality for advanced cases"""
        
        synthesis_indicators = [
            "multiple", "various", "different", "combine", "integrate",
            "balance", "consider", "weigh", "competing", "conflicting"
        ]
        
        response_lower = response_text.lower()
        found_indicators = sum(1 for indicator in synthesis_indicators if indicator in response_lower)
        
        # Check for multi-domain analysis
        domains = ["employment", "contract", "property", "corporate", "constitutional", "criminal"]
        found_domains = sum(1 for domain in domains if domain in response_lower)
        
        synthesis_score = 0.0
        
        # Base score for synthesis indicators
        if found_indicators >= 3:
            synthesis_score += 0.5
        elif found_indicators >= 1:
            synthesis_score += 0.3
        
        # Bonus for multi-domain analysis
        if found_domains >= 2:
            synthesis_score += 0.5
        elif found_domains >= 1:
            synthesis_score += 0.2
        
        return min(1.0, synthesis_score)
    
    def _evaluate_policy_awareness(
        self,
        response_text: str,
        evaluation_criteria: Dict[str, Any]
    ) -> float:
        """Evaluate policy awareness for advanced cases"""
        
        policy_indicators = [
            "policy", "public interest", "social", "economic", "constitutional principles",
            "justice", "fairness", "equity", "protection", "rights", "development"
        ]
        
        response_lower = response_text.lower()
        found_indicators = sum(1 for indicator in policy_indicators if indicator in response_lower)
        
        policy_score = min(found_indicators / 5, 1.0)  # Normalize to max 1.0
        
        return policy_score
    
    def _has_structured_reasoning(self, response_text: str) -> bool:
        """Check if response has structured reasoning"""
        
        structure_indicators = [
            r'\b(?:first|second|third|finally|therefore|consequently|however|moreover)\b',
            r'\b(?:step \d+|point \d+|\d+\.|\(\d+\))\b',
            r'\b(?:analysis|conclusion|reasoning|argument)\b'
        ]
        
        for pattern in structure_indicators:
            if re.search(pattern, response_text, re.IGNORECASE):
                return True
        
        return False
    
    def _check_required_elements(
        self,
        response_text: str,
        evaluation_criteria: Dict[str, Any]
    ) -> tuple[List[str], List[str]]:
        """Check which required elements are present or missing"""
        
        required_elements = evaluation_criteria.get("required_elements", [])
        response_lower = response_text.lower()
        
        found_elements = []
        missing_elements = []
        
        for element in required_elements:
            if isinstance(element, str):
                if element.lower() in response_lower:
                    found_elements.append(element)
                else:
                    missing_elements.append(element)
            elif isinstance(element, list):
                # OR condition
                if any(e.lower() in response_lower for e in element):
                    found_elements.append(" OR ".join(element))
                else:
                    missing_elements.append(" OR ".join(element))
        
        return found_elements, missing_elements
    
    def _count_legal_terms(self, response_text: str) -> int:
        """Count legal terms in response"""
        
        total_count = 0
        for pattern in self.legal_terms_patterns.values():
            total_count += len(pattern.findall(response_text))
        
        return total_count
    
    def _count_citations(self, response_text: str) -> int:
        """Count citations in response"""
        
        total_count = 0
        for pattern in self.citation_patterns.values():
            total_count += len(pattern.findall(response_text))
        
        return total_count
    
    def _calculate_overall_score(
        self,
        accuracy: float,
        completeness: float,
        reasoning: float,
        citation: float,
        synthesis: float,
        policy: float,
        level: int
    ) -> float:
        """Calculate overall score based on level-specific weights"""
        
        if level == 1:
            # Basic level - focus on accuracy and completeness
            weights = {"accuracy": 0.5, "completeness": 0.3, "reasoning": 0.15, "citation": 0.05}
        elif level == 2:
            # Intermediate level - balanced evaluation
            weights = {"accuracy": 0.35, "completeness": 0.25, "reasoning": 0.25, "citation": 0.15}
        else:
            # Advanced level - emphasis on reasoning and synthesis
            weights = {"accuracy": 0.25, "completeness": 0.2, "reasoning": 0.25, "citation": 0.15, "synthesis": 0.1, "policy": 0.05}
        
        overall = (
            accuracy * weights.get("accuracy", 0) +
            completeness * weights.get("completeness", 0) +
            reasoning * weights.get("reasoning", 0) +
            citation * weights.get("citation", 0) +
            synthesis * weights.get("synthesis", 0) +
            policy * weights.get("policy", 0)
        )
        
        return min(1.0, overall)
