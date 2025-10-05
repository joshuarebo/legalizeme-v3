# AWS Deployment Guide: Phase 1 Interactive Citations

**Date:** 2025-10-04
**Version:** 1.0
**Status:** Ready for Deployment
**Breaking Changes:** None ✅

---

## 📋 Pre-Deployment Checklist

### ✅ Code Changes Summary

**Modified Files:**
- `app/models/document.py` - Added 10 new fields + FlexibleJSON
- `app/services/enhanced_rag_service.py` - Added 8 citation methods
- `app/api/routes/counsel.py` - Enhanced agent + research modes
- `app/schemas/api_responses.py` - Added SourceMetadata, updated StructuredSource
- `app/database.py` - Cross-database compatibility

**New Files:**
- `migrations/001_add_interactive_source_fields.sql` (PostgreSQL)
- `migrations/001_add_interactive_source_fields_sqlite.sql` (SQLite)
- `scripts/run_migration_001.py`
- `scripts/init_database.py`

**Endpoints Enhanced (NO BREAKING CHANGES):**
- ✅ `POST /api/v1/counsel/query` - Enhanced RAG mode (citations enabled by default)
- ✅ `POST /api/v1/counsel/query` - Agent mode now has citations
- ✅ `POST /api/v1/counsel/research` - Research mode now has citations
- ✅ `GET /api/v1/counsel/sources/{id}/verify` - NEW endpoint
- ✅ `GET /api/v1/counsel/sources/{id}/full` - NEW endpoint

**Modes with Citations:**
1. ✅ Enhanced RAG Mode - `use_enhanced_rag: true` (default)
2. ✅ Agent Mode - `agent_mode: true` (NEW)
3. ✅ Research Mode - `/research` endpoint (NEW)
4. ❌ Direct Query Mode - No citations (by design)

---

## 🏗️ AWS Infrastructure Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    AWS Account (us-east-1)                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐       ┌──────────────────┐            │
│  │   ECS Fargate  │──────▶│  RDS PostgreSQL  │            │
│  │    (Backend)   │       │    (Database)    │            │
│  │                │       │  counsel-db-prod │            │
│  │ Task Count: 2  │       └──────────────────┘            │
│  └───────┬────────┘                                        │
│          │                ┌──────────────────┐            │
│          ├───────────────▶│  AWS Bedrock     │            │
│          │                │  (Claude 3.5)    │            │
│          │                └──────────────────┘            │
│          │                                                 │
│          │                ┌──────────────────┐            │
│          ├───────────────▶│    ChromaDB      │            │
│          │                │  (Vector Store)  │            │
│          │                └──────────────────┘            │
│          │                                                 │
│          │                ┌──────────────────┐            │
│          └───────────────▶│       ECR        │            │
│                           │  (Docker Images) │            │
│                           └──────────────────┘            │
│                                                             │
│  ┌────────────────┐                                        │
│  │  Application   │                                        │
│  │  Load Balancer │◀─── Internet                          │
│  │     (ALB)      │                                        │
│  └────────────────┘                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 🚀 Deployment Steps

### Step 1: Test Locally (5 minutes)

```bash
# 1. Test database schema
python scripts/test_steps_1_3_and_1_4.py

# 2. Test agent mode structure
python scripts/test_agent_mode_citations.py

# 3. Test citation utilities
python scripts/test_enhanced_rag_step_1_2.py

# Expected: All tests pass (without AWS, tests structure only)
```

### Step 2: Commit Changes (5 minutes)

```bash
# 1. Check status
git status

# 2. Review changes
git diff app/models/document.py
git diff app/services/enhanced_rag_service.py
git diff app/api/routes/counsel.py

# 3. Stage changes
git add app/models/document.py
git add app/services/enhanced_rag_service.py
git add app/api/routes/counsel.py
git add app/schemas/api_responses.py
git add app/database.py
git add migrations/
git add scripts/

# 4. Commit
git commit -m "feat: Add interactive citations to Enhanced RAG, Agent, and Research modes

- Add 10 new fields to Document model for interactive sources
- Implement 8 citation-aware methods in enhanced_rag_service
- Add inline [1][2][3] citations to Enhanced RAG mode
- Enhance Agent mode with structured sources and citations
- Enhance Research mode with structured sources and citations
- Add /sources/{id}/verify endpoint for source verification
- Add /sources/{id}/full endpoint for full source content
- Add SourceMetadata and StructuredSource Pydantic schemas
- Create PostgreSQL and SQLite database migrations
- Add FlexibleJSON type for cross-database compatibility

BREAKING CHANGES: None (fully backward compatible)

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# 5. Push to repository
git push origin main
```

### Step 3: Build Docker Image (10 minutes)

```bash
# Navigate to project root
cd c:\Users\HP\legalizeme-v3

# Set variables
$AWS_ACCOUNT_ID = "YOUR_AWS_ACCOUNT_ID"
$AWS_REGION = "us-east-1"
$IMAGE_NAME = "counsel-ai-backend"
$IMAGE_TAG = "phase1-citations-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$ECR_REPOSITORY = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE_NAME"

# 1. Build Docker image
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# 2. Tag for ECR
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY}:${IMAGE_TAG}
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY}:latest

# 3. Verify image
docker images | Select-String $IMAGE_NAME

# Expected output:
# counsel-ai-backend   phase1-citations-20251004-HHMMSS   abc123def   2 minutes ago   1.2GB
# counsel-ai-backend   latest                             abc123def   2 minutes ago   1.2GB
```

### Step 4: Push to ECR (5 minutes)

```bash
# 1. Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin ${ECR_REPOSITORY}

# 2. Push versioned image
docker push ${ECR_REPOSITORY}:${IMAGE_TAG}

# 3. Push latest tag
docker push ${ECR_REPOSITORY}:latest

# Expected output:
# The push refers to repository [123456789.dkr.ecr.us-east-1.amazonaws.com/counsel-ai-backend]
# phase1-citations-20251004-HHMMSS: digest: sha256:abc... size: 1234
```

### Step 5: Run Database Migration on RDS (10 minutes)

**Option A: ECS Task (Recommended)**

```bash
# 1. Create migration task definition (one-time setup)
aws ecs register-task-definition --cli-input-json file://ecs-migration-task.json

# 2. Run migration task
aws ecs run-task \
  --cluster counsel-ai-cluster \
  --task-definition counsel-ai-migration:latest \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-abc123],securityGroups=[sg-xyz789],assignPublicIp=ENABLED}" \
  --overrides '{
    "containerOverrides": [{
      "name": "migration",
      "command": ["python", "scripts/run_migration_001.py"]
    }]
  }'

# 3. Monitor migration task
aws ecs describe-tasks \
  --cluster counsel-ai-cluster \
  --tasks TASK_ARN

# 4. Check migration logs
aws logs tail /ecs/counsel-ai-migration --follow
```

**Option B: Bastion Host / RDS Proxy**

```bash
# 1. SSH to bastion
ssh -i counsel-ai-key.pem ec2-user@bastion-ip

# 2. Connect to database
psql -h counsel-db-prod.abc123.us-east-1.rds.amazonaws.com -U counsel_admin -d counsel

# 3. Run migration manually
\i /path/to/001_add_interactive_source_fields.sql

# 4. Verify new columns
\d documents

# Expected: Shows 35 columns including snippet, citation_text, etc.
```

### Step 6: Update ECS Service (15 minutes)

```bash
# 1. Get current task definition
aws ecs describe-task-definition \
  --task-definition counsel-ai-backend \
  --query 'taskDefinition' > current-task-def.json

# 2. Update image tag in task definition
# Edit current-task-def.json, change image to: ${ECR_REPOSITORY}:${IMAGE_TAG}

# 3. Register new task definition revision
aws ecs register-task-definition --cli-input-json file://current-task-def.json

# 4. Update ECS service (this triggers deployment)
aws ecs update-service \
  --cluster counsel-ai-cluster \
  --service counsel-ai-backend \
  --task-definition counsel-ai-backend:NEW_REVISION \
  --force-new-deployment

# Output example:
# {
#   "service": {
#     "serviceName": "counsel-ai-backend",
#     "status": "ACTIVE",
#     "desiredCount": 2,
#     "runningCount": 2,
#     "deployments": [
#       {
#         "status": "PRIMARY",
#         "taskDefinition": "arn:aws:ecs:us-east-1:...:task-definition/counsel-ai-backend:NEW",
#         "desiredCount": 2,
#         "runningCount": 0
#       },
#       {
#         "status": "ACTIVE",
#         "taskDefinition": "arn:aws:ecs:us-east-1:...:task-definition/counsel-ai-backend:OLD",
#         "desiredCount": 2,
#         "runningCount": 2
#       }
#     ]
#   }
# }
```

### Step 7: Monitor Deployment & Wait for Stabilization (10-15 minutes)

```bash
# 1. Watch deployment progress
aws ecs describe-services \
  --cluster counsel-ai-cluster \
  --services counsel-ai-backend \
  --query 'services[0].deployments' \
  --output table

# 2. Monitor deployment events
aws ecs describe-services \
  --cluster counsel-ai-cluster \
  --services counsel-ai-backend \
  --query 'services[0].events[0:10]' \
  --output table

# 3. Check task health
aws ecs list-tasks --cluster counsel-ai-cluster --service-name counsel-ai-backend

# 4. Stream application logs
aws logs tail /ecs/counsel-ai-backend --follow --since 5m

# 5. Wait for deployment to stabilize (automated)
aws ecs wait services-stable \
  --cluster counsel-ai-cluster \
  --services counsel-ai-backend

# Expected: Command completes when deployment is stable (both tasks running)
```

**Deployment Progress Indicators:**

- **Phase 1 (0-5 min):** New tasks starting
  ```
  runningCount: 0 (new), 2 (old)
  ```

- **Phase 2 (5-10 min):** New tasks running, old tasks draining
  ```
  runningCount: 2 (new), 2 (old draining)
  ```

- **Phase 3 (10-15 min):** Deployment complete
  ```
  runningCount: 2 (new), 0 (old)
  deploymentStatus: COMPLETED
  ```

### Step 8: Verify Deployment (10 minutes)

#### Health Checks

```bash
# 1. Check ALB health
curl https://api.legalizeme.co.ke/api/v1/health

# Expected:
# {
#   "status": "healthy",
#   "timestamp": "2025-10-04T..."
# }

# 2. Check database connection
curl https://api.legalizeme.co.ke/api/v1/counsel/health

# 3. Verify new fields exist
curl https://api.legalizeme.co.ke/api/v1/counsel/init-db
```

#### Test Enhanced RAG with Citations

```bash
# Test Enhanced RAG mode
curl -X POST https://api.legalizeme.co.ke/api/v1/counsel/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the notice period for employment termination in Kenya?",
    "use_enhanced_rag": true,
    "agent_mode": false
  }'

# Expected response structure:
# {
#   "success": true,
#   "answer": "Employment termination requires one month notice [1]...",
#   "sources": [
#     {
#       "source_id": "uuid",
#       "citation_id": 1,
#       "title": "Employment Act 2007, Section 35",
#       "snippet": "Section 35 of the Employment Act...",
#       "highlighted_excerpt": "...one month <mark>notice</mark>...",
#       "metadata": {
#         "freshness_score": 0.95,
#         "citation_text": "Employment Act 2007, Section 35"
#       }
#     }
#   ],
#   "citation_map": {"1": "Employment Act 2007, Section 35"}
# }
```

#### Test Agent Mode with Citations

```bash
# Test Agent mode
curl -X POST https://api.legalizeme.co.ke/api/v1/counsel/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Research employment law comprehensively",
    "use_enhanced_rag": true,
    "agent_mode": true
  }'

# Expected: Same citation structure + reasoning_chain field
```

#### Test Research Mode

```bash
# Test Research endpoint
curl -X POST https://api.legalizeme.co.ke/api/v1/counsel/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Employment termination procedures",
    "max_results": 5,
    "sources": ["kenya_law"]
  }'

# Expected: summary with citations + relevant_documents array
```

#### Test Source Verification

```bash
# Get a source_id from previous query, then:
curl https://api.legalizeme.co.ke/api/v1/counsel/sources/{SOURCE_ID}/verify

# Expected:
# {
#   "source_id": "uuid",
#   "title": "Employment Act 2007",
#   "is_accessible": true,
#   "crawl_status": "active",
#   "freshness_score": 0.95,
#   "http_status": 200
# }
```

#### Test Full Source Retrieval

```bash
curl https://api.legalizeme.co.ke/api/v1/counsel/sources/{SOURCE_ID}/full

# Expected:
# {
#   "source_id": "uuid",
#   "title": "Employment Act 2007, Section 35",
#   "full_content": "Complete document text...",
#   "document_type": "legislation",
#   "metadata": {...}
# }
```

---

## 🔄 Rollback Procedure

If deployment fails or issues arise:

### Quick Rollback (5 minutes)

```bash
# 1. Get previous task definition revision
aws ecs describe-services \
  --cluster counsel-ai-cluster \
  --services counsel-ai-backend \
  --query 'services[0].deployments[1].taskDefinition'

# 2. Rollback to previous revision
aws ecs update-service \
  --cluster counsel-ai-cluster \
  --service counsel-ai-backend \
  --task-definition counsel-ai-backend:PREVIOUS_REVISION \
  --force-new-deployment

# 3. Wait for rollback to complete
aws ecs wait services-stable \
  --cluster counsel-ai-cluster \
  --services counsel-ai-backend

# 4. Verify rollback
curl https://api.legalizeme.co.ke/api/v1/health
```

### Database Rollback (If needed)

```bash
# If migration causes issues, create rollback migration:
# migrations/001_rollback.sql

ALTER TABLE documents DROP COLUMN IF EXISTS snippet;
ALTER TABLE documents DROP COLUMN IF EXISTS citation_text;
ALTER TABLE documents DROP COLUMN IF EXISTS document_date;
ALTER TABLE documents DROP COLUMN IF EXISTS court_name;
ALTER TABLE documents DROP COLUMN IF EXISTS case_number;
ALTER TABLE documents DROP COLUMN IF EXISTS act_chapter;
ALTER TABLE documents DROP COLUMN IF EXISTS last_verified_at;
ALTER TABLE documents DROP COLUMN IF EXISTS crawl_status;
ALTER TABLE documents DROP COLUMN IF EXISTS freshness_score;
ALTER TABLE documents DROP COLUMN IF EXISTS legal_metadata;

# Run rollback
psql -h RDS_ENDPOINT -U counsel_admin -d counsel -f 001_rollback.sql
```

---

## 📊 Post-Deployment Monitoring

### CloudWatch Metrics to Watch (First 24 hours)

```bash
# 1. API Response Times
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/counsel-ai-alb/abc123 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# 2. Error Rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name HTTPCode_Target_5XX_Count \
  --dimensions Name=LoadBalancer,Value=app/counsel-ai-alb/abc123 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# 3. ECS CPU/Memory
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=counsel-ai-backend Name=ClusterName,Value=counsel-ai-cluster \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### Application Logs

```bash
# Monitor for errors
aws logs tail /ecs/counsel-ai-backend --follow --filter-pattern "ERROR"

# Monitor citation queries
aws logs tail /ecs/counsel-ai-backend --follow --filter-pattern "[1]"

# Monitor new endpoints
aws logs tail /ecs/counsel-ai-backend --follow --filter-pattern "/sources/"
```

### Database Monitoring

```bash
# Check RDS performance
aws rds describe-db-instances \
  --db-instance-identifier counsel-db-prod \
  --query 'DBInstances[0].[DBInstanceStatus,Engine,DBInstanceClass,AllocatedStorage]'

# Monitor active connections
# (Connect to database)
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

# Check query performance
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## ✅ Deployment Verification Checklist

### Infrastructure
- [ ] ECS service shows 2/2 tasks running
- [ ] ALB health checks passing
- [ ] RDS database accessible
- [ ] CloudWatch logs streaming
- [ ] No 5XX errors in ALB metrics

### Database
- [ ] Migration completed successfully
- [ ] `documents` table has 35 columns
- [ ] `legal_metadata` column type is JSONB
- [ ] Existing data intact
- [ ] No query performance degradation

### API Endpoints
- [ ] `/health` returns healthy
- [ ] `/query` with `use_enhanced_rag: true` returns citations
- [ ] `/query` with `agent_mode: true` returns citations + reasoning_chain
- [ ] `/research` returns citations in summary
- [ ] `/sources/{id}/verify` works
- [ ] `/sources/{id}/full` works

### Response Structure
- [ ] `answer` field contains [1][2][3] citations
- [ ] `sources` array has `source_id` UUID
- [ ] `sources` array has `snippet` field
- [ ] `sources` array has `highlighted_excerpt` with `<mark>` tags
- [ ] `citation_map` present
- [ ] `metadata.freshness_score` present

### Performance
- [ ] Response time < 2s for Enhanced RAG
- [ ] Response time < 3s for Agent mode
- [ ] Source verification < 500ms
- [ ] Full source retrieval < 100ms
- [ ] No memory leaks (stable over 24h)

---

## 🎯 Success Criteria

**Deployment is successful when:**

1. ✅ All ECS tasks healthy (2/2 running)
2. ✅ All API endpoints responding
3. ✅ Enhanced RAG returns inline citations
4. ✅ Agent mode returns citations + reasoning
5. ✅ Research mode returns citations
6. ✅ Source verification works
7. ✅ No 5XX errors
8. ✅ Response times within SLA
9. ✅ Database migration successful
10. ✅ No breaking changes to existing functionality

---

## 📞 Troubleshooting

### Issue: Tasks failing to start

**Check:**
```bash
aws ecs describe-tasks --cluster counsel-ai-cluster --tasks TASK_ARN
```

**Common causes:**
- Docker image not in ECR
- IAM role missing permissions
- Environment variables incorrect
- Health check failing

**Fix:**
```bash
# Check task stopped reason
aws ecs describe-tasks --cluster counsel-ai-cluster --tasks TASK_ARN --query 'tasks[0].stoppedReason'

# Check container logs
aws logs tail /ecs/counsel-ai-backend --since 10m
```

### Issue: Migration fails

**Check:**
```bash
# View migration logs
aws logs tail /ecs/counsel-ai-migration --follow
```

**Common causes:**
- Database connection timeout
- Insufficient permissions
- Duplicate column names (migration already run)

**Fix:**
```bash
# Check if migration already applied
psql -h RDS_ENDPOINT -U counsel_admin -d counsel \
  -c "\d documents" | grep "citation_text"

# If exists, skip migration
```

### Issue: Citations not appearing

**Check:**
```bash
# Test locally first
curl -X POST http://localhost:8000/api/v1/counsel/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "use_enhanced_rag": true}'

# Check if vector store has data
# Check if AWS Bedrock credentials valid
```

---

## 📝 Deployment Timeline

| Step | Duration | Cumulative |
|------|----------|------------|
| Local testing | 5 min | 5 min |
| Git commit | 5 min | 10 min |
| Docker build | 10 min | 20 min |
| ECR push | 5 min | 25 min |
| Database migration | 10 min | 35 min |
| ECS update | 15 min | 50 min |
| Stabilization wait | 10 min | 60 min |
| Verification | 10 min | 70 min |

**Total: ~70 minutes (1 hour 10 minutes)**

---

**Last Updated:** 2025-10-04
**Deployed By:** [Your Name]
**Deployment Date:** [To be filled]
**Status:** ✅ SUCCESS / ❌ FAILED / 🔄 ROLLED BACK
