# Counsel AI - Complete API Documentation
**Production-Ready Kenyan Legal AI System**

[![API Status](https://img.shields.io/badge/API-100%25%20Operational-brightgreen)](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health)
[![Endpoints](https://img.shields.io/badge/Endpoints-24%2F24%20Working-success)](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs)
[![AWS](https://img.shields.io/badge/AWS-ECS%20Fargate-orange)](https://console.aws.amazon.com/ecs/)
[![Models](https://img.shields.io/badge/AI-Claude%20%7C%20Mistral-blue)](https://console.aws.amazon.com/bedrock/)

---

## 🚀 **Production Environment**

| Component | Details |
|-----------|---------|
| **Base URL** | `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com` |
| **Region** | `us-east-1` |
| **Infrastructure** | AWS ECS Fargate + RDS PostgreSQL + Bedrock |
| **Status** | ✅ **100% Operational** (24/24 endpoints) |
| **Documentation** | [Interactive Docs](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs) |

---

## 📋 **Quick Reference**

### **Core Endpoints**
- **Legal Query**: `POST /api/v1/counsel/query`
- **Direct Query**: `POST /api/v1/counsel/query-direct`
- **Agent Query**: `POST /api/v1/agents/query`
- **Document Search**: `POST /api/v1/documents/search`
- **Health Check**: `GET /health`

### **Authentication**
- **Type**: Public API (No authentication required)
- **Rate Limiting**: Implemented via AWS ALB
- **CORS**: Configured for frontend integration

---

## 🏥 **Health & Monitoring Endpoints**

### 1. Root Endpoint
```http
GET /
```
**Response**: Basic API information and status

### 2. Health Check
```http
GET /health
```
**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-17T10:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "ai_models": "operational",
    "token_tracking": "active"
  }
}
```

### 3. Readiness Check
```http
GET /health/ready
```
**Response**: Service readiness status

### 4. Liveness Check
```http
GET /health/live
```
**Response**: Service liveness status

### 5. Version Information
```http
GET /health/version
```
**Response**: Detailed version and build information

### 6. System Metrics
```http
GET /metrics
```
**Response**: System performance metrics

### 7. API Documentation
```http
GET /docs
```
**Response**: Interactive Swagger/OpenAPI documentation

---

## ⚖️ **Legal Counsel Endpoints**

### 1. Legal Query (Enhanced)
```http
POST /api/v1/counsel/query
```

**Request Body**:
```json
{
  "query": "What are the employment termination procedures in Kenya?",
  "context": {
    "jurisdiction": "Kenya",
    "legal_area": "employment_law"
  },
  "query_type": "legal_query",
  "use_enhanced_rag": true,
  "agent_mode": false,
  "user_context": {
    "user_id": "optional_user_id"
  },
  "conversation_id": "optional_conversation_id",
  "message_history": [
    {
      "role": "user",
      "content": "Previous message"
    }
  ]
}
```

**Response**:
```json
{
  "query_id": "query_1752718169",
  "answer": "In Kenya, employment termination procedures are governed by the Employment Act 2007...",
  "relevant_documents": [],
  "confidence": 0.85,
  "model_used": "claude-sonnet-4",
  "processing_time": 12.5,
  "timestamp": "2025-01-17T10:30:00Z",
  "enhanced": true,
  "sources": [
    {
      "title": "Employment Act 2007",
      "url": "https://kenyalaw.org/...",
      "relevance": 0.92
    }
  ],
  "retrieval_strategy": "enhanced_rag",
  "agent_mode": false,
  "research_strategy": null,
  "reasoning_chain": [
    "Analyzed Employment Act 2007",
    "Cross-referenced with Labour Relations Act",
    "Identified key termination procedures"
  ],
  "follow_up_suggestions": [
    "What are the notice periods for different employment categories?",
    "What constitutes fair vs unfair dismissal in Kenya?"
  ],
  "related_queries": [
    "Employment contract requirements in Kenya",
    "Severance pay calculations under Kenyan law"
  ]
}
```

### 2. Direct Query (Simplified)
```http
POST /api/v1/counsel/query-direct
```

**Request Body**:
```json
{
  "query": "What is the minimum wage in Kenya?",
  "model_preference": "claude-sonnet-4"
}
```

**Response**:
```json
{
  "response_text": "The minimum wage in Kenya varies by sector and region...",
  "model_used": "claude-sonnet-4",
  "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
  "latency_ms": 3250.5,
  "success": true,
  "timestamp": "2025-01-17T10:30:00Z"
}
```

### 3. Query Suggestions
```http
GET /api/v1/counsel/suggestions?query=employment&limit=5
```

**Response**:
```json
{
  "suggestions": [
    "What are the legal requirements for employment in Kenya?",
    "How to comply with employment regulations in Kenya?",
    "What are the penalties for non-compliance with employment?",
    "What documents are needed for employment in Kenya?",
    "What are the procedures for employment under Kenyan law?"
  ],
  "query": "employment",
  "total_suggestions": 5
}
```

### 4. List Conversations
```http
GET /api/v1/counsel/conversations
```

**Response**:
```json
{
  "conversations": [
    {
      "conversation_id": "conv_123",
      "title": "Employment Law Consultation",
      "created_at": "2025-01-17T09:00:00Z",
      "message_count": 5,
      "last_activity": "2025-01-17T10:30:00Z"
    }
  ],
  "total": 1
}
```

### 5. Create Conversation
```http
POST /api/v1/counsel/conversations
```

**Request Body**:
```json
{
  "title": "New Legal Consultation",
  "description": "Discussion about contract law"
}
```

**Response**:
```json
{
  "conversation_id": "conv_456",
  "title": "New Legal Consultation",
  "created_at": "2025-01-17T10:30:00Z",
  "status": "active"
}
```

---

## 🤖 **Simple Agent Endpoints**

### 1. Agent Health Check
```http
GET /api/v1/agents/health
```

**Response**:
```json
{
  "status": "healthy",
  "agent_type": "legal_research",
  "models_available": ["claude-sonnet-4", "claude-3-7", "mistral-large"],
  "last_health_check": "2025-01-17T10:30:00Z"
}
```

### 2. Agent Query
```http
POST /api/v1/agents/query
```

**Request Body**:
```json
{
  "query": "Analyze the constitutional provisions on freedom of expression in Kenya",
  "strategy": "comprehensive",
  "model_preference": "claude-sonnet-4"
}
```

**Response**:
```json
{
  "answer": "The Constitution of Kenya 2010, Article 33, guarantees freedom of expression...",
  "confidence": 0.92,
  "model_used": "claude-sonnet-4",
  "processing_time_ms": 8500,
  "timestamp": "2025-01-17T10:30:00Z",
  "strategy_used": "comprehensive",
  "citations": [
    {
      "source": "Constitution of Kenya 2010",
      "article": "Article 33",
      "relevance": 0.95
    }
  ],
  "follow_up_suggestions": [
    "What are the limitations on freedom of expression?",
    "How does this relate to media freedom in Kenya?"
  ],
  "related_queries": [
    "Freedom of assembly provisions in Kenya",
    "Defamation laws under Kenyan constitution"
  ]
}
```

---

## 📄 **Document Processing Endpoints**

### 1. Document Search
```http
POST /api/v1/documents/search
```

**Request Body**:
```json
{
  "query": "employment contract templates",
  "limit": 10,
  "filters": {
    "document_type": "template",
    "legal_area": "employment"
  }
}
```

**Response**:
```json
{
  "documents": [
    {
      "document_id": "doc_123",
      "title": "Standard Employment Contract Template",
      "type": "template",
      "relevance_score": 0.89,
      "summary": "Comprehensive employment contract template compliant with Kenyan law",
      "url": "https://example.com/doc_123",
      "legal_area": "employment_law"
    }
  ],
  "total_results": 1,
  "query": "employment contract templates",
  "processing_time_ms": 450
}
```

### 2. Document Analysis
```http
GET /api/v1/documents/{document_id}/analysis
```

**Response**:
```json
{
  "document_id": 123,
  "analysis": {
    "document_type": "legal_document",
    "summary": "This document contains legal provisions and requirements for employment contracts in Kenya.",
    "key_points": [
      "Contains legal obligations for employers",
      "Includes compliance requirements under Employment Act 2007",
      "References constitutional provisions on worker rights"
    ],
    "risk_assessment": "Medium risk - requires legal review for specific circumstances",
    "compliance_score": 0.75
  },
  "confidence": 0.8,
  "model_used": "claude-sonnet-4",
  "timestamp": "2025-01-17T10:30:00Z",
  "status": "completed"
}
```

---

## 🎯 **Token Tracking Endpoints**

### 1. Token Tracking Health
```http
GET /api/v1/tokens/health
```

**Response**:
```json
{
  "status": "healthy",
  "tracking_active": true,
  "database_connected": true,
  "last_cleanup": "2025-01-17T09:00:00Z"
}
```

### 2. Token Status
```http
GET /api/v1/tokens/status/{user_id}
```

**Response**:
```json
{
  "user_id": "test-user",
  "current_usage": {
    "daily_tokens": 1250,
    "monthly_tokens": 15000,
    "daily_limit": 10000,
    "monthly_limit": 100000
  },
  "remaining": {
    "daily": 8750,
    "monthly": 85000
  },
  "reset_times": {
    "daily_reset": "2025-01-18T00:00:00Z",
    "monthly_reset": "2025-02-01T00:00:00Z"
  },
  "status": "active"
}
```

### 3. Token Check
```http
POST /api/v1/tokens/check
```

**Request Body**:
```json
{
  "userId": "test-user",
  "estimatedTokens": 500,
  "requestType": "chat_completion"
}
```

**Response**:
```json
{
  "allowed": true,
  "remaining_tokens": 8500,
  "estimated_cost": 0.0075,
  "rate_limit_status": "ok"
}
```

### 4. Token Tracking
```http
POST /api/v1/tokens/track
```

**Request Body**:
```json
{
  "userId": "test-user",
  "tokensUsed": 450,
  "requestType": "chat_completion",
  "modelUsed": "claude-sonnet-4",
  "cost": 0.00675
}
```

**Response**:
```json
{
  "tracked": true,
  "new_total": 1700,
  "remaining_daily": 8300,
  "timestamp": "2025-01-17T10:30:00Z"
}
```

### 5. Token History
```http
GET /api/v1/tokens/history/{user_id}?limit=10&offset=0
```

**Response**:
```json
{
  "user_id": "test-user",
  "history": [
    {
      "timestamp": "2025-01-17T10:30:00Z",
      "tokens_used": 450,
      "request_type": "chat_completion",
      "model_used": "claude-sonnet-4",
      "cost": 0.00675
    }
  ],
  "total_records": 1,
  "pagination": {
    "limit": 10,
    "offset": 0,
    "has_more": false
  }
}
```

---

## 🧠 **Model Management Endpoints**

### 1. Model Configuration
```http
GET /api/v1/models/config
```

**Response**:
```json
{
  "models": {
    "claude-sonnet-4": {
      "name": "claude-sonnet-4",
      "priority": 1,
      "timeout": 45.0,
      "max_error_rate": 0.05,
      "requires_gpu": false,
      "memory_requirement": "2GB",
      "fine_tuned": false,
      "model_path": "us.anthropic.claude-sonnet-4-20250514-v1:0"
    },
    "claude-3-7": {
      "name": "claude-3-7",
      "priority": 2,
      "timeout": 35.0,
      "max_error_rate": 0.05,
      "requires_gpu": false,
      "memory_requirement": "1.5GB",
      "fine_tuned": false,
      "model_path": "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    },
    "mistral-large": {
      "name": "mistral-large",
      "priority": 3,
      "timeout": 40.0,
      "max_error_rate": 0.05,
      "requires_gpu": false,
      "memory_requirement": "2GB",
      "fine_tuned": false,
      "model_path": "mistral.mistral-large-2402-v1:0"
    }
  },
  "timestamp": "2025-01-17T10:30:00Z"
}
```

---

## 🎭 **Multimodal Processing Endpoints**

### 1. Multimodal Health
```http
GET /api/v1/multimodal/health
```

**Response**:
```json
{
  "status": "healthy",
  "processors": {
    "pdf": "available",
    "image": "available",
    "text": "available"
  },
  "models": {
    "vision": "claude-sonnet-4",
    "ocr": "available"
  }
}
```

### 2. Multimodal Capabilities
```http
GET /api/v1/multimodal/capabilities
```

**Response**:
```json
{
  "supported_formats": {
    "documents": ["pdf", "docx", "txt"],
    "images": ["jpg", "jpeg", "png", "gif"],
    "max_file_size": "10MB"
  },
  "processing_types": [
    "document_analysis",
    "image_to_text",
    "legal_document_extraction",
    "contract_analysis"
  ],
  "ai_models": {
    "vision": "claude-sonnet-4",
    "text_processing": "claude-sonnet-4",
    "ocr": "aws-textract"
  }
}
```

---

## 🔧 **Error Handling**

### **Standard Error Response Format**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request format",
    "details": "Query field is required",
    "timestamp": "2025-01-17T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### **HTTP Status Codes**
| Code | Description | Common Causes |
|------|-------------|---------------|
| `200` | Success | Request processed successfully |
| `400` | Bad Request | Invalid request format or parameters |
| `404` | Not Found | Endpoint or resource not found |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | AI service error or system issue |
| `503` | Service Unavailable | Temporary service outage |

---

## 🚀 **Integration Examples**

### **JavaScript/TypeScript**
```javascript
class CounselAIClient {
  constructor(baseUrl = 'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com') {
    this.baseUrl = baseUrl;
  }

  async queryLegal(query, options = {}) {
    const response = await fetch(`${this.baseUrl}/api/v1/counsel/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'LegalizeMe-Frontend/1.0'
      },
      body: JSON.stringify({
        query,
        use_enhanced_rag: options.enhanced || true,
        agent_mode: options.agentMode || false,
        ...options
      })
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  }

  async queryDirect(query, modelPreference = 'claude-sonnet-4') {
    const response = await fetch(`${this.baseUrl}/api/v1/counsel/query-direct`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, model_preference: modelPreference })
    });

    return await response.json();
  }
}

// Usage
const client = new CounselAIClient();
const result = await client.queryLegal('What are employment rights in Kenya?');
```

### **Python**
```python
import requests
import json

class CounselAIClient:
    def __init__(self, base_url='http://counsel-alb-694525771.us-east-1.elb.amazonaws.com'):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CounselAI-Python-Client/1.0'
        })

    def query_legal(self, query, **options):
        payload = {
            'query': query,
            'use_enhanced_rag': options.get('enhanced', True),
            'agent_mode': options.get('agent_mode', False),
            **options
        }

        response = self.session.post(
            f'{self.base_url}/api/v1/counsel/query',
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def query_direct(self, query, model_preference='claude-sonnet-4'):
        payload = {
            'query': query,
            'model_preference': model_preference
        }

        response = self.session.post(
            f'{self.base_url}/api/v1/counsel/query-direct',
            json=payload
        )
        response.raise_for_status()
        return response.json()

# Usage
client = CounselAIClient()
result = client.query_legal('What are employment rights in Kenya?')
```

### **cURL Examples**
```bash
# Legal Query
curl -X POST "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/api/v1/counsel/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the basic employment rights in Kenya?",
    "use_enhanced_rag": true,
    "agent_mode": false
  }'

# Direct Query
curl -X POST "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/api/v1/counsel/query-direct" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the minimum wage in Kenya?",
    "model_preference": "claude-sonnet-4"
  }'

# Health Check
curl -X GET "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health"
```

---

## 📊 **Performance & Monitoring**

### **Response Times**
| Endpoint Type | Average Response Time | Timeout |
|---------------|----------------------|---------|
| Health Checks | 50-200ms | 5s |
| Direct Queries | 3-8 seconds | 30s |
| Enhanced Queries | 8-15 seconds | 45s |
| Document Processing | 2-10 seconds | 30s |
| Token Operations | 100-500ms | 10s |

### **Rate Limits**
- **Per IP**: 100 requests/minute
- **Per User**: 1000 requests/hour
- **Burst**: 10 requests/second

### **Monitoring URLs**
- **Health Dashboard**: `GET /health`
- **Metrics**: `GET /metrics`
- **API Docs**: `GET /docs`
- **AWS CloudWatch**: [Logs](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Fecs$252Fcounsel-task)

---

## 🔐 **Security & Compliance**

### **Security Headers**
- `Content-Security-Policy`: Strict CSP implementation
- `X-Frame-Options`: DENY
- `X-Content-Type-Options`: nosniff
- `Strict-Transport-Security`: HTTPS enforcement

### **Data Privacy**
- **No PII Storage**: Queries are processed but not permanently stored
- **Encryption**: All data encrypted in transit and at rest
- **Compliance**: GDPR-ready, data minimization principles

### **Legal Disclaimer**
All responses are for informational purposes only and do not constitute legal advice. Users should consult qualified legal professionals for specific legal matters.

---

## 📞 **Support & Resources**

### **Technical Support**
- **API Status**: [Health Endpoint](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health)
- **Interactive Docs**: [Swagger UI](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs)
- **AWS Console**: [ECS Service](https://us-east-1.console.aws.amazon.com/ecs/v2/clusters/counsel-cluster/services)

### **Development Resources**
- **OpenAPI Schema**: `GET /openapi.json`
- **Postman Collection**: Available on request
- **SDK Examples**: See integration examples above

---

**© 2025 Counsel AI - Kenyan Legal Intelligence System**
**Version**: 1.0.0 | **Last Updated**: January 17, 2025 | **Status**: ✅ Production Ready
```
