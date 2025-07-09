# 🔐 Credentials Configuration Template

## ⚠️ IMPORTANT SECURITY NOTICE
**Never commit actual credentials to version control!**

This template shows where to place your actual credentials. Replace the placeholder values with your real credentials when deploying.

---

## 🔑 Required Credentials

### AWS Credentials
```bash
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
AWS_REGION=us-east-1
```

### Application Secrets
```bash
SECRET_KEY=YOUR_SECRET_KEY_FOR_JWT
```

### AI Model Tokens
```bash
HUGGING_FACE_TOKEN=YOUR_HUGGING_FACE_TOKEN
```

---

## 📋 How to Use

### 1. For Local Development
Create a `.env` file in your project root:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 2. For AWS ECS Deployment
Update the task definition files with your credentials:
- `aws-ecs-deployment.json`
- `aws-ecs-deployment-fixed.json`
- `deploy-simple-infrastructure.ps1`

### 3. For Production (Recommended)
Use AWS Parameter Store or Secrets Manager:
```bash
# Store credentials securely
aws ssm put-parameter --name "/counsel/aws-access-key" --value "YOUR_KEY" --type "SecureString"
aws ssm put-parameter --name "/counsel/aws-secret-key" --value "YOUR_SECRET" --type "SecureString"
aws ssm put-parameter --name "/counsel/secret-key" --value "YOUR_JWT_SECRET" --type "SecureString"
aws ssm put-parameter --name "/counsel/hf-token" --value "YOUR_HF_TOKEN" --type "SecureString"
```

---

## 🛡️ Security Best Practices

1. **Never commit credentials to Git**
2. **Use environment variables for local development**
3. **Use AWS Parameter Store/Secrets Manager for production**
4. **Rotate credentials regularly**
5. **Use least privilege IAM policies**
6. **Enable AWS CloudTrail for audit logging**

---

## 🔄 Credential Rotation

### AWS Keys
1. Create new access key in AWS Console
2. Update all deployment configurations
3. Test new credentials
4. Delete old access key

### JWT Secret
1. Generate new secret: `openssl rand -base64 32`
2. Update all configurations
3. Restart all services

### Hugging Face Token
1. Generate new token in HF settings
2. Update configurations
3. Test model access

---

## 📞 Support

If you need help with credential configuration:
1. Check AWS IAM console for key status
2. Verify Parameter Store values
3. Test credentials with AWS CLI: `aws sts get-caller-identity`
4. Review CloudWatch logs for authentication errors
