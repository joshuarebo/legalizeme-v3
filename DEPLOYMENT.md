# LegalizeMe Counsel AI - Deployment Guide

This guide covers deploying the LegalizeMe Counsel AI backend to production environments, specifically Render.com.

## 🚀 Production Deployment Overview

### Architecture
- **Backend**: FastAPI with AWS Bedrock integration
- **Database**: PostgreSQL (managed by Render)
- **Cache**: Redis (managed by Render)
- **AI Models**: AWS Bedrock (Claude Sonnet 4, Claude 3.7, Mistral Large)
- **Frontend**: JavaScript deployment at legalizeme.site/counsel

## 📋 Pre-Deployment Checklist

### ✅ AWS Bedrock Setup
- [ ] AWS account with Bedrock access
- [ ] Model access granted for:
  - Claude Sonnet 4 (us.anthropic.claude-sonnet-4-20250514-v1:0)
  - Claude 3.7 (us.anthropic.claude-3-7-sonnet-20250219-v1:0)
  - Mistral Large (mistral.mistral-large-2402-v1:0)
- [ ] AWS credentials with Bedrock permissions

### ✅ Environment Configuration
- [ ] All sensitive data removed from code
- [ ] Environment variables configured
- [ ] .gitignore properly set up
- [ ] Tests passing

## 🔧 Render.com Deployment

### 1. Repository Setup
```bash
# Ensure your repository is clean and pushed to GitHub
git add .
git commit -m "Production ready deployment"
git push origin main
```

### 2. Create Render Services

#### Web Service (FastAPI Backend)
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository: `joshuarebo/legalizeme-v3`
4. Configure the service:

**Basic Settings:**
- **Name**: `legalizeme-counsel-api`
- **Environment**: `Python 3`
- **Region**: `Oregon (US West)` or closest to your users
- **Branch**: `main`

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

#### PostgreSQL Database
1. Click "New" → "PostgreSQL"
2. Configure:
   - **Name**: `legalizeme-counsel-db`
   - **Database Name**: `counsel_db`
   - **User**: `counsel_user`
   - **Region**: Same as web service

#### Redis Instance
1. Click "New" → "Redis"
2. Configure:
   - **Name**: `legalizeme-counsel-redis`
   - **Region**: Same as web service

### 3. Environment Variables

Set these in your Render web service environment variables:

#### Required Variables
```env
# AWS Bedrock Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1

# AWS Bedrock Model IDs
AWS_BEDROCK_MODEL_ID_PRIMARY=us.anthropic.claude-sonnet-4-20250514-v1:0
AWS_BEDROCK_MODEL_ID_SECONDARY=us.anthropic.claude-3-7-sonnet-20250219-v1:0
AWS_BEDROCK_MODEL_ID_FALLBACK=mistral.mistral-large-2402-v1:0

# Security
SECRET_KEY=your-super-secret-key-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
MAX_QUERY_LENGTH=2000

# CORS Settings
ALLOWED_ORIGINS=https://www.legalizeme.site,https://legalizeme.site

# Model Configuration
DEFAULT_AI_MODEL=claude-sonnet-4
FALLBACK_AI_MODEL=mistral-large
ENABLE_LOCAL_MODELS=false
MODEL_TIMEOUT=60

# Performance
WORKERS=4
MAX_REQUESTS=1000
KEEPALIVE_TIMEOUT=2

# Security Headers
SECURE_SSL_REDIRECT=true
SECURE_HSTS_SECONDS=31536000
SECURE_CONTENT_TYPE_NOSNIFF=true
SECURE_BROWSER_XSS_FILTER=true
```

#### Auto-Generated Variables (Render provides these)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `PORT` - Application port

### 4. Health Checks

Render will automatically configure health checks using:
- **Health Check Path**: `/health`
- **Expected Status**: `200`

## 🔒 Security Configuration

### Environment Variables Security
1. **Never commit sensitive data** to the repository
2. **Use Render's environment variables** for all secrets
3. **Rotate credentials regularly**
4. **Use least-privilege AWS IAM policies**

### AWS IAM Policy (Minimum Required)
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": [
                "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-*",
                "arn:aws:bedrock:us-east-1::foundation-model/mistral.*"
            ]
        }
    ]
}
```

## 📊 Monitoring & Logging

### Render Monitoring
- **Metrics**: CPU, Memory, Response times
- **Logs**: Real-time application logs
- **Alerts**: Configure for high error rates or downtime

### Application Monitoring
```python
# Health check endpoint provides:
{
    "status": "healthy",
    "timestamp": "2025-01-08T12:00:00Z",
    "models": {
        "claude-sonnet-4": "healthy",
        "claude-3-7": "healthy", 
        "mistral-large": "healthy"
    },
    "database": "connected",
    "redis": "connected"
}
```

## 🚀 Deployment Process

### Automatic Deployment
1. **Push to main branch** triggers automatic deployment
2. **Build process** installs dependencies
3. **Health checks** verify deployment
4. **Traffic routing** switches to new version

### Manual Deployment
```bash
# From Render dashboard
1. Go to your web service
2. Click "Manual Deploy"
3. Select branch and commit
4. Monitor deployment logs
```

## 🧪 Post-Deployment Testing

### 1. Health Check
```bash
curl https://your-app.onrender.com/health
```

### 2. API Functionality
```bash
curl -X POST https://your-app.onrender.com/api/v1/counsel/query-direct \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the constitutional rights in Kenya?",
    "model_preference": "claude-sonnet-4"
  }'
```

### 3. Model Fallback
```bash
# Test each model specifically
curl -X POST https://your-app.onrender.com/api/v1/counsel/query-direct \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Test query",
    "model_preference": "mistral-large"
  }'
```

## 🔧 Troubleshooting

### Common Issues

#### 1. AWS Credentials Error
```
Error: AWS credentials not found
```
**Solution**: Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in environment variables

#### 2. Model Access Denied
```
Error: AccessDeniedException when calling InvokeModel
```
**Solution**: Ensure your AWS account has access to the specific Bedrock models

#### 3. Database Connection Error
```
Error: could not connect to server
```
**Solution**: Check DATABASE_URL environment variable and PostgreSQL service status

#### 4. Redis Connection Error
```
Error: Redis connection failed
```
**Solution**: Verify REDIS_URL and Redis service status

### Performance Optimization

#### 1. Response Time Optimization
- **Enable Redis caching** for frequent queries
- **Use connection pooling** for database
- **Implement request batching** for multiple queries

#### 2. Scaling Configuration
```env
# For high traffic
WORKERS=8
MAX_REQUESTS=2000
WORKER_CONNECTIONS=1000
```

## 📈 Scaling & Maintenance

### Horizontal Scaling
- **Render Pro Plan**: Auto-scaling based on CPU/memory
- **Load balancing**: Automatic across multiple instances
- **Database scaling**: Upgrade PostgreSQL plan as needed

### Maintenance Tasks
1. **Monitor model performance** weekly
2. **Update dependencies** monthly
3. **Rotate AWS credentials** quarterly
4. **Review logs** for errors and optimization opportunities

## 🔄 CI/CD Pipeline

### GitHub Actions (Optional)
```yaml
# .github/workflows/deploy.yml
name: Deploy to Render
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest
```

---

**🚀 Your LegalizeMe Counsel AI is now ready for production!**

**📍 Next Steps:**
1. Configure your frontend at legalizeme.site/counsel to use the new API
2. Set up monitoring and alerting
3. Plan for scaling based on usage patterns
