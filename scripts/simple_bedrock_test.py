#!/usr/bin/env python3
"""
Simple test to check what Mistral is actually returning
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.services.llm_manager import llm_manager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mistral_response():
    """Test what Mistral actually returns"""
    
    test_queries = [
        "What are the constitutional rights in Kenya?",
        "Explain company registration in Kenya",
        "What is guardianship law in Kenya?"
    ]
    
    for query in test_queries:
        try:
            print(f"\n🔍 Testing query: {query}")
            print("-" * 50)
            
            result = await llm_manager.invoke_model(query, model_preference="mistral-large")
            
            print(f"✅ Success!")
            print(f"Model used: {result['model_used']}")
            print(f"Model ID: {result['model_id']}")
            print(f"Latency: {result['latency_ms']:.0f}ms")
            print(f"Response length: {len(result['response_text'])} chars")
            print(f"Response preview: {result['response_text'][:200]}...")
            
            # Check for keywords
            response_lower = result['response_text'].lower()
            keywords = ["kenya", "law", "legal", "constitution", "rights", "company", "registration", "guardianship"]
            found_keywords = [kw for kw in keywords if kw in response_lower]
            print(f"Keywords found: {found_keywords}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 50)

async def test_model_status():
    """Test model status"""
    print("\n📊 Model Status:")
    print("=" * 50)
    
    status = llm_manager.get_model_status()
    
    for model_name, model_info in status['models'].items():
        print(f"{model_name}:")
        print(f"  Status: {model_info['status']}")
        print(f"  Model ID: {model_info['model_id']}")
        print(f"  Success Count: {model_info['success_count']}")
        print(f"  Error Count: {model_info['error_count']}")
        if model_info['last_error']:
            print(f"  Last Error: {model_info['last_error']}")
        print()

async def main():
    """Main test function"""
    print("🚀 Simple Bedrock Test")
    print("=" * 50)
    
    await test_model_status()
    await test_mistral_response()

if __name__ == "__main__":
    asyncio.run(main())
