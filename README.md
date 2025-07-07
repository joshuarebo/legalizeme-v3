# Counsel AI Backend - LegalizeMe Agent v2

AI-powered legal assistant backend for Kenyan jurisdiction, built with FastAPI and integrated with AWS Bedrock Claude Sonnet 4.

## 🚀 Features

- **AI-Powered Legal Assistance**: Uses Claude Sonnet 4 via AWS Bedrock for intelligent legal query responses
- **RAG Architecture**: Vector-based retrieval augmented generation for accurate, context-aware answers
- **Web Crawling**: Automated crawling of Kenya Law and Parliament websites for up-to-date legal information
- **Document Processing**: Parse and analyze PDFs, DOCX files, and web content
- **JWT Authentication**: Secure API endpoints with role-based access control
- **Legal Document Generation**: Generate contracts, agreements, and legal summaries
- **PostgreSQL Database**: Robust storage for legal documents, cases, and user data

## 📋 Requirements

- Python 3.11+
- PostgreSQL
- Redis (optional, for caching)
- AWS Account with Bedrock access
- Docker (for containerized deployment)

## 🔧 Installation

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/joshuarebo/legalizeme-agent-v2.git
cd legalizeme-agent-v2
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

### Docker Deployment

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

2. Or build the Docker image:
```bash
docker build -t counsel-ai-backend .
docker run -p 5000:5000 --env-file .env counsel-ai-backend
```

## 📚 API Documentation

### Base URL
```
https://www.legalizeme.site/counsel
```

### Endpoints

#### 1. Query Legal Questions
```http
POST /counsel/query
Content-Type: application/json
Authorization: Bearer {token}

{
    "query": "What are the requirements for registering a company in Kenya?",
    "context": {}
}
```

#### 2. Generate Legal Document
```http
POST /counsel/generate-document
Content-Type: application/json
Authorization: Bearer {token}

{
    "document_type": "employment_contract",
    "parameters": {
        "employer_name": "Tech Corp Ltd",
        "employee_name": "John Doe",
        "position": "Software Engineer",
        "salary": 100000
    }
}
```

#### 3. Summarize Legal Document
```http
POST /counsel/summarize
Content-Type: application/json
Authorization: Bearer {token}

{
    "content": "Full text of legal document...",
    "context": "employment law"
}
```

#### 4. Fetch Legal Resources
```http
GET /counsel/fetch-law?query=labor+laws&source=kenya_law&limit=10
Authorization: Bearer {token}
```

#### 5. Health Check
```http
GET /health
```

### Authentication

1. Register:
```http
POST /auth/register
{
    "email": "user@example.com",
    "password": "securepassword",
    "full_name": "John Doe"
}
```

2. Login:
```http
POST /auth/login
{
    "email": "user@example.com",
    "password": "securepassword"
}
```

## 🔐 Environment Variables

```env
# AWS Bedrock Credentials
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/counsel_db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256

# Redis (optional)
REDIS_URL=redis://localhost:6379

# API Configuration
ENVIRONMENT=production
```

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

## 🚢 Deployment

### GitHub Actions CI/CD

The repository includes GitHub Actions workflow for:
- Running tests on pull requests
- Building and pushing Docker images
- Automated deployment notifications

### Production Deployment Options

1. **AWS EC2/ECS**: Deploy Docker container
2. **Railway/Render**: Direct GitHub integration
3. **Replit**: Import and run with Replit configuration
4. **Kubernetes**: Use provided Docker image

## 📊 Architecture

```
counsel-ai-backend/
├── app/
│   ├── api/           # API routes
│   ├── core/          # Security, middleware
│   ├── models/        # Database models
│   ├── services/      # Business logic
│   ├── crawlers/      # Web crawlers
│   └── utils/         # Utilities
├── tests/             # Test suite
├── .github/           # CI/CD workflows
├── Dockerfile         # Container configuration
└── docker-compose.yml # Multi-container setup
```

## 🤝 Frontend Integration

CORS is configured for:
- https://www.legalizeme.site
- https://legalizeme.site
- http://localhost:3000

API responses follow standard REST patterns with appropriate status codes and error messages.

## 📝 License

Copyright 2025 LegalizeMe. All rights reserved.

## 🆘 Support

For issues or questions:
- Create an issue in the GitHub repository
- Contact the development team