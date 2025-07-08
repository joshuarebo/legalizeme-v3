# LegalizeMe Counsel AI - Production Backend

[![Production Ready](https://img.shields.io/badge/Production-Ready-green.svg)](https://legalizeme.site/counsel)
[![API Version](https://img.shields.io/badge/API-v3.0.0-blue.svg)](https://your-app.onrender.com/docs)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready AI-powered legal assistant specifically designed for Kenyan law, providing accurate legal guidance through AWS Bedrock integration.

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
- **AWS Bedrock Integration**: Enterprise AI models
- **PostgreSQL Database**: Robust data persistence
- **Redis Caching**: Sub-second response times
- **ChromaDB Vector Store**: Semantic legal document search
- **Comprehensive Monitoring**: Health checks and performance metrics

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

### Legal Query Endpoint
```bash
POST /api/v1/counsel/query
Content-Type: application/json

{
  "query": "What are the constitutional rights in Kenya?",
  "context": "employment dispute"
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

### Health Check
```bash
GET /api/v1/health
```

## 🧪 Testing

### Run Production Tests
```bash
# Test Bedrock models
python scripts/production_test.py

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
- **Uptime**: 99.9% with automatic fallback

## 🚢 Deployment

### Render Deployment
```bash
# Build command
pip install -r requirements.txt

# Start command
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
```

### Environment Variables for Render
Set these in your Render dashboard:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `DATABASE_URL` (provided by Render)
- `REDIS_URL` (provided by Render)
- `SECRET_KEY`

### Docker Deployment
```bash
docker build -t legalizeme-counsel .
docker run -p 8000:8000 --env-file .env legalizeme-counsel
```

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: `https://your-app.onrender.com/docs`
- **ReDoc**: `https://your-app.onrender.com/redoc`

### Frontend Integration
```javascript
// JavaScript integration example
const response = await fetch('https://your-app.onrender.com/api/v1/counsel/query-direct', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-jwt-token'
  },
  body: JSON.stringify({
    query: 'What are employment rights in Kenya?',
    model_preference: 'claude-sonnet-4'
  })
});

const result = await response.json();
console.log(result.response_text);
```

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

**🇰🇪 Built for the Kenyan legal community with enterprise-grade reliability**

**🚀 Ready for production deployment at legalizeme.site/counsel**
