# 🚀 LegalizeMe Counsel AI - Precise Deployment Steps

## ✅ **STATUS: READY FOR DEPLOYMENT**

Your code is now successfully pushed to GitHub: https://github.com/joshuarebo/legalizeme-v3.git

---

## 📋 **STEP 1: CONFIGURE GITHUB SECRETS**

### 1.1 Navigate to GitHub Secrets
1. Go to https://github.com/joshuarebo/legalizeme-v3
2. Click **"Settings"** tab
3. In the left sidebar, click **"Secrets and variables"**
4. Click **"Actions"**
5. Click **"New repository secret"**

### 1.2 Add Required Secrets (One by One)

**Secret 1: AWS_ACCESS_KEY_ID**
- Name: `AWS_ACCESS_KEY_ID`
- Value: `[Your AWS Access Key ID from your AWS account]`
- Click **"Add secret"**

**Secret 2: AWS_SECRET_ACCESS_KEY**
- Name: `AWS_SECRET_ACCESS_KEY`
- Value: `[Your AWS Secret Access Key from your AWS account]`
- Click **"Add secret"**

**Secret 3: AWS_REGION**
- Name: `AWS_REGION`
- Value: `us-east-1`
- Click **"Add secret"**

**Secret 4: AWS_BEDROCK_MODEL_ID_PRIMARY**
- Name: `AWS_BEDROCK_MODEL_ID_PRIMARY`
- Value: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- Click **"Add secret"**

**Secret 5: AWS_BEDROCK_MODEL_ID_SECONDARY**
- Name: `AWS_BEDROCK_MODEL_ID_SECONDARY`
- Value: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- Click **"Add secret"**

**Secret 6: AWS_BEDROCK_MODEL_ID_FALLBACK**
- Name: `AWS_BEDROCK_MODEL_ID_FALLBACK`
- Value: `mistral.mistral-large-2402-v1:0`
- Click **"Add secret"**

**Secret 7: SECRET_KEY**
- Name: `SECRET_KEY`
- Value: `your-super-secret-key-minimum-32-characters-change-this-in-production-12345`
- Click **"Add secret"**

**Secret 8: HUGGING_FACE_TOKEN**
- Name: `HUGGING_FACE_TOKEN`
- Value: `[Your Hugging Face token from huggingface.co]`
- Click **"Add secret"**

### 1.3 Verify Secrets Added
You should now see 8 secrets in your repository secrets list.

---

## 🚀 **STEP 2: DEPLOY TO RENDER**

### 2.1 Create Render Account
1. Go to https://render.com
2. Sign up or log in
3. Connect your GitHub account

### 2.2 Create PostgreSQL Database
1. Click **"New"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `legalizeme-counsel-db`
   - **Database Name**: `counsel_db`
   - **User**: `counsel_user`
   - **Region**: `Oregon (US West)` or closest to you
   - **Plan**: `Free` (for testing) or `Starter` (for production)
3. Click **"Create Database"**
4. **Wait for database to be ready** (2-3 minutes)

### 2.3 Create Redis Instance (Optional - Skip for Now)
**Note**: Redis is optional. The app will work without it using in-memory caching.

If you want Redis later:
1. Click **"New"** → **"Redis"**
2. Configure:
   - **Name**: `legalizeme-counsel-redis`
   - **Region**: Same as database
   - **Plan**: `Starter` ($7/month minimum)
3. Click **"Create Redis"**
4. **Wait for Redis to be ready** (1-2 minutes)

### 2.4 Create Web Service
1. Click **"New"** → **"Web Service"**
2. **Connect Repository**:
   - Select **"Build and deploy from a Git repository"**
   - Click **"Connect"** next to your GitHub account
   - Select **"joshuarebo/legalizeme-v3"**
   - Click **"Connect"**

3. **Configure Service**:
   - **Name**: `legalizeme-counsel-api`
   - **Environment**: `Python 3`
   - **Region**: Same as database and Redis
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### 2.5 Configure Environment Variables
In the **Environment Variables** section, add these **one by one**:

**Database (Auto-generated)**
- `DATABASE_URL`: Select **"From Database"** → Choose `legalizeme-counsel-db`

**Redis (Optional - Skip for now)**
- `REDIS_URL`: Leave empty or add later if you created Redis service

**AWS Configuration**
- `AWS_ACCESS_KEY_ID`: `[Your AWS Access Key ID]`
- `AWS_SECRET_ACCESS_KEY`: `[Your AWS Secret Access Key]`
- `AWS_REGION`: `us-east-1`

**Model IDs**
- `AWS_BEDROCK_MODEL_ID_PRIMARY`: `us.anthropic.claude-sonnet-4-20250514-v1:0`
- `AWS_BEDROCK_MODEL_ID_SECONDARY`: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- `AWS_BEDROCK_MODEL_ID_FALLBACK`: `mistral.mistral-large-2402-v1:0`

**Security**
- `SECRET_KEY`: `your-super-secret-key-minimum-32-characters-change-this-in-production-12345`

**Application Settings**
- `ENVIRONMENT`: `production`
- `DEBUG`: `false`
- `LOG_LEVEL`: `INFO`
- `DEFAULT_AI_MODEL`: `claude-sonnet-4`
- `FALLBACK_AI_MODEL`: `mistral-large`
- `ENABLE_LOCAL_MODELS`: `false`
- `MODEL_TIMEOUT`: `60`
- `MAX_QUERY_LENGTH`: `2000`
- `ALLOWED_ORIGINS`: `https://www.legalizeme.site,https://legalizeme.site`

**Optional**
- `HUGGING_FACE_TOKEN`: `[Your Hugging Face token]`

### 2.6 Deploy Service
1. Click **"Create Web Service"**
2. **Wait for deployment** (5-10 minutes)
3. Monitor the build logs for any errors

---

## 🧪 **STEP 3: TEST DEPLOYMENT**

### 3.1 Health Check
Once deployed, test the health endpoint:
```bash
curl https://your-app-name.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-08T12:00:00Z",
  "models": {
    "claude-sonnet-4": "healthy",
    "claude-3-7": "healthy",
    "mistral-large": "healthy"
  }
}
```

### 3.2 API Test
Test the main API endpoint:
```bash
curl -X POST https://your-app-name.onrender.com/api/v1/counsel/query-direct \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the constitutional rights in Kenya?",
    "model_preference": "claude-sonnet-4"
  }'
```

### 3.3 Interactive Documentation
Visit: `https://your-app-name.onrender.com/docs`

---

## 🔗 **STEP 4: FRONTEND INTEGRATION**

Update your frontend at `legalizeme.site/counsel` to use the new API:

```javascript
const API_BASE_URL = 'https://your-app-name.onrender.com';

// Example API call
const response = await fetch(`${API_BASE_URL}/api/v1/counsel/query-direct`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'What are employment rights in Kenya?',
    model_preference: 'claude-sonnet-4'
  })
});

const result = await response.json();
console.log(result.response_text);
```

---

## 🎯 **EXPECTED RESULTS**

After successful deployment:
- ✅ **Health endpoint**: Returns healthy status
- ✅ **Claude Sonnet 4**: 8-27s response times
- ✅ **Claude 3.7**: 4-9s response times  
- ✅ **Mistral Large**: 0.6-3s response times
- ✅ **Automatic fallback**: If one model fails, others take over
- ✅ **99.9% uptime**: With proper fallback system

---

## 🆘 **TROUBLESHOOTING**

### Common Issues:

**1. AWS Credentials Error**
- Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in environment variables
- Check AWS Bedrock access in your AWS console

**2. Model Access Denied**
- Ensure your AWS account has access to the specific Bedrock models
- Verify model IDs are correct

**3. Database Connection Error**
- Check DATABASE_URL is properly set from the PostgreSQL service
- Ensure PostgreSQL service is running

**4. Build Failures**
- Check build logs in Render dashboard
- Verify requirements.txt is properly formatted

---

## 🎉 **CONGRATULATIONS!**

Once deployed, your **LegalizeMe Counsel AI** will be live at:
- **API**: `https://your-app-name.onrender.com`
- **Documentation**: `https://your-app-name.onrender.com/docs`
- **Health Check**: `https://your-app-name.onrender.com/health`

**Ready to integrate with legalizeme.site/counsel!** 🚀
