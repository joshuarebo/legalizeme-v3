"""
Context Refinement Loop - Adaptive context improvement based on feedback
"""

import logging
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class RefinementTrigger(Enum):
    """Triggers for context refinement"""
    LOW_CONFIDENCE = "low_confidence"
    POOR_QUALITY = "poor_quality"
    USER_FEEDBACK = "user_feedback"
    BENCHMARK_FAILURE = "benchmark_failure"
    PATTERN_DETECTION = "pattern_detection"

@dataclass
class RefinementAction:
    """Action to take for context refinement"""
    action_type: str
    target_component: str
    modification: Dict[str, Any]
    expected_improvement: str
    confidence: float

@dataclass
class RefinementResult:
    """Result of a refinement attempt"""
    trigger: RefinementTrigger
    actions_taken: List[RefinementAction]
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    improvement_achieved: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)

class ContextRefinementLoop:
    """
    Implements adaptive context refinement based on performance feedback
    Analyzes failures and automatically adjusts context parameters
    """
    
    def __init__(self, context_manager, monitor, log_directory: str = "logs"):
        self.context_manager = context_manager
        self.monitor = monitor
        self.log_directory = Path(log_directory)
        self.refinement_logs_dir = self.log_directory / "context_refinements"
        
        # Create directories
        self.refinement_logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Refinement history
        self.refinement_history: List[RefinementResult] = []
        self.max_history_items = 50
        
        # Configuration
        self.enable_auto_refinement = True
        self.refinement_threshold = 0.6  # Quality threshold for triggering refinement
        self.min_samples_for_pattern = 5  # Minimum failures to detect pattern
        
        # Refinement strategies
        self.refinement_strategies = {
            RefinementTrigger.LOW_CONFIDENCE: self._refine_for_low_confidence,
            RefinementTrigger.POOR_QUALITY: self._refine_for_poor_quality,
            RefinementTrigger.USER_FEEDBACK: self._refine_for_user_feedback,
            RefinementTrigger.BENCHMARK_FAILURE: self._refine_for_benchmark_failure,
            RefinementTrigger.PATTERN_DETECTION: self._refine_for_pattern
        }
    
    async def analyze_and_refine(self) -> Optional[RefinementResult]:
        """Analyze recent performance and apply refinements if needed"""
        
        if not self.enable_auto_refinement:
            return None
        
        # Get recent performance data
        failure_stats = self.monitor.get_failure_statistics()
        quality_stats = self.monitor.get_quality_statistics()
        
        # Determine if refinement is needed
        refinement_trigger = self._determine_refinement_trigger(failure_stats, quality_stats)
        
        if refinement_trigger:
            logger.info(f"Context refinement triggered: {refinement_trigger.value}")
            return await self._execute_refinement(refinement_trigger, failure_stats, quality_stats)
        
        return None
    
    def _determine_refinement_trigger(
        self,
        failure_stats: Dict[str, Any],
        quality_stats: Dict[str, Any]
    ) -> Optional[RefinementTrigger]:
        """Determine if and why refinement should be triggered"""
        
        # Check for low quality trend
        avg_quality = quality_stats.get("average_quality", 1.0)
        if avg_quality < self.refinement_threshold:
            return RefinementTrigger.POOR_QUALITY
        
        # Check for low confidence
        avg_confidence = quality_stats.get("average_confidence", 1.0)
        if avg_confidence < 0.5:
            return RefinementTrigger.LOW_CONFIDENCE
        
        # Check for failure patterns
        total_failures = failure_stats.get("total_failures", 0)
        if total_failures >= self.min_samples_for_pattern:
            return RefinementTrigger.PATTERN_DETECTION
        
        # Check quality trend
        quality_trend = quality_stats.get("quality_trend", "stable")
        if quality_trend == "declining":
            return RefinementTrigger.POOR_QUALITY
        
        return None
    
    async def _execute_refinement(
        self,
        trigger: RefinementTrigger,
        failure_stats: Dict[str, Any],
        quality_stats: Dict[str, Any]
    ) -> RefinementResult:
        """Execute refinement based on trigger"""
        
        # Get current metrics
        before_metrics = {
            "average_quality": quality_stats.get("average_quality", 0.0),
            "average_confidence": quality_stats.get("average_confidence", 0.0),
            "total_failures": failure_stats.get("total_failures", 0)
        }
        
        # Apply refinement strategy
        refinement_strategy = self.refinement_strategies.get(trigger)
        if refinement_strategy:
            actions_taken = await refinement_strategy(failure_stats, quality_stats)
        else:
            actions_taken = []
        
        # Create refinement result (after_metrics would be populated later)
        result = RefinementResult(
            trigger=trigger,
            actions_taken=actions_taken,
            before_metrics=before_metrics,
            after_metrics={},  # Will be updated after observing results
            improvement_achieved=False  # Will be updated later
        )
        
        # Store refinement
        self.refinement_history.append(result)
        if len(self.refinement_history) > self.max_history_items:
            self.refinement_history = self.refinement_history[-self.max_history_items:]
        
        # Log refinement
        await self._log_refinement(result)
        
        return result
    
    async def _refine_for_low_confidence(
        self,
        failure_stats: Dict[str, Any],
        quality_stats: Dict[str, Any]
    ) -> List[RefinementAction]:
        """Refine context for low confidence issues"""
        
        actions = []
        
        # Action 1: Increase retrieval scope
        actions.append(RefinementAction(
            action_type="increase_retrieval_scope",
            target_component="VectorRetriever",
            modification={
                "max_sources": 15,  # Increase from default
                "relevance_threshold": 0.2,  # Lower threshold
                "use_hybrid": True
            },
            expected_improvement="More comprehensive document retrieval",
            confidence=0.7
        ))
        
        # Action 2: Enhance reasoning depth
        actions.append(RefinementAction(
            action_type="enhance_reasoning",
            target_component="LegalReasoner",
            modification={
                "depth_level": "deep",
                "max_reasoning_steps": 10,
                "include_counterarguments": True
            },
            expected_improvement="More thorough legal analysis",
            confidence=0.8
        ))
        
        # Apply actions
        await self._apply_refinement_actions(actions)
        
        return actions
    
    async def _refine_for_poor_quality(
        self,
        failure_stats: Dict[str, Any],
        quality_stats: Dict[str, Any]
    ) -> List[RefinementAction]:
        """Refine context for poor quality responses"""
        
        actions = []
        
        # Analyze failure stages to target specific components
        failure_stages = failure_stats.get("failure_stages", {})
        
        if "retrieval" in failure_stages:
            actions.append(RefinementAction(
                action_type="improve_retrieval_strategy",
                target_component="VectorRetriever",
                modification={
                    "strategy": "comprehensive",
                    "diversify_results": True,
                    "use_semantic": True,
                    "use_keyword": True
                },
                expected_improvement="Better document retrieval quality",
                confidence=0.75
            ))
        
        if "reasoning" in failure_stages:
            actions.append(RefinementAction(
                action_type="strengthen_reasoning",
                target_component="LegalReasoner",
                modification={
                    "include_precedents": True,
                    "include_practical_implications": True,
                    "confidence_threshold": 0.8
                },
                expected_improvement="Stronger legal reasoning",
                confidence=0.8
            ))
        
        if "formatting" in failure_stages:
            actions.append(RefinementAction(
                action_type="enhance_formatting",
                target_component="AnswerFormatter",
                modification={
                    "strategy": "comprehensive",
                    "include_citations": True,
                    "include_confidence": True
                },
                expected_improvement="Better response formatting",
                confidence=0.7
            ))
        
        # Apply actions
        await self._apply_refinement_actions(actions)
        
        return actions
    
    async def _refine_for_user_feedback(
        self,
        failure_stats: Dict[str, Any],
        quality_stats: Dict[str, Any]
    ) -> List[RefinementAction]:
        """Refine context based on user feedback"""
        
        # This would be implemented based on actual user feedback mechanisms
        actions = []
        
        # Placeholder for user feedback-based refinements
        actions.append(RefinementAction(
            action_type="adjust_based_on_feedback",
            target_component="ContextManager",
            modification={
                "user_feedback_integration": True,
                "adaptive_learning": True
            },
            expected_improvement="Better alignment with user expectations",
            confidence=0.6
        ))
        
        return actions
    
    async def _refine_for_benchmark_failure(
        self,
        failure_stats: Dict[str, Any],
        quality_stats: Dict[str, Any]
    ) -> List[RefinementAction]:
        """Refine context for benchmark failures"""
        
        actions = []
        
        # Enhance all components for benchmark performance
        actions.append(RefinementAction(
            action_type="optimize_for_benchmarks",
            target_component="All",
            modification={
                "benchmark_mode": True,
                "enhanced_accuracy": True,
                "comprehensive_analysis": True
            },
            expected_improvement="Better benchmark performance",
            confidence=0.8
        ))
        
        return actions
    
    async def _refine_for_pattern(
        self,
        failure_stats: Dict[str, Any],
        quality_stats: Dict[str, Any]
    ) -> List[RefinementAction]:
        """Refine context based on detected failure patterns"""
        
        actions = []
        failure_stages = failure_stats.get("failure_stages", {})
        
        # Find the most common failure stage
        if failure_stages:
            most_common_stage = max(failure_stages.items(), key=lambda x: x[1])[0]
            
            if most_common_stage == "context_analysis":
                actions.append(RefinementAction(
                    action_type="improve_context_analysis",
                    target_component="ContextManager",
                    modification={
                        "enhanced_domain_detection": True,
                        "improved_complexity_analysis": True
                    },
                    expected_improvement="Better context understanding",
                    confidence=0.75
                ))
            
            elif most_common_stage == "tool_selection":
                actions.append(RefinementAction(
                    action_type="improve_tool_routing",
                    target_component="ContextRouter",
                    modification={
                        "enhanced_routing_rules": True,
                        "better_tool_mapping": True
                    },
                    expected_improvement="More accurate tool selection",
                    confidence=0.8
                ))
        
        # Apply actions
        await self._apply_refinement_actions(actions)
        
        return actions
    
    async def _apply_refinement_actions(self, actions: List[RefinementAction]):
        """Apply refinement actions to the system"""
        
        for action in actions:
            try:
                await self._apply_single_action(action)
                logger.info(f"Applied refinement action: {action.action_type}")
            except Exception as e:
                logger.error(f"Failed to apply refinement action {action.action_type}: {e}")
    
    async def _apply_single_action(self, action: RefinementAction):
        """Apply a single refinement action"""
        
        # This is a simplified implementation
        # In practice, this would modify the actual component configurations
        
        if action.target_component == "VectorRetriever":
            # Update retriever configuration
            pass
        elif action.target_component == "LegalReasoner":
            # Update reasoner configuration
            pass
        elif action.target_component == "AnswerFormatter":
            # Update formatter configuration
            pass
        elif action.target_component == "ContextManager":
            # Update context manager configuration
            pass
        
        # For now, just log the action
        logger.info(f"Refinement action applied: {action.action_type} on {action.target_component}")
    
    async def _log_refinement(self, result: RefinementResult):
        """Log refinement result to file"""
        
        try:
            timestamp = result.timestamp
            filename = f"refinement_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.refinement_logs_dir / filename
            
            refinement_dict = {
                "timestamp": result.timestamp.isoformat(),
                "trigger": result.trigger.value,
                "actions_taken": [
                    {
                        "action_type": action.action_type,
                        "target_component": action.target_component,
                        "modification": action.modification,
                        "expected_improvement": action.expected_improvement,
                        "confidence": action.confidence
                    }
                    for action in result.actions_taken
                ],
                "before_metrics": result.before_metrics,
                "after_metrics": result.after_metrics,
                "improvement_achieved": result.improvement_achieved
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(refinement_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to log refinement: {e}")
    
    async def evaluate_refinement_effectiveness(self, refinement_id: str) -> bool:
        """Evaluate if a refinement was effective"""
        
        # This would compare metrics before and after refinement
        # For now, return a placeholder
        return True
    
    def get_refinement_statistics(self) -> Dict[str, Any]:
        """Get refinement statistics"""
        
        if not self.refinement_history:
            return {"total_refinements": 0, "success_rate": 0.0}
        
        total_refinements = len(self.refinement_history)
        successful_refinements = sum(1 for r in self.refinement_history if r.improvement_achieved)
        success_rate = successful_refinements / total_refinements
        
        # Count refinements by trigger
        trigger_counts = {}
        for refinement in self.refinement_history:
            trigger = refinement.trigger.value
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        return {
            "total_refinements": total_refinements,
            "success_rate": success_rate,
            "refinements_by_trigger": trigger_counts,
            "recent_refinements": [
                {
                    "trigger": r.trigger.value,
                    "actions_count": len(r.actions_taken),
                    "improvement": r.improvement_achieved,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.refinement_history[-5:]  # Last 5 refinements
            ]
        }


# Convenience decorator function
def refine_context(context_manager, monitor, log_directory: str = "logs"):
    """Convenience function to create ContextRefinementLoop"""
    return ContextRefinementLoop(context_manager, monitor, log_directory)
