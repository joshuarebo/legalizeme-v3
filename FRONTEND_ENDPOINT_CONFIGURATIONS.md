# 🎯 **PRECISE FRONTEND ENDPOINT CONFIGURATIONS**
**Based on Meticulous Codebase Analysis**

> **CRITICAL**: These are the EXACT configurations from the actual codebase implementation. Use these precise structures to avoid frontend errors.

---

## 🌐 **Base Configuration**

```javascript
const API_CONFIG = {
  baseURL: 'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com',
  timeout: 30000, // 30 seconds for AI processing
  headers: {
    'Content-Type': 'application/json',
    'User-Agent': 'LegalizeMe-Frontend/1.0'
  }
};
```

---

## ⚖️ **1. LEGAL COUNSEL ENDPOINTS**

### **1.1 Enhanced Legal Query**
```javascript
// POST /api/v1/counsel/query
const legalQuery = {
  method: 'POST',
  url: '/api/v1/counsel/query',
  requestBody: {
    query: 'string', // REQUIRED, max 2000 chars
    context: {}, // OPTIONAL object
    query_type: 'legal_query', // OPTIONAL, default: 'legal_query'
    use_enhanced_rag: true, // OPTIONAL, default: true
    agent_mode: false, // OPTIONAL, default: false
    user_context: {}, // OPTIONAL object
    conversation_id: null, // OPTIONAL string
    message_history: [] // OPTIONAL array of {role: string, content: string}
  },
  responseStructure: {
    query_id: 'string',
    answer: 'string',
    relevant_documents: [], // array of objects
    confidence: 0.8, // float 0-1
    model_used: 'string',
    processing_time: 12.5, // float seconds
    timestamp: '2025-01-17T10:30:00Z', // ISO string
    enhanced: true, // boolean
    sources: [], // OPTIONAL array
    retrieval_strategy: null, // OPTIONAL string
    agent_mode: false, // boolean
    research_strategy: null, // OPTIONAL string
    reasoning_chain: [], // OPTIONAL array
    follow_up_suggestions: [], // OPTIONAL array
    related_queries: [] // OPTIONAL array
  }
};
```

### **1.2 Direct Query (Simplified)**
```javascript
// POST /api/v1/counsel/query-direct
const directQuery = {
  method: 'POST',
  url: '/api/v1/counsel/query-direct',
  requestBody: {
    query: 'string', // REQUIRED, max 2000 chars
    model_preference: 'claude-sonnet-4' // OPTIONAL: 'claude-sonnet-4', 'claude-3-7', 'mistral-large'
  },
  responseStructure: {
    response_text: 'string',
    model_used: 'string',
    model_id: 'string',
    latency_ms: 3250.5, // float
    success: true, // boolean
    timestamp: '2025-01-17T10:30:00Z' // ISO string
  }
};
```

### **1.3 Query Suggestions**
```javascript
// GET /api/v1/counsel/suggestions?query={query}&limit={limit}
const querySuggestions = {
  method: 'GET',
  url: '/api/v1/counsel/suggestions',
  queryParams: {
    query: 'string', // REQUIRED
    limit: 5 // OPTIONAL, default: 5
  },
  responseStructure: {
    suggestions: [], // array of strings
    query: 'string',
    total_suggestions: 5 // integer
  }
};
```

### **1.4 Conversations**
```javascript
// GET /api/v1/counsel/conversations
const listConversations = {
  method: 'GET',
  url: '/api/v1/counsel/conversations',
  queryParams: {
    limit: 20, // OPTIONAL, default: 20
    offset: 0 // OPTIONAL, default: 0
  },
  responseStructure: {
    conversations: [
      {
        id: 'string',
        title: 'string',
        agent_mode: false, // boolean
        use_enhanced_rag: true, // boolean
        context: {}, // object
        created_at: '2025-01-17T10:30:00Z', // ISO string
        updated_at: '2025-01-17T10:30:00Z' // ISO string
      }
    ],
    total: 1, // integer
    limit: 20, // integer
    offset: 0 // integer
  }
};

// POST /api/v1/counsel/conversations
const createConversation = {
  method: 'POST',
  url: '/api/v1/counsel/conversations',
  requestBody: {
    title: 'string', // OPTIONAL
    agent_mode: false, // OPTIONAL, default: false
    use_enhanced_rag: true, // OPTIONAL, default: true
    initial_context: {} // OPTIONAL object
  },
  responseStructure: {
    id: 'string',
    title: 'string',
    agent_mode: false, // boolean
    use_enhanced_rag: true, // boolean
    context: {}, // object
    created_at: '2025-01-17T10:30:00Z', // ISO string
    updated_at: '2025-01-17T10:30:00Z' // ISO string
  }
};
```

---

## 🤖 **2. SIMPLE AGENT ENDPOINTS**

### **2.1 Agent Health Check**
```javascript
// GET /api/v1/agents/health
const agentHealth = {
  method: 'GET',
  url: '/api/v1/agents/health',
  responseStructure: {
    status: 'healthy', // string
    agent_type: 'legal_research', // string
    models_available: ['claude-sonnet-4', 'claude-3-7', 'mistral-large'], // array
    last_health_check: '2025-01-17T10:30:00Z' // ISO string
  }
};
```

### **2.2 Agent Query (Research)**
```javascript
// POST /api/v1/agents/query
const agentQuery = {
  method: 'POST',
  url: '/api/v1/agents/query',
  requestBody: {
    query: 'string', // REQUIRED, max 2000 chars
    strategy: 'comprehensive', // OPTIONAL: 'quick', 'comprehensive', 'focused', default: 'quick'
    context: {}, // OPTIONAL object
    user_context: {} // OPTIONAL object
  },
  responseStructure: {
    answer: 'string',
    confidence: 0.92, // float 0-1
    model_used: 'string',
    processing_time_ms: 8500.0, // float
    timestamp: '2025-01-17T10:30:00Z', // ISO string
    strategy_used: 'string',
    citations: [], // array of objects
    follow_up_suggestions: [], // array of strings
    related_queries: [] // array of strings
  }
};
```

---

## 📄 **3. DOCUMENT ENDPOINTS**

### **3.1 Document Search**
```javascript
// POST /api/v1/documents/search
const documentSearch = {
  method: 'POST',
  url: '/api/v1/documents/search',
  requestBody: {
    query: 'string', // REQUIRED, max 2000 chars
    filters: {}, // OPTIONAL object
    limit: 10, // OPTIONAL, default: 10, max: 50
    user_context: {} // OPTIONAL object
  },
  responseStructure: {
    documents: [
      {
        id: 1, // integer
        title: 'string',
        summary: 'string', // OPTIONAL
        source: 'string',
        document_type: 'string',
        url: 'string', // OPTIONAL
        word_count: 1500, // OPTIONAL integer
        created_at: '2025-01-17T10:30:00Z', // ISO string
        relevance_score: 0.89 // OPTIONAL float 0-1
      }
    ],
    total_results: 1, // integer
    query: 'string',
    processing_time_ms: 450.0 // float
  }
};
```

### **3.2 Document Analysis**
```javascript
// GET /api/v1/documents/{document_id}/analysis
const documentAnalysis = {
  method: 'GET',
  url: '/api/v1/documents/{document_id}/analysis', // Replace {document_id} with actual ID
  responseStructure: {
    document_id: 123, // integer
    analysis: {
      document_type: 'string',
      summary: 'string',
      key_points: [], // array of strings
      risk_assessment: 'string',
      compliance_score: 0.75 // float 0-1
    },
    confidence: 0.8, // float 0-1
    model_used: 'string',
    timestamp: '2025-01-17T10:30:00Z', // ISO string
    status: 'completed' // string
  }
};
```

---

## 🎯 **4. TOKEN TRACKING ENDPOINTS**

### **4.1 Token Health**
```javascript
// GET /api/v1/tokens/health
const tokenHealth = {
  method: 'GET',
  url: '/api/v1/tokens/health',
  responseStructure: {
    status: 'healthy', // string
    tracking_active: true, // boolean
    database_connected: true, // boolean
    last_cleanup: '2025-01-17T09:00:00Z' // ISO string
  }
};
```

### **4.2 Token Status**
```javascript
// GET /api/v1/tokens/status/{user_id}
const tokenStatus = {
  method: 'GET',
  url: '/api/v1/tokens/status/{user_id}', // Replace {user_id} with actual user ID
  responseStructure: {
    user_id: 'string',
    current_usage: {
      daily_tokens: 1250, // integer
      monthly_tokens: 15000, // integer
      daily_limit: 10000, // integer
      monthly_limit: 100000 // integer
    },
    remaining: {
      daily: 8750, // integer
      monthly: 85000 // integer
    },
    reset_times: {
      daily_reset: '2025-01-18T00:00:00Z', // ISO string
      monthly_reset: '2025-02-01T00:00:00Z' // ISO string
    },
    status: 'active' // string
  }
};
```

---

## 🧠 **5. MODEL MANAGEMENT ENDPOINTS**

### **5.1 Model Configuration**
```javascript
// GET /api/v1/models/config
const modelConfig = {
  method: 'GET',
  url: '/api/v1/models/config',
  responseStructure: {
    models: {
      'claude-sonnet-4': {
        name: 'string',
        priority: 1, // integer
        timeout: 45.0, // float
        max_error_rate: 0.05, // float
        requires_gpu: false, // boolean
        memory_requirement: 'string',
        fine_tuned: false, // boolean
        model_path: 'string'
      },
      'claude-3-7': {
        name: 'string',
        priority: 2, // integer
        timeout: 35.0, // float
        max_error_rate: 0.05, // float
        requires_gpu: false, // boolean
        memory_requirement: 'string',
        fine_tuned: false, // boolean
        model_path: 'string'
      },
      'mistral-large': {
        name: 'string',
        priority: 3, // integer
        timeout: 40.0, // float
        max_error_rate: 0.05, // float
        requires_gpu: false, // boolean
        memory_requirement: 'string',
        fine_tuned: false, // boolean
        model_path: 'string'
      }
    },
    timestamp: '2025-01-17T10:30:00Z' // ISO string
  }
};
```

---

## 🎭 **6. MULTIMODAL ENDPOINTS**

### **6.1 Multimodal Health**
```javascript
// GET /api/v1/multimodal/health
const multimodalHealth = {
  method: 'GET',
  url: '/api/v1/multimodal/health',
  responseStructure: {
    status: 'healthy', // string
    timestamp: '2025-01-17T10:30:00Z', // ISO string
    services: {
      document_processor: true, // boolean
      document_router: true, // boolean
      vector_integration: true // boolean
    }
  }
};
```

### **6.2 Multimodal Capabilities**
```javascript
// GET /api/v1/multimodal/capabilities
const multimodalCapabilities = {
  method: 'GET',
  url: '/api/v1/multimodal/capabilities',
  responseStructure: {
    multimodal_processing: true, // boolean
    supported_formats: [], // array of strings
    ocr_available: false, // boolean
    vector_indexing: false, // boolean
    bedrock_integration: false, // boolean
    features: [] // array of strings
  }
};
```

---

## 🏥 **7. HEALTH & MONITORING ENDPOINTS**

### **7.1 Root Endpoint**
```javascript
// GET /
const rootEndpoint = {
  method: 'GET',
  url: '/',
  responseStructure: {
    message: 'string',
    version: 'string',
    status: 'string',
    environment: 'string',
    features: [] // array of strings
  }
};
```

### **7.2 Health Check**
```javascript
// GET /health
const healthCheck = {
  method: 'GET',
  url: '/health',
  responseStructure: {
    status: 'healthy', // string
    timestamp: '2025-01-17T10:30:00Z', // ISO string
    version: 'string',
    uptime: 'string',
    services: {
      database: {
        status: 'string',
        details: {} // object
      },
      vector_store: {
        status: 'string',
        details: {} // object
      },
      ai_service: {
        status: 'string',
        details: {} // object
      },
      crawler: {
        status: 'string',
        details: {} // object
      }
    }
  }
};
```

### **7.3 Readiness Check**
```javascript
// GET /health/ready
const readinessCheck = {
  method: 'GET',
  url: '/health/ready',
  responseStructure: {
    status: 'ready', // string
    timestamp: '2025-01-17T10:30:00Z' // ISO string
  }
};
```

### **7.4 Liveness Check**
```javascript
// GET /health/live
const livenessCheck = {
  method: 'GET',
  url: '/health/live',
  responseStructure: {
    status: 'alive', // string
    timestamp: '2025-01-17T10:30:00Z', // ISO string
    message: 'string'
  }
};
```

### **7.5 Version Info**
```javascript
// GET /health/version
const versionInfo = {
  method: 'GET',
  url: '/health/version',
  responseStructure: {
    version: 'string',
    build_time: 'string',
    git_commit: 'string',
    environment: 'string',
    timestamp: '2025-01-17T10:30:00Z' // ISO string
  }
};
```

### **7.6 System Metrics**
```javascript
// GET /metrics
const systemMetrics = {
  method: 'GET',
  url: '/metrics',
  responseStructure: {
    uptime: 'string',
    requests_total: 15420, // integer
    requests_per_minute: 45.2, // float
    memory_usage: 'string',
    cpu_usage: 'string',
    active_connections: 12 // integer
  }
};
```

### **7.7 API Documentation**
```javascript
// GET /docs
const apiDocs = {
  method: 'GET',
  url: '/docs',
  responseType: 'HTML' // Returns interactive Swagger UI
};
```

---

## 🔧 **8. ERROR HANDLING**

### **Standard Error Response**
```javascript
const errorResponse = {
  error: {
    code: 'string', // Error code
    message: 'string', // Human readable message
    details: 'string', // Additional details
    timestamp: '2025-01-17T10:30:00Z', // ISO string
    request_id: 'string' // Request tracking ID
  }
};
```

### **HTTP Status Codes**
```javascript
const statusCodes = {
  200: 'Success',
  400: 'Bad Request - Invalid input parameters',
  404: 'Not Found - Endpoint or resource not found',
  429: 'Too Many Requests - Rate limit exceeded',
  500: 'Internal Server Error - AI service error',
  503: 'Service Unavailable - Temporary outage'
};
```

---

## 🚀 **9. FRONTEND INTEGRATION EXAMPLES**

### **React/JavaScript Implementation**
```javascript
class CounselAIClient {
  constructor() {
    this.baseURL = 'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com';
    this.timeout = 30000;
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
      timeout: this.timeout,
      ...options
    };

    if (options.body) {
      config.body = JSON.stringify(options.body);
    }

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`API Error ${response.status}: ${errorData.error?.message || response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // Legal Query Methods
  async legalQuery(query, options = {}) {
    return this.makeRequest('/api/v1/counsel/query', {
      method: 'POST',
      body: {
        query,
        use_enhanced_rag: options.enhanced ?? true,
        agent_mode: options.agentMode ?? false,
        context: options.context,
        user_context: options.userContext
      }
    });
  }

  async directQuery(query, modelPreference = 'claude-sonnet-4') {
    return this.makeRequest('/api/v1/counsel/query-direct', {
      method: 'POST',
      body: { query, model_preference: modelPreference }
    });
  }

  async getQuerySuggestions(query, limit = 5) {
    return this.makeRequest(`/api/v1/counsel/suggestions?query=${encodeURIComponent(query)}&limit=${limit}`);
  }

  // Agent Methods
  async agentQuery(query, strategy = 'comprehensive') {
    return this.makeRequest('/api/v1/agents/query', {
      method: 'POST',
      body: { query, strategy }
    });
  }

  // Document Methods
  async searchDocuments(query, options = {}) {
    return this.makeRequest('/api/v1/documents/search', {
      method: 'POST',
      body: {
        query,
        limit: options.limit ?? 10,
        filters: options.filters,
        user_context: options.userContext
      }
    });
  }

  // Token Methods
  async checkTokens(userId, estimatedTokens, requestType) {
    return this.makeRequest('/api/v1/tokens/check', {
      method: 'POST',
      body: { userId, estimatedTokens, requestType }
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
        sessionId: options.sessionId
      }
    });
  }

  // Health Methods
  async healthCheck() {
    return this.makeRequest('/health');
  }

  async getModelConfig() {
    return this.makeRequest('/api/v1/models/config');
  }
}

// Usage Example
const client = new CounselAIClient();

// Legal query with enhanced RAG
const result = await client.legalQuery('What are employment rights in Kenya?', {
  enhanced: true,
  agentMode: false,
  context: { jurisdiction: 'Kenya', legal_area: 'employment_law' }
});

// Direct query for faster response
const directResult = await client.directQuery('What is the minimum wage in Kenya?');

// Agent research query
const agentResult = await client.agentQuery('Analyze constitutional provisions on freedom of expression', 'comprehensive');
```

---

## ⚠️ **10. CRITICAL FRONTEND NOTES**

### **Required Headers**
```javascript
const requiredHeaders = {
  'Content-Type': 'application/json', // ALWAYS required for POST requests
  'User-Agent': 'LegalizeMe-Frontend/1.0' // Recommended for tracking
};
```

### **Timeout Configuration**
```javascript
const timeouts = {
  healthChecks: 5000,    // 5 seconds
  directQueries: 15000,  // 15 seconds
  enhancedQueries: 30000, // 30 seconds
  documentOps: 20000,    // 20 seconds
  tokenOps: 10000        // 10 seconds
};
```

### **Error Handling Best Practices**
```javascript
try {
  const result = await client.legalQuery(query);
  // Handle success
} catch (error) {
  if (error.message.includes('400')) {
    // Handle bad request - check input validation
  } else if (error.message.includes('429')) {
    // Handle rate limiting - implement retry logic
  } else if (error.message.includes('500')) {
    // Handle server error - show user-friendly message
  } else {
    // Handle network/other errors
  }
}
```

---

**🎯 This configuration file contains the EXACT endpoint structures from the live codebase. Use these precise formats to eliminate frontend integration errors!**

### **4.3 Token Check**
```javascript
// POST /api/v1/tokens/check
const tokenCheck = {
  method: 'POST',
  url: '/api/v1/tokens/check',
  requestBody: {
    userId: 'string', // REQUIRED
    estimatedTokens: 500, // REQUIRED integer >= 0
    requestType: 'chat_completion' // REQUIRED string
  },
  responseStructure: {
    allowed: true, // boolean
    remaining_tokens: 8500, // integer
    estimated_cost: 0.0075, // float
    rate_limit_status: 'ok' // string
  }
};
```

### **4.4 Token Tracking**
```javascript
// POST /api/v1/tokens/track
const tokenTrack = {
  method: 'POST',
  url: '/api/v1/tokens/track',
  requestBody: {
    userId: 'string', // REQUIRED
    tokensUsed: 450, // REQUIRED integer >= 0
    requestType: 'string', // REQUIRED
    mode: 'enhanced', // OPTIONAL string
    timestamp: '2025-01-17T10:30:00Z', // OPTIONAL ISO string
    sessionId: 'string' // OPTIONAL string
  },
  responseStructure: {
    tracked: true, // boolean
    new_total: 1700, // integer
    remaining_daily: 8300, // integer
    timestamp: '2025-01-17T10:30:00Z' // ISO string
  }
};
```

### **4.5 Token History**
```javascript
// GET /api/v1/tokens/history/{user_id}?limit={limit}&offset={offset}
const tokenHistory = {
  method: 'GET',
  url: '/api/v1/tokens/history/{user_id}', // Replace {user_id} with actual user ID
  queryParams: {
    limit: 10, // OPTIONAL, default: 10
    offset: 0 // OPTIONAL, default: 0
  },
  responseStructure: {
    user_id: 'string',
    history: [
      {
        timestamp: '2025-01-17T10:30:00Z', // ISO string
        tokens_used: 450, // integer
        request_type: 'string',
        model_used: 'string',
        cost: 0.00675 // float
      }
    ],
    total_records: 1, // integer
    pagination: {
      limit: 10, // integer
      offset: 0, // integer
      has_more: false // boolean
    }
  }
};
```
