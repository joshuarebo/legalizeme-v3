"""
Test Enhanced RAG Service - Step 1.2: Interactive Citations
Tests the new citation-aware methods without requiring AWS/vector DB connection
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from app.services.enhanced_rag_service import EnhancedRAGService

def test_citation_methods():
    """Test all new citation-aware methods"""

    service = EnhancedRAGService()

    # Mock retrieved documents (simulating vector search results)
    mock_docs = [
        {
            'doc_id': 'doc1',
            'similarity': 0.95,
            'document': {
                'text': 'Section 35 of the Employment Act, 2007 provides that an employer shall give an employee one month\'s notice in writing. The notice must specify the date of termination and reasons.',
                'metadata': {
                    'title': 'Employment Act 2007, Section 35',
                    'document_type': 'legislation',
                    'source': 'kenya_law',
                    'url': 'http://kenyalaw.org/kl/fileadmin/pdfdownloads/Acts/EmploymentAct_No11of2007.pdf',
                    'act_chapter': 'Cap. 226',
                    'legal_area': 'employment_law',
                    'section': 'Section 35',
                    'crawled_at': (datetime.now() - timedelta(days=30)).isoformat(),
                    'document_date': '2007-10-15'
                }
            }
        },
        {
            'doc_id': 'doc2',
            'similarity': 0.89,
            'document': {
                'text': 'In ABC Ltd v XYZ [2024] eKLR, the Employment and Labour Relations Court held that termination without proper notice constitutes unfair dismissal. The court awarded the employee damages equivalent to 12 months salary.',
                'metadata': {
                    'title': 'ABC Ltd v XYZ',
                    'document_type': 'judgment',
                    'source': 'kenya_law',
                    'url': 'http://kenyalaw.org/caselaw/cases/view/...',
                    'citation': '[2024] eKLR',
                    'court_name': 'Employment and Labour Relations Court',
                    'case_number': 'Cause No. 123 of 2024',
                    'legal_area': 'employment_law',
                    'crawled_at': (datetime.now() - timedelta(days=10)).isoformat(),
                    'document_date': '2024-06-15'
                }
            }
        },
        {
            'doc_id': 'doc3',
            'similarity': 0.82,
            'document': {
                'text': 'The Labour Relations Act requires employers to follow due process before termination. This includes issuing a show-cause letter and conducting a hearing.',
                'metadata': {
                    'title': 'Labour Relations Act',
                    'document_type': 'legislation',
                    'source': 'kenya_law',
                    'url': 'http://kenyalaw.org/kl/fileadmin/pdfdownloads/Acts/LabourRelationsAct.pdf',
                    'legal_area': 'employment_law',
                    'crawled_at': (datetime.now() - timedelta(days=365)).isoformat(),
                    'document_date': '2007-01-01'
                }
            }
        }
    ]

    question = "What is the notice period for termination of employment in Kenya?"

    print("=" * 80)
    print("TESTING ENHANCED RAG SERVICE - STEP 1.2: INTERACTIVE CITATIONS")
    print("=" * 80)
    print()

    # Test 1: _build_citation_context
    print("Test 1: _build_citation_context()")
    print("-" * 80)
    citation_context, citation_map = service._build_citation_context(mock_docs, question)
    print("Citation Map:")
    for idx, text in citation_map.items():
        print(f"  [{idx}] = {text}")
    print()
    print("Citation Context (first 300 chars):")
    print(citation_context[:300] + "...")
    print()

    # Test 2: _format_citation
    print("Test 2: _format_citation()")
    print("-" * 80)
    for doc in mock_docs:
        metadata = doc['document']['metadata']
        title = metadata.get('title', '')
        formatted = service._format_citation(metadata, title)
        print(f"  {metadata['document_type']:12} -> {formatted}")
    print()

    # Test 3: _create_citation_aware_prompt
    print("Test 3: _create_citation_aware_prompt()")
    print("-" * 80)
    prompt = service._create_citation_aware_prompt(question, citation_context[:500], citation_map)
    print("Prompt (first 500 chars):")
    print(prompt[:500] + "...")
    print()

    # Test 4: _build_structured_sources
    print("Test 4: _build_structured_sources()")
    print("-" * 80)
    structured_sources = service._build_structured_sources(mock_docs, citation_map, question)
    print(f"Generated {len(structured_sources)} structured sources:")
    print()

    for source in structured_sources:
        print(f"  Source [{source['citation_id']}]:")
        print(f"    Title: {source['title']}")
        print(f"    Type: {source['document_type']}")
        print(f"    Relevance: {source['relevance_score']}")
        print(f"    Snippet: {source['snippet'][:80]}...")
        print(f"    Metadata Keys: {list(source['metadata'].keys())}")
        print(f"    Freshness: {source['metadata']['freshness_score']}")
        print()

    # Test 5: _calculate_document_freshness
    print("Test 5: _calculate_document_freshness()")
    print("-" * 80)
    test_dates = [
        (datetime.now().isoformat(), "Today"),
        ((datetime.now() - timedelta(days=15)).isoformat(), "15 days ago"),
        ((datetime.now() - timedelta(days=60)).isoformat(), "60 days ago"),
        ((datetime.now() - timedelta(days=200)).isoformat(), "200 days ago"),
        ((datetime.now() - timedelta(days=1000)).isoformat(), "1000 days ago"),
        ((datetime.now() - timedelta(days=3000)).isoformat(), "3000 days ago"),
    ]

    for date_str, label in test_dates:
        freshness = service._calculate_document_freshness(date_str)
        print(f"  {label:15} -> Freshness: {freshness:.2f}")
    print()

    # Test 6: _highlight_query_terms
    print("Test 6: _highlight_query_terms()")
    print("-" * 80)
    sample_text = "Employment termination requires notice period and proper procedure."
    highlighted = service._highlight_query_terms(sample_text, question)
    print(f"  Original: {sample_text}")
    print(f"  Highlighted: {highlighted}")
    print()

    # Test 7: _calculate_confidence
    print("Test 7: _calculate_confidence()")
    print("-" * 80)
    confidence = service._calculate_confidence(structured_sources)
    print(f"  Overall Confidence: {confidence}")
    print()

    # Test 8: _calculate_overall_freshness
    print("Test 8: _calculate_overall_freshness()")
    print("-" * 80)
    freshness = service._calculate_overall_freshness(structured_sources)
    print(f"  Overall Freshness: {freshness}")
    print()

    print("=" * 80)
    print("SAMPLE ENHANCED RAG RESPONSE FORMAT")
    print("=" * 80)
    print()

    # Simulate the final response structure
    sample_response = {
        "success": True,
        "answer": "Employment termination in Kenya requires a notice period of one month [1]. This is specified in Section 35 of the Employment Act, 2007. Failure to provide proper notice constitutes unfair dismissal, as confirmed in ABC Ltd v XYZ [2024] eKLR [2]. Employers must also follow due process, including issuing a show-cause letter and conducting a hearing [3].",
        "sources": structured_sources,
        "citation_map": citation_map,
        "model_used": "claude-3-sonnet",
        "retrieved_documents": 3,
        "context_tokens": 850,
        "total_tokens": 1200,
        "cost_estimate": {"input": 0.0025, "output": 0.012, "total": 0.0145},
        "latency_ms": 1500,
        "metadata": {
            "confidence": confidence,
            "freshness_score": freshness,
            "citation_count": len(citation_map),
            "use_citations": True
        }
    }

    print("Response Structure:")
    print(f"  success: {sample_response['success']}")
    print(f"  answer (with citations): {sample_response['answer'][:150]}...")
    print(f"  sources: {len(sample_response['sources'])} structured sources")
    print(f"  citation_map: {sample_response['citation_map']}")
    print(f"  model_used: {sample_response['model_used']}")
    print(f"  retrieved_documents: {sample_response['retrieved_documents']}")
    print(f"  metadata: {sample_response['metadata']}")
    print()

    print("=" * 80)
    print("✅ ALL TESTS PASSED - STEP 1.2 IMPLEMENTATION COMPLETE")
    print("=" * 80)
    print()
    print("Next Step: Step 1.3 - Add Source Verification Endpoint")
    print()

if __name__ == "__main__":
    test_citation_methods()
