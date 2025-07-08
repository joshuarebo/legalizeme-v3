# Kenyan Legal AI - Production Deployment Guide

## 🚀 Quick Deployment to Render

### Prerequisites
- GitHub repository with your code
- Render account
- Environment variables configured

### 1. Environment Variables Setup

Create these environment variables in Render dashboard or GitHub secrets:

#### Required Variables
```bash
SECRET_KEY=your-secret-key-here
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
ANTHROPIC_API_KEY=your-anthropic-api-key
HUGGING_FACE_TOKEN=your-huggingface-token
```

#### Database & Cache
```bash
DATABASE_URL=postgresql://user:password@host:port/database
REDIS_URL=redis://user:password@host:port
```

#### Application Configuration
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://your-frontend-domain.com
```

#### AI Model Configuration
```bash
DEFAULT_AI_MODEL=claude-sonnet-4
FALLBACK_AI_MODEL=hunyuan
ENABLE_LOCAL_MODELS=false
ENABLE_MODEL_FINE_TUNING=false
MODEL_TIMEOUT=60
```

#### Security & Performance
```bash
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
MAX_DOCUMENT_SIZE=10485760
MAX_QUERY_LENGTH=2000
ENABLE_SECURITY_MIDDLEWARE=true
```

### 2. Render Service Configuration

#### Web Service
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
- **Health Check Path**: `/health`
- **Plan**: Standard (recommended for production)

#### Database Service
- **Type**: PostgreSQL
- **Plan**: Starter or higher
- **Database Name**: `kenyan_legal_ai`

#### Redis Service
- **Type**: Redis
- **Plan**: Starter or higher
- **Max Memory Policy**: `allkeys-lru`

### 3. Deployment Steps

1. **Fork/Clone Repository**
   ```bash
   git clone https://github.com/your-username/KenyanLegalAI.git
   cd KenyanLegalAI
   ```

2. **Validate Environment**
   ```bash
   python scripts/deploy_render.py --validate-only
   ```

3. **Prepare Deployment**
   ```bash
   python scripts/deploy_render.py --prepare-only
   ```

4. **Deploy to Render**
   - Connect your GitHub repository to Render
   - Configure environment variables
   - Deploy using `render.yaml` configuration

5. **Verify Deployment**
   ```bash
   python scripts/deploy_render.py --verify-url https://your-app.onrender.com
   ```

### 4. Post-Deployment Verification

#### Health Checks
- ✅ `/health` - Basic health check
- ✅ `/models/health` - AI models health
- ✅ `/metrics` - System metrics

#### API Endpoints
- ✅ `/counsel/query` - AI query processing
- ✅ `/counsel/generate-document` - Document generation
- ✅ `/models/status` - Model management

#### Performance Monitoring
- Response times < 5 seconds
- Error rates < 5%
- Cache hit rates > 70%

## 🔧 Local Development Setup

### 1. Environment Setup
```bash
# Clone repository
git clone https://github.com/your-username/KenyanLegalAI.git
cd KenyanLegalAI

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Database Setup
```bash
# Start PostgreSQL and Redis (using Docker)
docker-compose up -d postgres redis

# Run migrations
python -m alembic upgrade head
```

### 4. Generate Training Data
```bash
python scripts/prepare_training_data.py
```

### 5. Start Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🛡️ Security Configuration

### Rate Limiting
- **General API**: 100 requests/hour
- **AI Queries**: 50 requests/hour
- **Document Generation**: 20 requests/hour
- **Model Management**: 10 requests/hour (admin only)

### Content Validation
- Max request size: 10MB
- Max query length: 2000 characters
- XSS protection enabled
- SQL injection protection enabled

### Security Headers
- Content Security Policy
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- HSTS (HTTPS only)

## 📊 Monitoring & Observability

### Key Metrics
- Request/response times
- Error rates by endpoint
- Model performance metrics
- Cache hit rates
- Rate limiting statistics

### Logging
- Structured JSON logging
- Request/response logging
- Security event logging
- Performance metrics logging

### Health Checks
- Application health: `/health`
- Model health: `/models/health`
- System metrics: `/metrics`

## 🔄 CI/CD Pipeline

### GitHub Actions (Optional)
```yaml
name: Deploy to Render
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate deployment
        run: python scripts/deploy_render.py --validate-only
      - name: Deploy to Render
        # Render auto-deploys on push to main
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Model Loading Failures
```bash
# Check model status
curl https://your-app.onrender.com/models/status

# Reload models
curl -X POST https://your-app.onrender.com/models/reload \
  -H "Authorization: Bearer your-admin-token" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "claude-sonnet-4"}'
```

#### 2. High Error Rates
```bash
# Check system metrics
curl https://your-app.onrender.com/metrics

# Optimize models
curl -X POST https://your-app.onrender.com/models/optimize \
  -H "Authorization: Bearer your-admin-token"
```

#### 3. Slow Response Times
- Check Redis connection
- Verify database performance
- Monitor model response times
- Check rate limiting settings

### Performance Optimization

#### 1. Enable Caching
```bash
CACHE_ENHANCEMENTS=true
MODEL_CACHE_TTL=3600
```

#### 2. Optimize Models
```bash
ENABLE_LOCAL_MODELS=false  # For production
MODEL_TIMEOUT=30
MAX_ENHANCEMENT_TIME=15.0
```

#### 3. Scale Resources
- Upgrade Render plan
- Increase worker count
- Optimize database queries

## 📈 Scaling Considerations

### Horizontal Scaling
- Multiple Render instances
- Load balancer configuration
- Shared Redis cache
- Database connection pooling

### Vertical Scaling
- Upgrade Render plan
- Increase memory allocation
- Optimize worker configuration

### Model Scaling
- Model-specific instances
- GPU-enabled instances for local models
- Model load balancing

## 🔐 Security Best Practices

### Environment Variables
- Use Render's secret management
- Rotate keys regularly
- Separate staging/production secrets

### API Security
- Implement proper authentication
- Use HTTPS only
- Enable rate limiting
- Validate all inputs

### Data Protection
- Encrypt sensitive data
- Implement audit logging
- Regular security updates
- GDPR compliance considerations

## 📞 Support & Maintenance

### Regular Tasks
- Monitor system health
- Update dependencies
- Rotate security keys
- Review performance metrics
- Update training data

### Emergency Procedures
- Model fallback activation
- Service restart procedures
- Database backup/restore
- Security incident response

For additional support, check the logs and metrics endpoints, or refer to the troubleshooting section above.
