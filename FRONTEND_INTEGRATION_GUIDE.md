# 🚀 Frontend Integration Guide - Counsel AI Legal Platform

## 📋 Overview

This guide provides step-by-step instructions for integrating the Counsel AI Legal Backend with your frontend application at `https://www.legalizeme.site/counsel`. The backend is deployed on AWS ECS Fargate and provides comprehensive legal AI services for Kenyan jurisdiction.

---

## 🔗 API Base URL

**Production Backend URL**: `http://YOUR-ALB-DNS-NAME`

> **Note**: Replace `YOUR-ALB-DNS-NAME` with the actual Application Load Balancer DNS name from your AWS deployment.

---

## 🛠️ Quick Setup

### 1. Environment Configuration

Create a configuration file for your API endpoints:

```javascript
// config/api.js
const API_CONFIG = {
  BASE_URL: 'http://YOUR-ALB-DNS-NAME', // Replace with actual ALB DNS
  ENDPOINTS: {
    // Authentication
    AUTH_TOKEN: '/auth/token',
    
    // Health & Status
    HEALTH: '/health',
    HEALTH_LIVE: '/health/live',
    HEALTH_READY: '/health/ready',
    
    // AI Counsel Services
    COUNSEL_QUERY: '/counsel/query',
    COUNSEL_DIRECT: '/counsel/query-direct',
    COUNSEL_GENERATE_DOC: '/counsel/generate-document',
    
    // Document Management
    DOCUMENTS_SEARCH: '/documents/search',
    DOCUMENTS_UPLOAD: '/documents/upload',
    DOCUMENTS_ANALYZE: '/documents/analyze',
    
    // Model Management (Admin)
    MODELS_STATUS: '/models/status',
    MODELS_TEST: '/models/test-fallback'
  },
  
  // Request Configuration
  TIMEOUT: 60000, // 60 seconds
  RETRY_ATTEMPTS: 3,
  
  // CORS Settings
  CORS_ENABLED: true
};

export default API_CONFIG;
```

### 2. API Client Setup

Create a reusable API client:

```javascript
// services/apiClient.js
import API_CONFIG from '../config/api.js';

class CounselAPIClient {
  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
    this.token = localStorage.getItem('counsel_token');
  }

  // Set authentication token
  setToken(token) {
    this.token = token;
    localStorage.setItem('counsel_token', token);
  }

  // Remove authentication token
  clearToken() {
    this.token = null;
    localStorage.removeItem('counsel_token');
  }

  // Generic request method
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    // Add authentication header if token exists
    if (this.token) {
      config.headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // GET request
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url);
  }

  // POST request
  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // File upload request
  async upload(endpoint, formData) {
    return this.request(endpoint, {
      method: 'POST',
      headers: {
        // Don't set Content-Type for FormData, let browser set it
      },
      body: formData
    });
  }
}

export default new CounselAPIClient();
```

---

## 🔐 Authentication Implementation

### 1. Login Function

```javascript
// services/authService.js
import apiClient from './apiClient.js';
import API_CONFIG from '../config/api.js';

export const authService = {
  async login(username, password) {
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.AUTH_TOKEN}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error('Authentication failed');
      }

      const data = await response.json();
      apiClient.setToken(data.access_token);
      
      return {
        success: true,
        token: data.access_token,
        expiresIn: data.expires_in
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  },

  logout() {
    apiClient.clearToken();
  },

  isAuthenticated() {
    return !!apiClient.token;
  }
};
```

### 2. Login Component Example

```javascript
// components/LoginForm.js
import { authService } from '../services/authService.js';

export function LoginForm() {
  const handleLogin = async (event) => {
    event.preventDefault();
    const formData = new FormData(event.target);
    const username = formData.get('username');
    const password = formData.get('password');

    const result = await authService.login(username, password);
    
    if (result.success) {
      console.log('Login successful');
      // Redirect to main application
      window.location.href = '/counsel/dashboard';
    } else {
      console.error('Login failed:', result.error);
      // Show error message to user
    }
  };

  return `
    <form onsubmit="handleLogin(event)">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Login</button>
    </form>
  `;
}
```

---

## 🤖 AI Counsel Integration

### 1. Legal Query Service

```javascript
// services/counselService.js
import apiClient from './apiClient.js';
import API_CONFIG from '../config/api.js';

export const counselService = {
  async askLegalQuestion(query, options = {}) {
    try {
      const requestData = {
        query: query,
        context: {
          user_type: options.userType || 'general',
          legal_area: options.legalArea || 'general',
          urgency: options.urgency || 'normal'
        },
        enhancement_config: {
          enable_rag: options.enableRAG !== false,
          enable_prompt_engineering: options.enablePromptEngineering !== false,
          retrieval_strategy: options.retrievalStrategy || 'hybrid'
        }
      };

      const response = await apiClient.post(API_CONFIG.ENDPOINTS.COUNSEL_QUERY, requestData);
      
      return {
        success: true,
        data: response
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  },

  async generateDocument(documentType, parameters, options = {}) {
    try {
      const requestData = {
        document_type: documentType,
        parameters: parameters,
        template_options: {
          include_signatures: options.includeSignatures !== false,
          include_witness_section: options.includeWitnessSection !== false,
          legal_compliance: 'kenyan_law'
        }
      };

      const response = await apiClient.post(API_CONFIG.ENDPOINTS.COUNSEL_GENERATE_DOC, requestData);
      
      return {
        success: true,
        data: response
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
};
```

### 2. Chat Interface Component

```javascript
// components/ChatInterface.js
import { counselService } from '../services/counselService.js';

export class ChatInterface {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.messages = [];
    this.init();
  }

  init() {
    this.render();
    this.attachEventListeners();
  }

  async sendMessage(message) {
    // Add user message to chat
    this.addMessage('user', message);
    
    // Show typing indicator
    this.showTyping();

    try {
      const result = await counselService.askLegalQuestion(message, {
        userType: 'general',
        legalArea: 'general',
        urgency: 'normal'
      });

      this.hideTyping();

      if (result.success) {
        this.addMessage('assistant', result.data.response, {
          sources: result.data.sources,
          metadata: result.data.metadata
        });
      } else {
        this.addMessage('error', 'Sorry, I encountered an error processing your request.');
      }
    } catch (error) {
      this.hideTyping();
      this.addMessage('error', 'Connection error. Please try again.');
    }
  }

  addMessage(type, content, metadata = {}) {
    const message = {
      type,
      content,
      metadata,
      timestamp: new Date()
    };
    
    this.messages.push(message);
    this.renderMessage(message);
  }

  renderMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.className = `message message-${message.type}`;
    
    let html = `
      <div class="message-content">${message.content}</div>
      <div class="message-time">${message.timestamp.toLocaleTimeString()}</div>
    `;

    if (message.metadata.sources) {
      html += '<div class="message-sources">Sources: ';
      message.metadata.sources.forEach(source => {
        html += `<a href="${source.url}" target="_blank">${source.title}</a> `;
      });
      html += '</div>';
    }

    messageElement.innerHTML = html;
    this.container.querySelector('.messages').appendChild(messageElement);
    this.scrollToBottom();
  }

  showTyping() {
    const typingElement = document.createElement('div');
    typingElement.className = 'typing-indicator';
    typingElement.innerHTML = 'Counsel AI is thinking...';
    this.container.querySelector('.messages').appendChild(typingElement);
    this.scrollToBottom();
  }

  hideTyping() {
    const typingElement = this.container.querySelector('.typing-indicator');
    if (typingElement) {
      typingElement.remove();
    }
  }

  scrollToBottom() {
    const messagesContainer = this.container.querySelector('.messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  attachEventListeners() {
    const input = this.container.querySelector('.message-input');
    const sendButton = this.container.querySelector('.send-button');

    sendButton.addEventListener('click', () => {
      const message = input.value.trim();
      if (message) {
        this.sendMessage(message);
        input.value = '';
      }
    });

    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendButton.click();
      }
    });
  }

  render() {
    this.container.innerHTML = `
      <div class="chat-interface">
        <div class="messages"></div>
        <div class="input-area">
          <input type="text" class="message-input" placeholder="Ask a legal question...">
          <button class="send-button">Send</button>
        </div>
      </div>
    `;
  }
}
```

---

## 📄 Document Management Integration

### 1. Document Search Service

```javascript
// services/documentService.js
import apiClient from './apiClient.js';
import API_CONFIG from '../config/api.js';

export const documentService = {
  async searchDocuments(query, options = {}) {
    try {
      const params = {
        q: query,
        limit: options.limit || 10,
        source: options.source || 'kenyan_law'
      };

      const response = await apiClient.get(API_CONFIG.ENDPOINTS.DOCUMENTS_SEARCH, params);
      
      return {
        success: true,
        data: response
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  },

  async uploadDocument(file, analysisType = 'compliance_check') {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('analysis_type', analysisType);
      formData.append('jurisdiction', 'kenya');

      const response = await apiClient.upload(API_CONFIG.ENDPOINTS.DOCUMENTS_UPLOAD, formData);
      
      return {
        success: true,
        data: response
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
};
```

---

## 🏥 Health Check & Monitoring

### 1. Health Check Service

```javascript
// services/healthService.js
import apiClient from './apiClient.js';
import API_CONFIG from '../config/api.js';

export const healthService = {
  async checkHealth() {
    try {
      const response = await apiClient.get(API_CONFIG.ENDPOINTS.HEALTH);
      return {
        success: true,
        data: response
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  },

  async checkLiveness() {
    try {
      const response = await apiClient.get(API_CONFIG.ENDPOINTS.HEALTH_LIVE);
      return {
        success: true,
        data: response
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
};
```

---

## 🎨 CSS Styling Examples

### 1. Chat Interface Styles

```css
/* styles/chat.css */
.chat-interface {
  display: flex;
  flex-direction: column;
  height: 600px;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f9f9f9;
}

.message {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 8px;
  max-width: 80%;
}

.message-user {
  background-color: #007bff;
  color: white;
  margin-left: auto;
}

.message-assistant {
  background-color: white;
  border: 1px solid #ddd;
}

.message-error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.input-area {
  display: flex;
  padding: 15px;
  background-color: white;
  border-top: 1px solid #ddd;
}

.message-input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-right: 10px;
}

.send-button {
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.send-button:hover {
  background-color: #0056b3;
}

.typing-indicator {
  font-style: italic;
  color: #666;
  padding: 10px;
}

.message-sources {
  margin-top: 10px;
  font-size: 0.9em;
  color: #666;
}

.message-sources a {
  color: #007bff;
  text-decoration: none;
  margin-right: 10px;
}

.message-sources a:hover {
  text-decoration: underline;
}
```

---

## 🚀 Complete Integration Example

### 1. Main Application File

```javascript
// app.js
import { authService } from './services/authService.js';
import { ChatInterface } from './components/ChatInterface.js';
import { healthService } from './services/healthService.js';

class CounselApp {
  constructor() {
    this.init();
  }

  async init() {
    // Check backend health
    const health = await healthService.checkHealth();
    if (!health.success) {
      console.error('Backend is not available');
      this.showError('Service temporarily unavailable');
      return;
    }

    // Check authentication
    if (!authService.isAuthenticated()) {
      this.showLogin();
    } else {
      this.showMainApp();
    }
  }

  showLogin() {
    document.getElementById('app').innerHTML = `
      <div class="login-container">
        <h1>Counsel AI Legal Platform</h1>
        <form id="loginForm">
          <input type="text" name="username" placeholder="Username" required>
          <input type="password" name="password" placeholder="Password" required>
          <button type="submit">Login</button>
        </form>
      </div>
    `;

    document.getElementById('loginForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const formData = new FormData(e.target);
      const result = await authService.login(
        formData.get('username'),
        formData.get('password')
      );

      if (result.success) {
        this.showMainApp();
      } else {
        this.showError('Login failed: ' + result.error);
      }
    });
  }

  showMainApp() {
    document.getElementById('app').innerHTML = `
      <div class="main-app">
        <header>
          <h1>Counsel AI Legal Platform</h1>
          <button id="logoutBtn">Logout</button>
        </header>
        <main>
          <div id="chatContainer"></div>
        </main>
      </div>
    `;

    // Initialize chat interface
    new ChatInterface('chatContainer');

    // Add logout functionality
    document.getElementById('logoutBtn').addEventListener('click', () => {
      authService.logout();
      this.showLogin();
    });
  }

  showError(message) {
    document.getElementById('app').innerHTML = `
      <div class="error-container">
        <h2>Error</h2>
        <p>${message}</p>
        <button onclick="location.reload()">Retry</button>
      </div>
    `;
  }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  new CounselApp();
});
```

---

## 📝 Implementation Checklist

### ✅ Pre-Integration Steps
- [ ] Obtain ALB DNS name from AWS deployment
- [ ] Update `API_CONFIG.BASE_URL` with actual backend URL
- [ ] Test backend health endpoint: `GET /health`
- [ ] Verify CORS configuration allows your frontend domain

### ✅ Authentication Setup
- [ ] Implement login form
- [ ] Set up token storage (localStorage/sessionStorage)
- [ ] Add authentication headers to API requests
- [ ] Handle token expiration and refresh

### ✅ Core Features Integration
- [ ] Legal query chat interface
- [ ] Document search functionality
- [ ] Document upload and analysis
- [ ] Error handling and user feedback
- [ ] Loading states and progress indicators

### ✅ Production Considerations
- [ ] Implement proper error boundaries
- [ ] Add request timeout handling
- [ ] Set up monitoring and analytics
- [ ] Optimize for mobile responsiveness
- [ ] Add accessibility features (ARIA labels, keyboard navigation)

---

## 🔧 Troubleshooting

### Common Issues

1. **CORS Errors**
   - Ensure your domain is added to `ALLOWED_ORIGINS` in backend configuration
   - Check browser developer tools for specific CORS error messages

2. **Authentication Failures**
   - Verify username/password credentials
   - Check token expiration and refresh logic
   - Ensure Authorization header format: `Bearer <token>`

3. **API Request Timeouts**
   - AI responses can take 30-60 seconds for complex queries
   - Implement proper loading states
   - Consider increasing timeout values for AI endpoints

4. **Backend Unavailability**
   - Check AWS ECS service status
   - Verify ALB health checks are passing
   - Monitor CloudWatch logs for errors

---

## 📞 Support

For technical support and questions:
- Check AWS CloudWatch logs for backend errors
- Monitor ECS service health in AWS Console
- Review API documentation for endpoint specifications
- Test individual endpoints using tools like Postman

---

## 🌐 Deployment Configuration

### 1. Environment Variables

Create environment-specific configuration files:

```javascript
// config/environments/production.js
export const productionConfig = {
  API_BASE_URL: 'http://YOUR-PRODUCTION-ALB-DNS-NAME',
  ENVIRONMENT: 'production',
  DEBUG: false,
  ANALYTICS_ENABLED: true,
  ERROR_REPORTING: true
};

// config/environments/staging.js
export const stagingConfig = {
  API_BASE_URL: 'http://YOUR-STAGING-ALB-DNS-NAME',
  ENVIRONMENT: 'staging',
  DEBUG: true,
  ANALYTICS_ENABLED: false,
  ERROR_REPORTING: true
};
```

### 2. Build Configuration

For deployment to `https://www.legalizeme.site/counsel`:

```javascript
// webpack.config.js or vite.config.js
export default {
  base: '/counsel/',
  build: {
    outDir: 'dist/counsel',
    assetsDir: 'assets'
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://YOUR-ALB-DNS-NAME',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
};
```

---

## 📊 Performance Optimization

### 1. Request Caching

```javascript
// utils/cache.js
class APICache {
  constructor(ttl = 300000) { // 5 minutes default
    this.cache = new Map();
    this.ttl = ttl;
  }

  set(key, value) {
    this.cache.set(key, {
      value,
      timestamp: Date.now()
    });
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }

  clear() {
    this.cache.clear();
  }
}

export const apiCache = new APICache();
```

### 2. Optimized API Client with Caching

```javascript
// services/optimizedApiClient.js
import { apiCache } from '../utils/cache.js';

class OptimizedAPIClient extends CounselAPIClient {
  async get(endpoint, params = {}, useCache = true) {
    const cacheKey = `${endpoint}?${new URLSearchParams(params).toString()}`;

    if (useCache) {
      const cached = apiCache.get(cacheKey);
      if (cached) return cached;
    }

    const result = await super.get(endpoint, params);

    if (useCache && result) {
      apiCache.set(cacheKey, result);
    }

    return result;
  }
}

export default new OptimizedAPIClient();
```

---

## 🔒 Security Best Practices

### 1. Token Management

```javascript
// utils/tokenManager.js
class TokenManager {
  constructor() {
    this.tokenKey = 'counsel_token';
    this.refreshKey = 'counsel_refresh_token';
  }

  setTokens(accessToken, refreshToken = null) {
    localStorage.setItem(this.tokenKey, accessToken);
    if (refreshToken) {
      localStorage.setItem(this.refreshKey, refreshToken);
    }
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  getRefreshToken() {
    return localStorage.getItem(this.refreshKey);
  }

  clearTokens() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.refreshKey);
  }

  isTokenExpired(token) {
    if (!token) return true;

    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  }
}

export const tokenManager = new TokenManager();
```

### 2. Input Sanitization

```javascript
// utils/sanitizer.js
export const sanitizer = {
  sanitizeInput(input) {
    if (typeof input !== 'string') return input;

    return input
      .replace(/[<>]/g, '') // Remove potential HTML tags
      .trim()
      .substring(0, 2000); // Limit length
  },

  validateLegalQuery(query) {
    if (!query || query.length < 3) {
      throw new Error('Query must be at least 3 characters long');
    }

    if (query.length > 2000) {
      throw new Error('Query is too long (max 2000 characters)');
    }

    return this.sanitizeInput(query);
  }
};
```

---

## 📱 Mobile Responsiveness

### 1. Responsive Chat Interface

```css
/* styles/responsive.css */
@media (max-width: 768px) {
  .chat-interface {
    height: calc(100vh - 120px);
    border-radius: 0;
    border: none;
  }

  .messages {
    padding: 10px;
  }

  .message {
    max-width: 95%;
    font-size: 14px;
  }

  .input-area {
    padding: 10px;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: white;
    border-top: 1px solid #ddd;
  }

  .message-input {
    font-size: 16px; /* Prevents zoom on iOS */
  }
}

@media (max-width: 480px) {
  .input-area {
    flex-direction: column;
  }

  .message-input {
    margin-right: 0;
    margin-bottom: 10px;
  }

  .send-button {
    width: 100%;
  }
}
```

---

## 🧪 Testing Integration

### 1. API Testing Utilities

```javascript
// tests/apiTestUtils.js
export class APITestUtils {
  static async testEndpoint(endpoint, method = 'GET', data = null) {
    try {
      const config = {
        method,
        headers: {
          'Content-Type': 'application/json'
        }
      };

      if (data) {
        config.body = JSON.stringify(data);
      }

      const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, config);

      return {
        success: response.ok,
        status: response.status,
        data: await response.json()
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  static async runHealthChecks() {
    const tests = [
      { name: 'Health Check', endpoint: '/health' },
      { name: 'Liveness Check', endpoint: '/health/live' },
      { name: 'Readiness Check', endpoint: '/health/ready' }
    ];

    const results = [];

    for (const test of tests) {
      const result = await this.testEndpoint(test.endpoint);
      results.push({
        ...test,
        ...result
      });
    }

    return results;
  }
}
```

### 2. Integration Test Suite

```javascript
// tests/integrationTests.js
import { APITestUtils } from './apiTestUtils.js';
import { authService } from '../services/authService.js';
import { counselService } from '../services/counselService.js';

export class IntegrationTests {
  static async runAllTests() {
    console.log('🧪 Running Integration Tests...');

    const results = {
      health: await this.testHealthEndpoints(),
      auth: await this.testAuthentication(),
      counsel: await this.testCounselServices()
    };

    this.displayResults(results);
    return results;
  }

  static async testHealthEndpoints() {
    console.log('Testing health endpoints...');
    return await APITestUtils.runHealthChecks();
  }

  static async testAuthentication() {
    console.log('Testing authentication...');
    // Note: Use test credentials, not production ones
    const result = await authService.login('test_user', 'test_password');
    return {
      success: result.success,
      message: result.success ? 'Authentication working' : result.error
    };
  }

  static async testCounselServices() {
    console.log('Testing counsel services...');
    const result = await counselService.askLegalQuestion('What is the Companies Act 2015?');
    return {
      success: result.success,
      message: result.success ? 'Counsel service working' : result.error
    };
  }

  static displayResults(results) {
    console.log('📊 Test Results:');
    console.table(results);
  }
}
```

---

## 🚀 Production Deployment Steps

### Step-by-Step Deployment to legalizeme.site/counsel

1. **Build the Application**
   ```bash
   npm run build
   # or
   yarn build
   ```

2. **Configure Web Server**
   ```nginx
   # nginx.conf
   location /counsel/ {
       alias /var/www/legalizeme/counsel/;
       try_files $uri $uri/ /counsel/index.html;

       # API proxy
       location /counsel/api/ {
           proxy_pass http://YOUR-ALB-DNS-NAME/;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Deploy Files**
   ```bash
   # Copy built files to server
   rsync -avz dist/counsel/ user@legalizeme.site:/var/www/legalizeme/counsel/
   ```

4. **Update DNS/CDN Configuration**
   - Ensure `www.legalizeme.site` points to your web server
   - Configure SSL certificate for HTTPS
   - Set up CDN caching rules for static assets

5. **Test Production Deployment**
   ```javascript
   // Run in browser console at https://www.legalizeme.site/counsel
   IntegrationTests.runAllTests();
   ```

---

## 📈 Monitoring & Analytics

### 1. Error Tracking

```javascript
// utils/errorTracker.js
class ErrorTracker {
  static track(error, context = {}) {
    const errorData = {
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      context
    };

    // Send to your analytics service
    console.error('Error tracked:', errorData);

    // Example: Send to external service
    // fetch('/api/errors', {
    //   method: 'POST',
    //   body: JSON.stringify(errorData)
    // });
  }
}

export default ErrorTracker;
```

### 2. Usage Analytics

```javascript
// utils/analytics.js
class Analytics {
  static trackEvent(eventName, properties = {}) {
    const eventData = {
      event: eventName,
      properties: {
        ...properties,
        timestamp: new Date().toISOString(),
        page: window.location.pathname
      }
    };

    console.log('Event tracked:', eventData);

    // Send to analytics service
    // Example: Google Analytics, Mixpanel, etc.
  }

  static trackLegalQuery(query, responseTime, success) {
    this.trackEvent('legal_query', {
      query_length: query.length,
      response_time: responseTime,
      success: success
    });
  }

  static trackDocumentUpload(fileSize, fileType, success) {
    this.trackEvent('document_upload', {
      file_size: fileSize,
      file_type: fileType,
      success: success
    });
  }
}

export default Analytics;
```

---

**🎉 Your Counsel AI Legal Platform is now ready for production use at https://www.legalizeme.site/counsel!**

### 🔗 Quick Links
- **Production URL**: https://www.legalizeme.site/counsel
- **Backend API**: http://YOUR-ALB-DNS-NAME
- **Health Check**: http://YOUR-ALB-DNS-NAME/health
- **API Documentation**: http://YOUR-ALB-DNS-NAME/docs (if enabled)

### 📞 Final Support Checklist
- [ ] Backend deployed and healthy
- [ ] Frontend deployed to correct path
- [ ] CORS configured properly
- [ ] SSL certificate active
- [ ] Error tracking implemented
- [ ] Analytics configured
- [ ] Mobile responsiveness tested
- [ ] Performance optimized
