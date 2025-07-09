# Simple AWS Infrastructure Deployment for Counsel AI
# This script creates the basic infrastructure without complex features

param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "counsel-cluster",
    [string]$ServiceName = "counsel-service"
)

$ErrorActionPreference = "Stop"

Write-Host "Deploying Simple AWS Infrastructure for Counsel AI" -ForegroundColor Blue

try {
    # Get Account ID
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "AWS Account ID: $AccountId" -ForegroundColor Green

    # Step 1: Check if ECS cluster exists, create if not
    Write-Host "Step 1: Setting up ECS Cluster..." -ForegroundColor Yellow
    
    $ExistingCluster = aws ecs describe-clusters --clusters $ClusterName 2>$null
    if ($LASTEXITCODE -ne 0) {
        aws ecs create-cluster --cluster-name $ClusterName --capacity-providers FARGATE
        Write-Host "ECS Cluster created: $ClusterName" -ForegroundColor Green
    } else {
        Write-Host "ECS Cluster already exists: $ClusterName" -ForegroundColor Green
    }

    # Step 2: Check if ECR repository exists
    Write-Host "Step 2: Setting up ECR Repository..." -ForegroundColor Yellow
    
    $ExistingRepo = aws ecr describe-repositories --repository-names counsel-ai 2>$null
    if ($LASTEXITCODE -ne 0) {
        aws ecr create-repository --repository-name counsel-ai --region $Region
        Write-Host "ECR Repository created: counsel-ai" -ForegroundColor Green
    } else {
        Write-Host "ECR Repository already exists: counsel-ai" -ForegroundColor Green
    }

    # Step 3: Build and push Docker image
    Write-Host "Step 3: Building and pushing Docker image..." -ForegroundColor Yellow
    
    # Login to ECR
    aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"
    
    # Build image
    docker build -f Dockerfile.ecs -t counsel-ai .
    docker tag counsel-ai:latest "$AccountId.dkr.ecr.$Region.amazonaws.com/counsel-ai:latest"
    docker push "$AccountId.dkr.ecr.$Region.amazonaws.com/counsel-ai:latest"
    
    Write-Host "Docker image pushed successfully" -ForegroundColor Green

    # Step 4: Create CloudWatch Log Group
    Write-Host "Step 4: Setting up CloudWatch Logs..." -ForegroundColor Yellow
    
    $ExistingLogGroup = aws logs describe-log-groups --log-group-name-prefix "/ecs/counsel-task" 2>$null
    if ($LASTEXITCODE -ne 0) {
        aws logs create-log-group --log-group-name "/ecs/counsel-task" --region $Region
        Write-Host "CloudWatch Log Group created" -ForegroundColor Green
    } else {
        Write-Host "CloudWatch Log Group already exists" -ForegroundColor Green
    }

    # Step 5: Create IAM roles if they don't exist
    Write-Host "Step 5: Setting up IAM Roles..." -ForegroundColor Yellow
    
    # Check if execution role exists
    $ExistingExecutionRole = aws iam get-role --role-name ecsTaskExecutionRole 2>$null
    if ($LASTEXITCODE -ne 0) {
        # Create execution role
        $TrustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@
        $TrustPolicy | Out-File -FilePath "trust-policy-temp.json" -Encoding UTF8
        aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document file://trust-policy-temp.json
        aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
        Remove-Item "trust-policy-temp.json"
        Write-Host "ECS Task Execution Role created" -ForegroundColor Green
    } else {
        Write-Host "ECS Task Execution Role already exists" -ForegroundColor Green
    }

    # Check if task role exists
    $ExistingTaskRole = aws iam get-role --role-name counsel-task-role 2>$null
    if ($LASTEXITCODE -ne 0) {
        # Create task role
        $TrustPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
"@
        $TaskPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": "*"
    }
  ]
}
"@
        $TrustPolicy | Out-File -FilePath "trust-policy-temp.json" -Encoding UTF8
        $TaskPolicy | Out-File -FilePath "task-policy-temp.json" -Encoding UTF8
        
        aws iam create-role --role-name counsel-task-role --assume-role-policy-document file://trust-policy-temp.json
        aws iam put-role-policy --role-name counsel-task-role --policy-name counsel-task-policy --policy-document file://task-policy-temp.json
        
        Remove-Item "trust-policy-temp.json"
        Remove-Item "task-policy-temp.json"
        Write-Host "Counsel Task Role created" -ForegroundColor Green
    } else {
        Write-Host "Counsel Task Role already exists" -ForegroundColor Green
    }

    # Step 6: Register Task Definition
    Write-Host "Step 6: Registering Task Definition..." -ForegroundColor Yellow
    
    # Create a simple task definition
    $TaskDef = @"
{
  "family": "counsel-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$AccountId:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$AccountId:role/counsel-task-role",
  "containerDefinitions": [
    {
      "name": "counsel-container",
      "image": "$AccountId.dkr.ecr.$Region.amazonaws.com/counsel-ai:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/counsel-task",
          "awslogs-region": "$Region",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "DEBUG",
          "value": "false"
        },
        {
          "name": "AWS_REGION",
          "value": "$Region"
        },
        {
          "name": "AWS_BEDROCK_MODEL_ID_PRIMARY",
          "value": "us.anthropic.claude-sonnet-4-20250514-v1:0"
        },
        {
          "name": "AWS_BEDROCK_MODEL_ID_SECONDARY",
          "value": "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        },
        {
          "name": "AWS_BEDROCK_MODEL_ID_FALLBACK",
          "value": "mistral.mistral-7b-instruct-v0:2"
        },
        {
          "name": "ALLOWED_ORIGINS",
          "value": "https://www.legalizeme.site,https://legalizeme.site"
        },
        {
          "name": "AWS_ACCESS_KEY_ID",
          "value": "YOUR_AWS_ACCESS_KEY_ID"
        },
        {
          "name": "AWS_SECRET_ACCESS_KEY",
          "value": "YOUR_AWS_SECRET_ACCESS_KEY"
        },
        {
          "name": "SECRET_KEY",
          "value": "YOUR_SECRET_KEY_FOR_JWT"
        }
      ],
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health/live || exit 1"
        ],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
"@

    $TaskDef | Out-File -FilePath "simple-task-definition.json" -Encoding UTF8
    aws ecs register-task-definition --cli-input-json file://simple-task-definition.json
    Remove-Item "simple-task-definition.json"
    
    Write-Host "Task Definition registered successfully" -ForegroundColor Green

    # Step 7: Get default VPC and subnets
    Write-Host "Step 7: Getting VPC information..." -ForegroundColor Yellow
    
    $DefaultVpc = aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text
    $DefaultSubnets = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$DefaultVpc" --query "Subnets[0:2].SubnetId" --output text
    $SubnetArray = $DefaultSubnets.Split("`t")
    
    Write-Host "Using default VPC: $DefaultVpc" -ForegroundColor Green
    Write-Host "Using subnets: $($SubnetArray -join ', ')" -ForegroundColor Green

    # Step 8: Create security group
    Write-Host "Step 8: Creating Security Group..." -ForegroundColor Yellow
    
    $ExistingSG = aws ec2 describe-security-groups --filters "Name=group-name,Values=counsel-ecs-sg" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $SGResult = aws ec2 create-security-group --group-name counsel-ecs-sg --description "Security group for Counsel ECS tasks" --vpc-id $DefaultVpc | ConvertFrom-Json
        $SecurityGroupId = $SGResult.GroupId
        
        # Allow HTTP traffic
        aws ec2 authorize-security-group-ingress --group-id $SecurityGroupId --protocol tcp --port 8000 --cidr 0.0.0.0/0
        
        Write-Host "Security Group created: $SecurityGroupId" -ForegroundColor Green
    } else {
        $SecurityGroupId = aws ec2 describe-security-groups --filters "Name=group-name,Values=counsel-ecs-sg" --query "SecurityGroups[0].GroupId" --output text
        Write-Host "Security Group already exists: $SecurityGroupId" -ForegroundColor Green
    }

    # Step 9: Create ECS Service
    Write-Host "Step 9: Creating ECS Service..." -ForegroundColor Yellow
    
    $ServiceConfig = @"
{
  "serviceName": "$ServiceName",
  "cluster": "$ClusterName",
  "taskDefinition": "counsel-task",
  "desiredCount": 1,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["$($SubnetArray[0])", "$($SubnetArray[1])"],
      "securityGroups": ["$SecurityGroupId"],
      "assignPublicIp": "ENABLED"
    }
  }
}
"@

    $ServiceConfig | Out-File -FilePath "simple-service-config.json" -Encoding UTF8
    aws ecs create-service --cli-input-json file://simple-service-config.json
    Remove-Item "simple-service-config.json"
    
    Write-Host "ECS Service created successfully" -ForegroundColor Green

    # Output summary
    Write-Host ""
    Write-Host "Deployment Complete!" -ForegroundColor Green
    Write-Host "===================" -ForegroundColor Cyan
    Write-Host "ECS Cluster: $ClusterName" -ForegroundColor White
    Write-Host "ECS Service: $ServiceName" -ForegroundColor White
    Write-Host "Security Group: $SecurityGroupId" -ForegroundColor White
    Write-Host ""
    Write-Host "To get the public IP of your service:" -ForegroundColor Yellow
    Write-Host "aws ecs describe-tasks --cluster $ClusterName --tasks `$(aws ecs list-tasks --cluster $ClusterName --service-name $ServiceName --query 'taskArns[0]' --output text) --query 'tasks[0].attachments[0].details[?name==``networkInterfaceId``].value' --output text | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} --query 'NetworkInterfaces[0].Association.PublicIp' --output text" -ForegroundColor Cyan

}
catch {
    Write-Host "Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Simple Infrastructure Deployment Complete!" -ForegroundColor Green
