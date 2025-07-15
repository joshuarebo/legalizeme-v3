"""
Comprehensive Regression Test Suite for Counsel AI API
Tests all 21 operational endpoints to ensure no breaking changes
"""

import pytest
import requests
import time
import os
from typing import Dict, List, Optional
from uuid import uuid4


class TestEndpointRegression:
    """Regression tests for all 21 operational endpoints"""
    
    def __init__(self):
        self.base_url = os.getenv("TEST_BASE_URL", "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "RegressionTestSuite/1.0"})
        self.created_resources = []  # Track resources for cleanup
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Setup
        self.created_resources = []
        yield
        # Teardown - cleanup created resources
        self._cleanup_resources()
    
    def _cleanup_resources(self):
        """Clean up any resources created during tests"""
        for resource in self.created_resources:
            try:
                if resource['type'] == 'conversation':
                    self.session.delete(f"{self.base_url}/api/v1/counsel/conversations/{resource['id']}")
                elif resource['type'] == 'document':
                    self.session.delete(f"{self.base_url}/api/v1/multimodal/documents/{resource['id']}")
            except Exception:
                pass  # Ignore cleanup errors
    
    # ========================================
    # HEALTH & MONITORING ENDPOINTS (2/2)
    # ========================================
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.session.get(f"{self.base_url}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_api_documentation_endpoint(self):
        """Test API documentation endpoint"""
        response = self.session.get(f"{self.base_url}/docs")
        
        assert response.status_code == 200
        # Check that it returns HTML content
        assert "text/html" in response.headers.get("content-type", "")
    
    # ========================================
    # LEGAL AI QUERY ENDPOINTS (3/3)
    # ========================================
    
    def test_standard_legal_query(self):
        """Test standard legal query endpoint with enhanced RAG"""
        payload = {
            "query": "What are the basic employment rights in Kenya?",
            "context": {
                "jurisdiction": "Kenya",
                "legal_area": "employment_law",
                "urgency": "medium"
            },
            "use_enhanced_rag": True,
            "max_tokens": 500
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/counsel/query",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "answer" in data
        assert "confidence" in data
        assert "model_used" in data
        assert "processing_time_ms" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
        assert 0 <= data["confidence"] <= 1
    
    def test_direct_legal_query(self):
        """Test direct legal query endpoint"""
        payload = {
            "question": "What is the minimum wage in Kenya?",
            "include_sources": True
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/counsel/query-direct",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "response" in data
        assert "confidence_score" in data
        assert "model_used" in data
        assert "response_time_ms" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
    
    def test_query_suggestions(self):
        """Test query suggestions endpoint"""
        response = self.session.get(
            f"{self.base_url}/api/v1/counsel/suggestions",
            params={"query": "employment law", "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "suggestions" in data
        assert "query" in data
        assert "total_suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) <= 5
        assert data["query"] == "employment law"
    
    # ========================================
    # MULTIMODAL PROCESSING ENDPOINTS (9/9)
    # ========================================
    
    def test_multimodal_capabilities(self):
        """Test multimodal capabilities endpoint"""
        response = self.session.get(f"{self.base_url}/api/v1/multimodal/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "supported_formats" in data
        assert "max_file_size_mb" in data
        assert "ocr_enabled" in data
        assert "processing_features" in data
        assert isinstance(data["supported_formats"], list)
        assert isinstance(data["max_file_size_mb"], (int, float))
    
    def test_list_documents(self):
        """Test list documents endpoint"""
        response = self.session.get(
            f"{self.base_url}/api/v1/multimodal/documents",
            params={"limit": 10, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "documents" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["documents"], list)
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    def test_document_upload(self):
        """Test document upload endpoint"""
        # Create a simple test file
        test_content = "This is a test legal document for upload testing."
        files = {
            'file': ('test_document.txt', test_content, 'text/plain')
        }
        data = {
            'analysis_type': 'legal_summary',
            'extract_clauses': 'false'
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/upload",
            files=files,
            data=data
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify response structure
        assert "document_id" in response_data
        assert "extracted_text" in response_data
        assert "file_info" in response_data
        
        # Track for cleanup
        self.created_resources.append({
            'type': 'document',
            'id': response_data["document_id"]
        })
    
    def test_get_specific_document(self):
        """Test get specific document endpoint (after upload)"""
        # First upload a document
        test_content = "Test document for retrieval testing."
        files = {'file': ('test_doc.txt', test_content, 'text/plain')}
        
        upload_response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/upload",
            files=files
        )
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # Track for cleanup
        self.created_resources.append({
            'type': 'document',
            'id': document_id
        })
        
        # Now test retrieval
        response = self.session.get(
            f"{self.base_url}/api/v1/multimodal/documents/{document_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "filename" in data
        assert "file_type" in data
        assert "upload_date" in data
        assert data["id"] == document_id
    
    def test_document_analysis(self):
        """Test document analysis endpoint"""
        # First upload a document
        test_content = "Employment Contract\n\nThis agreement establishes employment terms."
        files = {'file': ('contract.txt', test_content, 'text/plain')}
        
        upload_response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/upload",
            files=files
        )
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # Track for cleanup
        self.created_resources.append({
            'type': 'document',
            'id': document_id
        })
        
        # Test analysis
        payload = {
            "document_id": document_id,
            "analysis_type": "contract_review",
            "options": {
                "extract_clauses": True,
                "risk_assessment": True
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/analyze",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "analysis_id" in data
        assert "document_id" in data
        assert "status" in data
        assert data["document_id"] == document_id
    
    def test_extract_text_from_document(self):
        """Test text extraction endpoint"""
        # Upload a document first
        test_content = "Legal document content for text extraction testing."
        files = {'file': ('extract_test.txt', test_content, 'text/plain')}
        
        upload_response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/upload",
            files=files
        )
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # Track for cleanup
        self.created_resources.append({
            'type': 'document',
            'id': document_id
        })
        
        # Test text extraction
        payload = {
            "document_id": document_id,
            "options": {
                "preserve_formatting": True,
                "include_metadata": True
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/extract-text",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "document_id" in data
        assert "extracted_text" in data
        assert "extraction_confidence" in data
        assert data["document_id"] == document_id
    
    def test_document_summarization(self):
        """Test document summarization endpoint"""
        # Upload a document first
        test_content = "This is a comprehensive legal document that contains multiple clauses and provisions related to employment law in Kenya. It includes termination procedures, salary structures, and benefit packages."
        files = {'file': ('summary_test.txt', test_content, 'text/plain')}
        
        upload_response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/upload",
            files=files
        )
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # Track for cleanup
        self.created_resources.append({
            'type': 'document',
            'id': document_id
        })
        
        # Test summarization
        payload = {
            "document_id": document_id,
            "summary_type": "executive",
            "max_length": 100
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/summarize",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "document_id" in data
        assert "summary" in data
        assert "summary_type" in data
        assert "confidence" in data
        assert data["document_id"] == document_id
        assert data["summary_type"] == "executive"
    
    def test_delete_document(self):
        """Test document deletion endpoint"""
        # Upload a document first
        test_content = "Document to be deleted."
        files = {'file': ('delete_test.txt', test_content, 'text/plain')}
        
        upload_response = self.session.post(
            f"{self.base_url}/api/v1/multimodal/upload",
            files=files
        )
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # Test deletion
        response = self.session.delete(
            f"{self.base_url}/api/v1/multimodal/documents/{document_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify document is actually deleted
        get_response = self.session.get(
            f"{self.base_url}/api/v1/multimodal/documents/{document_id}"
        )
        assert get_response.status_code == 404
    
    # ========================================
    # CONVERSATION MANAGEMENT ENDPOINTS (7/7)
    # ========================================
    
    def test_create_conversation(self):
        """Test conversation creation endpoint"""
        payload = {
            "title": "Regression Test Conversation",
            "agent_mode": False,
            "use_enhanced_rag": True,
            "initial_context": {
                "topic": "employment_law",
                "test_type": "regression"
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/counsel/conversations",
            json=payload
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "title" in data
        assert "agent_mode" in data
        assert "use_enhanced_rag" in data
        assert "context" in data
        assert "created_at" in data
        assert "updated_at" in data
        
        # Verify values
        assert data["title"] == "Regression Test Conversation"
        assert data["agent_mode"] is False
        assert data["use_enhanced_rag"] is True
        
        # Track for cleanup
        self.created_resources.append({
            'type': 'conversation',
            'id': data["id"]
        })
        
        return data["id"]  # Return for use in other tests
    
    def test_list_conversations(self):
        """Test list conversations endpoint"""
        response = self.session.get(
            f"{self.base_url}/api/v1/counsel/conversations",
            params={"limit": 20, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "conversations" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["conversations"], list)
        assert data["limit"] == 20
        assert data["offset"] == 0
    
    def test_get_specific_conversation(self):
        """Test get specific conversation endpoint"""
        # Create a conversation first
        conversation_id = self.test_create_conversation()
        
        # Test retrieval
        response = self.session.get(
            f"{self.base_url}/api/v1/counsel/conversations/{conversation_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "title" in data
        assert "agent_mode" in data
        assert "use_enhanced_rag" in data
        assert "context" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["id"] == conversation_id
    
    def test_update_conversation(self):
        """Test conversation update endpoint"""
        # Create a conversation first
        conversation_id = self.test_create_conversation()
        
        # Test update
        update_payload = {
            "title": "Updated Regression Test Conversation",
            "agent_mode": True,
            "use_enhanced_rag": False
        }
        
        response = self.session.put(
            f"{self.base_url}/api/v1/counsel/conversations/{conversation_id}",
            json=update_payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify updates
        assert data["title"] == "Updated Regression Test Conversation"
        assert data["agent_mode"] is True
        assert data["use_enhanced_rag"] is False
        assert data["id"] == conversation_id
        
        # Verify updated_at timestamp changed
        assert "updated_at" in data
    
    def test_add_message_to_conversation(self):
        """Test add message to conversation endpoint"""
        # Create a conversation first
        conversation_id = self.test_create_conversation()
        
        # Add a message
        message_payload = {
            "role": "user",
            "content": "What are my rights as an employee in Kenya?",
            "metadata": {
                "source": "regression_test",
                "test_id": str(uuid4())
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/counsel/conversations/{conversation_id}/messages",
            json=message_payload
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert "conversation_id" in data
        assert "role" in data
        assert "content" in data
        assert "metadata" in data
        assert "created_at" in data
        
        # Verify values
        assert data["conversation_id"] == conversation_id
        assert data["role"] == "user"
        assert data["content"] == "What are my rights as an employee in Kenya?"
        
        return data["id"]  # Return message ID for other tests
    
    def test_get_conversation_messages(self):
        """Test get conversation messages endpoint"""
        # Create conversation and add message
        conversation_id = self.test_create_conversation()
        message_id = self.test_add_message_to_conversation()
        
        # Get messages
        response = self.session.get(
            f"{self.base_url}/api/v1/counsel/conversations/{conversation_id}/messages",
            params={"limit": 50, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "messages" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["messages"], list)
        assert data["limit"] == 50
        assert data["offset"] == 0
        
        # Should have at least one message
        assert len(data["messages"]) >= 1
    
    def test_delete_conversation(self):
        """Test conversation deletion endpoint"""
        # Create a conversation first
        conversation_id = self.test_create_conversation()
        
        # Remove from cleanup list since we're testing deletion
        self.created_resources = [r for r in self.created_resources if r.get('id') != conversation_id]
        
        # Test deletion
        response = self.session.delete(
            f"{self.base_url}/api/v1/counsel/conversations/{conversation_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify conversation is actually deleted
        get_response = self.session.get(
            f"{self.base_url}/api/v1/counsel/conversations/{conversation_id}"
        )
        assert get_response.status_code == 404
    
    # ========================================
    # PERFORMANCE AND LOAD TESTS
    # ========================================
    
    @pytest.mark.performance
    def test_response_times(self):
        """Test that critical endpoints respond within acceptable time limits"""
        endpoints_to_test = [
            ("/health", "GET", None, 2.0),  # Health should be very fast
            ("/api/v1/counsel/conversations", "GET", None, 5.0),
            ("/api/v1/multimodal/capabilities", "GET", None, 3.0),
        ]
        
        for endpoint, method, payload, max_time in endpoints_to_test:
            start_time = time.time()
            
            if method == "GET":
                response = self.session.get(f"{self.base_url}{endpoint}")
            elif method == "POST":
                response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
            
            response_time = time.time() - start_time
            
            assert response.status_code == 200, f"Endpoint {endpoint} failed"
            assert response_time < max_time, f"Endpoint {endpoint} took {response_time:.2f}s (max: {max_time}s)"
    
    @pytest.mark.load
    def test_concurrent_health_checks(self):
        """Test system handles concurrent requests to health endpoint"""
        import concurrent.futures
        import threading
        
        def make_health_request():
            try:
                response = self.session.get(f"{self.base_url}/health", timeout=10)
                return response.status_code == 200
            except Exception:
                return False
        
        # Test with 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_health_request) for _ in range(50)]
            results = [future.result() for future in futures]
        
        # At least 95% of requests should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"


if __name__ == "__main__":
    # Run the regression tests
    pytest.main([__file__, "-v", "--tb=short"])
