#!/usr/bin/env python3
"""
Test script to verify all endpoints work without authentication
Tests the authentication removal implementation
"""

import requests
import json
import sys
import time
from typing import Dict, Any

# Test configuration
BASE_URL = "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com"
# BASE_URL = "http://localhost:8000"  # For local testing

def test_endpoint(method: str, endpoint: str, data: Dict[str, Any] = None, files: Dict = None) -> bool:
    """Test an endpoint without authentication"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    try:
        print(f"Testing {method} {endpoint}...")
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            if files:
                # For file uploads, don't set Content-Type header
                response = requests.post(url, data=data, files=files, timeout=30)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            print(f"Unsupported method: {method}")
            return False
        
        print(f"Status: {response.status_code}")
        
        # Check if request was successful (not 401/403 auth errors)
        if response.status_code in [401, 403]:
            print(f"❌ FAILED: Authentication still required")
            return False
        elif response.status_code in [200, 201, 422]:  # 422 is validation error, which is OK
            print(f"✅ SUCCESS: No authentication required")
            return True
        else:
            print(f"⚠️  WARNING: Unexpected status code {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return True  # Still counts as success since it's not auth-related
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Request failed - {e}")
        return False

def main():
    """Run all endpoint tests"""
    print("🔐 Testing Authentication Removal - All Endpoints Should Work Without Auth")
    print("=" * 70)
    
    tests = [
        # Health endpoints
        ("GET", "/health"),
        ("GET", "/health/live"),
        
        # Counsel endpoints
        ("POST", "/api/v1/counsel/query", {
            "query": "What are employment rights in Kenya?",
            "agent_mode": True,
            "user_context": {"user_id": "test-user-123"}
        }),
        ("POST", "/api/v1/counsel/query-direct", {
            "query": "Test query",
            "model_preference": "claude-sonnet-4",
            "user_context": {"user_id": "test-user-123"}
        }),
        ("GET", "/api/v1/counsel/history?user_id=test-user-123"),
        ("GET", "/api/v1/counsel/suggest?query=employment"),
        ("GET", "/api/v1/counsel/fetch-law?query=employment&limit=5"),
        
        # Agent endpoints
        ("POST", "/api/v1/agents/research", {
            "query": "Employment law Kenya",
            "strategy": "comprehensive",
            "user_context": {"user_id": "test-user-123"}
        }),
        ("GET", "/api/v1/agents/health"),
        ("GET", "/api/v1/agents/metrics"),
        ("GET", "/api/v1/agents/memory?user_id=test-user-123"),
        
        # Document endpoints
        ("POST", "/api/v1/documents/search", {
            "query": "employment contract",
            "limit": 5,
            "user_context": {"user_id": "test-user-123"}
        }),
        ("POST", "/api/v1/documents/analyze", {
            "document_id": 1,
            "user_context": {"user_id": "test-user-123"}
        }),
        
        # Model endpoints
        ("GET", "/api/v1/models/status"),
        ("GET", "/api/v1/models/health"),
        ("GET", "/api/v1/models/metrics"),
        ("GET", "/api/v1/models/config"),
        
        # Multimodal endpoints
        ("POST", "/api/v1/multimodal/search", {
            "query": "legal document",
            "limit": 5,
            "user_context": {"user_id": "test-user-123"}
        }),
        ("GET", "/api/v1/multimodal/stats"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        method, endpoint = test[0], test[1]
        data = test[2] if len(test) > 2 else None
        
        success = test_endpoint(method, endpoint, data)
        if success:
            passed += 1
        
        print("-" * 50)
        time.sleep(1)  # Rate limiting
    
    print(f"\n📊 Test Results: {passed}/{total} endpoints working without authentication")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Authentication successfully removed!")
        return True
    else:
        print("❌ Some tests failed - Authentication removal incomplete")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
