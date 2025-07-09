# AWS ECS Fargate Deployment Script for Counsel AI Legal Backend (PowerShell)
# This script automates the complete deployment process

param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "counsel-cluster",
    [string]$ServiceName = "counsel-service",
    [string]$TaskFamily = "counsel-task",
    [string]$ECRRepoName = "counsel-ai",
    [string]$ALBName = "counsel-alb",
    [string]$TargetGroupName = "counsel-targets"
)

# Error handling
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting AWS ECS Fargate Deployment for Counsel AI" -ForegroundColor Blue

try {
    # Get AWS Account ID
    Write-Host "📋 Getting AWS Account ID..." -ForegroundColor Yellow
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "✓ AWS Account ID: $AccountId" -ForegroundColor Green

    # Step 1: Create ECR Repository
    Write-Host "📦 Step 1: Creating ECR Repository..." -ForegroundColor Yellow
    try {
        aws ecr describe-repositories --repository-names $ECRRepoName --region $Region 2>$null
        Write-Host "✓ ECR Repository already exists" -ForegroundColor Green
    }
    catch {
        aws ecr create-repository --repository-name $ECRRepoName --region $Region
        Write-Host "✓ ECR Repository created" -ForegroundColor Green
    }

    # Step 2: Build and Push Docker Image
    Write-Host "🐳 Step 2: Building and pushing Docker image..." -ForegroundColor Yellow
    
    # Login to ECR
    $LoginCommand = aws ecr get-login-password --region $Region
    $LoginCommand | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"
    
    # Build and tag image
    docker build -f Dockerfile.ecs -t $ECRRepoName .
    docker tag "${ECRRepoName}:latest" "$AccountId.dkr.ecr.$Region.amazonaws.com/${ECRRepoName}:latest"
    docker push "$AccountId.dkr.ecr.$Region.amazonaws.com/${ECRRepoName}:latest"
    Write-Host "✓ Docker image pushed to ECR" -ForegroundColor Green

    # Step 3: Create CloudWatch Log Group
    Write-Host "📊 Step 3: Creating CloudWatch Log Group..." -ForegroundColor Yellow
    try {
        aws logs describe-log-groups --log-group-name-prefix "/ecs/counsel-task" --region $Region 2>$null | Out-Null
        Write-Host "✓ CloudWatch Log Group already exists" -ForegroundColor Green
    }
    catch {
        aws logs create-log-group --log-group-name "/ecs/counsel-task" --region $Region
        Write-Host "✓ CloudWatch Log Group created" -ForegroundColor Green
    }

    # Step 4: Create IAM Roles
    Write-Host "🔐 Step 4: Creating IAM Roles..." -ForegroundColor Yellow

    # Trust policy for ECS tasks
    $TrustPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{
                    Service = "ecs-tasks.amazonaws.com"
                }
                Action = "sts:AssumeRole"
            }
        )
    } | ConvertTo-Json -Depth 10

    $TrustPolicy | Out-File -FilePath "trust-policy.json" -Encoding UTF8

    # Create execution role if it doesn't exist
    try {
        aws iam get-role --role-name ecsTaskExecutionRole 2>$null | Out-Null
        Write-Host "✓ ECS Task Execution Role already exists" -ForegroundColor Green
    }
    catch {
        aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file://trust-policy.json
        Write-Host "✓ ECS Task Execution Role created" -ForegroundColor Green
    }

    aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

    # Task Role with Bedrock permissions
    $TaskRolePolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @(
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                )
                Resource = "*"
            },
            @{
                Effect = "Allow"
                Action = @(
                    "ssm:GetParameter",
                    "ssm:GetParameters"
                )
                Resource = "arn:aws:ssm:${Region}:${AccountId}:parameter/counsel/*"
            },
            @{
                Effect = "Allow"
                Action = @(
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                )
                Resource = "*"
            }
        )
    } | ConvertTo-Json -Depth 10

    $TaskRolePolicy | Out-File -FilePath "task-role-policy.json" -Encoding UTF8

    try {
        aws iam get-role --role-name counsel-task-role 2>$null | Out-Null
        Write-Host "✓ Counsel Task Role already exists" -ForegroundColor Green
    }
    catch {
        aws iam create-role --role-name counsel-task-role --assume-role-policy-document file://trust-policy.json
        Write-Host "✓ Counsel Task Role created" -ForegroundColor Green
    }

    aws iam put-role-policy --role-name counsel-task-role --policy-name CounselTaskPolicy --policy-document file://task-role-policy.json
    Write-Host "✓ IAM Roles configured" -ForegroundColor Green

    # Step 5: Store secrets in Parameter Store
    Write-Host "🔑 Step 5: Storing secrets in Parameter Store..." -ForegroundColor Yellow
    Write-Host "Please provide the following credentials:" -ForegroundColor Cyan

    $AwsAccessKeyId = Read-Host "AWS Access Key ID"
    $AwsSecretAccessKey = Read-Host "AWS Secret Access Key" -AsSecureString
    $SecretKey = Read-Host "Secret Key (32+ characters)" -AsSecureString
    $HuggingFaceToken = Read-Host "Hugging Face Token" -AsSecureString

    # Convert secure strings to plain text for AWS CLI
    $AwsSecretAccessKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($AwsSecretAccessKey))
    $SecretKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecretKey))
    $HuggingFaceTokenPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($HuggingFaceToken))

    aws ssm put-parameter --name "/counsel/aws-access-key-id" --value $AwsAccessKeyId --type "SecureString" --overwrite
    aws ssm put-parameter --name "/counsel/aws-secret-access-key" --value $AwsSecretAccessKeyPlain --type "SecureString" --overwrite
    aws ssm put-parameter --name "/counsel/secret-key" --value $SecretKeyPlain --type "SecureString" --overwrite
    aws ssm put-parameter --name "/counsel/hugging-face-token" --value $HuggingFaceTokenPlain --type "SecureString" --overwrite

    Write-Host "✓ Secrets stored in Parameter Store" -ForegroundColor Green

    # Step 6: Create ECS Cluster
    Write-Host "🏗️ Step 6: Creating ECS Cluster..." -ForegroundColor Yellow
    try {
        $ClusterStatus = aws ecs describe-clusters --clusters $ClusterName --region $Region 2>$null | ConvertFrom-Json
        if ($ClusterStatus.clusters[0].status -eq "ACTIVE") {
            Write-Host "✓ ECS Cluster already exists and is active" -ForegroundColor Green
        }
    }
    catch {
        aws ecs create-cluster --cluster-name $ClusterName --capacity-providers FARGATE --region $Region
        Write-Host "✓ ECS Cluster created" -ForegroundColor Green
    }

    # Update task definition with account ID
    Write-Host "📝 Updating task definition with Account ID..." -ForegroundColor Yellow
    $TaskDefinition = Get-Content "aws-ecs-deployment.json" | ConvertFrom-Json
    $TaskDefinition.executionRoleArn = $TaskDefinition.executionRoleArn -replace "ACCOUNT_ID", $AccountId
    $TaskDefinition.taskRoleArn = $TaskDefinition.taskRoleArn -replace "ACCOUNT_ID", $AccountId
    $TaskDefinition.containerDefinitions[0].image = $TaskDefinition.containerDefinitions[0].image -replace "ACCOUNT_ID", $AccountId
    
    # Update secrets ARNs
    foreach ($secret in $TaskDefinition.containerDefinitions[0].secrets) {
        $secret.valueFrom = $secret.valueFrom -replace "ACCOUNT_ID", $AccountId
    }
    
    $TaskDefinition | ConvertTo-Json -Depth 10 | Out-File "aws-ecs-deployment-updated.json" -Encoding UTF8
    Write-Host "✓ Task definition updated" -ForegroundColor Green

    Write-Host "🎉 Deployment preparation complete!" -ForegroundColor Green
    Write-Host "Next steps:" -ForegroundColor Blue
    Write-Host "1. Review aws-ecs-deployment-updated.json" -ForegroundColor White
    Write-Host "2. Create VPC and subnets if needed" -ForegroundColor White
    Write-Host "3. Create Application Load Balancer" -ForegroundColor White
    Write-Host "4. Register task definition and create service" -ForegroundColor White
    Write-Host ""
    Write-Host "Account ID: $AccountId" -ForegroundColor Cyan
    Write-Host "ECR Repository: $AccountId.dkr.ecr.$Region.amazonaws.com/$ECRRepoName" -ForegroundColor Cyan

}
catch {
    Write-Host "❌ Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    # Cleanup temporary files
    if (Test-Path "trust-policy.json") { Remove-Item "trust-policy.json" }
    if (Test-Path "task-role-policy.json") { Remove-Item "task-role-policy.json" }
}

Write-Host "✅ AWS ECS Infrastructure Setup Complete!" -ForegroundColor Green
