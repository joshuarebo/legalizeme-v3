"""
Feature Flag Management System for Counsel AI
Enables safe feature rollouts with instant disable capability
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from functools import wraps
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class FeatureFlags:
    """
    Feature flag management for safe feature rollouts
    
    Features can be controlled via:
    1. Environment variables (FEATURE_<NAME>=true/false)
    2. Configuration file (feature_flags.json)
    3. Database configuration (future enhancement)
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "feature_flags.json"
        self._flags = {}
        self._load_flags()
    
    def _load_flags(self):
        """Load feature flags from environment and config file"""
        # Default feature flags
        default_flags = {
            # Core features (always enabled)
            "legal_queries": True,
            "conversation_management": True,
            "multimodal_processing": True,
            
            # New features (can be toggled)
            "enhanced_legal_analysis": self._get_env_flag("FEATURE_ENHANCED_ANALYSIS", False),
            "advanced_document_processing": self._get_env_flag("FEATURE_ADVANCED_DOCS", False),
            "real_time_notifications": self._get_env_flag("FEATURE_NOTIFICATIONS", False),
            "batch_operations": self._get_env_flag("FEATURE_BATCH_OPS", False),
            "webhook_support": self._get_env_flag("FEATURE_WEBHOOKS", False),
            "api_authentication": self._get_env_flag("FEATURE_AUTH", False),
            "advanced_search": self._get_env_flag("FEATURE_SEARCH", False),
            "analytics_dashboard": self._get_env_flag("FEATURE_ANALYTICS", False),
            "ai_model_selection": self._get_env_flag("FEATURE_MODEL_SELECTION", False),
            "conversation_export": self._get_env_flag("FEATURE_EXPORT", False),
        }
        
        # Load from config file if exists
        file_flags = self._load_from_file()
        
        # Merge flags (environment variables take precedence)
        self._flags = {**default_flags, **file_flags}
        
        # Override with environment variables
        for flag_name in self._flags.keys():
            env_value = self._get_env_flag(f"FEATURE_{flag_name.upper()}")
            if env_value is not None:
                self._flags[flag_name] = env_value
        
        logger.info(f"Loaded feature flags: {self._get_enabled_flags()}")
    
    def _get_env_flag(self, env_var: str, default: Optional[bool] = None) -> Optional[bool]:
        """Get feature flag value from environment variable"""
        value = os.getenv(env_var)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on", "enabled")
    
    def _load_from_file(self) -> Dict[str, bool]:
        """Load feature flags from configuration file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('feature_flags', {})
        except Exception as e:
            logger.warning(f"Failed to load feature flags from {self.config_file}: {e}")
        return {}
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled"""
        return self._flags.get(flag_name, False)
    
    def enable_flag(self, flag_name: str):
        """Enable a feature flag (runtime only)"""
        self._flags[flag_name] = True
        logger.info(f"Enabled feature flag: {flag_name}")
    
    def disable_flag(self, flag_name: str):
        """Disable a feature flag (runtime only)"""
        self._flags[flag_name] = False
        logger.info(f"Disabled feature flag: {flag_name}")
    
    def get_flag_status(self) -> Dict[str, bool]:
        """Get status of all feature flags"""
        return self._flags.copy()
    
    def _get_enabled_flags(self) -> list:
        """Get list of enabled feature flags"""
        return [name for name, enabled in self._flags.items() if enabled]
    
    def save_to_file(self):
        """Save current flag configuration to file"""
        try:
            config = {"feature_flags": self._flags}
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved feature flags to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save feature flags: {e}")


# Global feature flags instance
feature_flags = FeatureFlags()


def require_feature(flag_name: str, error_message: Optional[str] = None):
    """
    Decorator to require a feature flag for endpoint access
    
    Usage:
    @require_feature("enhanced_legal_analysis")
    async def enhanced_analysis_endpoint():
        return {"message": "Enhanced analysis feature"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not feature_flags.is_enabled(flag_name):
                message = error_message or f"Feature '{flag_name}' is not available"
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=message
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def feature_enabled(flag_name: str) -> bool:
    """
    Simple function to check if a feature is enabled
    
    Usage:
    if feature_enabled("enhanced_legal_analysis"):
        # Use enhanced analysis
        pass
    else:
        # Use standard analysis
        pass
    """
    return feature_flags.is_enabled(flag_name)


class FeatureFlagMiddleware:
    """
    Middleware to add feature flag information to responses
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add feature flags to request state
            scope["feature_flags"] = feature_flags
        
        await self.app(scope, receive, send)


# Feature flag configuration for different environments
ENVIRONMENT_CONFIGS = {
    "development": {
        "enhanced_legal_analysis": True,
        "advanced_document_processing": True,
        "real_time_notifications": True,
        "batch_operations": True,
        "webhook_support": True,
        "api_authentication": False,  # Keep disabled in dev for easier testing
        "advanced_search": True,
        "analytics_dashboard": True,
        "ai_model_selection": True,
        "conversation_export": True,
    },
    "staging": {
        "enhanced_legal_analysis": True,
        "advanced_document_processing": True,
        "real_time_notifications": False,  # Test gradually
        "batch_operations": True,
        "webhook_support": False,
        "api_authentication": False,
        "advanced_search": True,
        "analytics_dashboard": False,
        "ai_model_selection": True,
        "conversation_export": True,
    },
    "production": {
        "enhanced_legal_analysis": False,  # Gradual rollout
        "advanced_document_processing": False,
        "real_time_notifications": False,
        "batch_operations": False,
        "webhook_support": False,
        "api_authentication": False,
        "advanced_search": False,
        "analytics_dashboard": False,
        "ai_model_selection": False,
        "conversation_export": False,
    }
}


def apply_environment_config(environment: str):
    """Apply feature flag configuration for specific environment"""
    config = ENVIRONMENT_CONFIGS.get(environment, {})
    for flag_name, enabled in config.items():
        if enabled:
            feature_flags.enable_flag(flag_name)
        else:
            feature_flags.disable_flag(flag_name)
    
    logger.info(f"Applied {environment} environment configuration")


# Example usage in endpoints
"""
from app.utils.feature_flags import require_feature, feature_enabled

# Method 1: Using decorator
@router.post("/enhanced-analysis")
@require_feature("enhanced_legal_analysis")
async def enhanced_legal_analysis(query: str):
    # This endpoint is only accessible if the feature flag is enabled
    return {"analysis": "Enhanced analysis result"}

# Method 2: Using conditional logic
@router.post("/document-processing")
async def process_document(document_id: str):
    if feature_enabled("advanced_document_processing"):
        # Use advanced processing
        result = await advanced_document_processing(document_id)
    else:
        # Use standard processing
        result = await standard_document_processing(document_id)
    
    return result

# Method 3: Feature flag status endpoint
@router.get("/feature-flags")
async def get_feature_flags():
    return {
        "feature_flags": feature_flags.get_flag_status(),
        "enabled_features": [name for name, enabled in feature_flags.get_flag_status().items() if enabled]
    }
"""


# Emergency feature disable function
def emergency_disable_all_new_features():
    """
    Emergency function to disable all new features
    Call this if new features are causing issues
    """
    new_features = [
        "enhanced_legal_analysis",
        "advanced_document_processing",
        "real_time_notifications",
        "batch_operations",
        "webhook_support",
        "api_authentication",
        "advanced_search",
        "analytics_dashboard",
        "ai_model_selection",
        "conversation_export",
    ]
    
    for feature in new_features:
        feature_flags.disable_flag(feature)
    
    logger.warning("EMERGENCY: Disabled all new features")
    return {"message": "All new features disabled", "disabled_features": new_features}


# Health check integration
def get_feature_health_status() -> Dict[str, Any]:
    """Get feature flag status for health checks"""
    enabled_flags = feature_flags._get_enabled_flags()
    return {
        "total_flags": len(feature_flags._flags),
        "enabled_flags": len(enabled_flags),
        "enabled_features": enabled_flags,
        "core_features_enabled": all([
            feature_flags.is_enabled("legal_queries"),
            feature_flags.is_enabled("conversation_management"),
            feature_flags.is_enabled("multimodal_processing")
        ])
    }
