"""
Context Blueprint - Loads and manages the context configuration
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ContextLayerType(Enum):
    """Types of context layers"""
    SYSTEM = "system_context"
    DOMAIN = "domain_context" 
    TASK = "task_context"
    INTERACTION = "interaction_context"
    RESPONSE = "response_context"

@dataclass
class ContextLayer:
    """Represents a single context layer"""
    layer_type: ContextLayerType
    data: Dict[str, Any]
    priority: int = 1
    active: bool = True

@dataclass
class QueryContext:
    """Context information for a specific query"""
    query: str
    query_type: str = "legal_research"
    user_context: Dict[str, Any] = field(default_factory=dict)
    file_attached: bool = False
    urgency_level: str = "normal"
    domain_hints: List[str] = field(default_factory=list)
    previous_queries: List[str] = field(default_factory=list)

class ContextBlueprint:
    """
    Manages the context blueprint configuration and provides
    context-aware decision making for the Legal Research Agent
    """
    
    def __init__(self, blueprint_path: Optional[str] = None):
        self.blueprint_path = blueprint_path or self._get_default_blueprint_path()
        self.blueprint_data: Dict[str, Any] = {}
        self.context_layers: Dict[ContextLayerType, ContextLayer] = {}
        self._loaded = False
        
    def _get_default_blueprint_path(self) -> str:
        """Get the default blueprint file path"""
        current_dir = Path(__file__).parent
        return str(current_dir / "context_blueprint.yaml")
    
    def load_blueprint(self) -> bool:
        """Load the context blueprint from YAML file"""
        try:
            with open(self.blueprint_path, 'r', encoding='utf-8') as file:
                self.blueprint_data = yaml.safe_load(file)
            
            # Initialize context layers
            self._initialize_context_layers()
            self._loaded = True
            
            logger.info(f"Context blueprint loaded successfully from {self.blueprint_path}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Context blueprint file not found: {self.blueprint_path}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"Error parsing context blueprint YAML: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading context blueprint: {e}")
            return False
    
    def _initialize_context_layers(self):
        """Initialize context layers from blueprint data"""
        for layer_type in ContextLayerType:
            layer_data = self.blueprint_data.get(layer_type.value, {})
            if layer_data:
                self.context_layers[layer_type] = ContextLayer(
                    layer_type=layer_type,
                    data=layer_data,
                    priority=self._get_layer_priority(layer_type),
                    active=True
                )
    
    def _get_layer_priority(self, layer_type: ContextLayerType) -> int:
        """Get priority for context layer (higher number = higher priority)"""
        priority_map = {
            ContextLayerType.SYSTEM: 5,      # Highest - core constraints
            ContextLayerType.DOMAIN: 4,      # High - legal domain knowledge
            ContextLayerType.TASK: 3,        # Medium - specific task context
            ContextLayerType.INTERACTION: 2, # Low - communication patterns
            ContextLayerType.RESPONSE: 1     # Lowest - formatting preferences
        }
        return priority_map.get(layer_type, 1)
    
    def get_context_for_query(self, query_context: QueryContext) -> Dict[str, Any]:
        """
        Get comprehensive context for a specific query
        
        Args:
            query_context: Query context information
            
        Returns:
            Merged context dictionary with all relevant layers
        """
        if not self._loaded:
            self.load_blueprint()
        
        merged_context = {
            "agent_name": self.blueprint_data.get("agent_name", "LegalResearchAgent"),
            "version": self.blueprint_data.get("version", "1.0.0"),
            "query_info": {
                "query": query_context.query,
                "query_type": query_context.query_type,
                "file_attached": query_context.file_attached,
                "urgency_level": query_context.urgency_level,
                "domain_hints": query_context.domain_hints
            }
        }
        
        # Merge context layers by priority (highest first)
        sorted_layers = sorted(
            self.context_layers.values(),
            key=lambda x: x.priority,
            reverse=True
        )
        
        for layer in sorted_layers:
            if layer.active:
                merged_context[layer.layer_type.value] = layer.data
        
        # Apply query-specific context enhancements
        merged_context = self._apply_query_specific_context(merged_context, query_context)
        
        return merged_context
    
    def _apply_query_specific_context(self, context: Dict[str, Any], query_context: QueryContext) -> Dict[str, Any]:
        """Apply query-specific context enhancements"""
        
        # Task-specific context
        task_context = context.get("task_context", {})
        query_types = task_context.get("query_types", {})
        
        if query_context.query_type in query_types:
            context["active_task_context"] = query_types[query_context.query_type]
        
        # Domain-specific enhancements
        domain_context = context.get("domain_context", {})
        legal_terminology = domain_context.get("legal_terminology", {})
        
        # Detect domain from query content
        detected_domains = self._detect_legal_domains(query_context.query, legal_terminology)
        if detected_domains:
            context["detected_domains"] = detected_domains
            context["domain_specific_terms"] = self._get_domain_terms(detected_domains, legal_terminology)
        
        # Routing context
        routing_rules = self.blueprint_data.get("context_routing", {})
        applicable_rules = self._get_applicable_routing_rules(query_context, routing_rules)
        if applicable_rules:
            context["routing_rules"] = applicable_rules
        
        return context
    
    def _detect_legal_domains(self, query: str, legal_terminology: Dict[str, List[str]]) -> List[str]:
        """Detect legal domains from query content"""
        detected_domains = []
        query_lower = query.lower()
        
        for domain, terms in legal_terminology.items():
            if any(term.lower() in query_lower for term in terms):
                detected_domains.append(domain)
        
        return detected_domains
    
    def _get_domain_terms(self, domains: List[str], legal_terminology: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Get relevant terms for detected domains"""
        domain_terms = {}
        for domain in domains:
            if domain in legal_terminology:
                domain_terms[domain] = legal_terminology[domain]
        return domain_terms
    
    def _get_applicable_routing_rules(self, query_context: QueryContext, routing_rules: Dict[str, Any]) -> Dict[str, Any]:
        """Get applicable routing rules for the query"""
        applicable_rules = {}
        
        for rule_name, rule_config in routing_rules.items():
            triggers = rule_config.get("triggers", [])
            
            if self._check_routing_triggers(query_context, triggers):
                applicable_rules[rule_name] = rule_config
        
        return applicable_rules
    
    def _check_routing_triggers(self, query_context: QueryContext, triggers: List[str]) -> bool:
        """Check if routing triggers are met"""
        query_lower = query_context.query.lower()
        
        for trigger in triggers:
            if isinstance(trigger, str):
                if "file_attached:" in trigger:
                    expected_value = "true" in trigger.lower()
                    if query_context.file_attached == expected_value:
                        return True
                elif "query contains:" in trigger:
                    search_terms = trigger.split("query contains:")[1].strip().strip("'\"")
                    terms = [term.strip().strip("'\"") for term in search_terms.split(",")]
                    if any(term.lower() in query_lower for term in terms):
                        return True
        
        return False
    
    def get_system_constraints(self) -> List[str]:
        """Get system-level constraints"""
        if not self._loaded:
            self.load_blueprint()
        
        system_context = self.context_layers.get(ContextLayerType.SYSTEM)
        if system_context:
            return system_context.data.get("constraints", [])
        return []
    
    def get_response_format(self, query_type: str = "legal_research") -> Dict[str, Any]:
        """Get response formatting requirements"""
        if not self._loaded:
            self.load_blueprint()
        
        response_context = self.context_layers.get(ContextLayerType.RESPONSE)
        if response_context:
            return response_context.data.get("formatting", {})
        return {}
    
    def get_quality_standards(self) -> Dict[str, Any]:
        """Get quality standards for responses"""
        if not self._loaded:
            self.load_blueprint()
        
        response_context = self.context_layers.get(ContextLayerType.RESPONSE)
        if response_context:
            return response_context.data.get("quality_standards", {})
        return {}
    
    def validate_blueprint(self) -> Dict[str, Any]:
        """Validate the loaded blueprint for completeness and correctness"""
        if not self._loaded:
            self.load_blueprint()
        
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_sections": []
        }
        
        # Check required sections
        required_sections = [layer.value for layer in ContextLayerType]
        for section in required_sections:
            if section not in self.blueprint_data:
                validation_results["missing_sections"].append(section)
                validation_results["valid"] = False
        
        # Check system constraints
        system_context = self.blueprint_data.get("system_context", {})
        if not system_context.get("constraints"):
            validation_results["warnings"].append("No system constraints defined")
        
        # Check domain knowledge
        domain_context = self.blueprint_data.get("domain_context", {})
        if not domain_context.get("primary_sources"):
            validation_results["warnings"].append("No primary legal sources defined")
        
        return validation_results
