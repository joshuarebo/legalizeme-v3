# 🚀 QUICK FIX: Enable HTTPS for CounselAI Backend

## 📋 Problem Summary
- ✅ Backend is **WORKING PERFECTLY** on HTTP
- ❌ Frontend cannot access via HTTPS (connection timeout)
- 🔧 **Root Cause:** ALB missing HTTPS listener on port 443

---

## ⚡ IMMEDIATE WORKAROUND (5 minutes)

### Tell Frontend Team to Use HTTP Temporarily

**Change frontend API base URL from:**
```
https://counsel-alb-694525771.us-east-1.elb.amazonaws.com
```

**To:**
```
http://counsel-alb-694525771.us-east-1.elb.amazonaws.com
```

**Test it works:**
```bash
curl http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live
# Response: {"status":"alive","timestamp":"...","message":"Counsel AI Backend is running"}

curl http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/api/v1/info
# Response: Full API information
```

⚠️ **WARNING:** This is HTTP (not secure). Use only for testing!

---

## 🔒 PERMANENT FIX: Add HTTPS Listener (30 minutes)

### Option A: Using AWS Console (Easiest)

#### Step 1: Get or Create SSL Certificate

**Go to AWS Certificate Manager (ACM):**
1. Open AWS Console → Certificate Manager
2. Region: **us-east-1** (must match ALB region)
3. Click "Request certificate"
4. Choose "Request a public certificate"
5. Enter domain name (e.g., `api.legalizeme.co.ke` or `*.legalizeme.co.ke`)
6. Validation method: DNS (recommended) or Email
7. Click "Request"
8. **Complete DNS validation** (add CNAME records to your DNS)
9. Wait for status to become "Issued"
10. **Copy the Certificate ARN** (looks like: `arn:aws:acm:us-east-1:585008043505:certificate/xxxxx`)

**OR use existing certificate:**
- If you already have a certificate in ACM, just copy its ARN

#### Step 2: Add HTTPS Listener to Load Balancer

1. **Go to:** EC2 Console → Load Balancers
2. **Select:** `counsel-alb`
3. **Click:** "Listeners and rules" tab
4. **Click:** "Add listener" button
5. **Configure:**
   - **Protocol:** HTTPS
   - **Port:** 443
   - **Default action:** Forward to → Select `counsel-targets`
   - **Security policy:** ELBSecurityPolicy-TLS13-1-2-2021-06 (recommended)
   - **Default SSL/TLS certificate:** 
     - Choose "From ACM"
     - Select your certificate from dropdown
6. **Click:** "Add"

#### Step 3: Update Security Group

1. **In Load Balancer details**, click on the Security Group (sg-0c806fa2a8d706486)
2. **Click:** "Edit inbound rules"
3. **Click:** "Add rule"
4. **Configure:**
   - **Type:** HTTPS
   - **Protocol:** TCP
   - **Port:** 443
   - **Source:** 0.0.0.0/0 (Anywhere IPv4)
5. **Click:** "Add rule" again for IPv6:
   - **Type:** HTTPS
   - **Protocol:** TCP
   - **Port:** 443
   - **Source:** ::/0 (Anywhere IPv6)
6. **Click:** "Save rules"

#### Step 4: Test HTTPS Endpoint

```bash
# Should now work!
curl https://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live

# Expected response:
# {"status":"alive","timestamp":"...","message":"Counsel AI Backend is running"}
```

---

### Option B: Using AWS CLI (For Automation)

#### Prerequisites
```bash
# Set AWS credentials (replace with your own credentials)
$env:AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
$env:AWS_DEFAULT_REGION="us-east-1"
```

#### Step 1: Request Certificate (if needed)
```bash
# Request certificate for your domain
aws acm request-certificate \
  --domain-name api.legalizeme.co.ke \
  --validation-method DNS \
  --region us-east-1

# Note the CertificateArn from the output
```

#### Step 2: Add Security Group Rule
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-0c806fa2a8d706486 \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

#### Step 3: Create HTTPS Listener
```bash
# Replace YOUR-CERTIFICATE-ARN with actual ARN
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:585008043505:loadbalancer/app/counsel-alb/16e7673184dc51c5 \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=YOUR-CERTIFICATE-ARN \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:us-east-1:585008043505:targetgroup/counsel-targets/fc001c3a020a5821 \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --region us-east-1
```

#### Step 4: (Optional) Redirect HTTP to HTTPS
```bash
# Get HTTP listener ARN
aws elbv2 describe-listeners \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:585008043505:loadbalancer/app/counsel-alb/16e7673184dc51c5 \
  --region us-east-1

# Modify HTTP listener to redirect to HTTPS
aws elbv2 modify-listener \
  --listener-arn <HTTP-LISTENER-ARN> \
  --default-actions Type=redirect,RedirectConfig="{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}" \
  --region us-east-1
```

---

### Option C: Using PowerShell Script

We've created a script for you:

```powershell
# First, get your certificate ARN from ACM
# Then run:
.\fix-https-listener.ps1 -CertificateArn "arn:aws:acm:us-east-1:585008043505:certificate/YOUR-CERT-ID"

# To also enable HTTP to HTTPS redirect:
.\fix-https-listener.ps1 -CertificateArn "arn:aws:acm:us-east-1:585008043505:certificate/YOUR-CERT-ID" -UseHTTPRedirect
```

---

## 🎯 RECOMMENDED: Set Up Custom Domain

### Why?
- Professional URL: `https://api.legalizeme.co.ke` instead of `https://counsel-alb-694525771...`
- Better for production
- Easier to remember
- Can change backend without changing frontend

### How?

1. **Request ACM Certificate for your domain:**
   - Domain: `api.legalizeme.co.ke` or `*.legalizeme.co.ke`
   - Validate via DNS

2. **Create Route53 Record:**
   - Go to Route53 → Hosted Zones
   - Select your domain (`legalizeme.co.ke`)
   - Create Record:
     - Name: `api`
     - Type: `A` (Alias)
     - Alias to: Application Load Balancer
     - Region: us-east-1
     - Load Balancer: counsel-alb

3. **Update HTTPS Listener:**
   - Use the certificate for `api.legalizeme.co.ke`

4. **Update Frontend:**
   - API Base URL: `https://api.legalizeme.co.ke`

---

## ✅ VERIFICATION CHECKLIST

After adding HTTPS listener:

- [ ] HTTPS endpoint responds: `curl https://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live`
- [ ] HTTP endpoint still works: `curl http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live`
- [ ] Security group allows port 443
- [ ] Certificate is valid and issued
- [ ] Frontend can access HTTPS endpoint
- [ ] All API endpoints work via HTTPS

---

## 📞 COMMUNICATION WITH FRONTEND TEAM

### Email Template

```
Subject: CounselAI Backend - HTTPS Configuration Update

Hi Frontend Team,

The backend is fully operational and healthy. The issue was that the load balancer 
was only configured for HTTP, not HTTPS.

IMMEDIATE WORKAROUND (for testing):
Use HTTP endpoint: http://counsel-alb-694525771.us-east-1.elb.amazonaws.com

PERMANENT FIX (in progress):
We're adding HTTPS listener to the load balancer. Once complete, you can use:
https://counsel-alb-694525771.us-east-1.elb.amazonaws.com

OR (recommended for production):
https://api.legalizeme.co.ke (custom domain with SSL)

ETA: 30 minutes for HTTPS setup

All endpoints are working:
- GET /health/live
- GET /api/v1/info
- POST /api/v1/counsel/query
- etc.

Let me know if you need any assistance!
```

---

## 🔍 TROUBLESHOOTING

### Issue: Certificate validation pending
**Solution:** Complete DNS validation by adding CNAME records to your DNS provider

### Issue: HTTPS still times out after adding listener
**Solution:** Check security group allows port 443 inbound from 0.0.0.0/0

### Issue: Certificate not showing in dropdown
**Solution:** Make sure certificate is in us-east-1 region (same as ALB)

### Issue: "Certificate not valid for domain"
**Solution:** Certificate domain must match the domain you're accessing

---

## 📚 ADDITIONAL RESOURCES

- **Full Diagnosis Report:** See `INFRASTRUCTURE_DIAGNOSIS_REPORT.md`
- **Automated Script:** See `fix-https-listener.ps1`
- **AWS Documentation:** [ALB HTTPS Listeners](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html)
- **ACM Documentation:** [Request Certificate](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html)

---

## 🎉 SUCCESS CRITERIA

You'll know it's working when:
1. ✅ `curl https://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health/live` returns 200 OK
2. ✅ Frontend can make API calls via HTTPS
3. ✅ No SSL certificate warnings in browser
4. ✅ All endpoints accessible via HTTPS

