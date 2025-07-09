"""
Unit tests for AWS Bedrock model integration
Tests successful responses, fallback triggering, and max token cutoff
"""

import pytest
import asyncio
import json
import os
from unittest.mock import Mock, patch, AsyncMock
from botocore.exceptions import ClientError

# Set testing environment before importing app modules
os.environ["TESTING"] = "true"
os.environ["AWS_ACCESS_KEY_ID"] = "test-key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret"

from app.config import settings


class TestBedrockModels:
    """Test suite for Bedrock model integration"""
    
    @pytest.fixture
    def llm_manager(self):
        """Create LLM manager instance for testing"""
        return LLMManager()
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock client"""
        mock_client = Mock()
        return mock_client
    
    @pytest.fixture
    def claude_success_response(self):
        """Mock successful Claude response"""
        return {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': [{'text': 'This is a successful response from Claude about Kenyan law.'}]
            }).encode()))
        }
    
    @pytest.fixture
    def mistral_success_response(self):
        """Mock successful Mistral response"""
        return {
            'body': Mock(read=Mock(return_value=json.dumps({
                'outputs': [{'text': 'This is a successful response from Mistral about Kenyan law.'}]
            }).encode()))
        }
    
    @pytest.mark.asyncio
    async def test_claude_sonnet_success(self, llm_manager, mock_bedrock_client, claude_success_response):
        """Test successful Claude Sonnet response"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = claude_success_response
        
        # Test the invocation
        result = await llm_manager.invoke_model(
            "What are the constitutional rights in Kenya?",
            model_preference="claude-sonnet-4"
        )

        # Assertions
        assert result['success'] is True
        assert result['model_used'] == 'claude-sonnet-4'
        assert 'constitutional rights' in result['response_text'].lower() or 'claude' in result['response_text'].lower()
        assert result['latency_ms'] > 0
        assert result['model_id'] == settings.AWS_BEDROCK_MODEL_ID_PRIMARY
        
        # Verify the correct model was called
        mock_bedrock_client.invoke_model.assert_called_once()
        call_args = mock_bedrock_client.invoke_model.call_args
        assert call_args[1]['modelId'] == settings.AWS_BEDROCK_MODEL_ID_PRIMARY
    
    @pytest.mark.asyncio
    async def test_claude_haiku_success(self, llm_manager, mock_bedrock_client, claude_success_response):
        """Test successful Claude Haiku response"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = claude_success_response
        
        # Test the invocation
        result = await llm_manager.invoke_model(
            "Explain company registration in Kenya",
            model_preference="claude-3-7"
        )

        # Assertions
        assert result['success'] is True
        assert result['model_used'] == 'claude-3-7'
        assert result['model_id'] == settings.AWS_BEDROCK_MODEL_ID_SECONDARY
    
    @pytest.mark.asyncio
    async def test_mistral_success(self, llm_manager, mock_bedrock_client, mistral_success_response):
        """Test successful Mistral response"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = mistral_success_response
        
        # Test the invocation
        result = await llm_manager.invoke_model(
            "What is guardianship law in Kenya?",
            model_preference="mistral-large"
        )

        # Assertions
        assert result['success'] is True
        assert result['model_used'] == 'mistral-large'
        assert result['model_id'] == settings.AWS_BEDROCK_MODEL_ID_FALLBACK
    
    @pytest.mark.asyncio
    async def test_fallback_primary_to_secondary(self, llm_manager, mock_bedrock_client, claude_success_response):
        """Test fallback from primary to secondary model"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        
        # First call fails (primary model), second succeeds (secondary model)
        mock_bedrock_client.invoke_model.side_effect = [
            ClientError(
                error_response={'Error': {'Code': 'ValidationException', 'Message': 'Model not available'}},
                operation_name='InvokeModel'
            ),
            claude_success_response
        ]
        
        # Test the invocation
        result = await llm_manager.invoke_model("Test query")
        
        # Assertions
        assert result['success'] is True
        assert result['model_used'] == 'claude-3-7'  # Should fallback to secondary
        assert mock_bedrock_client.invoke_model.call_count == 2
    
    @pytest.mark.asyncio
    async def test_fallback_to_mistral(self, llm_manager, mock_bedrock_client, mistral_success_response):
        """Test fallback all the way to Mistral"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        
        # First two calls fail, third succeeds (Mistral)
        mock_bedrock_client.invoke_model.side_effect = [
            ClientError(
                error_response={'Error': {'Code': 'ValidationException', 'Message': 'Model not available'}},
                operation_name='InvokeModel'
            ),
            ClientError(
                error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate limit exceeded'}},
                operation_name='InvokeModel'
            ),
            mistral_success_response
        ]
        
        # Test the invocation
        result = await llm_manager.invoke_model("Test query")
        
        # Assertions
        assert result['success'] is True
        assert result['model_used'] == 'mistral-large'  # Should fallback to tertiary
        assert mock_bedrock_client.invoke_model.call_count == 3
    
    @pytest.mark.asyncio
    async def test_all_models_fail(self, llm_manager, mock_bedrock_client):
        """Test when all models fail"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        
        # All calls fail
        mock_bedrock_client.invoke_model.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'All models unavailable'}},
            operation_name='InvokeModel'
        )
        
        # Test the invocation
        with pytest.raises(Exception) as exc_info:
            await llm_manager.invoke_model("Test query")
        
        # Assertions
        assert "All models failed" in str(exc_info.value)
        assert mock_bedrock_client.invoke_model.call_count == 3  # Should try all 3 models
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, llm_manager, mock_bedrock_client):
        """Test timeout handling"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        
        # Mock a timeout
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(35)  # Longer than timeout
            return Mock()
        
        with patch('asyncio.to_thread', side_effect=slow_invoke):
            with pytest.raises(Exception) as exc_info:
                await llm_manager.invoke_model("Test query", model_preference="claude-sonnet-4")
        
        # Should timeout
        assert "timeout" in str(exc_info.value).lower() or "timed out" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_max_token_cutoff(self, llm_manager, mock_bedrock_client):
        """Test max token cutoff handling"""
        # Mock response with truncated content
        truncated_response = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': [{'text': 'This response was cut off due to max'}]
            }).encode()))
        }
        
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = truncated_response
        
        # Test with a very long prompt
        long_prompt = "Explain Kenyan law in detail. " * 1000  # Very long prompt
        
        result = await llm_manager.invoke_model(long_prompt, model_preference="claude-sonnet-4")
        
        # Should still succeed but with truncated response
        assert result['success'] is True
        assert len(result['response_text']) > 0
    
    @pytest.mark.asyncio
    async def test_model_status_tracking(self, llm_manager, mock_bedrock_client, claude_success_response):
        """Test model status tracking"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = claude_success_response
        
        # Initial status should be healthy
        status = llm_manager.get_model_status()
        assert status['models']['claude-sonnet-4']['status'] == 'healthy'

        # Make a successful call
        await llm_manager.invoke_model("Test", model_preference="claude-sonnet-4")

        # Status should still be healthy and success count should increase
        status = llm_manager.get_model_status()
        assert status['models']['claude-sonnet-4']['status'] == 'healthy'
        assert status['models']['claude-sonnet-4']['success_count'] > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, llm_manager, mock_bedrock_client, claude_success_response):
        """Test health check functionality"""
        # Mock the bedrock client
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = claude_success_response
        
        # Run health check
        health_results = await llm_manager.health_check()
        
        # Should have results for all models
        assert 'claude-sonnet-4' in health_results
        assert 'claude-3-7' in health_results
        assert 'mistral-large' in health_results
        
        # At least one model should be healthy
        healthy_models = [name for name, result in health_results.items() if result.get('healthy', False)]
        assert len(healthy_models) > 0
    
    def test_model_configuration(self, llm_manager):
        """Test model configuration"""
        # Check that all expected models are configured
        assert 'claude-sonnet-4' in llm_manager.models
        assert 'claude-3-7' in llm_manager.models
        assert 'mistral-large' in llm_manager.models

        # Check priority ordering
        claude_sonnet = llm_manager.models['claude-sonnet-4']
        claude_3_7 = llm_manager.models['claude-3-7']
        mistral = llm_manager.models['mistral-large']

        assert claude_sonnet.priority < claude_3_7.priority
        assert claude_3_7.priority < mistral.priority
        
        # Check model IDs
        assert claude_sonnet.model_id == settings.AWS_BEDROCK_MODEL_ID_PRIMARY
        assert claude_3_7.model_id == settings.AWS_BEDROCK_MODEL_ID_SECONDARY
        assert mistral.model_id == settings.AWS_BEDROCK_MODEL_ID_FALLBACK
    
    @pytest.mark.asyncio
    async def test_request_body_format(self, llm_manager, mock_bedrock_client, claude_success_response):
        """Test that request bodies are formatted correctly for different models"""
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = claude_success_response
        
        # Test Claude model request format
        await llm_manager.invoke_model("Test", model_preference="claude-sonnet-4")
        
        call_args = mock_bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        
        # Claude should have anthropic_version and messages format
        assert 'anthropic_version' in body
        assert 'messages' in body
        assert body['messages'][0]['role'] == 'user'
        assert body['messages'][0]['content'] == 'Test'
    
    @pytest.mark.asyncio
    async def test_mistral_request_format(self, llm_manager, mock_bedrock_client, mistral_success_response):
        """Test Mistral request format"""
        llm_manager.bedrock_client = mock_bedrock_client
        mock_bedrock_client.invoke_model.return_value = mistral_success_response
        
        # Test Mistral model request format
        await llm_manager.invoke_model("Test", model_preference="mistral-large")
        
        call_args = mock_bedrock_client.invoke_model.call_args
        body = json.loads(call_args[1]['body'])
        
        # Mistral should have prompt format
        assert 'prompt' in body
        assert body['prompt'] == 'Test'
        assert 'stop' in body

# Simple tests that don't require complex mocking
def test_settings_configuration():
    """Test that settings are properly configured for testing"""
    assert settings.ENVIRONMENT == "testing"
    assert settings.AWS_ACCESS_KEY_ID == "test-key"
    assert settings.AWS_SECRET_ACCESS_KEY == "test-secret"

def test_model_ids_configured():
    """Test that model IDs are configured"""
    assert settings.AWS_BEDROCK_MODEL_ID_PRIMARY is not None
    assert settings.AWS_BEDROCK_MODEL_ID_SECONDARY is not None
    assert settings.AWS_BEDROCK_MODEL_ID_FALLBACK is not None
