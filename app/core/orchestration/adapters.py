"""
Adapter Pattern Implementation for Dynamic Model Enhancement
Provides modular adapters for different AI models and capabilities without altering base weights
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class AdapterType(Enum):
    """Types of adapters available"""
    MODEL = "model"
    PROMPT = "prompt"
    RAG = "rag"
    CONTEXT = "context"
    OUTPUT = "output"

@dataclass
class AdapterConfig:
    """Configuration for adapters"""
    name: str
    adapter_type: AdapterType
    priority: int = 1
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseAdapter(ABC):
    """Base class for all adapters"""
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.name = config.name
        self.adapter_type = config.adapter_type
        self.priority = config.priority
        self.enabled = config.enabled
        self.parameters = config.parameters
        self.metadata = config.metadata
        self.performance_metrics = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "avg_latency": 0.0,
            "last_used": None
        }
    
    @abstractmethod
    async def apply(self, input_data: Any, context: Dict[str, Any] = None) -> Any:
        """Apply the adapter transformation"""
        pass
    
    async def _track_performance(self, func: Callable, *args, **kwargs):
        """Track performance metrics for adapter calls"""
        start_time = time.time()
        self.performance_metrics["calls"] += 1
        
        try:
            result = await func(*args, **kwargs)
            self.performance_metrics["successes"] += 1
            return result
        except Exception as e:
            self.performance_metrics["failures"] += 1
            logger.error(f"Adapter {self.name} failed: {e}")
            raise
        finally:
            latency = time.time() - start_time
            # Update rolling average
            total_calls = self.performance_metrics["calls"]
            current_avg = self.performance_metrics["avg_latency"]
            self.performance_metrics["avg_latency"] = (
                (current_avg * (total_calls - 1) + latency) / total_calls
            )
            self.performance_metrics["last_used"] = datetime.utcnow()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "name": self.name,
            "type": self.adapter_type.value,
            "enabled": self.enabled,
            "metrics": self.performance_metrics.copy()
        }
    
    def enable(self):
        """Enable the adapter"""
        self.enabled = True
        logger.info(f"Adapter {self.name} enabled")
    
    def disable(self):
        """Disable the adapter"""
        self.enabled = False
        logger.info(f"Adapter {self.name} disabled")

class ModelAdapter(BaseAdapter):
    """Adapter for enhancing model behavior without changing base weights"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.model_enhancements = config.parameters.get("enhancements", {})
        self.temperature_modifier = config.parameters.get("temperature_modifier", 0.0)
        self.max_tokens_modifier = config.parameters.get("max_tokens_modifier", 0)
        self.system_prompt_injection = config.parameters.get("system_prompt", "")
    
    async def apply(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply model enhancements to input"""
        if not self.enabled:
            return input_data
        
        return await self._track_performance(self._apply_enhancements, input_data, context)
    
    async def _apply_enhancements(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply model-specific enhancements"""
        enhanced_data = input_data.copy()
        
        # Inject system prompt if specified
        if self.system_prompt_injection:
            if "messages" in enhanced_data:
                # Insert system message at the beginning
                system_msg = {"role": "system", "content": self.system_prompt_injection}
                enhanced_data["messages"].insert(0, system_msg)
            elif "prompt" in enhanced_data:
                # Prepend to existing prompt
                enhanced_data["prompt"] = f"{self.system_prompt_injection}\n\n{enhanced_data['prompt']}"
        
        # Apply parameter modifications
        if "temperature" in enhanced_data and self.temperature_modifier != 0:
            enhanced_data["temperature"] = max(0.0, min(2.0, 
                enhanced_data["temperature"] + self.temperature_modifier))
        
        if "max_tokens" in enhanced_data and self.max_tokens_modifier != 0:
            enhanced_data["max_tokens"] = max(1, 
                enhanced_data["max_tokens"] + self.max_tokens_modifier)
        
        # Apply context-specific enhancements
        if context and context.get("task_type") == "legal_analysis":
            enhanced_data = await self._apply_legal_enhancements(enhanced_data, context)
        
        return enhanced_data
    
    async def _apply_legal_enhancements(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Kenyan legal-specific enhancements"""
        legal_context = """
        You are a specialized legal AI assistant for Kenyan jurisdiction. Always:
        1. Reference relevant Kenyan laws and regulations
        2. Consider the Constitution of Kenya 2010
        3. Cite appropriate case law where applicable
        4. Provide practical legal advice within Kenyan context
        5. Use proper legal terminology and formatting
        """
        
        if "messages" in data:
            # Add legal context to system message
            for msg in data["messages"]:
                if msg["role"] == "system":
                    msg["content"] = f"{legal_context}\n\n{msg['content']}"
                    break
            else:
                # No system message found, add one
                data["messages"].insert(0, {"role": "system", "content": legal_context})
        
        return data

class PromptAdapter(BaseAdapter):
    """Adapter for dynamic prompt engineering and enhancement"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.prompt_templates = config.parameters.get("templates", {})
        self.enhancement_rules = config.parameters.get("enhancement_rules", [])
        self.context_injection = config.parameters.get("context_injection", True)
    
    async def apply(self, input_data: Union[str, Dict[str, Any]], context: Dict[str, Any] = None) -> Union[str, Dict[str, Any]]:
        """Apply prompt enhancements"""
        if not self.enabled:
            return input_data
        
        return await self._track_performance(self._enhance_prompt, input_data, context)
    
    async def _enhance_prompt(self, input_data: Union[str, Dict[str, Any]], context: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Enhance prompts with dynamic engineering"""
        if isinstance(input_data, str):
            return await self._enhance_string_prompt(input_data, context)
        elif isinstance(input_data, dict):
            return await self._enhance_structured_prompt(input_data, context)
        else:
            return input_data
    
    async def _enhance_string_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """Enhance a string prompt"""
        enhanced_prompt = prompt
        
        # Apply enhancement rules
        for rule in self.enhancement_rules:
            if rule["type"] == "prefix":
                enhanced_prompt = f"{rule['content']}\n\n{enhanced_prompt}"
            elif rule["type"] == "suffix":
                enhanced_prompt = f"{enhanced_prompt}\n\n{rule['content']}"
            elif rule["type"] == "replace":
                enhanced_prompt = enhanced_prompt.replace(rule["pattern"], rule["replacement"])
        
        # Inject context if enabled
        if self.context_injection and context:
            context_str = self._format_context(context)
            enhanced_prompt = f"{context_str}\n\n{enhanced_prompt}"
        
        return enhanced_prompt
    
    async def _enhance_structured_prompt(self, prompt_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance structured prompt data"""
        enhanced_data = prompt_data.copy()
        
        # Enhance main prompt field
        if "prompt" in enhanced_data:
            enhanced_data["prompt"] = await self._enhance_string_prompt(enhanced_data["prompt"], context)
        
        # Enhance messages if present
        if "messages" in enhanced_data:
            for message in enhanced_data["messages"]:
                if message["role"] == "user":
                    message["content"] = await self._enhance_string_prompt(message["content"], context)
        
        return enhanced_data
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for injection"""
        if not context:
            return ""
        
        context_parts = []
        
        if context.get("user_type"):
            context_parts.append(f"User Type: {context['user_type']}")
        
        if context.get("jurisdiction"):
            context_parts.append(f"Jurisdiction: {context['jurisdiction']}")
        
        if context.get("legal_area"):
            context_parts.append(f"Legal Area: {context['legal_area']}")
        
        if context.get("urgency"):
            context_parts.append(f"Urgency: {context['urgency']}")
        
        if context_parts:
            return f"Context:\n{chr(10).join(context_parts)}"
        
        return ""

class RAGAdapter(BaseAdapter):
    """Adapter for Retrieval-Augmented Generation enhancement"""
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.retrieval_config = config.parameters.get("retrieval", {})
        self.max_documents = config.parameters.get("max_documents", 5)
        self.relevance_threshold = config.parameters.get("relevance_threshold", 0.7)
        self.document_sources = config.parameters.get("sources", ["kenyan_law", "case_law", "regulations"])
    
    async def apply(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Apply RAG enhancement to input"""
        if not self.enabled:
            return input_data
        
        return await self._track_performance(self._apply_rag, input_data, context)
    
    async def _apply_rag(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply RAG enhancement"""
        enhanced_data = input_data.copy()
        
        # Extract query from input
        query = self._extract_query(input_data)
        if not query:
            return enhanced_data
        
        # Retrieve relevant documents
        relevant_docs = await self._retrieve_documents(query, context)
        
        if relevant_docs:
            # Inject retrieved context
            enhanced_data = await self._inject_retrieved_context(enhanced_data, relevant_docs)
        
        return enhanced_data
    
    def _extract_query(self, input_data: Dict[str, Any]) -> str:
        """Extract query from input data"""
        if "query" in input_data:
            return input_data["query"]
        elif "prompt" in input_data:
            return input_data["prompt"]
        elif "messages" in input_data:
            # Get last user message
            for msg in reversed(input_data["messages"]):
                if msg["role"] == "user":
                    return msg["content"]
        
        return ""
    
    async def _retrieve_documents(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for the query"""
        # This would integrate with your vector service
        # For now, return mock relevant documents
        mock_docs = [
            {
                "title": "Companies Act 2015 - Registration Requirements",
                "content": "The Companies Act 2015 provides the legal framework for company registration in Kenya...",
                "source": "kenyan_law",
                "relevance_score": 0.95,
                "url": "https://kenyalaw.org/companies-act-2015"
            },
            {
                "title": "Employment Act 2007 - Termination Procedures", 
                "content": "Under the Employment Act 2007, employment termination must follow due process...",
                "source": "kenyan_law",
                "relevance_score": 0.88,
                "url": "https://kenyalaw.org/employment-act-2007"
            }
        ]
        
        # Filter by relevance threshold
        relevant_docs = [
            doc for doc in mock_docs 
            if doc["relevance_score"] >= self.relevance_threshold
        ]
        
        # Limit number of documents
        return relevant_docs[:self.max_documents]
    
    async def _inject_retrieved_context(self, input_data: Dict[str, Any], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Inject retrieved documents into the input"""
        enhanced_data = input_data.copy()
        
        # Format retrieved context
        context_text = self._format_retrieved_context(documents)
        
        if "messages" in enhanced_data:
            # Add context as system message
            context_msg = {
                "role": "system",
                "content": f"Relevant Legal Context:\n{context_text}"
            }
            enhanced_data["messages"].insert(-1, context_msg)  # Insert before last user message
        elif "prompt" in enhanced_data:
            # Prepend context to prompt
            enhanced_data["prompt"] = f"Relevant Legal Context:\n{context_text}\n\nUser Query: {enhanced_data['prompt']}"
        
        # Add metadata about retrieved documents
        enhanced_data["retrieved_documents"] = [
            {
                "title": doc["title"],
                "source": doc["source"],
                "relevance_score": doc["relevance_score"],
                "url": doc.get("url")
            }
            for doc in documents
        ]
        
        return enhanced_data
    
    def _format_retrieved_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents for context injection"""
        if not documents:
            return ""
        
        formatted_docs = []
        for i, doc in enumerate(documents, 1):
            formatted_doc = f"{i}. {doc['title']}\n{doc['content'][:500]}..."
            if doc.get("url"):
                formatted_doc += f"\nSource: {doc['url']}"
            formatted_docs.append(formatted_doc)
        
        return "\n\n".join(formatted_docs)
