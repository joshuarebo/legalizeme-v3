"""
Context Manager - Central orchestrator for context-aware operations
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .context_blueprint import ContextBlueprint, QueryContext, ContextLayer, ContextLayerType
from .context_router import ContextRouter
from .context_monitor import ContextMonitor

logger = logging.getLogger(__name__)

@dataclass
class ContextSnapshot:
    """Snapshot of context at a specific point in processing"""
    timestamp: datetime
    query_id: str
    processing_stage: str
    context_data: Dict[str, Any]
    confidence_score: float = 0.0
    tools_selected: List[str] = field(default_factory=list)
    routing_decisions: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContextDecision:
    """Represents a context-driven decision"""
    decision_type: str  # "tool_selection", "strategy_choice", "enhancement_trigger"
    decision_value: Any
    confidence: float
    reasoning: str
    context_factors: List[str] = field(default_factory=list)

class ContextManager:
    """
    Central context manager that orchestrates all context-aware operations
    for the Legal Research Agent
    """
    
    def __init__(self, blueprint_path: Optional[str] = None):
        self.blueprint = ContextBlueprint(blueprint_path)
        self.router = ContextRouter(self.blueprint)
        self.monitor = ContextMonitor()
        
        # Context state
        self.current_context: Optional[Dict[str, Any]] = None
        self.context_history: List[ContextSnapshot] = []
        self.active_decisions: List[ContextDecision] = []
        
        # Performance tracking
        self.metrics = {
            "context_analysis_time": 0.0,
            "routing_decisions": 0,
            "successful_contexts": 0,
            "failed_contexts": 0
        }
        
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the context manager and all components"""
        try:
            # Load blueprint
            if not self.blueprint.load_blueprint():
                logger.error("Failed to load context blueprint")
                return False
            
            # Initialize router and monitor
            await self.router.initialize()
            await self.monitor.initialize()
            
            self._initialized = True
            logger.info("Context Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Context Manager: {e}")
            return False
    
    async def analyze_query_context(
        self,
        query: str,
        query_type: str = "legal_research",
        user_context: Dict[str, Any] = None,
        file_attached: bool = False,
        previous_queries: List[str] = None
    ) -> Tuple[Dict[str, Any], List[ContextDecision]]:
        """
        Analyze query and build comprehensive context
        
        Args:
            query: The user's query
            query_type: Type of query (legal_research, contract_analysis, etc.)
            user_context: Additional user-provided context
            file_attached: Whether files are attached
            previous_queries: Previous queries for context
            
        Returns:
            Tuple of (context_dict, context_decisions)
        """
        start_time = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Create query context
            query_context = QueryContext(
                query=query,
                query_type=query_type,
                user_context=user_context or {},
                file_attached=file_attached,
                previous_queries=previous_queries or []
            )
            
            # Get base context from blueprint
            base_context = self.blueprint.get_context_for_query(query_context)
            
            # Enhance context with dynamic analysis
            enhanced_context = await self._enhance_context_dynamically(base_context, query_context)
            
            # Make routing decisions
            routing_decisions = await self.router.make_routing_decisions(enhanced_context, query_context)
            
            # Create context decisions
            context_decisions = self._create_context_decisions(enhanced_context, routing_decisions)
            
            # Store current context
            self.current_context = enhanced_context
            self.active_decisions = context_decisions
            
            # Create context snapshot
            snapshot = ContextSnapshot(
                timestamp=datetime.utcnow(),
                query_id=self._generate_query_id(query),
                processing_stage="context_analysis",
                context_data=enhanced_context,
                tools_selected=[d.decision_value for d in context_decisions if d.decision_type == "tool_selection"],
                routing_decisions=routing_decisions
            )
            
            self.context_history.append(snapshot)
            
            # Update metrics
            analysis_time = time.time() - start_time
            self.metrics["context_analysis_time"] = analysis_time
            self.metrics["successful_contexts"] += 1
            
            # Monitor context quality
            await self.monitor.log_context_snapshot(snapshot)
            
            logger.info(f"Context analysis completed in {analysis_time:.3f}s")
            return enhanced_context, context_decisions
            
        except Exception as e:
            self.metrics["failed_contexts"] += 1
            logger.error(f"Context analysis failed: {e}")
            
            # Return minimal context for fallback
            fallback_context = self._create_fallback_context(query, query_type)
            return fallback_context, []
    
    async def _enhance_context_dynamically(
        self,
        base_context: Dict[str, Any],
        query_context: QueryContext
    ) -> Dict[str, Any]:
        """Enhance context with dynamic analysis"""
        enhanced_context = base_context.copy()
        
        # Analyze query complexity
        complexity_analysis = self._analyze_query_complexity(query_context.query)
        enhanced_context["query_complexity"] = complexity_analysis
        
        # Detect urgency indicators
        urgency_analysis = self._detect_urgency_indicators(query_context.query)
        enhanced_context["urgency_analysis"] = urgency_analysis
        
        # Analyze legal domain specificity
        domain_analysis = self._analyze_domain_specificity(query_context.query, base_context)
        enhanced_context["domain_analysis"] = domain_analysis
        
        # Add contextual enhancements based on previous queries
        if query_context.previous_queries:
            pattern_analysis = self._analyze_query_patterns(query_context.previous_queries)
            enhanced_context["pattern_analysis"] = pattern_analysis
        
        return enhanced_context
    
    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze the complexity of the query"""
        complexity_indicators = {
            "multiple_legal_areas": len([term for term in ["employment", "contract", "property", "criminal", "civil"] 
                                       if term in query.lower()]) > 1,
            "conditional_language": any(word in query.lower() for word in ["if", "unless", "provided", "except"]),
            "temporal_elements": any(word in query.lower() for word in ["before", "after", "during", "within"]),
            "multiple_parties": len([term for term in ["employer", "employee", "landlord", "tenant", "buyer", "seller"] 
                                   if term in query.lower()]) > 1,
            "procedural_elements": any(word in query.lower() for word in ["procedure", "process", "steps", "requirements"]),
            "query_length": len(query.split())
        }
        
        complexity_score = sum([
            complexity_indicators["multiple_legal_areas"] * 0.3,
            complexity_indicators["conditional_language"] * 0.2,
            complexity_indicators["temporal_elements"] * 0.15,
            complexity_indicators["multiple_parties"] * 0.15,
            complexity_indicators["procedural_elements"] * 0.1,
            min(complexity_indicators["query_length"] / 50, 1.0) * 0.1
        ])
        
        return {
            "score": complexity_score,
            "level": "high" if complexity_score > 0.7 else "medium" if complexity_score > 0.4 else "low",
            "indicators": complexity_indicators
        }
    
    def _detect_urgency_indicators(self, query: str) -> Dict[str, Any]:
        """Detect urgency indicators in the query"""
        urgency_keywords = {
            "high": ["urgent", "emergency", "immediate", "asap", "deadline", "court date"],
            "medium": ["soon", "quickly", "time-sensitive", "pending"],
            "low": ["general", "information", "understand", "clarify"]
        }
        
        query_lower = query.lower()
        detected_urgency = "low"  # default
        
        for level, keywords in urgency_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                detected_urgency = level
                break
        
        return {
            "level": detected_urgency,
            "keywords_found": [kw for level_kws in urgency_keywords.values() 
                             for kw in level_kws if kw in query_lower]
        }
    
    def _analyze_domain_specificity(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how domain-specific the query is"""
        domain_context = context.get("domain_context", {})
        legal_terminology = domain_context.get("legal_terminology", {})
        
        domain_matches = {}
        total_matches = 0
        
        for domain, terms in legal_terminology.items():
            matches = [term for term in terms if term.lower() in query.lower()]
            if matches:
                domain_matches[domain] = matches
                total_matches += len(matches)
        
        specificity_score = min(total_matches / 5.0, 1.0)  # Normalize to 0-1
        
        return {
            "score": specificity_score,
            "level": "high" if specificity_score > 0.6 else "medium" if specificity_score > 0.3 else "low",
            "domain_matches": domain_matches,
            "primary_domain": max(domain_matches.keys(), key=lambda k: len(domain_matches[k])) if domain_matches else None
        }
    
    def _analyze_query_patterns(self, previous_queries: List[str]) -> Dict[str, Any]:
        """Analyze patterns in previous queries"""
        if not previous_queries:
            return {"patterns": [], "trend": "none"}
        
        # Simple pattern analysis
        common_terms = {}
        for query in previous_queries:
            words = query.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    common_terms[word] = common_terms.get(word, 0) + 1
        
        # Find most common terms
        frequent_terms = [term for term, count in common_terms.items() if count > 1]
        
        return {
            "frequent_terms": frequent_terms[:5],  # Top 5
            "query_count": len(previous_queries),
            "trend": "focused" if len(frequent_terms) > 2 else "exploratory"
        }
    
    def _create_context_decisions(
        self,
        context: Dict[str, Any],
        routing_decisions: Dict[str, Any]
    ) -> List[ContextDecision]:
        """Create context-driven decisions"""
        decisions = []
        
        # Tool selection decisions
        for rule_name, rule_config in routing_decisions.items():
            tools = rule_config.get("tools", [])
            strategy = rule_config.get("strategy", "default")
            
            for tool in tools:
                decision = ContextDecision(
                    decision_type="tool_selection",
                    decision_value=tool,
                    confidence=0.8,  # Base confidence
                    reasoning=f"Selected based on {rule_name} routing rule",
                    context_factors=[rule_name]
                )
                decisions.append(decision)
            
            # Strategy decision
            if strategy != "default":
                decision = ContextDecision(
                    decision_type="strategy_choice",
                    decision_value=strategy,
                    confidence=0.9,
                    reasoning=f"Strategy selected based on {rule_name} context",
                    context_factors=[rule_name]
                )
                decisions.append(decision)
        
        # Enhancement trigger decisions
        complexity = context.get("query_complexity", {})
        if complexity.get("level") == "high":
            decision = ContextDecision(
                decision_type="enhancement_trigger",
                decision_value="comprehensive_analysis",
                confidence=0.85,
                reasoning="High complexity query requires comprehensive analysis",
                context_factors=["query_complexity"]
            )
            decisions.append(decision)
        
        return decisions
    
    def _create_fallback_context(self, query: str, query_type: str) -> Dict[str, Any]:
        """Create minimal fallback context"""
        return {
            "agent_name": "LegalResearchAgent",
            "version": "1.0.0",
            "query_info": {
                "query": query,
                "query_type": query_type,
                "fallback_mode": True
            },
            "system_context": {
                "behavior": "Formal, factual, legally grounded",
                "constraints": ["No hallucinations", "Cite sources when possible"]
            }
        }
    
    def _generate_query_id(self, query: str) -> str:
        """Generate a unique ID for the query"""
        import hashlib
        timestamp = str(int(time.time()))
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"query_{timestamp}_{query_hash}"
    
    def get_current_context(self) -> Optional[Dict[str, Any]]:
        """Get the current active context"""
        return self.current_context
    
    def get_active_decisions(self) -> List[ContextDecision]:
        """Get the current active context decisions"""
        return self.active_decisions
    
    def get_context_metrics(self) -> Dict[str, Any]:
        """Get context management metrics"""
        return {
            **self.metrics,
            "context_history_size": len(self.context_history),
            "active_decisions_count": len(self.active_decisions)
        }
