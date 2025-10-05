# Deployment & AI Modes Guide

**Date:** 2025-10-04
**Status:** Phase 1 Backend Complete

---

## 🎯 Which AI Modes Get Interactive Citations?

### Current AI Modes in Counsel AI

Based on your architecture, you have **4 AI Intelligence Modes**:

#### 1. ✅ **Enhanced RAG Mode** - GETS INTERACTIVE CITATIONS
**Endpoint:** `POST /api/v1/counsel/query`
**Request:**
```json
{
  "query": "What is the notice period for employment termination?",
  "use_enhanced_rag": true,  // THIS ENABLES IT
  "agent_mode": false
}
```

**Response:**
```json
{
  "answer": "Employment termination requires one month notice [1]...",
  "sources": [
    {
      "source_id": "uuid",
      "citation_id": 1,
      "snippet": "Preview...",
      "highlighted_excerpt": "...with <mark>highlights</mark>..."
    }
  ],
  "citation_map": {1: "Employment Act 2007, Section 35"}
}
```

**When Used:**
- User asks legal questions that need citations
- Frontend sets `use_enhanced_rag: true`
- DEFAULT mode for most queries

#### 2. ❌ **Direct Query Mode** - NO CITATIONS
**Endpoint:** `POST /api/v1/counsel/query-direct`
**Request:**
```json
{
  "query": "What is employment law?",
  "model_preference": "claude-sonnet-4"
}
```

**Response:**
```json
{
  "response_text": "Plain text without citations",
  "model_used": "claude-sonnet-4",
  "success": true
}
```

**When Used:**
- Quick questions
- No need for source verification
- Faster responses (no RAG retrieval)

#### 3. 🔄 **Agent Mode** - PARTIAL CITATIONS (Future Enhancement)
**Endpoint:** `POST /api/v1/counsel/query`
**Request:**
```json
{
  "query": "Research employment law comprehensively",
  "use_enhanced_rag": true,
  "agent_mode": true  // AGENT MODE
}
```

**Current Response:**
```json
{
  "answer": "Research findings...",
  "reasoning_chain": ["Step 1...", "Step 2..."],
  "sources": ["basic list"]  // NOT structured yet
}
```

**Future Enhancement:**
You can add citations to agent mode by modifying:
```python
# In app/api/routes/counsel.py
async def _process_agent_mode_query(request: LegalQueryRequest) -> Dict:
    # ... existing code ...

    # ADD: Use enhanced RAG service for agent mode
    from app.services.enhanced_rag_service import enhanced_rag_service

    rag_response = await enhanced_rag_service.query(
        question=request.query,
        use_citations=True  # Enable for agent mode too
    )

    return {
        "response_text": rag_response["answer"],
        "sources": rag_response["sources"],  # Structured sources
        "citation_map": rag_response["citation_map"],
        "reasoning_chain": reasoning_chain,
        # ... rest
    }
```

#### 4. ❌ **Streaming Mode** - NO CITATIONS (Yet)
**Endpoint:** `POST /api/v1/counsel/query-stream`
**Response:** Server-sent events (SSE)

**Current:** Plain text streaming
**Future:** Can add citations in post-processing

---

## 🌍 Deployment Context

### Current Status: Development (SQLite)

**Location:** Local machine (`c:\Users\HP\legalizeme-v3`)
**Database:** SQLite (`counsel.db`)
**Vector Store:** ChromaDB (local)
**LLM:** AWS Bedrock (requires credentials)

**Can You Test Locally?**
- ✅ Database changes (SQLite)
- ✅ API endpoints structure
- ✅ Citation parsing logic
- ❌ **Full RAG with citations** (needs AWS credentials + vector data)

**Why?**
```python
# In enhanced_rag_service.py
retrieved_docs = await self.vector_service.search_similar(...)
# ↑ This requires:
# 1. AWS credentials configured
# 2. ChromaDB/OpenSearch with embedded documents
# 3. Bedrock access for embeddings
```

### Production Deployment: AWS

**Infrastructure:**
```
┌─────────────────────────────────────────────────────┐
│                  AWS Cloud (us-east-1)              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐         ┌──────────────┐        │
│  │  ECS Fargate │────────▶│ RDS Postgres │        │
│  │   (Backend)  │         │  (Database)  │        │
│  └──────┬───────┘         └──────────────┘        │
│         │                                          │
│         │                 ┌──────────────┐        │
│         ├────────────────▶│ AWS Bedrock  │        │
│         │                 │ (Claude AI)  │        │
│         │                 └──────────────┘        │
│         │                                          │
│         │                 ┌──────────────┐        │
│         └────────────────▶│  ChromaDB    │        │
│                           │ (Vectors)    │        │
│                           └──────────────┘        │
│                                                     │
│  ┌──────────────┐                                 │
│  │  CloudFront  │◀─── Frontend (React/Next.js)    │
│  │     (CDN)    │                                 │
│  └──────────────┘                                 │
└─────────────────────────────────────────────────────┘
```

**When Deployed to AWS:**

1. **Backend (ECS Fargate):**
   ```bash
   # Environment variables
   DATABASE_URL=postgresql://user:pass@rds-endpoint/counsel
   AWS_REGION=us-east-1
   BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
   CHROMA_HOST=chromadb-service
   ```

2. **Database (RDS PostgreSQL):**
   - All 35 document fields available
   - JSONB for `legal_metadata` (faster than SQLite JSON)
   - GIN indexes on JSONB fields

3. **Vector Store (ChromaDB or OpenSearch):**
   - Embeddings for all Kenya Law documents
   - Fast similarity search (<100ms)

4. **LLM (AWS Bedrock):**
   - Claude 3.5 Sonnet
   - Streaming responses
   - Cost tracking

**Where Interactive Citations Work:**

| Environment | Enhanced RAG | Citations | Source Verification | Full Source Modal |
|-------------|--------------|-----------|---------------------|-------------------|
| **Local Dev (SQLite)** | ⚠️ Partial* | ✅ Yes | ✅ Yes | ✅ Yes |
| **AWS Staging** | ✅ Full | ✅ Yes | ✅ Yes | ✅ Yes |
| **AWS Production** | ✅ Full | ✅ Yes | ✅ Yes | ✅ Yes |

*Partial = Backend code works, but RAG requires AWS credentials + vector data

---

## 🔧 Testing Locally (Without Full AWS)

### What You CAN Test Locally

#### 1. Database Schema ✅
```bash
# Initialize database
python scripts/init_database.py

# Check new fields exist
python -c "from app.database import SessionLocal; from app.models.document import Document; print(Document.__table__.columns.keys())"
# Should show: snippet, citation_text, document_date, etc.
```

#### 2. Document Methods ✅
```bash
# Test freshness calculation, snippet generation
python scripts/test_steps_1_3_and_1_4.py
```

#### 3. API Endpoints ✅
```bash
# Start FastAPI server
uvicorn app.main:app --reload --port 8000

# Test source verification (with mock data)
curl http://localhost:8000/api/v1/counsel/sources/{uuid}/verify

# Test full source
curl http://localhost:8000/api/v1/counsel/sources/{uuid}/full
```

#### 4. Citation Parsing ✅
```python
# Test citation utilities
from utils.citation import parseCitations

text = "Employment law requires notice [1] and process [2]."
result = parseCitations(text)
# Returns: {citations: [1, 2]}
```

### What You CANNOT Test Locally (Needs AWS)

#### 1. Vector Search ❌
```python
# This requires ChromaDB with embedded documents
retrieved_docs = await vector_service.search_similar(
    query="employment termination",
    limit=5
)
# ERROR: No vector embeddings available
```

#### 2. LLM with Citations ❌
```python
# This requires AWS Bedrock credentials
response = await llm_manager.invoke_model(
    prompt=citation_aware_prompt
)
# ERROR: AWS credentials not configured
```

#### 3. Full RAG Pipeline ❌
```python
# This requires:
# - AWS credentials
# - Vector embeddings
# - LLM access
result = await enhanced_rag_service.query(
    question="What is notice period?",
    use_citations=True
)
# ERROR: Service unavailable
```

---

## 🚀 Deployment Strategy

### Step 1: Local Testing (Now)
**What:** Database, API structure, citation parsing
**How:**
```bash
# Test database
python scripts/test_steps_1_3_and_1_4.py

# Test citation utilities (frontend can do this)
# No AWS needed
```

### Step 2: AWS Staging Deployment (Next)
**When:** After frontend integration
**What:** Full RAG with citations

**Deployment Steps:**
```bash
# 1. Build Docker image
docker build -t counsel-ai-backend:latest .

# 2. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login ...
docker push {aws-account-id}.dkr.ecr.us-east-1.amazonaws.com/counsel-ai:latest

# 3. Update ECS service
aws ecs update-service \
  --cluster counsel-ai-cluster \
  --service counsel-ai-backend \
  --force-new-deployment

# 4. Run database migration on RDS
aws ecs run-task \
  --cluster counsel-ai-cluster \
  --task-definition counsel-ai-migration \
  --overrides '{"containerOverrides": [{"name": "migration", "command": ["python", "scripts/run_migration_001.py"]}]}'
```

### Step 3: Production Deployment
**When:** After staging validation
**What:** Same as staging, different environment

**Environment Variables (Production):**
```bash
DATABASE_URL=postgresql://prod_user:***@rds-prod.amazonaws.com/counsel
AWS_REGION=us-east-1
ENVIRONMENT=production
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
CHROMA_HOST=chromadb-prod.internal
CORS_ORIGINS=https://legalizeme.co.ke
```

---

## 📊 Which Users See Interactive Citations?

### Current Behavior (After AWS Deployment)

**1. Mobile Users:** ✅ See citations
- Mode: Enhanced RAG (default)
- Citations: [1][2][3] clickable
- Sources: Structured with metadata

**2. Web Users:** ✅ See citations
- Mode: Enhanced RAG (default)
- Full modals available
- Source verification

**3. API Users:** ✅ Get structured response
- JSON with `sources` array
- `citation_map` included
- Can build own UI

### Control via Frontend

**To ENABLE citations:**
```typescript
// Frontend controls this
const response = await fetch('/api/v1/counsel/query', {
  method: 'POST',
  body: JSON.stringify({
    query: userQuestion,
    use_enhanced_rag: true,  // ← ENABLES CITATIONS
    agent_mode: false
  })
});
```

**To DISABLE citations:**
```typescript
// Use direct mode instead
const response = await fetch('/api/v1/counsel/query-direct', {
  method: 'POST',
  body: JSON.stringify({
    query: userQuestion
  })
});
// OR set use_citations: false in backend (future parameter)
```

---

## 🔐 AWS Credentials Setup (For Testing)

If you want to test RAG locally with AWS:

### Option 1: AWS Profile
```bash
# Configure AWS CLI
aws configure

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### Option 2: Environment Variables
```bash
# Add to .env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
```

### Option 3: IAM Role (Production)
```bash
# ECS tasks use IAM role (no credentials needed)
# Role permissions:
# - bedrock:InvokeModel
# - rds:Connect
# - s3:GetObject (for documents)
```

---

## 📝 Summary

### Interactive Citations Availability

| Mode | Local (SQLite) | AWS Staging | AWS Production |
|------|---------------|-------------|----------------|
| **Enhanced RAG** | Schema only* | ✅ Full | ✅ Full |
| **Direct Query** | N/A | N/A | N/A |
| **Agent Mode** | Schema only* | 🔄 Future | 🔄 Future |
| **Streaming** | N/A | 🔄 Future | 🔄 Future |

*Schema only = Database ready, but RAG requires AWS

### Deployment Required?

**For Frontend Testing:**
- ❌ No AWS needed
- ✅ Can test citation parsing, UI components
- ✅ Can test modal structure
- ✅ Can use mock data

**For Full Integration:**
- ✅ AWS deployment required
- ✅ Vector embeddings needed
- ✅ Bedrock credentials required
- ✅ RDS PostgreSQL recommended

### Next Steps

1. **Frontend Team:** Build UI with mock data (no AWS needed)
2. **Backend Team:** Test on AWS staging
3. **Integration:** Connect frontend to staging API
4. **Production:** Deploy to legalizeme.co.ke

---

**Questions?**

**Q: Can we test citations without AWS?**
A: Yes, for UI components. No, for actual RAG responses.

**Q: When will users see citations?**
A: After AWS deployment + frontend deployment.

**Q: Do all modes get citations?**
A: Only Enhanced RAG mode currently. Agent mode can be added.

**Q: Is local testing possible?**
A: Yes, for database/API structure. No, for full RAG pipeline.

---

**Last Updated:** 2025-10-04
**AWS Deployment:** Pending
**Frontend Integration:** Ready to start
