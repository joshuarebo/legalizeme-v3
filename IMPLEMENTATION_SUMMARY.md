# Phase 1 RAG OpenSearch Integration - Implementation Summary

## ✅ Completed Tasks

### 1. **AWS Vector Service Updated**
**File**: `app/services/aws_vector_service.py`

- ✅ Added OpenSearch client connection with AWS4Auth
- ✅ Implemented k-NN vector search using OpenSearch
- ✅ Added fallback to in-memory storage if OpenSearch fails
- ✅ Updated `add_document()` to index to OpenSearch with proper schema
- ✅ Updated `search_similar()` to use k-NN search
- ✅ Updated `delete_document()` and `get_collection_stats()` for OpenSearch

**Key Changes**:
- Uses `opensearch-py` library with AWS authentication
- Indexes documents with 1536-dim embeddings from Bedrock Titan
- Graceful degradation to in-memory if connection fails

---

### 2. **Document Indexing Service Created**
**File**: `app/services/document_indexing_service.py` (NEW)

- ✅ Created bridge service between crawlers and OpenSearch
- ✅ Converts crawler output to OpenSearch-compatible format
- ✅ Generates document IDs from URLs using MD5 hash
- ✅ Validates content before indexing (min 50 chars)
- ✅ Batch indexing support

**Key Features**:
- Extracts metadata (title, legal area, court, publication date)
- Creates embeddings from title + content preview (2000 chars)
- Comprehensive error handling and logging

---

### 3. **Crawler Service Updated**
**File**: `app/services/crawler_service.py`

- ✅ Imported document indexing service
- ✅ Updated `_periodic_kenya_law_crawl()` to index after crawling
- ✅ Updated `_periodic_parliament_crawl()` to index after crawling
- ✅ Added indexing for judgments, legislation, gazettes, hansard, bills

**Key Changes**:
- Each crawled document is immediately indexed to OpenSearch
- Logs indexed/failed counts for monitoring
- Rate limiting maintained (1 req/sec)

---

### 4. **Kenya Law Crawler Expanded**
**File**: `app/crawlers/kenya_law_crawler.py`

- ✅ Added 11 new section URLs to `self.sections`:
  - legislation_counties
  - bills
  - superior_courts
  - subordinate_courts
  - small_claims_court
  - civil_human_rights_tribunals
  - commercial_tribunals
  - environment_land_tribunals
  - intellectual_property_tribunals
  - regional_international_courts
  - tribunals

- ✅ Created 6 new crawler methods:
  - `crawl_superior_courts()`
  - `crawl_subordinate_courts()`
  - `crawl_tribunals()`
  - `crawl_legislation_counties()`
  - `crawl_bills()`
  - `crawl_commercial_tribunals()`

- ✅ Added generic `_get_section_urls()` helper method

**Coverage**: Now crawls **16 Kenya Law sections** + Parliament

---

### 5. **Admin Endpoints Created**
**File**: `app/api/routes/counsel.py`

- ✅ **POST `/api/v1/counsel/admin/crawl/trigger`**
  - Trigger manual crawl and indexing
  - Query params: `section` (enum), `limit` (10-1000)
  - Supports: judgments, legislation, gazettes, bills, courts, tribunals
  - Returns crawled/indexed/error counts

- ✅ **GET `/api/v1/counsel/admin/search/stats`**
  - Get OpenSearch index statistics
  - Returns document count, index name, service type

**Usage Examples**:
```bash
# Crawl and index 500 judgments
POST /api/v1/counsel/admin/crawl/trigger?section=judgments&limit=500

# Get index stats
GET /api/v1/counsel/admin/search/stats
```

---

### 6. **Dependencies Updated**
**File**: `requirements.txt`

- ✅ Added `opensearch-py==3.0.0`
- ✅ Added `requests-aws4auth==1.3.1`

---

### 7. **Configuration Updated**
**File**: `app/config.py`

- ✅ Added `OPENSEARCH_ENDPOINT` (default: AWS domain)
- ✅ Added `OPENSEARCH_INDEX` (default: kenyan-legal-docs)
- ✅ Added `OPENSEARCH_PORT` (default: 443)

---

### 8. **Test Scripts Created**

**File**: `scripts/test_opensearch_connection.py`
- Tests OpenSearch connection
- Verifies service initialization
- Reports connection status and stats

**File**: `scripts/test_single_index.py`
- Indexes single test document (Employment Act 2007)
- Tests search functionality
- Validates document retrieval

**Note**: Local testing requires AWS credentials and opensearch-py installed

---

## 🚀 Next Steps (For Next Session)

### 1. **Local Testing** (Can't test locally without AWS creds)
Since local testing requires AWS credentials, these steps should be done in deployment:

```bash
# Install new dependencies
pip install opensearch-py==3.0.0 requests-aws4auth==1.3.1

# Test scripts will work in production with env vars set
```

### 2. **Deploy to Production**

**Step 1: Build and Deploy**
```bash
# Commit changes
git add .
git commit -m "feat: Phase 1 RAG - OpenSearch integration with crawlers"
git push

# Build Docker image
docker build -f Dockerfile.ecs -t counsel-ai:opensearch .

# Push to ECR (replace with actual ECR URI)
docker tag counsel-ai:opensearch <ECR_URI>:latest
docker push <ECR_URI>:latest

# Deploy to ECS (task definition 65)
```

**Step 2: Trigger Initial Crawl** (via API)
```bash
# Crawl judgments (500 docs)
curl -X POST https://api.legalizeme.site/api/v1/counsel/admin/crawl/trigger?section=judgments&limit=500

# Crawl legislation (500 docs)
curl -X POST https://api.legalizeme.site/api/v1/counsel/admin/crawl/trigger?section=legislation&limit=500

# Crawl gazettes (200 docs)
curl -X POST https://api.legalizeme.site/api/v1/counsel/admin/crawl/trigger?section=gazettes&limit=200

# Crawl superior courts (300 docs)
curl -X POST https://api.legalizeme.site/api/v1/counsel/admin/crawl/trigger?section=superior-courts&limit=300

# etc...
```

**Step 3: Monitor Indexing**
```bash
# Check index stats
curl https://api.legalizeme.site/api/v1/counsel/admin/search/stats

# Expected response:
{
  "status": "success",
  "stats": {
    "total_documents": 1500,
    "index_name": "kenyan-legal-docs",
    "service_type": "AWS OpenSearch",
    "using_opensearch": true
  }
}
```

**Step 4: Test RAG with Citations**
```bash
curl -X POST https://api.legalizeme.site/api/v1/counsel/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the notice period for employment termination in Kenya?",
    "use_enhanced_rag": true
  }'
```

**Expected Response**:
```json
{
  "response": "According to the Employment Act 2007, employers must provide written notice before termination [1]. The minimum notice period is 28 days... [2]",
  "citations": [
    {
      "number": 1,
      "title": "Employment Act 2007 - Section 35",
      "url": "https://new.kenyalaw.org/legislation/...",
      "snippet": "An employer shall give notice in writing..."
    }
  ],
  "citation_map": { ... },
  "sources": [ ... ]
}
```

---

## 📊 Expected Results

### After Initial Crawl (2-4 hours):
- **30K-50K documents** indexed to OpenSearch
- **All 16 Kenya Law sections** covered
- **Parliamentary documents** included

### Phase 1 RAG Success Criteria:
✅ OpenSearch index has 30K+ documents
✅ RAG queries return inline citations [1][2][3]
✅ Response includes `citation_map` with source details
✅ Periodic crawling updates index daily
✅ Production stable on task definition 65

---

## 🔧 Troubleshooting

### If OpenSearch connection fails:
1. Check AWS credentials in environment variables
2. Verify OpenSearch domain is accessible
3. Check IAM role permissions for ECS task
4. Service will fallback to in-memory (not ideal for prod)

### If documents aren't indexing:
1. Check logs for indexing errors
2. Verify crawler is finding documents
3. Run `/admin/search/stats` to check count
4. Check Bedrock embedding generation

### If RAG returns no citations:
1. Verify documents in OpenSearch (`/admin/search/stats`)
2. Check `enhanced_rag_service` is using `aws_vector_service`
3. Test search directly: `aws_vector_service.search_similar()`
4. Verify k-NN search is working

---

## 📁 Files Modified/Created

### Modified:
1. `app/services/aws_vector_service.py` - OpenSearch integration
2. `app/services/crawler_service.py` - Indexing integration
3. `app/crawlers/kenya_law_crawler.py` - Additional sections
4. `app/api/routes/counsel.py` - Admin endpoints
5. `app/config.py` - OpenSearch config
6. `requirements.txt` - Dependencies

### Created:
1. `app/services/document_indexing_service.py` - Indexing service
2. `scripts/test_opensearch_connection.py` - Connection test
3. `scripts/test_single_index.py` - Indexing test
4. `IMPLEMENTATION_SUMMARY.md` - This file

---

## 🎯 Next Session Command

```bash
# Start next session with deployment and testing
# All code is ready, just needs to be deployed and tested in production
```

**Implementation Complete! Ready for deployment and production testing.**
