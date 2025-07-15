"""
Simple Token Counting Service
Replaces tiktoken with lightweight token estimation
"""

import logging
import re
from typing import Dict, Any, List
import math

logger = logging.getLogger(__name__)

class TokenService:
    """Lightweight token counting service"""
    
    def __init__(self):
        # Approximate tokens per character for different models
        self.model_ratios = {
            'claude-3-sonnet': 0.25,  # ~4 chars per token
            'claude-3-haiku': 0.25,
            'claude-3-opus': 0.25,
            'gpt-4': 0.25,
            'gpt-3.5-turbo': 0.25,
            'default': 0.25
        }
        
        # Common patterns that affect token count
        self.patterns = {
            'whitespace': re.compile(r'\s+'),
            'punctuation': re.compile(r'[^\w\s]'),
            'numbers': re.compile(r'\d+'),
            'words': re.compile(r'\b\w+\b')
        }
    
    def count_tokens(self, text: str, model: str = 'default') -> int:
        """Estimate token count for text"""
        if not text:
            return 0
        
        try:
            # Get model-specific ratio
            ratio = self.model_ratios.get(model, self.model_ratios['default'])
            
            # Basic character-based estimation
            char_estimate = len(text) * ratio
            
            # Adjust based on text characteristics
            word_count = len(self.patterns['words'].findall(text))
            punct_count = len(self.patterns['punctuation'].findall(text))
            
            # More words = slightly fewer tokens per character
            # More punctuation = slightly more tokens
            adjustment = 1.0
            if word_count > 0:
                avg_word_length = len(text.replace(' ', '')) / word_count
                if avg_word_length > 6:  # Longer words = fewer tokens
                    adjustment *= 0.9
                elif avg_word_length < 4:  # Shorter words = more tokens
                    adjustment *= 1.1
            
            # Punctuation adjustment
            punct_ratio = punct_count / len(text) if text else 0
            if punct_ratio > 0.1:  # High punctuation
                adjustment *= 1.1
            
            estimated_tokens = int(char_estimate * adjustment)
            
            # Minimum of 1 token for non-empty text
            return max(1, estimated_tokens)
            
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: very rough estimate
            return max(1, len(text) // 4)
    
    def count_tokens_batch(self, texts: List[str], model: str = 'default') -> List[int]:
        """Count tokens for multiple texts"""
        return [self.count_tokens(text, model) for text in texts]
    
    def estimate_cost(self, text: str, model: str = 'claude-3-sonnet', 
                     input_cost_per_1k: float = 0.003, 
                     output_cost_per_1k: float = 0.015) -> Dict[str, Any]:
        """Estimate API cost for text processing"""
        try:
            token_count = self.count_tokens(text, model)
            
            # Estimate input cost
            input_cost = (token_count / 1000) * input_cost_per_1k
            
            # Estimate output cost (assume 1:1 ratio for simplicity)
            output_cost = (token_count / 1000) * output_cost_per_1k
            
            total_cost = input_cost + output_cost
            
            return {
                'token_count': token_count,
                'input_cost': round(input_cost, 6),
                'output_cost': round(output_cost, 6),
                'total_cost': round(total_cost, 6),
                'model': model
            }
            
        except Exception as e:
            logger.error(f"Error estimating cost: {e}")
            return {
                'token_count': 0,
                'input_cost': 0.0,
                'output_cost': 0.0,
                'total_cost': 0.0,
                'model': model,
                'error': str(e)
            }
    
    def check_token_limit(self, text: str, limit: int = 8000, model: str = 'default') -> Dict[str, Any]:
        """Check if text exceeds token limit"""
        try:
            token_count = self.count_tokens(text, model)
            
            return {
                'token_count': token_count,
                'limit': limit,
                'within_limit': token_count <= limit,
                'excess_tokens': max(0, token_count - limit),
                'usage_percentage': round((token_count / limit) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Error checking token limit: {e}")
            return {
                'token_count': 0,
                'limit': limit,
                'within_limit': True,
                'excess_tokens': 0,
                'usage_percentage': 0.0,
                'error': str(e)
            }
    
    def truncate_to_limit(self, text: str, limit: int = 8000, model: str = 'default') -> str:
        """Truncate text to stay within token limit"""
        try:
            current_tokens = self.count_tokens(text, model)
            
            if current_tokens <= limit:
                return text
            
            # Estimate how much to truncate
            ratio = limit / current_tokens
            target_chars = int(len(text) * ratio * 0.9)  # 90% to be safe
            
            # Truncate at word boundary
            truncated = text[:target_chars]
            last_space = truncated.rfind(' ')
            if last_space > target_chars * 0.8:  # If we can find a reasonable word boundary
                truncated = truncated[:last_space]
            
            # Verify it's within limit
            if self.count_tokens(truncated, model) > limit:
                # More aggressive truncation
                while len(truncated) > 0 and self.count_tokens(truncated, model) > limit:
                    truncated = truncated[:-100]  # Remove 100 chars at a time
                    last_space = truncated.rfind(' ')
                    if last_space > 0:
                        truncated = truncated[:last_space]
            
            return truncated
            
        except Exception as e:
            logger.error(f"Error truncating text: {e}")
            # Fallback: simple character truncation
            return text[:limit * 4]  # Rough estimate
    
    def get_text_stats(self, text: str, model: str = 'default') -> Dict[str, Any]:
        """Get comprehensive text statistics"""
        try:
            return {
                'character_count': len(text),
                'word_count': len(self.patterns['words'].findall(text)),
                'token_count': self.count_tokens(text, model),
                'punctuation_count': len(self.patterns['punctuation'].findall(text)),
                'line_count': text.count('\n') + 1,
                'estimated_reading_time_minutes': round(len(self.patterns['words'].findall(text)) / 200, 1),
                'model': model
            }
            
        except Exception as e:
            logger.error(f"Error getting text stats: {e}")
            return {
                'character_count': 0,
                'word_count': 0,
                'token_count': 0,
                'punctuation_count': 0,
                'line_count': 0,
                'estimated_reading_time_minutes': 0.0,
                'model': model,
                'error': str(e)
            }

# Global instance
token_service = TokenService()
