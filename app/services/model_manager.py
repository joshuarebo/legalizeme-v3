"""
Model Manager Service for AI Model Orchestration and Fine-tuning
Handles model lifecycle, fine-tuning pipelines, and performance monitoring
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import threading
import time

from app.services.ai_service import AIService
from app.core.exceptions import AIServiceException
from app.config import settings

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages AI model lifecycle, fine-tuning, and monitoring"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.fine_tuning_queue = []
        self.fine_tuning_in_progress = False
        self.monitoring_active = True
        
        # Start background monitoring
        self._start_background_monitoring()
    
    def _start_background_monitoring(self):
        """Start background monitoring thread"""
        def monitor():
            while self.monitoring_active:
                try:
                    self._monitor_model_performance()
                    self._check_fine_tuning_queue()
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Error in background monitoring: {e}")
                    time.sleep(60)
        
        threading.Thread(target=monitor, daemon=True).start()
        logger.info("Model manager background monitoring started")
    
    def _monitor_model_performance(self):
        """Monitor model performance and trigger actions if needed"""
        try:
            status = self.ai_service.get_model_status()

            for model_name, model_info in status['models'].items():
                # Extract metrics from the actual model_info structure
                success_count = model_info.get('success_count', 0)
                error_count = model_info.get('error_count', 0)
                total_requests = success_count + error_count
                error_rate = error_count / total_requests if total_requests > 0 else 0.0
                avg_response_time = model_info.get('avg_response_time', 0.0)

                # Check if model needs attention
                if error_rate > 0.5:  # 50% error rate
                    logger.warning(f"Model {model_name} has high error rate: {error_rate:.2%}")
                    self._schedule_model_reload(model_name)

                elif avg_response_time > 120:  # 2 minutes
                    logger.warning(f"Model {model_name} has slow response time: {avg_response_time:.2f}s")

                # Check if fine-tuning is needed (skip for Bedrock models)
                if model_name != 'claude-sonnet-4' and model_name != 'claude-3' and model_name != 'mistral-7b':
                    if total_requests > 100:  # Enough data to fine-tune
                        self._schedule_fine_tuning(model_name)

        except Exception as e:
            logger.error(f"Error monitoring model performance: {e}")
    
    def _schedule_model_reload(self, model_name: str):
        """Schedule a model reload"""
        try:
            asyncio.create_task(self.ai_service.reload_model(model_name))
            logger.info(f"Scheduled reload for model {model_name}")
        except Exception as e:
            logger.error(f"Failed to schedule reload for {model_name}: {e}")
    
    def _schedule_fine_tuning(self, model_name: str):
        """Schedule fine-tuning for a model"""
        if model_name not in [item['model_name'] for item in self.fine_tuning_queue]:
            self.fine_tuning_queue.append({
                'model_name': model_name,
                'scheduled_at': datetime.utcnow(),
                'priority': self.ai_service.model_configs[model_name].priority
            })
            logger.info(f"Scheduled fine-tuning for model {model_name}")
    
    def _check_fine_tuning_queue(self):
        """Process fine-tuning queue"""
        if self.fine_tuning_in_progress or not self.fine_tuning_queue:
            return
        
        # Sort by priority
        self.fine_tuning_queue.sort(key=lambda x: x['priority'])
        
        # Process next item
        next_item = self.fine_tuning_queue.pop(0)
        asyncio.create_task(self._process_fine_tuning(next_item))
    
    async def _process_fine_tuning(self, item: Dict[str, Any]):
        """Process a fine-tuning request"""
        model_name = item['model_name']
        
        try:
            self.fine_tuning_in_progress = True
            logger.info(f"Starting fine-tuning for {model_name}")
            
            # Generate training data from recent queries
            training_data_path = await self._prepare_training_data(model_name)
            
            # Start fine-tuning
            result = await self.ai_service.fine_tune_model(model_name, training_data_path)
            
            if result['success']:
                logger.info(f"Fine-tuning completed successfully for {model_name}")
                # Reload the model with fine-tuned version
                await self.ai_service.reload_model(model_name)
            else:
                logger.error(f"Fine-tuning failed for {model_name}: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"Error processing fine-tuning for {model_name}: {e}")
        
        finally:
            self.fine_tuning_in_progress = False
    
    async def _prepare_training_data(self, model_name: str) -> str:
        """Prepare training data from recent successful queries"""
        try:
            # This would typically query the database for recent successful queries
            # For now, we'll use the synthetic data generation
            
            training_data_path = f"./data/training_{model_name}_{int(time.time())}.jsonl"
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(training_data_path), exist_ok=True)
            
            # Generate training data (in production, this would come from actual queries)
            training_examples = [
                {
                    "prompt": "What are the requirements for starting a business in Kenya?",
                    "completion": "To start a business in Kenya, you need to: 1) Register your business name with the Registrar of Companies, 2) Obtain necessary licenses and permits, 3) Register for taxes with KRA, 4) Open a business bank account, 5) Comply with employment laws if hiring staff. The specific requirements depend on your business type and location."
                },
                {
                    "prompt": "Explain the process of property inheritance in Kenya.",
                    "completion": "Property inheritance in Kenya is governed by the Law of Succession Act. The process involves: 1) Obtaining a death certificate, 2) Filing for grant of representation (probate or letters of administration), 3) Publishing in the Kenya Gazette, 4) Distributing assets according to the will or intestacy laws, 5) Transferring property titles. The process can take 6-12 months depending on complexity."
                }
            ]
            
            # Write training data
            with open(training_data_path, 'w', encoding='utf-8') as f:
                for example in training_examples:
                    f.write(json.dumps(example) + '\n')
            
            return training_data_path
        
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            raise
    
    async def trigger_fine_tuning(self, model_name: str, priority: bool = False) -> Dict[str, Any]:
        """Manually trigger fine-tuning for a model"""
        try:
            if model_name not in self.ai_service.model_configs:
                raise AIServiceException(f"Model {model_name} not configured", "model_not_configured")
            
            if model_name == 'claude-sonnet-4':
                raise AIServiceException("Cannot fine-tune Claude Sonnet 4", "model_not_fine_tunable")
            
            item = {
                'model_name': model_name,
                'scheduled_at': datetime.utcnow(),
                'priority': 0 if priority else self.ai_service.model_configs[model_name].priority
            }
            
            if priority:
                self.fine_tuning_queue.insert(0, item)
            else:
                self.fine_tuning_queue.append(item)
            
            return {
                'success': True,
                'message': f"Fine-tuning scheduled for {model_name}",
                'queue_position': 0 if priority else len(self.fine_tuning_queue)
            }
        
        except Exception as e:
            logger.error(f"Error triggering fine-tuning for {model_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_fine_tuning_status(self) -> Dict[str, Any]:
        """Get current fine-tuning status"""
        return {
            'in_progress': self.fine_tuning_in_progress,
            'queue_length': len(self.fine_tuning_queue),
            'queue': [
                {
                    'model_name': item['model_name'],
                    'scheduled_at': item['scheduled_at'].isoformat(),
                    'priority': item['priority']
                }
                for item in self.fine_tuning_queue
            ]
        }
    
    async def optimize_model_performance(self) -> Dict[str, Any]:
        """Optimize overall model performance"""
        try:
            results = {}
            
            # Get current status
            status = self.ai_service.get_model_status()
            
            for model_name, model_info in status['models'].items():
                if model_info['status'] == 'failed':
                    # Try to reload failed models
                    reload_result = await self.ai_service.reload_model(model_name)
                    results[model_name] = {
                        'action': 'reload',
                        'result': reload_result
                    }

                else:
                    # Calculate error rate from actual model info
                    success_count = model_info.get('success_count', 0)
                    error_count = model_info.get('error_count', 0)
                    total_requests = success_count + error_count
                    error_rate = error_count / total_requests if total_requests > 0 else 0.0

                    if error_rate > 0.3:
                        # Schedule fine-tuning for models with high error rates (skip Bedrock models)
                        if model_name not in ['claude-sonnet-4', 'claude-3', 'mistral-7b']:
                            ft_result = await self.trigger_fine_tuning(model_name, priority=True)
                            results[model_name] = {
                                'action': 'fine_tune',
                                'result': ft_result
                            }
            
            return {
                'success': True,
                'optimizations': results,
                'timestamp': datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error optimizing model performance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        logger.info("Model manager monitoring stopped")
