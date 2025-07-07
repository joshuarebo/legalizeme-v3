# Counsel AI Backend - Legal Assistant System

## Overview

Counsel AI is a sophisticated AI-powered legal assistant backend specifically designed for Kenyan jurisdiction. The system provides comprehensive legal services including document generation, legal query processing, case law research, and automated crawling of Kenyan legal resources. Built with FastAPI, it integrates multiple AI models and provides a robust API for legal professionals and citizens seeking legal guidance.

## System Architecture

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs with Python 3.7+
- **SQLAlchemy**: ORM for database operations with PostgreSQL
- **Pydantic**: Data validation and settings management
- **Redis**: Caching and session management
- **ChromaDB**: Vector database for document similarity search and retrieval

### AI Integration
- **Primary AI Model**: AWS Bedrock with Claude Sonnet 4 (anthropic.claude-3-sonnet-20240229-v1:0)
- **Alternative Models**: Hunyuan-A13B, MiniMax-01 (optional, via Hugging Face)
- **Embeddings**: SentenceTransformers for document vectorization (optional)
- **Model Context Protocol (MCP)**: Coordinated AI service orchestration
- **AWS Integration**: Uses AWS credentials for Bedrock access (no direct Anthropic API needed)

### Web Crawling System
- **Legal Sources**: Kenya Law website and Parliament of Kenya
- **Document Types**: Judgments, legislation, gazettes, Hansard records, bills
- **Crawler Architecture**: Async-based crawlers with rate limiting and respectful scraping

## Key Components

### 1. Authentication & Security
- JWT-based authentication with HTTPBearer
- Password hashing using bcrypt
- Role-based access control (user/admin)
- Request/response logging and security middleware

### 2. Database Models
- **User**: Authentication and user management
- **Document**: Legal documents with metadata and embeddings
- **Query**: User queries with AI responses and feedback
- **LegalCase**: Court cases with detailed metadata and relationships

### 3. AI Services
- **AIService**: Handles AI model interactions and prompt management
- **VectorService**: Manages document embeddings and similarity search
- **MCPService**: Orchestrates complex legal operations across services
- **DocumentService**: Processes and analyzes legal documents

### 4. Web Crawling
- **KenyaLawCrawler**: Extracts judgments, legislation, and gazettes
- **ParliamentCrawler**: Collects Hansard records, bills, and parliamentary proceedings
- **BaseCrawler**: Common functionality with rate limiting and error handling

### 5. Document Processing
- **PDFParser**: Extracts text from PDF, DOCX, and other formats
- **TextProcessor**: Legal text analysis, keyword extraction, and preprocessing
- **Content Analysis**: Readability scoring and legal term identification

## Data Flow

1. **User Request**: Client sends legal query or document upload
2. **Authentication**: JWT token validation and user identification
3. **Query Processing**: MCP service coordinates AI model selection and processing
4. **Vector Search**: Relevant documents retrieved from ChromaDB
5. **AI Response**: Context-aware legal advice generated using Claude Sonnet 4
6. **Document Storage**: Queries and responses stored in PostgreSQL
7. **Feedback Loop**: User ratings and feedback collected for model improvement

## External Dependencies

### Required Services
- **PostgreSQL**: Primary database for structured data
- **Redis**: Caching and session management
- **ChromaDB**: Vector database for document embeddings

### AI APIs
- **Anthropic Claude**: Primary AI model for legal reasoning
- **AWS Bedrock**: Alternative AI model access
- **Hugging Face**: Local model deployment option

### Web Scraping Targets
- **Kenya Law Website**: https://new.kenyalaw.org (judgments, legislation, gazettes)
- **Parliament of Kenya**: http://parliament.go.ke (Hansard, bills, proceedings)

## Deployment Strategy

### Environment Configuration
- Development, staging, and production environments
- Environment-specific settings via .env files
- Docker containerization ready
- Health checks and monitoring endpoints

### Scaling Considerations
- Async request handling for high concurrency
- Redis caching for frequent queries
- Vector database persistence for document storage
- Rate limiting for external API calls

### Security Measures
- CORS middleware for cross-origin requests
- Request logging and monitoring
- Input validation and sanitization
- Secure password hashing and JWT tokens

## User Preferences

Preferred communication style: Simple, everyday language.

## API Endpoints

All endpoints are prefixed with `/counsel` for production deployment at `https://www.legalizeme.site/counsel`.

- **POST /query**: Answer legal queries with AI assistance
- **POST /generate-document**: Generate legal documents from templates
- **POST /summarize**: Summarize legal documents
- **GET /fetch-law**: Search and retrieve legal resources from Kenya Law and Parliament
- **POST /feedback**: Submit user feedback on query responses
- **GET /history**: Get user's query history

## Deployment Ready

The backend is production-ready with:
- Docker containerization (Dockerfile and docker-compose.yml)
- CI/CD pipeline (GitHub Actions workflow)
- Comprehensive API documentation (README.md and Postman collection)
- Test suite structure
- CORS configured for https://www.legalizeme.site

## Changelog

- July 07, 2025: Initial setup
- July 07, 2025: Integrated AWS Bedrock for Claude access (replaced direct Anthropic API)
- July 07, 2025: Added /fetch-law endpoint for legal resource retrieval
- July 07, 2025: Made heavy ML dependencies optional for lightweight deployment
- July 07, 2025: Created Docker configuration and CI/CD pipeline for production deployment