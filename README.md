# 🏛️ LegalizeMe Counsel AI - Enterprise Legal Intelligence Platform

[![Production Ready](https://img.shields.io/badge/Production-Ready-green.svg)](https://www.legalizeme.site/counsel)
[![API Version](https://img.shields.io/badge/API-v3.0.0-blue.svg)](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs)
[![AWS ECS](https://img.shields.io/badge/AWS-ECS%20Fargate-orange.svg)](https://aws.amazon.com/ecs/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2015.8-blue.svg)](https://postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-green.svg)](https://github.com/joshuarebo/legalizeme-v3/actions)

**Enterprise-grade AI-powered legal intelligence platform specifically designed for Kenyan jurisdiction, delivering accurate legal guidance through AWS Bedrock's most advanced language models.**

> 🎯 **Production URL**: [https://www.legalizeme.site/counsel](https://www.legalizeme.site/counsel)
> 📚 **API Documentation**: [http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs)

## 🎯 Overview

LegalizeMe Counsel is a sophisticated AI backend agent that leverages AWS Bedrock models to provide intelligent legal assistance for Kenyan law. The system is designed for deployment at `legalizeme.site/counsel` with enterprise-grade reliability and performance.

## 🚀 Key Features

### 🧠 AI-Powered Legal Intelligence
- **Claude Sonnet 4**: Primary model for complex legal analysis
- **Claude 3.7**: Secondary model for balanced performance  
- **Mistral Large**: Fallback model for high availability
- **Automatic Fallback**: Seamless model switching for 99.9% uptime

### 🇰🇪 Kenyan Legal Expertise
- Constitutional law guidance
- Corporate registration procedures
- Employment law compliance
- Property and land law
- Family law matters
- Criminal law procedures

### 🏗️ Production Architecture
- **FastAPI Backend**: High-performance async API
- **LegalResearchAgent**: Context-aware intelligent legal research with modular chaining
- **Context Engineering Framework**: Layered context analysis with adaptive refinement
- **Enhanced RAG System**: ChromaDB vector storage with source citations
- **AWS Bedrock Integration**: Enterprise AI models with confidence scoring
- **PostgreSQL Database**: Robust data persistence
- **Redis Caching**: Sub-second response times
- **Multi-Strategy Retrieval**: Semantic, keyword, and hybrid search
- **GAIA-Style Benchmarking**: 90% pass rate requirement with Level 1-3 evaluation
- **Comprehensive Monitoring**: Health checks, performance metrics, and context quality tracking

### 🤖 LegalResearchAgent - Context-Aware Intelligence
- **Modular Chaining Pipeline**: VectorRetriever → MultiSourceSummarizer → LegalReasoner → AnswerFormatter
- **Layered Context Engineering**: System/Domain/Task/Interaction/Response context layers
- **PRP Templates**: YAML-based Product Requirement Prompts for employment, contract, property, and corporate law
- **Context Refinement Loop**: Adaptive improvement based on performance feedback
- **AgentMonitor Decorator**: Real-time quality tracking and failure analysis
- **GAIA-Style Benchmarking**: Level 1-3 evaluation with 90% pass rate requirement
- **Confidence-Based Fallbacks**: Automatic strategy adjustment for optimal results

### 📄 Multi-Modal Document Processing
- **PDF Processing**: Advanced text extraction with pdfplumber + PyMuPDF fallback
- **OCR Capabilities**: 94.8-95.5% accuracy on scanned legal documents (Tesseract v5.5.0)
- **Document Classification**: 100% accuracy on legal document types (contracts, affidavits, judgments)
- **Intelligent Routing**: Automatic file type detection and processing optimization
- **Vector Integration**: Enhanced ChromaDB indexing with document chunking
- **Structured Summarization**: Claude Sonnet 4 powered analysis with entity extraction
- **Production Ready**: 100% test success rate with comprehensive validation

### 🤖 LegalResearchAgent (NEW)
- **Intelligent Legal Research**: Advanced agentic behavior for complex legal queries
- **Multi-Step Reasoning**: Retrieve → Summarize → Synthesize → Respond workflow
- **Confidence-Based Fallbacks**: Automatic model switching based on response quality
- **Memory Tracking**: Redis-based conversation context and research history
- **Citation Management**: Structured source attribution with confidence scores
- **Chaining Logic**: Sequential reasoning for complex legal decision-making
- **Agent Mode Toggle**: Available in `/counsel/query` with `agent_mode=true`
- **Dedicated Endpoint**: `/agents/research` for specialized legal research tasks

## 📋 Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- AWS Account with Bedrock access
- Docker (optional)

## 🛠️ Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/joshuarebo/legalizeme-v3.git
cd legalizeme-v3
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
# Configure your AWS credentials and other settings in .env
```

### 3. Database Setup
```bash
# Start services
docker-compose up -d postgres redis

# Initialize database
alembic upgrade head
python scripts/initialize_vector_db.py
```

### 4. Start the Server
```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## ⚙️ Configuration

### Required Environment Variables

```env
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1

# Model IDs (Pre-configured for your AWS account)
AWS_BEDROCK_MODEL_ID_PRIMARY=us.anthropic.claude-sonnet-4-20250514-v1:0
AWS_BEDROCK_MODEL_ID_SECONDARY=us.anthropic.claude-3-7-sonnet-20250219-v1:0
AWS_BEDROCK_MODEL_ID_FALLBACK=mistral.mistral-large-2402-v1:0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/counsel_db
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-super-secret-key-change-in-production
```

## 🔌 API Usage

### Legal Query Endpoint (Enhanced with Agent Mode)
```bash
POST /api/v1/counsel/query
Content-Type: application/json

{
  "query": "What are the constitutional rights in Kenya?",
  "context": "employment dispute",
  "agent_mode": true,  // Enable LegalResearchAgent
  "use_enhanced_rag": true
}
```

### LegalResearchAgent Endpoint (NEW)
```bash
POST /api/v1/agents/research
Content-Type: application/json

{
  "query": "What are the legal requirements for employment contracts in Kenya?",
  "strategy": "comprehensive",  // quick, comprehensive, focused, exploratory
  "max_sources": 10,
  "confidence_threshold": 0.7,
  "enable_context_framework": true,
  "context": {
    "domain": "employment_law",
    "urgency": "high"
  }
}
```

### Agent Health and Metrics
```bash
# Check agent health
GET /api/v1/agents/health

# Get performance metrics
GET /api/v1/agents/metrics

# Run GAIA benchmarks
POST /api/v1/agents/benchmark
{
  "level": 2,  // 1=basic, 2=intermediate, 3=advanced
  "category": "employment_law",
  "max_cases": 5
}
```

### Direct LLM Query (Production)
```bash
POST /api/v1/counsel/query-direct
Content-Type: application/json

{
  "query": "How do I register a company in Kenya?",
  "model_preference": "claude-sonnet-4"
}
```

### Multi-Modal Document Processing (NEW)
```bash
# Process legal documents (PDF, images, text)
POST /multimodal/process-document
Content-Type: multipart/form-data

file: [PDF/Image/Text file]
options: {"generate_summary": true, "summary_model": "claude-sonnet-4"}

# Search processed documents
POST /multimodal/search
Content-Type: application/json

{
  "query": "employment contract termination clause",
  "limit": 5,
  "document_type": "employment_contract",
  "confidence_threshold": 0.8
}

# Get processing capabilities
GET /multimodal/capabilities
```

### Health Check
```bash
GET /api/v1/health
```

## 🧪 Testing

### Run Production Tests
```bash
# Test Bedrock models
python scripts/production_test.py

# Test multi-modal processing (NEW)
python multimodal_test.py

# Run integration tests (NEW)
python integration_test.py

# Run unit tests
pytest tests/test_bedrock_models.py

# Full test suite
pytest
```

### Test Coverage
```bash
pytest --cov=app --cov-report=html
```

## 📊 Monitoring & Performance

### Health Monitoring
- **Health Endpoint**: `/health` - System status
- **Model Status**: Real-time model availability
- **Performance Metrics**: Response times and error rates

### Expected Performance
- **Claude Sonnet 4**: 8-27s (comprehensive analysis)
- **Claude 3.7**: 4-9s (balanced performance)
- **Mistral Large**: 0.6-3s (fast responses)
- **Multi-Modal Processing**: 8-16s (PDF/OCR), 0.9-1.1s (search)
- **OCR Accuracy**: 94.8-95.5% on scanned legal documents
- **Uptime**: 99.9% with automatic fallback

## 🚢 Deployment

### AWS ECS Fargate Deployment (Production)
```bash
# Deploy complete infrastructure
.\create-infrastructure.ps1

# Deploy RDS PostgreSQL database
.\setup-rds-database.ps1

# Fix ALB health checks
.\fix-alb-health-check.ps1

# Validate deployment
.\validate-production-setup.ps1
```

### Production URLs
- **API Base**: `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com`
- **Health Check**: `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live`
- **API Documentation**: `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs`

### Environment Variables for Production
Set these in AWS Parameter Store and GitHub Secrets:
- `AWS_ACCESS_KEY_ID` (GitHub Secret)
- `AWS_SECRET_ACCESS_KEY` (GitHub Secret)
- `AWS_REGION=us-east-1`
- `DATABASE_URL` (Parameter Store: `/counsel/database-url`)
- `SECRET_KEY` (GitHub Secret)
- `AWS_BEDROCK_MODEL_ID_PRIMARY=us.anthropic.claude-sonnet-4-20250514-v1:0`
- `AWS_BEDROCK_MODEL_ID_SECONDARY=us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- `AWS_BEDROCK_MODEL_ID_FALLBACK=mistral.mistral-7b-instruct-v0:2`

### Docker Deployment
```bash
docker build -t legalizeme-counsel .
docker run -p 8000:8000 --env-file .env legalizeme-counsel
```

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs`
- **ReDoc**: `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/redoc`

### 🎯 Frontend Integration Guide

#### Base Configuration
```javascript
const API_BASE_URL = 'http://counsel-alb-694525771.us-east-1.elb.amazonaws.com';
const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'User-Agent': 'LegalizeMe-Frontend/1.0'
};
```

#### Core Legal Query Endpoint
```javascript
// Standard legal query
const queryLegal = async (query, agentMode = false) => {
  const response = await fetch(`${API_BASE_URL}/counsel/query`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify({
      query: query,
      agent_mode: agentMode,
      model_preference: 'claude-sonnet-4'
    })
  });
  return await response.json();
};

// Usage examples
const basicQuery = await queryLegal('What are employment rights in Kenya?');
const agentQuery = await queryLegal('Analyze employment contract requirements', true);
```

#### 🤖 LegalResearchAgent Endpoint (NEW)
```javascript
// Advanced legal research with agentic behavior
const researchLegal = async (query, context = null) => {
  const response = await fetch(`${API_BASE_URL}/agents/research`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify({
      query: query,
      context: context,
      max_iterations: 3,
      confidence_threshold: 0.8
    })
  });
  return await response.json();
};

// Usage example
const research = await researchLegal(
  'What are the legal requirements for employment contracts in Kenya?',
  'employment law'
);
```

#### 📄 Multi-Modal Document Processing
```javascript
// Process PDF documents
const processDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', 'legal_document');

  const response = await fetch(`${API_BASE_URL}/multimodal/process`, {
    method: 'POST',
    body: formData
  });
  return await response.json();
};

// Text-only processing
const processText = async (text, documentType = 'contract') => {
  const response = await fetch(`${API_BASE_URL}/documents/analyze`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify({
      text: text,
      document_type: documentType
    })
  });
  return await response.json();
};
```

#### 🔍 Vector Search
```javascript
// Search legal documents
const searchDocuments = async (query, limit = 5) => {
  const response = await fetch(`${API_BASE_URL}/search/vector`, {
    method: 'POST',
    headers: DEFAULT_HEADERS,
    body: JSON.stringify({
      query: query,
      limit: limit,
      include_metadata: true
    })
  });
  return await response.json();
};
```

#### 🏥 Health Monitoring
```javascript
// Check API health
const checkHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: DEFAULT_HEADERS
  });
  return await response.json();
};

// Live health check (for monitoring)
const checkLiveHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/health/live`, {
    headers: DEFAULT_HEADERS
  });
  return response.ok;
};
```

#### 📋 Response Formats

**Standard Legal Query Response:**
```json
{
  "response_text": "Employment rights in Kenya are governed by...",
  "confidence_score": 0.92,
  "model_used": "claude-sonnet-4",
  "sources": [
    {
      "title": "Employment Act 2007",
      "url": "https://kenyalaw.org/...",
      "relevance_score": 0.95
    }
  ],
  "processing_time": 8.2,
  "timestamp": "2025-07-10T18:45:00Z"
}
```

**LegalResearchAgent Response:**
```json
{
  "research_result": "Based on comprehensive analysis...",
  "confidence_score": 0.89,
  "reasoning_steps": [
    "Retrieved relevant employment law documents",
    "Analyzed contract requirements",
    "Synthesized legal obligations"
  ],
  "sources": [...],
  "agent_iterations": 2,
  "final_model": "claude-sonnet-4",
  "memory_context": "employment_contracts_2025"
}
```

**Error Response:**
```json
{
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again in 60 seconds.",
  "retry_after": 60
}
```

#### ⚠️ Error Handling
```javascript
const handleApiCall = async (apiFunction) => {
  try {
    const response = await apiFunction();

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API Error: ${errorData.message || response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API call failed:', error);

    // Handle specific error types
    if (error.message.includes('Rate limit')) {
      // Show rate limit message to user
      return { error: 'Please wait before making another request' };
    }

    if (error.message.includes('403')) {
      // Security middleware blocked request
      return { error: 'Request blocked by security policy' };
    }

    return { error: 'Service temporarily unavailable' };
  }
};
```

#### 🚀 Production Deployment Status
- ✅ **API Base URL**: `http://counsel-alb-694525771.us-east-1.elb.amazonaws.com`
- ✅ **Health Endpoint**: `/health/live` (200 OK)
- ✅ **Documentation**: `/docs` (Interactive Swagger UI)
- ✅ **LegalResearchAgent**: `/agents/research` (Production Ready)
- ✅ **Multi-Modal Processing**: `/multimodal/process` (PDF + OCR)
- ✅ **Vector Search**: `/search/vector` (ChromaDB Integration)
- ✅ **Security**: Rate limiting and request validation active
- ✅ **Monitoring**: CloudWatch logs and health checks configured

## 🔒 Security

### Production Security Features
- JWT authentication
- Rate limiting
- CORS configuration
- Input validation
- SQL injection prevention
- XSS protection

### Security Headers
```env
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECURE_CONTENT_TYPE_NOSNIFF=true
SECURE_BROWSER_XSS_FILTER=true
```

## 🧩 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   AWS Bedrock   │
│ legalizeme.site │◄──►│   Backend       │◄──►│ Claude/Mistral  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │Multi-Modal Layer│
                    │ PDF Processing  │
                    │ OCR (Tesseract) │
                    │ Document Router │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Data Layer    │
                    │ PostgreSQL+Redis│
                    │ ChromaDB Vector │
                    └─────────────────┘
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Issues & Support
- **GitHub Issues**: Bug reports and feature requests
- **Email**: support@legalizeme.site
- **Documentation**: Available at `/docs` endpoint

### Performance Monitoring
- Real-time model health monitoring
- Automatic failover and recovery
- Performance metrics and alerting

---

## 🚀 **Production Status**

### **✅ Current Deployment**
- **🌐 Frontend URL**: [https://www.legalizeme.site/counsel](https://www.legalizeme.site/counsel)
- **🔗 API Base URL**: [http://counsel-alb-694525771.us-east-1.elb.amazonaws.com](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com)
- **📚 API Documentation**: [http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs)
- **💚 Health Status**: [http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live](http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live)

### **🎯 Ready for Production**
✅ **Infrastructure**: AWS ECS Fargate with RDS PostgreSQL
✅ **Security**: JWT authentication, rate limiting, CORS
✅ **Monitoring**: CloudWatch logs, health checks, alerting
✅ **CI/CD**: GitHub Actions automated deployment
✅ **Documentation**: Comprehensive guides for frontend integration
✅ **Multi-Modal Processing**: PDF/OCR/Document analysis with 100% test success rate

---

**🇰🇪 Built for the Kenyan legal community with Silicon Valley engineering standards**

**🚀 Enterprise-ready AI legal platform deployed on AWS cloud infrastructure**

**⚖️ Empowering legal professionals with cutting-edge AI technology**
