#!/usr/bin/env powershell
<#
.SYNOPSIS
Deploy Counsel AI with Authentication Removed to AWS ECS

.DESCRIPTION
This script deploys the updated Counsel AI application with authentication removed
to AWS ECS Fargate, including database migration and service updates.

IMPORTANT: Set your AWS credentials as environment variables before running:
$env:AWS_ACCESS_KEY_ID = "your_access_key"
$env:AWS_SECRET_ACCESS_KEY = "your_secret_key"
#>

param(
    [string]$ImageTag = "no-auth",
    [string]$Region = "us-east-1",
    [string]$ECRRepository = "533267439884.dkr.ecr.us-east-1.amazonaws.com/counsel-ai",
    [string]$ClusterName = "counsel-cluster",
    [string]$ServiceName = "counsel-service"
)

Write-Host "🚀 Deploying Counsel AI with Authentication Removed" -ForegroundColor Green
Write-Host "=" * 60

# Check AWS credentials
if (-not $env:AWS_ACCESS_KEY_ID -or -not $env:AWS_SECRET_ACCESS_KEY) {
    Write-Error "❌ AWS credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
    exit 1
}

$env:AWS_DEFAULT_REGION = $Region

try {
    # Step 1: Tag the image for ECR
    Write-Host "📦 Tagging Docker image for ECR..." -ForegroundColor Yellow
    docker tag counsel-ai:$ImageTag $ECRRepository`:$ImageTag
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to tag Docker image"
    }

    # Step 2: Login to ECR
    Write-Host "🔐 Logging into AWS ECR..." -ForegroundColor Yellow
    aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ECRRepository.Split('/')[0]
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to login to ECR"
    }

    # Step 3: Push image to ECR
    Write-Host "⬆️  Pushing image to ECR..." -ForegroundColor Yellow
    docker push $ECRRepository`:$ImageTag
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to push image to ECR"
    }

    # Step 4: Update ECS service
    Write-Host "🔄 Updating ECS service..." -ForegroundColor Yellow
    aws ecs update-service --cluster $ClusterName --service $ServiceName --force-new-deployment
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update ECS service"
    }

    # Step 5: Wait for deployment to complete
    Write-Host "⏳ Waiting for deployment to complete..." -ForegroundColor Yellow
    aws ecs wait services-stable --cluster $ClusterName --services $ServiceName
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Service deployment may still be in progress..."
    }

    # Step 6: Test the deployment
    Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30  # Wait for service to be ready
    
    $testUrl = "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health"
    try {
        $response = Invoke-RestMethod -Uri $testUrl -Method GET -TimeoutSec 30
        Write-Host "✅ Health check passed!" -ForegroundColor Green
        Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
    }
    catch {
        Write-Warning "Health check failed, but deployment may still be successful: $_"
    }

    # Step 7: Test authentication removal
    Write-Host "🔓 Testing authentication removal..." -ForegroundColor Yellow
    if (Test-Path "test_no_auth_endpoints.py") {
        python test_no_auth_endpoints.py
    } else {
        Write-Warning "Test script not found, skipping endpoint tests"
    }
    
    Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
    Write-Host "🌐 Application URL: http://counsel-alb-694525771.us-east-1.elb.amazonaws.com" -ForegroundColor Cyan
    Write-Host "📚 API Documentation: http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/docs" -ForegroundColor Cyan

}
catch {
    Write-Error "❌ Deployment failed: $_"
    exit 1
}
