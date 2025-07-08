"""
Intelligence Enhancer - Orchestrates all modular components for dynamic AI enhancement
Coordinates adapters, RAG, and prompt engineering without altering base model weights
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from datetime import datetime

from .adapters import BaseAdapter, ModelAdapter, PromptAdapter, RAGAdapter, AdapterConfig, AdapterType
from .rag_orchestrator import RAGOrchestrator, RetrievalConfig, RetrievalStrategy
from .prompt_engine import PromptEngine, PromptContext, PromptType, PromptStrategy

logger = logging.getLogger(__name__)

class EnhancementMode(Enum):
    """Different enhancement modes"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    CUSTOM = "custom"

@dataclass
class EnhancementConfig:
    """Configuration for intelligence enhancement"""
    mode: EnhancementMode = EnhancementMode.STANDARD
    enable_rag: bool = True
    enable_prompt_engineering: bool = True
    enable_adapters: bool = True
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    prompt_strategy: PromptStrategy = PromptStrategy.CHAIN_OF_THOUGHT
    max_enhancement_time: float = 30.0
    cache_enhancements: bool = True
    custom_adapters: List[str] = field(default_factory=list)

class IntelligenceEnhancer:
    """Main orchestrator for dynamic intelligence enhancement"""
    
    def __init__(self, vector_service=None):
        self.prompt_engine = PromptEngine()
        self.rag_orchestrator = RAGOrchestrator(vector_service)
        self.adapters = {}
        self.enhancement_cache = {}
        self.cache_ttl = 1800  # 30 minutes
        
        # Performance tracking
        self.metrics = {
            "total_enhancements": 0,
            "cache_hits": 0,
            "avg_enhancement_time": 0.0,
            "mode_usage": {},
            "component_usage": {
                "rag": 0,
                "prompt_engineering": 0,
                "adapters": 0
            }
        }
        
        # Initialize default adapters
        self._initialize_default_adapters()
    
    def _initialize_default_adapters(self):
        """Initialize default adapters for Kenyan legal AI"""
        
        # Legal Context Adapter
        legal_adapter_config = AdapterConfig(
            name="kenyan_legal_context",
            adapter_type=AdapterType.CONTEXT,
            priority=1,
            parameters={
                "system_prompt": "You are a specialized AI assistant for Kenyan legal matters. Always consider Kenyan law, the Constitution of Kenya 2010, and local legal practices.",
                "temperature_modifier": -0.1,  # Slightly more conservative
                "enhancements": {
                    "legal_focus": True,
                    "kenyan_jurisdiction": True
                }
            }
        )
        self.register_adapter(ModelAdapter(legal_adapter_config))
        
        # Prompt Enhancement Adapter
        prompt_adapter_config = AdapterConfig(
            name="legal_prompt_enhancer",
            adapter_type=AdapterType.PROMPT,
            priority=2,
            parameters={
                "enhancement_rules": [
                    {
                        "type": "prefix",
                        "content": "Legal Context: This query relates to Kenyan jurisdiction and law."
                    }
                ],
                "context_injection": True
            }
        )
        self.register_adapter(PromptAdapter(prompt_adapter_config))
        
        # RAG Enhancement Adapter
        rag_adapter_config = AdapterConfig(
            name="legal_rag_enhancer",
            adapter_type=AdapterType.RAG,
            priority=3,
            parameters={
                "max_documents": 5,
                "relevance_threshold": 0.7,
                "sources": ["kenyan_law", "case_law", "regulations"]
            }
        )
        self.register_adapter(RAGAdapter(rag_adapter_config))
    
    def register_adapter(self, adapter: BaseAdapter):
        """Register a new adapter"""
        self.adapters[adapter.name] = adapter
        logger.info(f"Registered adapter: {adapter.name} (type: {adapter.adapter_type.value})")
    
    async def enhance_intelligence(
        self,
        input_data: Dict[str, Any],
        config: EnhancementConfig = None,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Main method to enhance AI intelligence dynamically"""
        start_time = time.time()
        config = config or EnhancementConfig()
        context = context or {}
        
        try:
            # Check cache first
            if config.cache_enhancements:
                cache_key = self._generate_cache_key(input_data, config)
                cached_result = self._get_cached_enhancement(cache_key)
                if cached_result:
                    self.metrics["cache_hits"] += 1
                    return cached_result
            
            # Apply enhancement pipeline
            enhanced_data = await self._apply_enhancement_pipeline(input_data, config, context)
            
            # Cache result if enabled
            if config.cache_enhancements:
                self._cache_enhancement(cache_key, enhanced_data)
            
            # Update metrics
            self._update_metrics(config, time.time() - start_time)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Intelligence enhancement failed: {e}")
            # Return original data with error information
            return {
                **input_data,
                "enhancement_error": str(e),
                "enhancement_applied": False
            }
    
    async def _apply_enhancement_pipeline(
        self,
        input_data: Dict[str, Any],
        config: EnhancementConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply the complete enhancement pipeline"""
        
        enhanced_data = input_data.copy()
        enhancement_metadata = {
            "enhancements_applied": [],
            "processing_time": {},
            "components_used": []
        }
        
        # Phase 1: Apply Adapters
        if config.enable_adapters:
            start_time = time.time()
            enhanced_data = await self._apply_adapters(enhanced_data, context)
            enhancement_metadata["processing_time"]["adapters"] = time.time() - start_time
            enhancement_metadata["components_used"].append("adapters")
            enhancement_metadata["enhancements_applied"].append("adapter_enhancement")
            self.metrics["component_usage"]["adapters"] += 1
        
        # Phase 2: RAG Enhancement
        if config.enable_rag:
            start_time = time.time()
            enhanced_data = await self._apply_rag_enhancement(enhanced_data, config, context)
            enhancement_metadata["processing_time"]["rag"] = time.time() - start_time
            enhancement_metadata["components_used"].append("rag")
            enhancement_metadata["enhancements_applied"].append("rag_enhancement")
            self.metrics["component_usage"]["rag"] += 1
        
        # Phase 3: Prompt Engineering
        if config.enable_prompt_engineering:
            start_time = time.time()
            enhanced_data = await self._apply_prompt_engineering(enhanced_data, config, context)
            enhancement_metadata["processing_time"]["prompt_engineering"] = time.time() - start_time
            enhancement_metadata["components_used"].append("prompt_engineering")
            enhancement_metadata["enhancements_applied"].append("prompt_enhancement")
            self.metrics["component_usage"]["prompt_engineering"] += 1
        
        # Add enhancement metadata
        enhanced_data["enhancement_metadata"] = enhancement_metadata
        enhanced_data["enhancement_applied"] = True
        enhanced_data["enhancement_mode"] = config.mode.value
        
        return enhanced_data
    
    async def _apply_adapters(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all enabled adapters in priority order"""
        enhanced_data = data.copy()
        
        # Sort adapters by priority
        sorted_adapters = sorted(
            [adapter for adapter in self.adapters.values() if adapter.enabled],
            key=lambda x: x.priority
        )
        
        for adapter in sorted_adapters:
            try:
                enhanced_data = await adapter.apply(enhanced_data, context)
                logger.debug(f"Applied adapter: {adapter.name}")
            except Exception as e:
                logger.warning(f"Adapter {adapter.name} failed: {e}")
                continue
        
        return enhanced_data
    
    async def _apply_rag_enhancement(
        self,
        data: Dict[str, Any],
        config: EnhancementConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply RAG enhancement"""
        try:
            # Extract query for retrieval
            query = self._extract_query_for_rag(data)
            if not query:
                return data
            
            # Configure retrieval
            retrieval_config = RetrievalConfig(
                strategy=config.retrieval_strategy,
                max_documents=5,
                relevance_threshold=0.7
            )
            
            # Retrieve relevant documents
            retrieved_docs = await self.rag_orchestrator.retrieve_and_rank(
                query, retrieval_config, context
            )
            
            if retrieved_docs:
                # Inject retrieved context
                enhanced_data = data.copy()
                enhanced_data = await self._inject_rag_context(enhanced_data, retrieved_docs)
                return enhanced_data
            
        except Exception as e:
            logger.warning(f"RAG enhancement failed: {e}")
        
        return data
    
    async def _apply_prompt_engineering(
        self,
        data: Dict[str, Any],
        config: EnhancementConfig,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply prompt engineering enhancement"""
        try:
            # Determine prompt type based on context
            prompt_type = self._determine_prompt_type(data, context)
            
            # Create prompt context
            prompt_context = PromptContext(
                user_type=context.get("user_type"),
                legal_area=context.get("legal_area"),
                jurisdiction=context.get("jurisdiction", "Kenya"),
                urgency=context.get("urgency"),
                complexity=context.get("complexity")
            )
            
            # Select appropriate template
            template_name = self._select_template(prompt_type, context)
            
            if template_name:
                # Generate enhanced prompt
                prompt_result = await self.prompt_engine.generate_prompt(
                    template_name,
                    data,
                    prompt_context,
                    config.prompt_strategy
                )
                
                # Update data with enhanced prompt
                enhanced_data = data.copy()
                enhanced_data.update(prompt_result)
                return enhanced_data
            
        except Exception as e:
            logger.warning(f"Prompt engineering failed: {e}")
        
        return data
    
    def _extract_query_for_rag(self, data: Dict[str, Any]) -> str:
        """Extract query text for RAG retrieval"""
        if "query" in data:
            return data["query"]
        elif "prompt" in data:
            return data["prompt"]
        elif "messages" in data:
            # Get last user message
            for msg in reversed(data["messages"]):
                if msg.get("role") == "user":
                    return msg.get("content", "")
        
        return ""
    
    async def _inject_rag_context(
        self,
        data: Dict[str, Any],
        retrieved_docs: List[Any]
    ) -> Dict[str, Any]:
        """Inject RAG context into the data"""
        if not retrieved_docs:
            return data
        
        # Format retrieved context
        context_text = "\n\n".join([
            f"Document {i+1}: {doc.title}\n{doc.content[:500]}..."
            for i, doc in enumerate(retrieved_docs[:3])
        ])
        
        enhanced_data = data.copy()
        
        # Add to messages if present
        if "messages" in enhanced_data:
            context_msg = {
                "role": "system",
                "content": f"Relevant Legal Context:\n{context_text}"
            }
            enhanced_data["messages"].insert(-1, context_msg)
        
        # Add to prompt if present
        elif "prompt" in enhanced_data:
            enhanced_data["prompt"] = f"Legal Context:\n{context_text}\n\nQuery: {enhanced_data['prompt']}"
        
        # Add metadata about retrieved documents
        enhanced_data["retrieved_documents"] = [
            {
                "title": doc.title,
                "relevance_score": doc.relevance_score,
                "source": doc.source.value if hasattr(doc.source, 'value') else str(doc.source)
            }
            for doc in retrieved_docs
        ]
        
        return enhanced_data
    
    def _determine_prompt_type(self, data: Dict[str, Any], context: Dict[str, Any]) -> PromptType:
        """Determine the appropriate prompt type"""
        if context.get("task_type") == "document_generation":
            return PromptType.DOCUMENT_GENERATION
        elif context.get("task_type") == "legal_analysis":
            return PromptType.LEGAL_ANALYSIS
        elif context.get("task_type") == "case_research":
            return PromptType.CASE_RESEARCH
        else:
            return PromptType.LEGAL_QUERY
    
    def _select_template(self, prompt_type: PromptType, context: Dict[str, Any]) -> str:
        """Select appropriate template based on prompt type"""
        template_mapping = {
            PromptType.LEGAL_QUERY: "kenyan_legal_query",
            PromptType.DOCUMENT_GENERATION: "kenyan_legal_document",
            PromptType.LEGAL_ANALYSIS: "kenyan_legal_analysis"
        }
        
        return template_mapping.get(prompt_type, "kenyan_legal_query")
    
    def _generate_cache_key(self, input_data: Dict[str, Any], config: EnhancementConfig) -> str:
        """Generate cache key for enhancement results"""
        import hashlib
        
        key_data = {
            "input": str(sorted(input_data.items())),
            "mode": config.mode.value,
            "rag": config.enable_rag,
            "prompt": config.enable_prompt_engineering,
            "adapters": config.enable_adapters
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_enhancement(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached enhancement result"""
        if cache_key in self.enhancement_cache:
            cached_data = self.enhancement_cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                return cached_data["result"]
            else:
                del self.enhancement_cache[cache_key]
        return None
    
    def _cache_enhancement(self, cache_key: str, result: Dict[str, Any]):
        """Cache enhancement result"""
        self.enhancement_cache[cache_key] = {
            "result": result,
            "timestamp": time.time()
        }
        
        # Limit cache size
        if len(self.enhancement_cache) > 500:
            # Remove oldest entries
            sorted_cache = sorted(
                self.enhancement_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_cache[:50]:
                del self.enhancement_cache[key]
    
    def _update_metrics(self, config: EnhancementConfig, processing_time: float):
        """Update performance metrics"""
        self.metrics["total_enhancements"] += 1
        
        # Update mode usage
        mode_name = config.mode.value
        if mode_name not in self.metrics["mode_usage"]:
            self.metrics["mode_usage"][mode_name] = 0
        self.metrics["mode_usage"][mode_name] += 1
        
        # Update average processing time
        total = self.metrics["total_enhancements"]
        current_avg = self.metrics["avg_enhancement_time"]
        self.metrics["avg_enhancement_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_adapter_metrics(self) -> Dict[str, Any]:
        """Get metrics for all adapters"""
        return {
            name: adapter.get_metrics()
            for name, adapter in self.adapters.items()
        }
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for all components"""
        return {
            "intelligence_enhancer": self.metrics.copy(),
            "adapters": self.get_adapter_metrics(),
            "rag_orchestrator": self.rag_orchestrator.get_metrics(),
            "prompt_engine": self.prompt_engine.get_metrics(),
            "cache_stats": {
                "cache_size": len(self.enhancement_cache),
                "cache_hit_rate": (
                    self.metrics["cache_hits"] / 
                    max(self.metrics["total_enhancements"], 1)
                )
            }
        }
    
    async def optimize_performance(self) -> Dict[str, Any]:
        """Optimize performance of all components"""
        optimizations = []
        
        # Optimize adapters
        for adapter in self.adapters.values():
            metrics = adapter.get_metrics()
            if metrics["metrics"]["error_rate"] > 0.1:  # 10% error rate
                adapter.disable()
                optimizations.append(f"Disabled adapter {adapter.name} due to high error rate")
        
        # Clear old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, data in self.enhancement_cache.items()
            if current_time - data["timestamp"] > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.enhancement_cache[key]
        
        if expired_keys:
            optimizations.append(f"Cleared {len(expired_keys)} expired cache entries")
        
        return {
            "optimizations_applied": optimizations,
            "timestamp": datetime.utcnow().isoformat()
        }
