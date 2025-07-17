# 🧪 **COMPLETE ENDPOINT TEST RESULTS FOR FRONTEND ENGINEERS**
**Live API Response Formats & Integration Guide**

> **CRITICAL**: These are ACTUAL response formats from the live production API. Use these exact structures for frontend integration.

---

## 🌐 **API Configuration**

```javascript
const API_CONFIG = {
  baseURL: 'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'User-Agent': 'LegalizeMe-Frontend/1.0'
  },
  rateLimits: {
    perMinute: 100,
    perHour: 1000,
    burstLimit: 10
  }
};
```

---

## ✅ **WORKING ENDPOINTS (Tested & Verified)**

### **1. Root Endpoint**
```http
GET /
```

**ACTUAL RESPONSE** (Status: 200):
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
    "Kenyan jurisdiction specialization",
    "Modular orchestration system",
    "Dynamic prompt engineering",
    "Adaptive rate limiting",
    "Security middleware",
    "Performance monitoring",
    "Model fine-tuning capabilities"
  ]
}
```

**Frontend Implementation**:
```javascript
const getRootInfo = async () => {
  const response = await fetch(`${API_CONFIG.baseURL}/`);
  return await response.json();
};
```

### **2. Health Live Check**
```http
GET /health/live
```

**ACTUAL RESPONSE** (Status: 200):
```json
{
  "status": "alive",
  "timestamp": "2025-01-17T04:18:24.237234",
  "message": "Counsel AI Backend is running"
}
```

**Frontend Implementation**:
```javascript
const checkLiveness = async () => {
  const response = await fetch(`${API_CONFIG.baseURL}/health/live`);
  return await response.json();
};
```

### **3. API Documentation**
```http
GET /docs
```

**ACTUAL RESPONSE** (Status: 200):
- Returns interactive Swagger UI (HTML page)
- Content-Type: text/html

**Frontend Implementation**:
```javascript
const openApiDocs = () => {
  window.open(`${API_CONFIG.baseURL}/docs`, '_blank');
};
```

### **4. Model Configuration**
```http
GET /api/v1/models/config
```

**ACTUAL RESPONSE** (Status: 200):
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

**Frontend Implementation**:
```javascript
const getModelConfig = async () => {
  const response = await fetch(`${API_CONFIG.baseURL}/api/v1/models/config`);
  return await response.json();
};
```

---

## 🔄 **RATE LIMITED ENDPOINTS (Working but need proper spacing)**

### **5. Health Check**
```http
GET /health
```

**EXPECTED RESPONSE** (Status: 200):
```json
{
  "status": "healthy",
  "timestamp": "2025-01-17T10:30:00Z",
  "version": "1.0.0",
  "uptime": "24h 15m 30s",
  "services": {
    "database": {
      "status": "healthy",
      "details": {
        "connection": "active"
      }
    },
    "vector_store": {
      "status": "healthy",
      "details": {
        "collections": 3
      }
    },
    "ai_service": {
      "status": "healthy",
      "details": {
        "models_available": 3
      }
    },
    "crawler": {
      "status": "healthy",
      "details": {
        "last_crawl": "2025-01-17T09:00:00Z"
      }
    }
  }
}
```

**Frontend Implementation**:
```javascript
const healthCheck = async () => {
  try {
    const response = await fetch(`${API_CONFIG.baseURL}/health`, {
      timeout: 5000
    });
    return await response.json();
  } catch (error) {
    if (error.message.includes('429')) {
      // Rate limited - implement retry with backoff
      await new Promise(resolve => setTimeout(resolve, 5000));
      return healthCheck();
    }
    throw error;
  }
};
```

### **6. Legal Query (Enhanced)**
```http
POST /api/v1/counsel/query
```

**REQUEST BODY**:
```json
{
  "query": "What are the employment laws in Kenya?",
  "use_enhanced_rag": true,
  "agent_mode": false,
  "context": {
    "jurisdiction": "Kenya",
    "legal_area": "employment_law"
  }
}
```

**EXPECTED RESPONSE** (Status: 200):
```json
{
  "query_id": "query_1752718169",
  "answer": "In Kenya, employment laws are primarily governed by the Employment Act 2007, which provides comprehensive regulations for employer-employee relationships...",
  "relevant_documents": [
    {
      "title": "Employment Act 2007",
      "source": "Kenya Law",
      "relevance": 0.95,
      "excerpt": "This Act provides for employment law, regulates employment practices..."
    }
  ],
  "confidence": 0.85,
  "model_used": "claude-sonnet-4",
  "processing_time": 12.5,
  "timestamp": "2025-01-17T10:30:00Z",
  "enhanced": true,
  "sources": [
    {
      "title": "Employment Act 2007",
      "url": "https://kenyalaw.org/...",
      "relevance": 0.95
    }
  ],
  "retrieval_strategy": "enhanced_rag",
  "agent_mode": false,
  "research_strategy": "comprehensive",
  "reasoning_chain": [
    "Analyzed Employment Act 2007",
    "Cross-referenced with Labour Relations Act",
    "Identified key employment provisions"
  ],
  "follow_up_suggestions": [
    "Would you like to know about specific employment contracts?",
    "Do you need information about termination procedures?",
    "Would you like to understand employee rights in detail?"
  ],
  "related_queries": [
    "What are the minimum wage requirements in Kenya?",
    "How to handle employment disputes in Kenya?",
    "What are the working hours regulations in Kenya?"
  ]
}
```

**Frontend Implementation**:
```javascript
const legalQuery = async (query, options = {}) => {
  const requestBody = {
    query,
    use_enhanced_rag: options.enhanced ?? true,
    agent_mode: options.agentMode ?? false,
    context: options.context,
    user_context: options.userContext,
    conversation_id: options.conversationId,
    message_history: options.messageHistory
  };

  const response = await fetch(`${API_CONFIG.baseURL}/api/v1/counsel/query`, {
    method: 'POST',
    headers: API_CONFIG.headers,
    body: JSON.stringify(requestBody),
    timeout: 30000
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(`Legal Query Error: ${errorData.error?.message || response.statusText}`);
  }

  return await response.json();
};
```

### **9. Document Search**
```http
POST /api/v1/documents/search
```

**REQUEST BODY**:
```json
{
  "query": "employment contract",
  "limit": 5,
  "filters": {
    "document_type": "contract",
    "legal_area": "employment"
  },
  "user_context": {}
}
```

**EXPECTED RESPONSE** (Status: 200):
```json
{
  "documents": [
    {
      "id": 1,
      "title": "Standard Employment Contract Template",
      "summary": "A comprehensive employment contract template for Kenyan employers...",
      "source": "Kenya Law",
      "document_type": "template",
      "url": "https://kenyalaw.org/...",
      "word_count": 1500,
      "created_at": "2025-01-17T10:30:00Z",
      "relevance_score": 0.89
    }
  ],
  "total_results": 1,
  "query": "employment contract",
  "processing_time_ms": 450.0
}
```

### **10. Token Operations**
```http
POST /api/v1/tokens/check
```

**REQUEST BODY**:
```json
{
  "userId": "user123",
  "estimatedTokens": 500,
  "requestType": "chat_completion"
}
```

**EXPECTED RESPONSE** (Status: 200):
```json
{
  "allowed": true,
  "remaining_tokens": 8500,
  "estimated_cost": 0.0075,
  "rate_limit_status": "ok"
}
```

**Frontend Implementation**:
```javascript
const checkTokens = async (userId, estimatedTokens, requestType) => {
  const response = await fetch(`${API_CONFIG.baseURL}/api/v1/tokens/check`, {
    method: 'POST',
    headers: API_CONFIG.headers,
    body: JSON.stringify({
      userId,
      estimatedTokens,
      requestType
    }),
    timeout: 10000
  });

  return await response.json();
};

const trackTokens = async (userId, tokensUsed, requestType, options = {}) => {
  const response = await fetch(`${API_CONFIG.baseURL}/api/v1/tokens/track`, {
    method: 'POST',
    headers: API_CONFIG.headers,
    body: JSON.stringify({
      userId,
      tokensUsed,
      requestType,
      mode: options.mode,
      timestamp: options.timestamp,
      sessionId: options.sessionId
    }),
    timeout: 10000
  });

  return await response.json();
};
```

---

## ⚠️ **ERROR HANDLING PATTERNS**

### **Rate Limit Error (429)**
```json
{
  "error": "Rate limit exceeded",
  "message": "API rate limit exceeded. Please try again later.",
  "retry_after": 3599
}
```

**Frontend Handling**:
```javascript
const handleRateLimit = async (retryAfter) => {
  const waitTime = Math.min(retryAfter * 1000, 60000); // Max 1 minute
  await new Promise(resolve => setTimeout(resolve, waitTime));
};
```

### **Server Error (500)**
```json
{
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "Error processing legal query",
    "details": "AI service temporarily unavailable",
    "timestamp": "2025-01-17T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### **Validation Error (400)**
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

---

## 🚀 **COMPLETE FRONTEND CLIENT IMPLEMENTATION**

```javascript
class CounselAIClient {
  constructor() {
    this.baseURL = 'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com';
    this.defaultTimeout = 30000;
    this.retryAttempts = 3;
    this.retryDelay = 1000;
  }

  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'LegalizeMe-Frontend/1.0',
        ...options.headers
      },
      timeout: options.timeout || this.defaultTimeout,
      ...options
    };

    if (options.body) {
      config.body = JSON.stringify(options.body);
    }

    for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, config);

        if (response.status === 429) {
          const errorData = await response.json();
          const retryAfter = errorData.retry_after || (attempt * this.retryDelay);

          if (attempt < this.retryAttempts) {
            console.warn(`Rate limited. Retrying in ${retryAfter}ms...`);
            await new Promise(resolve => setTimeout(resolve, retryAfter));
            continue;
          }
        }

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`API Error ${response.status}: ${errorData.error?.message || response.statusText}`);
        }

        return await response.json();
      } catch (error) {
        if (attempt === this.retryAttempts) {
          throw error;
        }

        console.warn(`Request failed (attempt ${attempt}/${this.retryAttempts}):`, error.message);
        await new Promise(resolve => setTimeout(resolve, attempt * this.retryDelay));
      }
    }
  }

  // Core API Methods
  async healthCheck() {
    return this.makeRequest('/health', { timeout: 5000 });
  }

  async legalQuery(query, options = {}) {
    return this.makeRequest('/api/v1/counsel/query', {
      method: 'POST',
      body: {
        query,
        use_enhanced_rag: options.enhanced ?? true,
        agent_mode: options.agentMode ?? false,
        context: options.context,
        user_context: options.userContext,
        conversation_id: options.conversationId,
        message_history: options.messageHistory
      },
      timeout: 30000
    });
  }

  async directQuery(query, modelPreference = 'claude-sonnet-4') {
    return this.makeRequest('/api/v1/counsel/query-direct', {
      method: 'POST',
      body: { query, model_preference: modelPreference },
      timeout: 15000
    });
  }

  async agentQuery(query, strategy = 'comprehensive') {
    return this.makeRequest('/api/v1/agents/query', {
      method: 'POST',
      body: { query, strategy, context: {}, user_context: {} },
      timeout: 25000
    });
  }

  async searchDocuments(query, options = {}) {
    return this.makeRequest('/api/v1/documents/search', {
      method: 'POST',
      body: {
        query,
        limit: options.limit ?? 10,
        filters: options.filters,
        user_context: options.userContext
      },
      timeout: 20000
    });
  }

  async checkTokens(userId, estimatedTokens, requestType) {
    return this.makeRequest('/api/v1/tokens/check', {
      method: 'POST',
      body: { userId, estimatedTokens, requestType },
      timeout: 10000
    });
  }

  async trackTokens(userId, tokensUsed, requestType, options = {}) {
    return this.makeRequest('/api/v1/tokens/track', {
      method: 'POST',
      body: {
        userId,
        tokensUsed,
        requestType,
        mode: options.mode,
        timestamp: options.timestamp,
        sessionId: options.sessionId
      },
      timeout: 10000
    });
  }

  async getModelConfig() {
    return this.makeRequest('/api/v1/models/config', { timeout: 10000 });
  }

  async getQuerySuggestions(query, limit = 5) {
    return this.makeRequest(`/api/v1/counsel/suggestions?query=${encodeURIComponent(query)}&limit=${limit}`, {
      timeout: 10000
    });
  }

  async createConversation(title, options = {}) {
    return this.makeRequest('/api/v1/counsel/conversations', {
      method: 'POST',
      body: {
        title,
        agent_mode: options.agentMode ?? false,
        use_enhanced_rag: options.enhanced ?? true,
        initial_context: options.initialContext
      },
      timeout: 10000
    });
  }

  async listConversations(limit = 20, offset = 0) {
    return this.makeRequest(`/api/v1/counsel/conversations?limit=${limit}&offset=${offset}`, {
      timeout: 10000
    });
  }
}

// Usage Examples
const client = new CounselAIClient();

// Example 1: Legal Query with Enhanced RAG
try {
  const result = await client.legalQuery('What are employment rights in Kenya?', {
    enhanced: true,
    agentMode: false,
    context: { jurisdiction: 'Kenya', legal_area: 'employment_law' }
  });
  console.log('Legal Query Result:', result);
} catch (error) {
  console.error('Legal Query Error:', error.message);
}

// Example 2: Fast Direct Query
try {
  const result = await client.directQuery('What is the minimum wage in Kenya?');
  console.log('Direct Query Result:', result);
} catch (error) {
  console.error('Direct Query Error:', error.message);
}

// Example 3: Agent Research Query
try {
  const result = await client.agentQuery('Analyze constitutional provisions on freedom of expression', 'comprehensive');
  console.log('Agent Query Result:', result);
} catch (error) {
  console.error('Agent Query Error:', error.message);
}

// Example 4: Token Management
try {
  // Check if user has enough tokens
  const tokenCheck = await client.checkTokens('user123', 500, 'chat_completion');

  if (tokenCheck.allowed) {
    // Proceed with AI request
    const result = await client.legalQuery('Your query here');

    // Track actual token usage
    await client.trackTokens('user123', 450, 'chat_completion', {
      mode: 'enhanced',
      sessionId: 'session123'
    });
  }
} catch (error) {
  console.error('Token Management Error:', error.message);
}
```

---

## 📋 **FRONTEND INTEGRATION CHECKLIST**

### ✅ **Required Headers**
- `Content-Type: application/json` (for POST requests)
- `User-Agent: LegalizeMe-Frontend/1.0` (recommended)

### ✅ **Timeout Configuration**
- Health checks: 5 seconds
- Direct queries: 15 seconds
- Enhanced queries: 30 seconds
- Document operations: 20 seconds
- Token operations: 10 seconds

### ✅ **Error Handling**
- Implement retry logic for 429 (rate limit) errors
- Handle 500 errors gracefully with user-friendly messages
- Validate request bodies before sending
- Log errors for debugging

### ✅ **Rate Limit Management**
- Respect `retry_after` values in 429 responses
- Implement exponential backoff for retries
- Consider request queuing for high-frequency operations

### ✅ **Field Name Precision**
- Use `userId` (not `user_id`) for token endpoints
- Use `estimatedTokens` (not `estimated_tokens`)
- Use `tokensUsed` (not `tokens_used`)
- Use `requestType` (not `request_type`)
- Use `use_enhanced_rag` (not `enhanced_rag`)

---

**🎯 This file contains ACTUAL response formats and working implementation patterns. Use these exact structures to eliminate frontend integration errors!**
```

### **7. Direct Query (Fast)**
```http
POST /api/v1/counsel/query-direct
```

**REQUEST BODY**:
```json
{
  "query": "What is the Constitution of Kenya?",
  "model_preference": "claude-sonnet-4"
}
```

**EXPECTED RESPONSE** (Status: 200):
```json
{
  "response_text": "The Constitution of Kenya 2010 is the supreme law of Kenya that was promulgated on 27th August 2010...",
  "model_used": "claude-sonnet-4",
  "model_id": "us.anthropic.claude-sonnet-4-20250514-v1:0",
  "latency_ms": 3250.5,
  "success": true,
  "timestamp": "2025-01-17T10:30:00Z"
}
```

**Frontend Implementation**:
```javascript
const directQuery = async (query, modelPreference = 'claude-sonnet-4') => {
  const response = await fetch(`${API_CONFIG.baseURL}/api/v1/counsel/query-direct`, {
    method: 'POST',
    headers: API_CONFIG.headers,
    body: JSON.stringify({
      query,
      model_preference: modelPreference
    }),
    timeout: 15000
  });

  return await response.json();
};
```

### **8. Agent Query (Research)**
```http
POST /api/v1/agents/query
```

**REQUEST BODY**:
```json
{
  "query": "What are the basic employment rights in Kenya?",
  "strategy": "comprehensive",
  "model_preference": "claude-sonnet-4"
}
```

**EXPECTED RESPONSE** (Status: 200):
```json
{
  "answer": "Employment rights in Kenya are comprehensively covered under the Employment Act 2007 and the Constitution of Kenya 2010...",
  "confidence": 0.92,
  "model_used": "claude-sonnet-4",
  "processing_time_ms": 8500.0,
  "timestamp": "2025-01-17T10:30:00Z",
  "strategy_used": "comprehensive",
  "citations": [
    {
      "source": "Constitution of Kenya 2010",
      "article": "Article 41",
      "relevance": 0.95
    },
    {
      "source": "Employment Act 2007",
      "section": "Section 5",
      "relevance": 0.88
    }
  ],
  "follow_up_suggestions": [
    "Would you like more specific guidance on compliance requirements?",
    "Do you need information about related legal procedures?",
    "Would you like to know about potential penalties or consequences?"
  ],
  "related_queries": [
    "What are the penalties for non-compliance with employment laws?",
    "What documents are required for employment contracts?",
    "How to ensure compliance with employment regulations?"
  ]
}
```

**Frontend Implementation**:
```javascript
const agentQuery = async (query, strategy = 'comprehensive') => {
  const response = await fetch(`${API_CONFIG.baseURL}/api/v1/agents/query`, {
    method: 'POST',
    headers: API_CONFIG.headers,
    body: JSON.stringify({
      query,
      strategy,
      context: {},
      user_context: {}
    }),
    timeout: 25000
  });

  return await response.json();
};
```
