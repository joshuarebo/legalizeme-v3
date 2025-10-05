# API Documentation Update - Interactive RAG Citations

**Date:** 2025-10-05
**Version:** 2.0.0 → 2.1.0
**Deployment:** Zero downtime rolling update

---

## ✅ FastAPI Documentation - FULLY CONFIGURED

### OpenAPI/Swagger UI
- **Location:** `https://api.legalizeme.co.ke/docs`
- **Status:** ✅ Enabled (line 191 in app/main.py)
- **Configuration:** Enhanced with deep linking, request duration display, try-it-out enabled

### ReDoc Documentation
- **Location:** `https://api.legalizeme.co.ke/redoc`
- **Status:** ✅ Enabled (line 192 in app/main.py)

### OpenAPI JSON Schema
- **Location:** `https://api.legalizeme.co.ke/openapi.json`
- **Status:** ✅ Enabled (line 193 in app/main.py)

---

## 📋 New API Endpoints (2)

### 1. Source Verification Endpoint

**Endpoint:** `GET /api/v1/counsel/sources/{source_id}/verify`
**Tag:** `counsel`
**Response Model:** `SourceVerificationResponse`
**File Location:** [app/api/routes/counsel.py:1076](app/api/routes/counsel.py#L1076)

**Purpose:** Verify if a cited source is still accessible and fresh

**Request:**
```bash
GET /api/v1/counsel/sources/550e8400-e29b-41d4-a716-446655440000/verify
```

**Response:**
```json
{
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Employment Act 2007",
  "url": "https://kenyalaw.org/kl/fileadmin/pdfdownloads/Acts/EmploymentAct_No11of2007.pdf",
  "is_accessible": true,
  "last_verified": "2025-10-05T10:30:00Z",
  "crawl_status": "active",
  "freshness_score": 0.95,
  "http_status": 200,
  "verification_time_ms": 234.5
}
```

**Schema (Pydantic):** Lines 152-161 in [app/api/routes/counsel.py](app/api/routes/counsel.py#L152)
```python
class SourceVerificationResponse(BaseModel):
    source_id: str
    title: str
    url: str
    is_accessible: bool
    last_verified: str
    crawl_status: str
    freshness_score: float
    http_status: Optional[int] = None
    verification_time_ms: float
```

**Documentation:** ✅ Complete docstring (lines 1078-1086)

---

### 2. Full Source Content Endpoint

**Endpoint:** `GET /api/v1/counsel/sources/{source_id}/full`
**Tag:** `counsel`
**Response Model:** `FullSourceResponse`
**File Location:** [app/api/routes/counsel.py:1153](app/api/routes/counsel.py#L1153)

**Purpose:** Retrieve full source content for modal display in frontend

**Request:**
```bash
GET /api/v1/counsel/sources/550e8400-e29b-41d4-a716-446655440000/full
```

**Response:**
```json
{
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Employment Act 2007",
  "url": "https://kenyalaw.org/kl/fileadmin/pdfdownloads/Acts/EmploymentAct_No11of2007.pdf",
  "full_content": "EMPLOYMENT ACT NO. 11 OF 2007...",
  "summary": "The Employment Act 2007 governs employment relationships in Kenya...",
  "document_type": "act",
  "legal_area": "employment_law",
  "metadata": {
    "act_chapter": "Chapter 226",
    "sections": 85,
    "last_amended": "2022"
  },
  "crawled_at": "2025-09-15T08:00:00Z",
  "last_verified": "2025-10-05T10:30:00Z",
  "document_date": "2007-12-31",
  "court_name": null,
  "case_number": null,
  "act_chapter": "226"
}
```

**Schema (Pydantic):** Lines 163-178 in [app/api/routes/counsel.py](app/api/routes/counsel.py#L163)
```python
class FullSourceResponse(BaseModel):
    source_id: str
    title: str
    url: str
    full_content: str
    summary: Optional[str] = None
    document_type: str
    legal_area: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    crawled_at: Optional[str] = None
    last_verified: Optional[str] = None
    document_date: Optional[str] = None
    court_name: Optional[str] = None
    case_number: Optional[str] = None
    act_chapter: Optional[str] = None
```

**Documentation:** ✅ Complete docstring (lines 1155-1163)

---

## 🔄 Enhanced Existing Endpoints (3)

### 1. Enhanced RAG Query (Existing - Now Enhanced)

**Endpoint:** `POST /api/v1/counsel/query`
**Tag:** `counsel`
**Status:** ✅ UNCHANGED - Enhanced internally only

**What Changed:**
- When `use_enhanced_rag=true` AND `agent_mode=false`, response now includes:
  - `sources` array (structured sources with metadata)
  - `citation_map` (mapping citation numbers to source names)
  - Answer text with inline citations `[1][2][3]`

**Request:**
```json
{
  "query": "What is the notice period for employment termination?",
  "use_enhanced_rag": true,
  "agent_mode": false
}
```

**Response (Enhanced):**
```json
{
  "query_id": "uuid-here",
  "answer": "In Kenya, the notice period for employment termination is governed by the Employment Act 2007 [1]. For permanent employees, the minimum notice period is 28 days [1][2]...",
  "sources": [
    {
      "source_id": "550e8400-e29b-41d4-a716-446655440000",
      "citation_id": 1,
      "title": "Employment Act 2007",
      "url": "https://kenyalaw.org/...",
      "snippet": "Section 35 states that notice period...",
      "document_type": "act",
      "legal_area": "employment_law",
      "relevance_score": 0.92,
      "highlighted_excerpt": "Section 35 states that <mark>notice period</mark>...",
      "metadata": {
        "source": "kenya_law",
        "crawled_at": "2025-09-15T08:00:00Z",
        "freshness_score": 0.95,
        "citation_text": "Employment Act 2007, Section 35",
        "crawl_status": "active"
      }
    }
  ],
  "citation_map": {
    "1": "Employment Act 2007, Section 35",
    "2": "Code of Conduct Regulations 2008"
  },
  "confidence": 0.92,
  "model_used": "claude-sonnet-4",
  "processing_time": 2.34,
  "timestamp": "2025-10-05T10:30:00Z"
}
```

**Backward Compatibility:** ✅ Yes
- Existing clients will receive all old fields
- New fields (`sources`, `citation_map`) are additive
- Frontend can check if fields exist before rendering

---

### 2. Agent Mode Query (Enhanced)

**Endpoint:** `POST /api/v1/counsel/query` with `agent_mode=true`
**Tag:** `counsel`
**Status:** ✅ ENHANCED - New fields added

**What Changed:**
- Now uses enhanced RAG service internally
- Response includes structured `sources` array
- Response includes `citation_map`
- Response includes `reasoning_chain`
- Answer text has inline citations

**Request:**
```json
{
  "query": "What are my rights if my employer terminates me without notice?",
  "agent_mode": true,
  "use_enhanced_rag": true
}
```

**Response (Enhanced):**
```json
{
  "success": true,
  "response_text": "CHAIN-OF-THOUGHT ANALYSIS:\n\n1. LEGAL ISSUE IDENTIFICATION:\nThe core issue is employment termination without notice in Kenya [1]...\n\n2. LEGAL FRAMEWORK ANALYSIS:\nThe Employment Act 2007 Section 35 requires notice [1][2]...",
  "sources": [...],  // Same structure as Enhanced RAG
  "citation_map": {"1": "Employment Act 2007", "2": "..."},
  "reasoning_chain": [
    "Identified termination without notice issue",
    "Analyzed Employment Act 2007 requirements",
    "Determined remedies available"
  ],
  "model_used": "claude-sonnet-4",
  "confidence": 0.88,
  "retrieval_strategy": "agent_reasoning_with_rag",
  "relevant_documents": [...],
  "retrieved_documents": 5,
  "context_tokens": 2500,
  "total_tokens": 3200,
  "cost_estimate": {...},
  "latency_ms": 2340,
  "metadata": {...}
}
```

**File Location:** [app/api/routes/counsel.py:416-499](app/api/routes/counsel.py#L416)

**Backward Compatibility:** ✅ Yes
- All existing fields preserved
- New fields are additive
- Graceful fallback to direct query if enhanced RAG fails (line 499)

---

### 3. Research Mode (Enhanced)

**Endpoint:** `POST /api/v1/counsel/research`
**Tag:** `counsel`
**Status:** ✅ ENHANCED - New fields in relevant_documents

**What Changed:**
- Now uses enhanced RAG service internally
- `relevant_documents` array now includes citation metadata
- `summary` field now includes inline citations

**Request:**
```json
{
  "query": "Research employment termination laws in Kenya"
}
```

**Response (Enhanced):**
```json
{
  "query": "Research employment termination laws in Kenya",
  "summary": "Employment termination in Kenya is governed by the Employment Act 2007 [1]. The Act requires employers to provide written notice [1][2]...",
  "relevant_documents": [
    {
      "source_id": "550e8400-e29b-41d4-a716-446655440000",
      "citation_id": 1,
      "title": "Employment Act 2007",
      "url": "https://kenyalaw.org/...",
      "snippet": "Section 35 states...",
      "document_type": "act",
      "relevance_score": 0.92,
      "citation_text": "Employment Act 2007, Section 35",
      "freshness_score": 0.95
    }
  ],
  "total_results": 5,
  "timestamp": "2025-10-05T10:30:00Z"
}
```

**File Location:** [app/api/routes/counsel.py:574-629](app/api/routes/counsel.py#L574)

**Backward Compatibility:** ✅ Yes
- All existing fields preserved
- New fields in `relevant_documents` are additive
- Graceful fallback to simple implementation if enhanced RAG fails (lines 623-629)

---

## 🚫 Unchanged Endpoints (No Breaking Changes)

The following endpoints remain **completely unchanged**:

1. ✅ `POST /api/v1/counsel/query` (direct mode - lines 265-360)
2. ✅ `GET /api/v1/counsel/conversation-history`
3. ✅ `GET /api/v1/counsel/suggestions`
4. ✅ `GET /api/v1/counsel/legal-documents`
5. ✅ `POST /api/v1/counsel/feedback`
6. ✅ `POST /api/v1/counsel/generate-document`
7. ✅ All CounselDocs endpoints (`/api/v1/counseldocs/*`)
8. ✅ All Simple Agent endpoints (`/api/v1/agents/*`)
9. ✅ All Multimodal endpoints (`/api/v1/multimodal/*`)
10. ✅ All Health endpoints (`/health/*`)

**Total Endpoints:** 2 new + 3 enhanced + 40+ unchanged = **100% backward compatible**

---

## 📊 OpenAPI Schema Changes

### Automatic OpenAPI Updates

FastAPI **automatically generates** OpenAPI schema from:
- ✅ Pydantic models (`SourceVerificationResponse`, `FullSourceResponse`)
- ✅ Route decorators (`@router.get`, `@router.post`)
- ✅ Docstrings (multi-line descriptions)
- ✅ Type hints (`str`, `bool`, `float`, `Optional[int]`)
- ✅ Field validators (`Field(...)`)

**No manual OpenAPI configuration needed!**

### How to Verify After Deployment

1. **Visit Swagger UI:**
   ```
   https://api.legalizeme.co.ke/docs
   ```
   - Look for "counsel" tag section
   - Should see 2 new endpoints:
     - `GET /api/v1/counsel/sources/{source_id}/verify`
     - `GET /api/v1/counsel/sources/{source_id}/full`

2. **Check OpenAPI JSON:**
   ```bash
   curl https://api.legalizeme.co.ke/openapi.json | jq '.paths | keys | .[] | select(contains("sources"))'
   ```

3. **Test Try-It-Out Feature:**
   - Click on new endpoint in Swagger UI
   - Click "Try it out"
   - Enter a source_id UUID
   - Click "Execute"
   - Should see example response

---

## 🎯 Zero Downtime Deployment Strategy

### Why No Downtime

1. **Database Changes are Additive:**
   - Migration adds 10 new columns (all `nullable=True`)
   - Old code can run with new columns (ignores them)
   - New code can run with old columns (graceful fallback)

2. **API Changes are Backward Compatible:**
   - No existing endpoints removed
   - No existing response fields removed
   - Only new fields added (clients ignore unknown fields)

3. **ECS Rolling Deployment:**
   - ECS keeps old tasks running while new tasks start
   - ALB health checks ensure new tasks are healthy
   - Only switches traffic when new tasks pass health checks
   - Old tasks gracefully shutdown after traffic drains

### Deployment Flow (Zero Downtime)

```
Step 1: Database Migration
├─ Add new columns to documents table
├─ Existing API keeps running (ignores new columns)
└─ Takes: 30 seconds

Step 2: ECS Task Update
├─ Old tasks: Running (2/2 healthy)
├─ New tasks: Starting (2 new tasks)
├─ New tasks: Running (2/2 healthy)
├─ ALB: Routes traffic to new tasks
├─ Old tasks: Draining connections
└─ Old tasks: Terminated
    Takes: 5-10 minutes

Total Downtime: 0 seconds ✅
```

---

## 📝 API Changes Summary for Frontend Team

### What Frontend Needs to Know

**1. Enhanced RAG Mode (`use_enhanced_rag=true`):**
```typescript
// NEW: Check for sources and citation_map
if (response.sources && response.citation_map) {
  // Render interactive citations
  renderCitations(response.answer, response.citation_map);
  renderSourceList(response.sources);
} else {
  // Render old way (fallback)
  renderPlainText(response.answer);
}
```

**2. Agent Mode (`agent_mode=true`):**
```typescript
// NEW: Check for reasoning_chain and sources
if (response.reasoning_chain && response.sources) {
  // Render reasoning steps with citations
  renderReasoningChain(response.reasoning_chain);
  renderCitations(response.response_text, response.citation_map);
  renderSourceList(response.sources);
}
```

**3. Research Mode:**
```typescript
// NEW: relevant_documents now includes citation_text and freshness_score
response.relevant_documents.forEach(doc => {
  renderDocument({
    title: doc.title,
    snippet: doc.snippet,
    citationText: doc.citation_text,      // NEW
    freshnessScore: doc.freshness_score,  // NEW
    url: doc.url
  });
});
```

**4. New Endpoints:**
```typescript
// Verify source is still accessible
const verification = await fetch(`/api/v1/counsel/sources/${sourceId}/verify`);
// verification.is_accessible → show badge color (green/red)
// verification.freshness_score → show freshness indicator

// Get full source content for modal
const fullSource = await fetch(`/api/v1/counsel/sources/${sourceId}/full`);
// fullSource.full_content → display in modal
```

### Frontend Changes Required: MINIMAL ✅

- **No breaking changes** to existing components
- **No changes required** for direct query mode
- **Optional enhancements** for Enhanced RAG/Agent/Research modes
- **New components** for citation display (all optional)

---

## ✅ Deployment Checklist

### Pre-Deployment
- [x] All Pydantic models have proper docstrings
- [x] All endpoints have `response_model` specified
- [x] All endpoints have descriptive docstrings
- [x] OpenAPI tags configured (`tags=["counsel"]`)
- [x] FastAPI docs enabled (`docs_url="/docs"`)
- [x] Swagger UI parameters configured for best UX

### Post-Deployment Verification
- [ ] Visit `https://api.legalizeme.co.ke/docs` - Swagger UI loads
- [ ] Verify 2 new endpoints appear under "counsel" tag
- [ ] Click on `/sources/{source_id}/verify` - see schema
- [ ] Click on `/sources/{source_id}/full` - see schema
- [ ] Test "Try it out" feature with sample UUID
- [ ] Check OpenAPI JSON schema includes new endpoints
- [ ] Verify existing endpoints still work (no 404s, no 500s)
- [ ] Test Enhanced RAG returns `sources` array
- [ ] Test Agent Mode returns `citation_map`
- [ ] Test Research Mode returns enriched `relevant_documents`

---

## 📞 Support & Resources

### Documentation Files
- **Full Deployment Guide:** [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md)
- **Frontend Integration:** [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md)
- **Quick Start:** [FRONTEND_QUICK_START.md](FRONTEND_QUICK_START.md)
- **Pre-Deployment Checklist:** [PRE_DEPLOYMENT_CHECKLIST.md](PRE_DEPLOYMENT_CHECKLIST.md)

### API Testing
```bash
# Health check
curl https://api.legalizeme.co.ke/health

# OpenAPI schema
curl https://api.legalizeme.co.ke/openapi.json

# Swagger UI
open https://api.legalizeme.co.ke/docs

# ReDoc UI
open https://api.legalizeme.co.ke/redoc
```

---

## 🎉 Summary

**New Endpoints:** 2 (source verification + full source)
**Enhanced Endpoints:** 3 (enhanced RAG, agent mode, research mode)
**Breaking Changes:** 0
**Downtime:** 0 seconds
**Frontend Changes Required:** Optional enhancements only
**OpenAPI Documentation:** Fully automated, no manual updates needed
**Deployment Risk:** Very Low ✅

**All systems ready for deployment! 🚀**

---

**Document Version:** 1.0
**Last Updated:** 2025-10-05
**Author:** Claude Code (Anthropic)
