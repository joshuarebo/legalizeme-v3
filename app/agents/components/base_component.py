"""
Base Component - Abstract base class for all chaining components
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ComponentStatus(Enum):
    """Status of component execution"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"

@dataclass
class ComponentResult:
    """Result from a component execution"""
    status: ComponentStatus
    data: Dict[str, Any]
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    reasoning_steps: List[str] = field(default_factory=list)
    sources_used: List[str] = field(default_factory=list)

class ComponentError(Exception):
    """Custom exception for component errors"""
    
    def __init__(self, message: str, component_name: str, error_code: str = "unknown"):
        self.message = message
        self.component_name = component_name
        self.error_code = error_code
        super().__init__(f"[{component_name}] {message}")

class BaseComponent(ABC):
    """
    Abstract base class for all chaining components
    Provides common functionality and interface
    """
    
    def __init__(self, name: str, context_manager=None):
        self.name = name
        self.context_manager = context_manager
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0
        }
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the component"""
        try:
            await self._initialize_component()
            self._initialized = True
            logger.info(f"Component {self.name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize component {self.name}: {e}")
            return False
    
    @abstractmethod
    async def _initialize_component(self):
        """Component-specific initialization logic"""
        pass
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        **kwargs
    ) -> ComponentResult:
        """
        Execute the component with input data and context
        
        Args:
            input_data: Input data for the component
            context: Context information from context manager
            **kwargs: Additional keyword arguments
            
        Returns:
            ComponentResult with execution results
        """
        start_time = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Validate input
            validation_result = await self._validate_input(input_data, context)
            if not validation_result["valid"]:
                return ComponentResult(
                    status=ComponentStatus.FAILURE,
                    data={},
                    error_message=f"Input validation failed: {validation_result['error']}",
                    processing_time_ms=(time.time() - start_time) * 1000
                )
            
            # Pre-processing
            preprocessed_data = await self._preprocess_input(input_data, context)
            
            # Main execution
            result_data = await self._execute_component(preprocessed_data, context, **kwargs)
            
            # Post-processing
            final_data = await self._postprocess_output(result_data, context)
            
            # Calculate confidence
            confidence = await self._calculate_confidence(final_data, context)
            
            # Create result
            processing_time = (time.time() - start_time) * 1000
            result = ComponentResult(
                status=ComponentStatus.SUCCESS,
                data=final_data,
                confidence=confidence,
                processing_time_ms=processing_time,
                metadata={
                    "component_name": self.name,
                    "execution_timestamp": datetime.utcnow().isoformat(),
                    "input_size": len(str(input_data)),
                    "output_size": len(str(final_data))
                }
            )
            
            # Update metrics
            self._update_metrics(result)
            
            return result
            
        except ComponentError as e:
            processing_time = (time.time() - start_time) * 1000
            self.metrics["failed_executions"] += 1
            
            return ComponentResult(
                status=ComponentStatus.FAILURE,
                data={},
                error_message=str(e),
                processing_time_ms=processing_time,
                metadata={"component_name": self.name, "error_code": e.error_code}
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.metrics["failed_executions"] += 1
            logger.error(f"Unexpected error in component {self.name}: {e}")
            
            return ComponentResult(
                status=ComponentStatus.FAILURE,
                data={},
                error_message=f"Unexpected error: {str(e)}",
                processing_time_ms=processing_time,
                metadata={"component_name": self.name}
            )
    
    @abstractmethod
    async def _execute_component(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Component-specific execution logic"""
        pass
    
    async def _validate_input(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate input data - override in subclasses for specific validation"""
        if not isinstance(input_data, dict):
            return {"valid": False, "error": "Input data must be a dictionary"}
        
        return {"valid": True}
    
    async def _preprocess_input(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Preprocess input data - override in subclasses for specific preprocessing"""
        return input_data
    
    async def _postprocess_output(
        self,
        output_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Postprocess output data - override in subclasses for specific postprocessing"""
        return output_data
    
    async def _calculate_confidence(
        self,
        output_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """Calculate confidence score - override in subclasses for specific confidence calculation"""
        return 0.8  # Default confidence
    
    def _update_metrics(self, result: ComponentResult):
        """Update component metrics"""
        self.metrics["total_executions"] += 1
        
        if result.status == ComponentStatus.SUCCESS:
            self.metrics["successful_executions"] += 1
        
        # Update averages
        total_executions = self.metrics["total_executions"]
        
        # Update average processing time
        current_avg_time = self.metrics["avg_processing_time"]
        new_avg_time = ((current_avg_time * (total_executions - 1)) + result.processing_time_ms) / total_executions
        self.metrics["avg_processing_time"] = new_avg_time
        
        # Update average confidence
        if result.status == ComponentStatus.SUCCESS:
            current_avg_confidence = self.metrics["avg_confidence"]
            successful_executions = self.metrics["successful_executions"]
            new_avg_confidence = ((current_avg_confidence * (successful_executions - 1)) + result.confidence) / successful_executions
            self.metrics["avg_confidence"] = new_avg_confidence
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get component metrics"""
        success_rate = (self.metrics["successful_executions"] / 
                       max(self.metrics["total_executions"], 1))
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "component_name": self.name,
            "initialized": self._initialized
        }
    
    def reset_metrics(self):
        """Reset component metrics"""
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the component"""
        health_status = {
            "component_name": self.name,
            "initialized": self._initialized,
            "status": "healthy",
            "issues": []
        }
        
        # Check if component is initialized
        if not self._initialized:
            health_status["status"] = "unhealthy"
            health_status["issues"].append("Component not initialized")
        
        # Check success rate
        if self.metrics["total_executions"] > 0:
            success_rate = (self.metrics["successful_executions"] / 
                           self.metrics["total_executions"])
            if success_rate < 0.5:
                health_status["status"] = "degraded"
                health_status["issues"].append(f"Low success rate: {success_rate:.2%}")
        
        # Component-specific health checks
        component_health = await self._component_health_check()
        health_status.update(component_health)
        
        return health_status
    
    async def _component_health_check(self) -> Dict[str, Any]:
        """Component-specific health check - override in subclasses"""
        return {}
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, initialized={self._initialized})"
    
    def __repr__(self) -> str:
        return self.__str__()
