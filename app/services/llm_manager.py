"""
Production LLM Manager for AWS Bedrock Integration
Handles Claude Sonnet, Claude Haiku, and Mistral 7B via AWS Bedrock only
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Any, List
from enum import Enum

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from app.config import settings

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model availability status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class BedrockModel:
    """Represents a Bedrock model configuration"""
    
    def __init__(self, name: str, model_id: str, priority: int, timeout: float = 30.0):
        self.name = name
        self.model_id = model_id
        self.priority = priority
        self.timeout = timeout
        self.status = ModelStatus.UNKNOWN
        self.last_error: Optional[str] = None
        self.response_times: List[float] = []
        self.error_count = 0
        self.success_count = 0


class LLMManager:
    """Production LLM Manager for AWS Bedrock"""
    
    def __init__(self):
        self.bedrock_client = None
        self.models: Dict[str, BedrockModel] = {}
        self._initialize_models()
        self._initialize_bedrock_client()
    
    def _initialize_models(self):
        """Initialize model configurations"""
        self.models = {
            "claude-sonnet-4": BedrockModel(
                name="claude-sonnet-4",
                model_id=settings.AWS_BEDROCK_MODEL_ID_PRIMARY,
                priority=1,
                timeout=45.0
            ),
            "claude-3-7": BedrockModel(
                name="claude-3-7",
                model_id=settings.AWS_BEDROCK_MODEL_ID_SECONDARY,
                priority=2,
                timeout=35.0
            ),
            "mistral-large": BedrockModel(
                name="mistral-large",
                model_id=settings.AWS_BEDROCK_MODEL_ID_FALLBACK,
                priority=3,
                timeout=40.0
            )
        }
        logger.info(f"Initialized {len(self.models)} Bedrock models")
    
    def _initialize_bedrock_client(self):
        """Initialize AWS Bedrock client"""
        try:
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                
                # Mark all models as healthy initially
                for model in self.models.values():
                    model.status = ModelStatus.HEALTHY
                
                logger.info("AWS Bedrock client initialized successfully")
            else:
                # Mark all models as failed
                for model in self.models.values():
                    model.status = ModelStatus.FAILED
                    model.last_error = "AWS credentials not configured"
                
                logger.error("AWS credentials not found - Bedrock unavailable")
                
        except Exception as e:
            for model in self.models.values():
                model.status = ModelStatus.FAILED
                model.last_error = str(e)
            
            logger.error(f"Failed to initialize Bedrock client: {e}")
    
    async def invoke_model(self, prompt: str, model_preference: Optional[str] = None) -> Dict[str, Any]:
        """
        Invoke a model with fallback logic
        
        Args:
            prompt: The input prompt
            model_preference: Preferred model name (optional)
            
        Returns:
            Dict containing response, model_used, latency_ms, etc.
        """
        if not self.bedrock_client:
            raise Exception("Bedrock client not initialized")
        
        # Determine model order
        if model_preference and model_preference in self.models:
            # Try preferred model first, then fallback
            model_order = [model_preference] + [
                name for name in self._get_models_by_priority() 
                if name != model_preference
            ]
        else:
            # Use priority order
            model_order = self._get_models_by_priority()
        
        last_error = None
        
        for model_name in model_order:
            model = self.models[model_name]
            
            # Skip failed models
            if model.status == ModelStatus.FAILED:
                continue
            
            try:
                logger.info(f"Attempting to invoke {model_name} ({model.model_id})")
                start_time = time.time()
                
                response_text = await self._invoke_bedrock_model(model, prompt)
                
                latency_ms = (time.time() - start_time) * 1000
                
                # Update model metrics
                model.response_times.append(latency_ms / 1000)
                model.success_count += 1
                model.status = ModelStatus.HEALTHY
                model.last_error = None
                
                # Keep only last 100 response times
                if len(model.response_times) > 100:
                    model.response_times = model.response_times[-100:]
                
                logger.info(f"Successfully invoked {model_name} ({latency_ms:.0f}ms)")
                
                return {
                    "response_text": response_text,
                    "model_used": model_name,
                    "model_id": model.model_id,
                    "latency_ms": latency_ms,
                    "success": True
                }
                
            except Exception as e:
                error_msg = str(e)
                model.error_count += 1
                model.last_error = error_msg
                
                # Mark model as degraded/failed based on error pattern
                if "ValidationException" in error_msg or "AccessDeniedException" in error_msg:
                    model.status = ModelStatus.FAILED
                else:
                    model.status = ModelStatus.DEGRADED
                
                logger.warning(f"Model {model_name} failed: {error_msg}")
                last_error = error_msg
                continue
        
        # All models failed
        raise Exception(f"All models failed. Last error: {last_error}")
    
    async def _invoke_bedrock_model(self, model: BedrockModel, prompt: str) -> str:
        """Invoke a specific Bedrock model"""
        
        # Prepare request body based on model type
        if "anthropic" in model.model_id:
            # Anthropic Claude models (Claude Sonnet 4, Claude 3.7)
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.7,
                "top_p": 0.9,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        elif "mistral" in model.model_id:
            # Mistral models (Mistral Large)
            body = {
                "prompt": f"<s>[INST] {prompt} [/INST]",
                "max_tokens": 1000,
                "temperature": 0.7,
                "top_p": 0.9,
                "stop": ["</s>"]
            }
        else:
            raise Exception(f"Unsupported model type: {model.model_id}")
        
        # Make the request with timeout
        response = await asyncio.wait_for(
            asyncio.to_thread(
                self.bedrock_client.invoke_model,
                modelId=model.model_id,
                body=json.dumps(body)
            ),
            timeout=model.timeout
        )
        
        # Parse response based on model type
        response_body = json.loads(response['body'].read())

        if "anthropic" in model.model_id:
            # Anthropic response format (Claude Sonnet 4, Claude 3.7)
            generated_text = response_body['content'][0]['text']
        elif "mistral" in model.model_id:
            # Mistral response format (Mistral Large)
            generated_text = response_body.get('outputs', [{}])[0].get('text', '')
            if not generated_text:
                # Alternative response formats for Mistral
                generated_text = response_body.get('text', '')
                if not generated_text and 'choices' in response_body:
                    generated_text = response_body['choices'][0].get('message', {}).get('content', '')
        else:
            raise Exception(f"Unknown response format for model: {model.model_id}")
        
        if not generated_text or len(generated_text.strip()) < 10:
            raise Exception("Generated response too short or empty")
        
        return generated_text
    
    def _get_models_by_priority(self) -> List[str]:
        """Get model names sorted by priority"""
        return sorted(
            [name for name, model in self.models.items() if model.status != ModelStatus.FAILED],
            key=lambda name: self.models[name].priority
        )
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get current status of all models"""
        return {
            "models": {
                name: {
                    "status": model.status.value,
                    "model_id": model.model_id,
                    "priority": model.priority,
                    "success_count": model.success_count,
                    "error_count": model.error_count,
                    "avg_response_time": sum(model.response_times) / len(model.response_times) if model.response_times else 0,
                    "last_error": model.last_error
                }
                for name, model in self.models.items()
            },
            "bedrock_client_available": self.bedrock_client is not None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all models"""
        test_prompt = "Hello, please respond with 'OK' if you can process this request."
        
        results = {}
        for model_name in self.models:
            try:
                result = await self.invoke_model(test_prompt, model_preference=model_name)
                results[model_name] = {
                    "healthy": True,
                    "latency_ms": result["latency_ms"]
                }
            except Exception as e:
                results[model_name] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return results


# Global instance
llm_manager = LLMManager()
