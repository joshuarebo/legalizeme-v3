# Backend Final Update: Add source_id UUID

**Priority:** High
**Time:** 5 minutes
**Required for:** Frontend modal integration

---

## Issue

Frontend needs a UUID to call `/sources/{source_id}/verify` and `/sources/{source_id}/full` endpoints, but currently we only return `citation_id` (integer 1, 2, 3).

---

## Solution

Add `source_id` UUID field to structured sources response.

---

## Code Changes

### File: `app/services/enhanced_rag_service.py`

**Line ~450-480** (in `_build_structured_sources` method):

**BEFORE:**
```python
# Build structured source
source = {
    'citation_id': idx,
    'title': metadata.get('title', f'Source {idx}'),
    'url': metadata.get('url', ''),
    'snippet': snippet,
    'document_type': metadata.get('document_type', 'unknown'),
    'legal_area': metadata.get('legal_area') or metadata.get('category'),
    'relevance_score': round(similarity, 3),
    'highlighted_excerpt': highlighted,
    'metadata': {
        'source': metadata.get('source', 'kenya_law'),
        'crawled_at': crawled_at,
        'last_verified': metadata.get('last_verified_at'),
        'freshness_score': freshness,
        'document_date': metadata.get('document_date'),
        'court_name': metadata.get('court_name'),
        'case_number': metadata.get('case_number'),
        'act_chapter': metadata.get('act_chapter'),
        'citation_text': citation_map.get(idx, ''),
        'crawl_status': metadata.get('crawl_status', 'active')
    }
}
```

**AFTER:**
```python
# Build structured source with SourceMetadata-compatible format
source = {
    'source_id': str(metadata.get('uuid', '')),  # ADD THIS LINE - Document UUID
    'citation_id': idx,
    'title': metadata.get('title', f'Source {idx}'),
    'url': metadata.get('url', ''),
    'snippet': snippet,
    'document_type': metadata.get('document_type', 'unknown'),
    'legal_area': metadata.get('legal_area') or metadata.get('category'),
    'relevance_score': round(similarity, 3),
    'highlighted_excerpt': highlighted,
    'metadata': {
        'source': metadata.get('source', 'kenya_law'),
        'crawled_at': crawled_at,
        'last_verified': metadata.get('last_verified_at'),
        'freshness_score': freshness,
        'document_date': metadata.get('document_date'),
        'court_name': metadata.get('court_name'),
        'case_number': metadata.get('case_number'),
        'act_chapter': metadata.get('act_chapter'),
        'citation_text': citation_map.get(idx, ''),
        'crawl_status': metadata.get('crawl_status', 'active')
    }
}
```

---

## Update Pydantic Schema

### File: `app/schemas/api_responses.py`

**Line ~92-103:**

**BEFORE:**
```python
class StructuredSource(BaseModel):
    """Interactive source with rich metadata for frontend display"""
    citation_id: int
    title: str
    url: str
    snippet: str
    document_type: str
    legal_area: Optional[str] = None
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    highlighted_excerpt: Optional[str] = None
    metadata: SourceMetadata
```

**AFTER:**
```python
class StructuredSource(BaseModel):
    """Interactive source with rich metadata for frontend display"""
    source_id: str  # ADD THIS LINE - Document UUID for /sources/{id} endpoints
    citation_id: int
    title: str
    url: str
    snippet: str
    document_type: str
    legal_area: Optional[str] = None
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    highlighted_excerpt: Optional[str] = None
    metadata: SourceMetadata
```

---

## Verification

After changes, the response will include `source_id`:

```json
{
  "sources": [
    {
      "source_id": "8b637e45-c4ff-4c85-8617-d522c46ecea6",  // NEW FIELD
      "citation_id": 1,
      "title": "Employment Act 2007, Section 35",
      "url": "http://kenyalaw.org/...",
      "snippet": "Section 35 of the Employment Act...",
      "metadata": {...}
    }
  ]
}
```

Frontend can now call:
```typescript
await fetch(`/api/v1/counsel/sources/${source.source_id}/verify`);
await fetch(`/api/v1/counsel/sources/${source.source_id}/full`);
```

---

## Testing

```bash
# Run existing test
python scripts/test_enhanced_rag_step_1_2.py

# Verify source_id appears in output
# Should see: "source_id": "..." in structured sources
```

---

## Priority: HIGH

This is required for frontend to complete Step 2.1 (Interactive Citation Component).

Without this change, frontend cannot:
- Open source modal (needs UUID)
- Verify sources (needs UUID)
- Fetch full content (needs UUID)

---

**Estimated time:** 5 minutes
**Breaking change:** No (additive only)
**Deploy:** With next backend release
