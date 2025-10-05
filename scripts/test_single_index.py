"""
Test Single Document Indexing
Index a test document to OpenSearch and verify it can be searched
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.document_indexing_service import document_indexing_service

async def test_single_indexing():
    """Test indexing a single document"""
    print("=" * 60)
    print("Testing Single Document Indexing")
    print("=" * 60)

    try:
        # Initialize service
        print("\n1. Initializing Document Indexing Service...")
        await document_indexing_service.initialize()
        print("   ✓ Service initialized")

        # Create test document
        test_doc = {
            'title': 'Employment Act 2007 - Section 35 (TEST)',
            'content': '''
            Employment Act 2007, Section 35 - Notice of Termination

            An employer shall, before terminating the employment of an employee,
            give the employee notice in writing of not less than one month or pay
            to the employee one month's wages in lieu of notice.

            This section establishes the minimum notice period required for employment
            termination in Kenya. The notice must be provided in writing, and employers
            have the option to pay wages instead of requiring the employee to work
            during the notice period.
            ''',
            'url': 'https://test.example.com/employment-act-test',
            'document_type': 'legislation',
            'metadata': {
                'legal_area': 'Employment Law',
                'court': None,
                'publication_date': '2007-01-01',
                'summary': 'Employment Act 2007 establishes notice requirements for employment termination'
            }
        }

        # Index test document
        print("\n2. Indexing test document...")
        success = await document_indexing_service.index_crawled_document(test_doc)

        if success:
            print("   ✓ Document indexed successfully")
        else:
            print("   ✗ Failed to index document")
            return False

        # Get stats
        print("\n3. Checking index stats...")
        stats = await document_indexing_service.get_stats()
        print(f"   ✓ Total documents: {stats.get('total_documents', 0)}")
        print(f"   ✓ Index: {stats.get('index_name', 'unknown')}")
        print(f"   ✓ Service: {stats.get('service_type', 'unknown')}")

        # Test search
        print("\n4. Testing search...")
        from app.services.aws_vector_service import aws_vector_service

        results = await aws_vector_service.search_similar("employment termination notice kenya", limit=5, threshold=0.3)

        print(f"   ✓ Found {len(results)} results")

        if results:
            print("\n   Top result:")
            top_result = results[0]
            print(f"     - Title: {top_result.get('document', {}).get('metadata', {}).get('title', 'N/A')[:80]}")
            print(f"     - Similarity: {top_result.get('similarity', 0):.3f}")
            print(f"     - Score: {top_result.get('score', 0):.3f}")

        print("\n" + "=" * 60)
        print("Single document indexing test completed!")
        print("=" * 60)

        return success

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_single_indexing())
    sys.exit(0 if success else 1)
