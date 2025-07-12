# Kenyan Legal AI - API Documentation

## 🚀 Base URL
- **Production**: `https://your-app.onrender.com`
- **Development**: `http://localhost:8000`
- **Frontend Integration**: `https://www.legalizeme.site/counsel`

## 📋 API Overview

The Kenyan Legal AI API provides comprehensive legal assistance services specifically tailored for Kenyan jurisdiction. It features intelligent orchestration, RAG-powered responses, and fallback model systems.

### Key Features
- **Claude 4 via AWS Bedrock** - Primary AI model with intelligent fallbacks
- **RAG-Enhanced Responses** - Context-aware legal document retrieval
- **Modular Orchestration** - Dynamic intelligence enhancement
- **Security & Rate Limiting** - Production-grade security measures
- **Kenyan Legal Specialization** - Focused on Kenyan law and jurisdiction

## 🔓 Public Service Layer

### No Authentication Required
All endpoints are now **public** and do not require authentication. Counsel AI functions as a service layer that can be called directly by frontend applications.

### Optional User Context
You can optionally provide user context in request bodies for tracking and personalization:

```json
{
  "query": "Your legal question",
  "user_context": {
    "user_id": "user-123",
    "email": "user@example.com",
    "session_id": "session-456"
  }
}
```

## 📊 System Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-08T17:00:00Z",
  "version": "2.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "ai_models": "operational"
  }
}
```

### System Metrics
```http
GET /metrics
```

**Response:**
```json
{
  "timestamp": 1720454400.0,
  "environment": "production",
  "version": "2.0.0",
  "intelligence_enhancer": {
    "total_enhancements": 1250,
    "cache_hit_rate": 0.75,
    "avg_enhancement_time": 0.85
  },
  "rate_limiter": {
    "rules_count": 5,
    "cache_size": 150
  }
}
```

### Root Information
```http
GET /
```

**Response:**
```json
{
  "message": "Counsel AI Backend is running",
  "version": "2.0.0",
  "status": "healthy",
  "environment": "production",
  "features": [
    "AI-powered legal query answering",
    "Legal document generation",
    "RAG-enabled search with multiple strategies",
    "Multi-model AI integration with intelligent fallbacks",
    "Kenyan jurisdiction specialization"
  ],
  "orchestration": {
    "intelligence_enhancement": true,
    "rag_orchestration": true,
    "prompt_engineering": true,
    "adapters": true
  }
}
```

## 🤖 AI Counsel Endpoints

### Legal Query Processing
```http
POST /counsel/query
Content-Type: application/json

{
  "query": "How do I register a company in Kenya?",
  "context": {
    "user_type": "entrepreneur",
    "legal_area": "corporate_law",
    "urgency": "normal"
  },
  "enhancement_config": {
    "enable_rag": true,
    "enable_prompt_engineering": true,
    "retrieval_strategy": "hybrid"
  },
  "user_context": {
    "user_id": "user-123",
    "email": "user@example.com"
  }
}
```

**Response:**
```json
{
  "response": "To register a company in Kenya under the Companies Act 2015, you need to...",
  "sources": [
    {
      "title": "Companies Act 2015 - Registration Requirements",
      "relevance_score": 0.95,
      "url": "https://kenyalaw.org/companies-act-2015"
    }
  ],
  "metadata": {
    "model_used": "claude-sonnet-4",
    "enhancement_applied": true,
    "processing_time": 2.3,
    "confidence_score": 0.92
  }
}
```

### Legal Document Generation
```http
POST /counsel/generate-document
Content-Type: application/json
# No authentication required

{
  "document_type": "contract",
  "parameters": {
    "parties": [
      {"name": "John Doe", "role": "buyer"},
      {"name": "Jane Smith", "role": "seller"}
    ],
    "subject_matter": "Sale of land in Nairobi",
    "consideration": "KES 5,000,000"
  },
  "template_options": {
    "include_signatures": true,
    "include_witness_section": true,
    "legal_compliance": "kenyan_law"
  }
}
```

**Response:**
```json
{
  "document": {
    "title": "Sale Agreement - Land Purchase",
    "content": "SALE AGREEMENT\n\nThis Agreement is made this __ day of __, 2025...",
    "format": "legal_document",
    "compliance_check": "passed"
  },
  "metadata": {
    "generated_at": "2025-07-08T17:00:00Z",
    "template_used": "kenyan_sale_agreement",
    "legal_review_required": true
  }
}
```

## 🔍 Document Search & Retrieval

### Search Legal Documents
```http
GET /documents/search?q=employment+termination&limit=10&source=kenyan_law
# No authentication required
```

**Response:**
```json
{
  "results": [
    {
      "id": "doc_001",
      "title": "Employment Act 2007 - Termination Procedures",
      "excerpt": "An employer may terminate employment by giving notice...",
      "relevance_score": 0.89,
      "source": "kenyan_law",
      "url": "https://kenyalaw.org/employment-act-2007"
    }
  ],
  "total_results": 25,
  "search_metadata": {
    "query_processed": "employment termination Kenya",
    "search_strategy": "hybrid",
    "processing_time": 0.45
  }
}
```

### Upload Document for Analysis
```http
POST /documents/upload
Content-Type: multipart/form-data
# No authentication required

file: <legal_document.pdf>
analysis_type: "compliance_check"
jurisdiction: "kenya"
user_context: {"user_id": "user-123"}
```

**Response:**
```json
{
  "document_id": "upload_12345",
  "analysis": {
    "compliance_status": "compliant",
    "issues_found": [],
    "recommendations": [
      "Consider adding witness signatures",
      "Verify current statutory requirements"
    ]
  },
  "metadata": {
    "file_size": 245760,
    "pages": 5,
    "processed_at": "2025-07-08T17:00:00Z"
  }
}
```

## 🔧 Model Management (Public Access)

### Model Status
```http
GET /models/status
# No authentication required
```

**Response:**
```json
{
  "models": {
    "claude-sonnet-4": {
      "status": "operational",
      "health_score": 0.98,
      "last_check": "2025-07-08T16:59:00Z",
      "response_time_avg": 1.2
    },
    "hunyuan": {
      "status": "fallback",
      "health_score": 0.85,
      "last_check": "2025-07-08T16:59:00Z"
    }
  },
  "fallback_chain": ["claude-sonnet-4", "hunyuan", "minimax-01"]
}
```

### Trigger Model Fallback Test
```http
POST /models/test-fallback
Content-Type: application/json
# No authentication required

{
  "test_query": "Test fallback system",
  "simulate_failure": "claude-sonnet-4"
}
```

**Response:**
```json
{
  "test_results": {
    "primary_model_failed": true,
    "fallback_model_used": "hunyuan",
    "response_generated": true,
    "fallback_time": 0.3,
    "total_time": 2.1
  },
  "log_trace": "2025-07-08T17:00:00Z - Claude 4 failed, switching to Hunyuan..."
}
```

## 📈 Rate Limits

| Endpoint | Limit | Window | Notes |
|----------|-------|--------|-------|
| `/counsel/query` | 50 requests | 1 hour | Premium users: 200/hour |
| `/counsel/generate-document` | 20 requests | 1 hour | Premium users: 100/hour |
| `/documents/search` | 100 requests | 1 hour | |
| `/models/*` | 10 requests | 1 hour | Admin only |
| General API | 100 requests | 1 hour | |

## ❌ Error Responses

### Standard Error Format
```json
{
  "error": "error_type",
  "message": "Human readable error message",
  "details": {
    "code": "SPECIFIC_ERROR_CODE",
    "timestamp": "2025-07-08T17:00:00Z",
    "request_id": "req_12345"
  }
}
```

### Common Error Codes

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 400 | `validation_error` | Invalid request parameters |
| 401 | `authentication_required` | Missing or invalid token |
| 403 | `insufficient_permissions` | User lacks required permissions |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `internal_error` | Server error |
| 503 | `service_unavailable` | AI models temporarily unavailable |

## 🔌 Frontend Integration

### JavaScript Example
```javascript
// Initialize API client
const API_BASE = 'https://your-app.onrender.com';
const token = localStorage.getItem('auth_token');

// Query legal advice
async function queryLegalAdvice(question) {
  const response = await fetch(`${API_BASE}/counsel/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // No authentication required
    },
    body: JSON.stringify({
      query: question,
      context: {
        user_type: 'general_public',
        legal_area: 'general'
      }
    })
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return await response.json();
}

// Usage
queryLegalAdvice("How do I file for divorce in Kenya?")
  .then(result => {
    console.log('Legal advice:', result.response);
    console.log('Sources:', result.sources);
  })
  .catch(error => {
    console.error('Error:', error);
  });
```

### React Hook Example
```javascript
import { useState, useEffect } from 'react';

function useLegalQuery() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const queryLegal = async (question, context = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/counsel/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // No authentication required
        },
        body: JSON.stringify({ query: question, context })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };
  
  return { queryLegal, loading, error };
}
```

## 📝 Testing with Postman

### Collection Import
Import the API collection using this OpenAPI specification:
```
GET /openapi.json
```

### Environment Variables
```json
{
  "base_url": "https://your-app.onrender.com",
  "auth_token": "{{auth_token}}",
  "api_version": "v1"
}
```

## 🔧 Development & Testing

### Local Development
```bash
# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access API documentation
http://localhost:8000/docs
```

### Health Check Script
```bash
curl -X GET "https://your-app.onrender.com/health" \
  -H "accept: application/json"
```

## 📞 Support

For API support and integration assistance:
- **Documentation**: `/docs` (Swagger UI)
- **Health Status**: `/health`
- **System Metrics**: `/metrics`

---

**Note**: This API is specifically designed for Kenyan legal jurisdiction. All responses and document generation are tailored to Kenyan law and legal practices.
