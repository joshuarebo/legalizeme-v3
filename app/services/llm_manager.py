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
    
    async def invoke_model(self, prompt: str, model_preference: Optional[str] = None, speed_mode: bool = False) -> Dict[str, Any]:
        """
        Invoke a model with intelligent selection and fallback logic

        Args:
            prompt: The input prompt
            model_preference: Preferred model name (optional)
            speed_mode: If True, prioritize speed over accuracy

        Returns:
            Dict containing response, model_used, latency_ms, etc.
        """
        if not self.bedrock_client:
            raise Exception("Bedrock client not initialized")

        # Intelligent model selection based on query complexity and speed requirements
        if speed_mode:
            model_order = self._get_speed_optimized_order()
        elif model_preference and model_preference in self.models:
            # Try preferred model first, then intelligent fallback
            model_order = [model_preference] + self._get_intelligent_fallback_order(model_preference)
        else:
            # Use intelligent model selection based on prompt complexity
            model_order = self._select_optimal_model_order(prompt)

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
                    "success": True,
                    "query_complexity": self._assess_query_complexity(prompt),
                    "model_efficiency": self._calculate_model_efficiency(model)
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

    async def invoke_model_parallel(self, prompt: str, max_concurrent: int = 2) -> Dict[str, Any]:
        """
        Invoke multiple models in parallel and return the fastest response

        Args:
            prompt: The input prompt
            max_concurrent: Maximum number of concurrent model calls

        Returns:
            Dict containing the fastest response
        """
        if not self.bedrock_client:
            raise Exception("Bedrock client not initialized")

        # Get healthy models for parallel execution
        healthy_models = [
            name for name, model in self.models.items()
            if model.status != ModelStatus.FAILED
        ]

        if not healthy_models:
            raise Exception("No healthy models available")

        # Limit concurrent calls
        models_to_try = healthy_models[:max_concurrent]

        # Create tasks for parallel execution
        tasks = []
        for model_name in models_to_try:
            task = asyncio.create_task(
                self._invoke_single_model_with_timeout(model_name, prompt)
            )
            tasks.append((model_name, task))

        try:
            # Wait for first successful response
            done, pending = await asyncio.wait(
                [task for _, task in tasks],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=30.0  # 30 second timeout
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()

            # Get the first successful result
            for task in done:
                try:
                    result = await task
                    if result and result.get("success"):
                        logger.info(f"Parallel execution successful: {result.get('model_used')}")
                        return result
                except Exception as e:
                    logger.warning(f"Parallel task failed: {e}")
                    continue

            # If no successful result, fall back to sequential
            logger.warning("Parallel execution failed, falling back to sequential")
            return await self.invoke_model(prompt)

        except asyncio.TimeoutError:
            logger.error("Parallel model invocation timed out")
            # Cancel all tasks
            for _, task in tasks:
                task.cancel()
            raise Exception("Model invocation timed out")

    async def _invoke_single_model_with_timeout(self, model_name: str, prompt: str) -> Dict[str, Any]:
        """Invoke a single model with timeout protection"""
        try:
            model = self.models[model_name]
            start_time = time.time()

            response_text = await asyncio.wait_for(
                self._invoke_bedrock_model(model, prompt),
                timeout=model.timeout
            )

            latency_ms = (time.time() - start_time) * 1000

            # Update metrics
            model.response_times.append(latency_ms / 1000)
            model.success_count += 1
            model.status = ModelStatus.HEALTHY

            return {
                "response_text": response_text,
                "model_used": model_name,
                "model_id": model.model_id,
                "latency_ms": latency_ms,
                "success": True
            }

        except asyncio.TimeoutError:
            logger.warning(f"Model {model_name} timed out")
            model.status = ModelStatus.DEGRADED
            return {"success": False, "error": "timeout"}
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            model.error_count += 1
            model.last_error = str(e)
            return {"success": False, "error": str(e)}
    
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

    def _get_speed_optimized_order(self) -> List[str]:
        """Get models ordered by speed (fastest first)"""
        healthy_models = [
            name for name, model in self.models.items()
            if model.status != ModelStatus.FAILED
        ]

        # Sort by average response time (ascending)
        return sorted(
            healthy_models,
            key=lambda name: self._get_average_response_time(name)
        )

    def _get_intelligent_fallback_order(self, preferred_model: str) -> List[str]:
        """Get intelligent fallback order based on model performance"""
        fallback_models = [
            name for name in self.models.keys()
            if name != preferred_model and self.models[name].status != ModelStatus.FAILED
        ]

        # Sort by success rate and response time
        return sorted(
            fallback_models,
            key=lambda name: (
                -self._get_success_rate(name),  # Higher success rate first
                self._get_average_response_time(name)  # Then faster response time
            )
        )

    def _select_optimal_model_order(self, prompt: str) -> List[str]:
        """Select optimal model order based on prompt complexity"""
        complexity = self._assess_query_complexity(prompt)

        if complexity == "simple":
            # For simple queries, prioritize speed
            return self._get_speed_optimized_order()
        elif complexity == "complex":
            # For complex queries, prioritize accuracy (Claude Sonnet 4 first)
            return ["claude-sonnet-4", "claude-3-7", "mistral-large"]
        else:
            # For medium complexity, balance speed and accuracy
            return self._get_models_by_priority()

    def _assess_query_complexity(self, prompt: str) -> str:
        """Assess query complexity for optimal model selection"""
        # Simple heuristics for complexity assessment
        word_count = len(prompt.split())

        # Check for complex legal concepts
        complex_keywords = [
            "constitutional", "precedent", "jurisprudence", "statutory interpretation",
            "comparative analysis", "legal framework", "comprehensive analysis"
        ]

        simple_keywords = [
            "what is", "how to", "define", "explain", "basic", "simple"
        ]

        if word_count < 20 and any(keyword in prompt.lower() for keyword in simple_keywords):
            return "simple"
        elif word_count > 100 or any(keyword in prompt.lower() for keyword in complex_keywords):
            return "complex"
        else:
            return "medium"

    def _get_average_response_time(self, model_name: str) -> float:
        """Get average response time for a model"""
        model = self.models.get(model_name)
        if not model or not model.response_times:
            return float('inf')  # Penalize models with no data

        return sum(model.response_times) / len(model.response_times)

    def _get_success_rate(self, model_name: str) -> float:
        """Get success rate for a model"""
        model = self.models.get(model_name)
        if not model:
            return 0.0

        total_attempts = model.success_count + model.error_count
        if total_attempts == 0:
            return 0.5  # Neutral for untested models

        return model.success_count / total_attempts

    def _calculate_model_efficiency(self, model: BedrockModel) -> float:
        """Calculate model efficiency score (success rate / avg response time)"""
        success_rate = self._get_success_rate(model.name)
        avg_time = self._get_average_response_time(model.name)

        if avg_time == 0 or avg_time == float('inf'):
            return 0.0

        return success_rate / avg_time
    
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
