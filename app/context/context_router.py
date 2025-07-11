"""
Context Router - Intelligent routing based on context cues
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .context_blueprint import ContextBlueprint, QueryContext

logger = logging.getLogger(__name__)

class RoutingStrategy(Enum):
    """Available routing strategies"""
    DOCUMENT_FOCUSED = "document_focused"
    STATUTE_FOCUSED = "statute_focused"
    COMPREHENSIVE = "comprehensive"
    EMPLOYMENT_FOCUSED = "employment_focused"
    CONTRACT_FOCUSED = "contract_focused"
    QUICK = "quick"

@dataclass
class RoutingDecision:
    """Represents a routing decision"""
    strategy: RoutingStrategy
    tools: List[str]
    confidence: float
    reasoning: str
    context_factors: List[str]

class ContextRouter:
    """
    Intelligent router that makes tool and strategy decisions
    based on context analysis
    """
    
    def __init__(self, blueprint: ContextBlueprint):
        self.blueprint = blueprint
        self.routing_patterns = {}
        self.tool_mappings = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the context router"""
        try:
            # Load routing patterns from blueprint
            self._load_routing_patterns()
            
            # Initialize tool mappings
            self._initialize_tool_mappings()
            
            self._initialized = True
            logger.info("Context Router initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Context Router: {e}")
            raise
    
    def _load_routing_patterns(self):
        """Load routing patterns from the blueprint"""
        if not self.blueprint._loaded:
            self.blueprint.load_blueprint()
        
        routing_config = self.blueprint.blueprint_data.get("context_routing", {})
        
        for pattern_name, pattern_config in routing_config.items():
            self.routing_patterns[pattern_name] = {
                "triggers": pattern_config.get("triggers", []),
                "tools": pattern_config.get("tools", []),
                "strategy": pattern_config.get("strategy", "default"),
                "priority": pattern_config.get("priority", 1)
            }
    
    def _initialize_tool_mappings(self):
        """Initialize mappings between tools and their capabilities"""
        self.tool_mappings = {
            # Document processing tools
            "pdf_parser": {
                "capability": "document_parsing",
                "input_types": ["pdf", "document"],
                "output_types": ["text", "structured_data"]
            },
            "document_analyzer": {
                "capability": "document_analysis",
                "input_types": ["text", "document"],
                "output_types": ["analysis", "metadata"]
            },
            "clause_extractor": {
                "capability": "clause_extraction",
                "input_types": ["contract", "agreement"],
                "output_types": ["clauses", "structured_data"]
            },
            
            # Legal research tools
            "statute_search": {
                "capability": "statutory_research",
                "input_types": ["legal_query", "citation"],
                "output_types": ["statutes", "legal_text"]
            },
            "legal_database": {
                "capability": "legal_research",
                "input_types": ["legal_query"],
                "output_types": ["legal_documents", "cases"]
            },
            "citation_validator": {
                "capability": "citation_validation",
                "input_types": ["citation", "legal_reference"],
                "output_types": ["validation_result", "corrected_citation"]
            },
            
            # Case law tools
            "case_law_database": {
                "capability": "case_law_research",
                "input_types": ["legal_issue", "precedent_query"],
                "output_types": ["cases", "judgments"]
            },
            "precedent_analyzer": {
                "capability": "precedent_analysis",
                "input_types": ["cases", "legal_issue"],
                "output_types": ["precedent_analysis", "legal_reasoning"]
            },
            
            # Employment law tools
            "employment_act_search": {
                "capability": "employment_law_research",
                "input_types": ["employment_query"],
                "output_types": ["employment_law", "regulations"]
            },
            "labor_relations_db": {
                "capability": "labor_relations_research",
                "input_types": ["labor_query"],
                "output_types": ["labor_law", "tribunal_decisions"]
            },
            "employment_calculator": {
                "capability": "employment_calculations",
                "input_types": ["employment_scenario"],
                "output_types": ["calculations", "entitlements"]
            }
        }
    
    async def make_routing_decisions(
        self,
        context: Dict[str, Any],
        query_context: QueryContext
    ) -> Dict[str, Any]:
        """
        Make intelligent routing decisions based on context
        
        Args:
            context: Full context dictionary
            query_context: Query context information
            
        Returns:
            Dictionary of routing decisions
        """
        if not self._initialized:
            await self.initialize()
        
        routing_decisions = {}
        
        # Analyze query for routing cues
        routing_cues = self._analyze_routing_cues(query_context)
        
        # Apply routing patterns
        for pattern_name, pattern_config in self.routing_patterns.items():
            if self._check_pattern_match(routing_cues, pattern_config, query_context):
                routing_decisions[pattern_name] = pattern_config
        
        # If no patterns match, apply default routing
        if not routing_decisions:
            routing_decisions["default"] = self._get_default_routing(query_context)
        
        # Optimize routing decisions
        optimized_decisions = self._optimize_routing_decisions(routing_decisions, context)
        
        return optimized_decisions
    
    def _analyze_routing_cues(self, query_context: QueryContext) -> Dict[str, Any]:
        """Analyze the query for routing cues"""
        query = query_context.query.lower()
        
        cues = {
            "file_attached": query_context.file_attached,
            "query_length": len(query.split()),
            "contains_keywords": {},
            "legal_domains": [],
            "document_types": [],
            "urgency_indicators": []
        }
        
        # Keyword analysis
        keyword_categories = {
            "contract": ["contract", "agreement", "clause", "terms", "conditions"],
            "employment": ["employment", "job", "salary", "termination", "leave", "benefits"],
            "property": ["property", "land", "lease", "rent", "landlord", "tenant"],
            "statutory": ["law", "act", "section", "article", "statute", "regulation"],
            "procedural": ["procedure", "process", "steps", "requirements", "application"],
            "urgent": ["urgent", "emergency", "deadline", "court date", "immediate"]
        }
        
        for category, keywords in keyword_categories.items():
            matches = [kw for kw in keywords if kw in query]
            if matches:
                cues["contains_keywords"][category] = matches
                
                if category in ["contract", "employment", "property"]:
                    cues["legal_domains"].append(category)
                elif category == "urgent":
                    cues["urgency_indicators"].extend(matches)
        
        # Document type detection
        document_patterns = {
            "pdf": r"\b(pdf|document|file)\b",
            "contract": r"\b(contract|agreement)\b",
            "lease": r"\b(lease|rental)\b",
            "employment_contract": r"\b(employment contract|job contract)\b"
        }
        
        for doc_type, pattern in document_patterns.items():
            if re.search(pattern, query):
                cues["document_types"].append(doc_type)
        
        return cues
    
    def _check_pattern_match(
        self,
        routing_cues: Dict[str, Any],
        pattern_config: Dict[str, Any],
        query_context: QueryContext
    ) -> bool:
        """Check if a routing pattern matches the current context"""
        triggers = pattern_config.get("triggers", [])
        
        for trigger in triggers:
            if self._evaluate_trigger(trigger, routing_cues, query_context):
                return True
        
        return False
    
    def _evaluate_trigger(
        self,
        trigger: str,
        routing_cues: Dict[str, Any],
        query_context: QueryContext
    ) -> bool:
        """Evaluate a single trigger condition"""
        trigger = trigger.strip()
        
        # File attachment trigger
        if "file_attached:" in trigger:
            expected_value = "true" in trigger.lower()
            return routing_cues["file_attached"] == expected_value
        
        # Query contains trigger
        if "query contains:" in trigger:
            search_terms = trigger.split("query contains:")[1].strip().strip("'\"")
            terms = [term.strip().strip("'\"") for term in search_terms.split(",")]
            query_lower = query_context.query.lower()
            return any(term.lower() in query_lower for term in terms)
        
        # Domain context trigger
        if "domain_context:" in trigger:
            domain = trigger.split("domain_context:")[1].strip()
            return domain in routing_cues["legal_domains"]
        
        # Keyword category trigger
        if "contains_keywords:" in trigger:
            category = trigger.split("contains_keywords:")[1].strip()
            return category in routing_cues["contains_keywords"]
        
        # Complex trigger evaluation
        if "legal_terminology_detected:" in trigger:
            return len(routing_cues["contains_keywords"]) > 0
        
        if "complex_legal_issue:" in trigger:
            return (len(routing_cues["legal_domains"]) > 1 or 
                   routing_cues["query_length"] > 20)
        
        return False
    
    def _get_default_routing(self, query_context: QueryContext) -> Dict[str, Any]:
        """Get default routing when no patterns match"""
        return {
            "tools": ["legal_database", "statute_search"],
            "strategy": "comprehensive",
            "priority": 0
        }
    
    def _optimize_routing_decisions(
        self,
        routing_decisions: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize routing decisions to avoid conflicts and redundancy"""
        optimized = {}
        all_tools = set()
        strategies = []
        
        # Sort by priority (higher first)
        sorted_decisions = sorted(
            routing_decisions.items(),
            key=lambda x: x[1].get("priority", 0),
            reverse=True
        )
        
        for decision_name, decision_config in sorted_decisions:
            tools = decision_config.get("tools", [])
            strategy = decision_config.get("strategy", "default")
            
            # Add non-duplicate tools
            new_tools = [tool for tool in tools if tool not in all_tools]
            if new_tools:
                optimized[decision_name] = {
                    **decision_config,
                    "tools": new_tools
                }
                all_tools.update(new_tools)
                
                if strategy not in strategies:
                    strategies.append(strategy)
        
        # Select primary strategy
        if strategies:
            primary_strategy = strategies[0]  # Highest priority
            optimized["primary_strategy"] = primary_strategy
        
        return optimized
    
    def get_tool_capabilities(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get capabilities of a specific tool"""
        return self.tool_mappings.get(tool_name)
    
    def recommend_tools_for_capability(self, capability: str) -> List[str]:
        """Recommend tools that provide a specific capability"""
        recommended_tools = []
        
        for tool_name, tool_info in self.tool_mappings.items():
            if tool_info.get("capability") == capability:
                recommended_tools.append(tool_name)
        
        return recommended_tools
    
    def validate_tool_chain(self, tools: List[str]) -> Dict[str, Any]:
        """Validate that a chain of tools can work together"""
        validation_result = {
            "valid": True,
            "issues": [],
            "suggestions": []
        }
        
        if not tools:
            validation_result["valid"] = False
            validation_result["issues"].append("No tools specified")
            return validation_result
        
        # Check tool compatibility
        for i, tool in enumerate(tools):
            if tool not in self.tool_mappings:
                validation_result["issues"].append(f"Unknown tool: {tool}")
                validation_result["valid"] = False
                continue
            
            tool_info = self.tool_mappings[tool]
            
            # Check if tool can process input from previous tool
            if i > 0:
                prev_tool = tools[i-1]
                if prev_tool in self.tool_mappings:
                    prev_outputs = self.tool_mappings[prev_tool]["output_types"]
                    current_inputs = tool_info["input_types"]
                    
                    if not any(output in current_inputs for output in prev_outputs):
                        validation_result["issues"].append(
                            f"Tool {tool} cannot process output from {prev_tool}"
                        )
                        validation_result["suggestions"].append(
                            f"Consider adding a converter between {prev_tool} and {tool}"
                        )
        
        return validation_result
