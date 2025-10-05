"""
Test OpenSearch Connection
Verify that we can connect to OpenSearch and perform basic operations
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.aws_vector_service import aws_vector_service

async def test_connection():
    """Test OpenSearch connection"""
    print("=" * 60)
    print("Testing OpenSearch Connection")
    print("=" * 60)

    try:
        # Initialize service
        print("\n1. Initializing AWS Vector Service...")
        await aws_vector_service.initialize()
        print("   ✓ Service initialized")

        # Get stats
        print("\n2. Getting collection stats...")
        stats = await aws_vector_service.get_collection_stats()
        print(f"   ✓ Stats retrieved:")
        for key, value in stats.items():
            print(f"     - {key}: {value}")

        # Check if using OpenSearch
        if stats.get('using_opensearch'):
            print("\n   ✓ Successfully connected to OpenSearch!")
        else:
            print("\n   ⚠ Fallback to in-memory storage (OpenSearch connection failed)")

        print("\n" + "=" * 60)
        print("Connection test completed!")
        print("=" * 60)

        return stats.get('using_opensearch', False)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
